import math

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import channels as channels_repo
from app.repositories import videos as videos_repo
from app.schemas.schemas import (
    ChannelOut,
    PaginatedResponse,
    SubscriptionOut,
    UserOut,
)
from app.services import playlists as playlists_service
from app.services import videos as videos_service


async def _get_channel(db: AsyncSession, channel_id: str):
    channel = await channels_repo.get(db, channel_id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
        )
    return channel


async def get_channel(db: AsyncSession, channel_id: str, user) -> ChannelOut:
    channel = await _get_channel(db, channel_id)
    subscriber_count = await channels_repo.subscriber_count(db, channel.id)
    is_subscribed = (
        await channels_repo.is_subscribed(db, user.id, channel.id)
        if user is not None
        else None
    )
    out = ChannelOut.model_validate(channel)
    return out.model_copy(
        update={
            "subscriber_count": subscriber_count,
            "video_count": await channels_repo.video_count(db, channel.id),
            "is_subscribed": is_subscribed,
        }
    )


async def list_channel_videos(
    db: AsyncSession,
    channel_id: str,
    *,
    page: int,
    page_size: int,
    user,
) -> PaginatedResponse:
    channel = await _get_channel(db, channel_id)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    videos, total = await videos_repo.list_by_owner(
        db, channel.id, offset=(page - 1) * page_size, limit=page_size
    )
    return PaginatedResponse(
        items=await videos_service.serialize_videos(db, videos, user),
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def list_channel_playlists(
    db: AsyncSession,
    channel_id: str,
    *,
    page: int,
    page_size: int,
) -> PaginatedResponse:
    channel = await _get_channel(db, channel_id)
    items, total, page, page_size = await playlists_service.list_channel_playlists(
        db, channel.id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def subscribe(db: AsyncSession, channel_id: str, user) -> SubscriptionOut:
    channel = await _get_channel(db, channel_id)
    if channel.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot subscribe to your own channel",
        )
    # Build the nested UserOut before any commit/rollback can expire `channel`.
    channel_out = UserOut.model_validate(channel)
    subscription = await channels_repo.create_subscription(
        db, subscriber_id=user.id, channel_id=channel.id
    )
    return SubscriptionOut(
        id=subscription.id,
        channel_id=subscription.channel_id,
        created_at=subscription.created_at,
        channel=channel_out,
    )


async def unsubscribe(db: AsyncSession, channel_id: str, user) -> None:
    channel = await _get_channel(db, channel_id)
    subscription = await channels_repo.get_subscription(db, user.id, channel.id)
    # Unsubscribing when not subscribed is a no-op, so the call stays idempotent.
    if subscription is not None:
        await channels_repo.delete_subscription(db, subscription)


async def subscriber_count(db: AsyncSession, channel_id: str) -> dict[str, int]:
    channel = await _get_channel(db, channel_id)
    return {"count": await channels_repo.subscriber_count(db, channel.id)}