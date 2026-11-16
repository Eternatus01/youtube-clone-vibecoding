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


async def like_video(db: AsyncSession, video_id: str, user) -> LikeInfo:
    video = await videos_service.get_video(db, video_id, user)
    _ensure_likeable(video)
    like = await likes_repo.get(db, video.id, user.id)
    if like is None:
        await likes_repo.create(db, video_id=video.id, user_id=user.id)
    elif not like.is_like:
        like.is_like = True
        await likes_repo.save(db, like)
    return LikeInfo(liked=True)


async def unlike_video(db: AsyncSession, video_id: str, user) -> LikeInfo:
    video = await videos_service.get_video(db, video_id, user)
    like = await likes_repo.get(db, video.id, user.id)
    if like is not None:
        await likes_repo.delete_like(db, like)
    return LikeInfo(liked=False)