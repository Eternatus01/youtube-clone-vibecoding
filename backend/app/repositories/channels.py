from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Subscription, User, Video, VideoStatus, Visibility


async def get(db: AsyncSession, channel_id: str) -> User | None:
    result = await db.execute(
        select(User).where(User.id == channel_id, User.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def subscriber_count(db: AsyncSession, channel_id: str) -> int:
    total = await db.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.channel_id == channel_id
        )
    )
    return int(total or 0)


async def video_count(db: AsyncSession, channel_id: str) -> int:
    total = await db.scalar(
        select(func.count(Video.id)).where(
            Video.owner_id == channel_id,
            Video.status == VideoStatus.ready,
            Video.visibility == Visibility.public,
        )
    )
    return int(total or 0)





async def get_subscription(
    db: AsyncSession, subscriber_id: str, channel_id: str
) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(
            Subscription.subscriber_id == subscriber_id,
            Subscription.channel_id == channel_id,
        )
    )
    return result.scalar_one_or_none()


async def is_subscribed(db: AsyncSession, subscriber_id: str, channel_id: str) -> bool:
    existing = await get_subscription(db, subscriber_id, channel_id)
    return existing is not None


async def create_subscription(
    db: AsyncSession, *, subscriber_id: str, channel_id: str
) -> Subscription:
    subscription = Subscription(subscriber_id=subscriber_id, channel_id=channel_id)
    db.add(subscription)
    try:
        await db.commit()
    except IntegrityError:
        # Already subscribed: keep the operation idempotent.
        await db.rollback()
        existing = await get_subscription(db, subscriber_id, channel_id)
        if existing is None:
            raise
        return existing
    await db.refresh(subscription)
    return subscription


async def delete_subscription(db: AsyncSession, subscription: Subscription) -> None:
    await db.delete(subscription)
    await db.commit()