from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Subscription, User, Video, VideoStatus, Visibility


async def list_subscribed_channels(
    db: AsyncSession, user_id: str, offset: int, limit: int
) -> tuple[list[Subscription], int]:
    conditions = (Subscription.subscriber_id == user_id,)

    total = await db.scalar(select(func.count(Subscription.id)).where(*conditions))
    result = await db.execute(
        select(Subscription)
        .join(User, User.id == Subscription.channel_id)
        .options(selectinload(Subscription.channel))
        .where(*conditions)
        .order_by(User.username.asc(), Subscription.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def get_subscription_feed(
    db: AsyncSession, user_id: str, offset: int, limit: int
) -> tuple[list[Video], int]:
    channel_ids = select(Subscription.channel_id).where(
        Subscription.subscriber_id == user_id
    )
    conditions = (
        Video.owner_id.in_(channel_ids),
        Video.status == VideoStatus.ready,
        Video.visibility == Visibility.public,
    )

    total = await db.scalar(select(func.count(Video.id)).where(*conditions))
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.owner), selectinload(Video.shares))
        .where(*conditions)
        .order_by(Video.created_at.desc(), Video.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)
