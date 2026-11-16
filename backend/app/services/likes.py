from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Video, VideoStatus
from app.repositories import likes as likes_repo
from app.schemas.schemas import LikeInfo
from app.services import videos as videos_service


def _ensure_likeable(video: Video) -> None:
    if video.status != VideoStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Video is not ready"
        )


async def _set_reaction(
    db: AsyncSession, video_id: str, user, *, is_like: bool
) -> LikeInfo:
    video = await videos_service.get_video(db, video_id, user)
    _ensure_likeable(video)
    like = await likes_repo.get(db, video.id, user.id)
    if like is None:
        created = await likes_repo.create(
            db, video_id=video.id, user_id=user.id, is_like=is_like
        )
        # A concurrent insert may have won the unique constraint with the
        # opposite reaction; reconcile so the stored row matches the request.
        if created.is_like != is_like:
            created.is_like = is_like
            await likes_repo.save(db, created)
    elif like.is_like != is_like:
        like.is_like = is_like
        await likes_repo.save(db, like)
    return LikeInfo(like_status="like" if is_like else "dislike")


async def _clear_reaction(db: AsyncSession, video_id: str, user) -> LikeInfo:
    video = await videos_service.get_video(db, video_id, user)
    like = await likes_repo.get(db, video.id, user.id)
    if like is not None:
        await likes_repo.delete_like(db, like)
    return LikeInfo(like_status=None)


async def like_video(db: AsyncSession, video_id: str, user) -> LikeInfo:
    return await _set_reaction(db, video_id, user, is_like=True)


async def dislike_video(db: AsyncSession, video_id: str, user) -> LikeInfo:
    return await _set_reaction(db, video_id, user, is_like=False)


async def unlike_video(db: AsyncSession, video_id: str, user) -> LikeInfo:
    return await _clear_reaction(db, video_id, user)


async def undislike_video(db: AsyncSession, video_id: str, user) -> LikeInfo:
    return await _clear_reaction(db, video_id, user)