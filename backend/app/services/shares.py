"""Video share management (owner grants view access to private videos)."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Video, VideoShare
from app.repositories import shares as shares_repo
from app.repositories import users as users_repo
from app.schemas.schemas import UserOut, VideoShareOut
from app.services import videos as videos_service


def _serialize(share: VideoShare) -> VideoShareOut:
    out = VideoShareOut.model_validate(share)
    return out.model_copy(
        update={
            "user": (
                UserOut.model_validate(share.user) if share.user is not None else None
            )
        }
    )


def _ensure_owner(video: Video, user) -> None:
    if video.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner only"
        )


async def list_shares(db: AsyncSession, video: Video, user) -> list[VideoShareOut]:
    if video.owner_id != user.id and not videos_service.is_moderator(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    shares = await shares_repo.list_for_video(db, video.id)
    return [_serialize(share) for share in shares]


async def add_share(db: AsyncSession, video: Video, body, user) -> VideoShareOut:
    _ensure_owner(video, user)
    target = await users_repo.get_by_username(db, body.username)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if target.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share a video with yourself",
        )
    existing = await shares_repo.get(db, video.id, target.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video already shared with this user",
        )
    share = await shares_repo.create(db, video_id=video.id, user_id=target.id)
    return _serialize(share)


async def remove_share(db: AsyncSession, video: Video, user_id: str, user) -> None:
    _ensure_owner(video, user)
    try:
        UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )
    share = await shares_repo.get(db, video.id, user_id)
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )
    await shares_repo.delete(db, share)