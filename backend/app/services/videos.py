import math

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.s3_client import get_s3_client
from app.models.models import (
    Role,
    UploadSession,
    Video,
    VideoAsset,
    Visibility,
)
from app.repositories import videos as videos_repo
from app.schemas.schemas import PaginatedResponse, UserOut, VideoOut

MODERATOR_ROLES = (Role.moderator, Role.admin)


def is_moderator(user) -> bool:
    return user is not None and user.role in MODERATOR_ROLES


def is_admin(user) -> bool:
    return user is not None and user.role == Role.admin


def ensure_can_view(video: Video, user) -> None:
    """Enforce visibility rules for a single video or its media."""
    if video.visibility == Visibility.hidden:
        if not is_moderator(user):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
        return
    if video.visibility != Visibility.public:
        if user is None or (video.owner_id != user.id and not is_moderator(user)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def ensure_can_edit(video: Video, user) -> None:
    if video.owner_id != user.id and not is_moderator(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def ensure_can_delete(video: Video, user) -> None:
    if video.owner_id != user.id and not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def serialize_videos(db: AsyncSession, videos: list[Video], user) -> list[VideoOut]:
    ids = [v.id for v in videos]
    counts = await videos_repo.like_counts(db, ids)
    comments = await videos_repo.comment_counts(db, ids)
    liked = (
        await videos_repo.user_likes(db, user.id, ids) if user is not None else {}
    )
    result: list[VideoOut] = []
    for video in videos:
        like_bucket = counts.get(video.id, {})
        out = VideoOut.model_validate(video)
        result.append(
            out.model_copy(
                update={
                    "owner": UserOut.model_validate(video.owner),
                    "like_count": like_bucket.get("like", 0),
                    "dislike_count": like_bucket.get("dislike", 0),
                    "comment_count": comments.get(video.id, 0),
                    "user_like": liked.get(video.id),
                }
            )
        )
    return result


async def serialize_video(db: AsyncSession, video: Video, user) -> VideoOut:
    return (await serialize_videos(db, [video], user))[0]


async def list_feed(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    user,
) -> PaginatedResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    videos, total = await videos_repo.get_feed(
        db, search=search, offset=(page - 1) * page_size, limit=page_size
    )
    items = await serialize_videos(db, videos, user)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def get_video(db: AsyncSession, video_id: str, user) -> Video:
    video = await videos_repo.get(db, video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    ensure_can_view(video, user)
    return video


async def register_view(db: AsyncSession, video: Video, user) -> None:
    """Count a view unless the owner is watching their own video."""
    if user is not None and video.owner_id == user.id:
        return
    await videos_repo.increment_views(db, video.id)
    # increment_views commits, expiring `video`; re-read the committed row so
    # the serialized views value is exact (no double-count).
    await db.refresh(video)


async def list_related(
    db: AsyncSession,
    video: Video,
    *,
    page: int,
    page_size: int,
    user,
) -> PaginatedResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    videos, total = await videos_repo.list_related(
        db,
        video_id=video.id,
        owner_id=video.owner_id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    items = await serialize_videos(db, videos, user)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def get_assets(db: AsyncSession, video_id: str) -> list[VideoAsset]:
    result = await db.execute(
        select(VideoAsset).where(VideoAsset.video_id == video_id)
    )
    return list(result.scalars().all())


def _quality_height(quality: str) -> int:
    try:
        return int(quality.lower().rstrip("p"))
    except ValueError:
        return -1


def choose_stream_asset(assets: list[VideoAsset], quality: str | None) -> VideoAsset:
    candidates = [a for a in assets if a.quality != "poster"]
    if quality:
        for asset in candidates:
            if asset.quality.lower() == quality.lower():
                return asset
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality not available")
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No media available")
    return max(candidates, key=lambda a: _quality_height(a.quality))


def choose_poster_asset(assets: list[VideoAsset]) -> VideoAsset:
    for asset in assets:
        if asset.quality == "poster":
            return asset
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poster not available")


async def update_video(db: AsyncSession, video: Video, body, user) -> VideoOut:
    ensure_can_edit(video, user)
    if body.title is not None:
        video.title = body.title
    if body.description is not None:
        video.description = body.description
    if body.visibility is not None:
        try:
            video.visibility = Visibility(body.visibility)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visibility"
            )
    await videos_repo.save(db, video)
    return await serialize_video(db, video, user)


async def delete_video(db: AsyncSession, video: Video, user) -> None:
    ensure_can_delete(video, user)
    assets = await get_assets(db, video.id)
    sessions = await db.execute(
        select(UploadSession).where(UploadSession.video_id == video.id)
    )
    keys = {a.object_key for a in assets}
    keys.update(s.object_key for s in sessions.scalars().all())

    await db.delete(video)
    await db.commit()

    if keys:
        s3 = get_s3_client()
        try:
            await run_in_threadpool(
                s3.delete_objects,
                Bucket=settings.s3_bucket,
                Delete={"Objects": [{"Key": k} for k in keys]},
            )
        except Exception:
            # Media cleanup is best-effort; the database rows are already gone.
            pass


async def open_media(key: str, range_header: str | None) -> dict:
    s3 = get_s3_client()
    params = {"Bucket": settings.s3_bucket, "Key": key}
    if range_header:
        params["Range"] = range_header
    try:
        obj = await run_in_threadpool(s3.get_object, **params)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media object not found"
        )
    return obj