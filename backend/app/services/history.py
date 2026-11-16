import math

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Role, Video, Visibility
from app.repositories import history as history_repo
from app.repositories import videos as videos_repo
from app.schemas.schemas import PaginatedResponse, WatchHistoryOut
from app.services import videos as videos_service

MODERATOR_ROLES = (Role.moderator, Role.admin)


def _clamp(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


def _is_visible_to(video: Video, user) -> bool:
    """Mirror of ensure_can_view, but non-raising for list filtering."""
    if video.visibility == Visibility.hidden:
        return user is not None and user.role in MODERATOR_ROLES
    if video.visibility in (Visibility.public, Visibility.unlisted):
        return True
    if user is not None:
        if video.owner_id == user.id:
            return True
        if video.role in MODERATOR_ROLES:
            return True
        shares = video.__dict__.get("shares") or []
        return any(share.user_id == user.id for share in shares)
    return False


async def list_history(
    db: AsyncSession, *, user, page: int, page_size: int
) -> PaginatedResponse:
    page, page_size = _clamp(page, page_size)
    items, total = await history_repo.get_user_history(
        db, user.id, offset=(page - 1) * page_size, limit=page_size
    )

    # Safety filter: the query already drops hidden videos; re-check each entry
    # so entries the user may no longer access are never exposed.
    visible = [entry for entry in items if _is_visible_to(entry.video, user)]

    video_out = await videos_service.serialize_videos(
        db, [entry.video for entry in visible], user
    )
    out_items = [
        WatchHistoryOut(
            id=entry.id,
            video_id=entry.video_id,
            progress_seconds=entry.progress_seconds,
            last_watched_at=entry.last_watched_at,
            video=video,
        )
        for entry, video in zip(visible, video_out)
    ]
    return PaginatedResponse(
        items=out_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def record_history(
    db: AsyncSession, *, user, video_id: str, progress_seconds: int | None
) -> None:
    video = await videos_repo.get(db, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )
    videos_service.ensure_can_view(video, user)
    # Owners do not build watch history on their own videos.
    if video.owner_id == user.id:
        return
    await history_repo.upsert_history(db, user.id, video.id, progress_seconds)


async def remove_history_item(db: AsyncSession, *, user, video_id: str) -> None:
    await history_repo.delete_history_item(db, user.id, video_id)


async def clear_history(db: AsyncSession, *, user) -> None:
    await history_repo.delete_all_history(db, user.id)
