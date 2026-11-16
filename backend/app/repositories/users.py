from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


async def get_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_many(db: AsyncSession, user_ids: list[str]) -> list[User]:
    if not user_ids:
        return []
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return list(result.scalars().all())


async def get_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    )
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    return result.scalar_one_or_none()


async def get_by_login(db: AsyncSession, login: str) -> User | None:
    value = login.lower()
    result = await db.execute(
        select(User).where(
            or_(func.lower(User.username) == value, func.lower(User.email) == value)
        )
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, **fields) -> User:
    user = User(**fields)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user