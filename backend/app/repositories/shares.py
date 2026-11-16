from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import VideoShare


async def get(db: AsyncSession, video_id: str, user_id: str) -> VideoShare | None:
    result = await db.execute(
        select(VideoShare).where(
            VideoShare.video_id == video_id, VideoShare.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_for_video(db: AsyncSession, video_id: str) -> list[VideoShare]:
    result = await db.execute(
        select(VideoShare)
        .options(selectinload(VideoShare.user))
        .where(VideoShare.video_id == video_id)
        .order_by(VideoShare.created_at.asc(), VideoShare.id.asc())
    )
    return list(result.scalars().all())


async def create(db: AsyncSession, *, video_id: str, user_id: str) -> VideoShare:
    share = VideoShare(video_id=video_id, user_id=user_id)
    db.add(share)
    await db.commit()
    result = await db.execute(
        select(VideoShare)
        .options(selectinload(VideoShare.user))
        .where(VideoShare.id == share.id)
    )
    return result.scalar_one()


async def delete(db: AsyncSession, share: VideoShare) -> None:
    await db.delete(share)
    await db.commit()