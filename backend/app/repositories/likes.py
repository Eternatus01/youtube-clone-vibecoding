from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Like


async def get(db: AsyncSession, video_id: str, user_id: str) -> Like | None:
    result = await db.execute(
        select(Like).where(Like.video_id == video_id, Like.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession, *, video_id: str, user_id: str, is_like: bool = True
) -> Like:
    like = Like(video_id=video_id, user_id=user_id, is_like=is_like)
    db.add(like)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent insert won the unique constraint; reuse that row.
        await db.rollback()
        existing = await get(db, video_id, user_id)
        if existing is None:
            raise
        return existing
    await db.refresh(like)
    return like


async def save(db: AsyncSession, like: Like) -> Like:
    await db.commit()
    await db.refresh(like)
    return like


async def delete_like(db: AsyncSession, like: Like) -> None:
    await db.delete(like)
    await db.commit()