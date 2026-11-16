from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


async def get(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
) -> tuple[list[User], int]:
    total = await db.scalar(select(func.count(User.id)))
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def save(db: AsyncSession, user: User) -> User:
    await db.commit()
    await db.refresh(user)
    return user