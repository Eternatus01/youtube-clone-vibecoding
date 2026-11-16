from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Subscription, User, Video, VideoStatus, Visibility


async def search_videos(
    db: AsyncSession,
    pattern: str,
    *,
    offset: int,
    limit: int,
) -> list[Video]:
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.owner))
        .where(
            Video.status == VideoStatus.ready,
            Video.visibility == Visibility.public,
            Video.title.ilike(pattern, escape="\\"),
        )
        .order_by(Video.created_at.desc(), Video.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def search_channels(
    db: AsyncSession,
    pattern: str,
    *,
    offset: int,
    limit: int,
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(
            User.is_active == True,  # noqa: E712
            User.username.ilike(pattern, escape="\\"),
        )
        .order_by(User.username.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def subscriber_counts(
    db: AsyncSession, channel_ids: list[str]
) -> dict[str, int]:
    if not channel_ids:
        return {}
    result = await db.execute(
        select(Subscription.channel_id, func.count(Subscription.id))
        .where(Subscription.channel_id.in_(channel_ids))
        .group_by(Subscription.channel_id)
    )
    return {channel_id: int(count) for channel_id, count in result.all()}