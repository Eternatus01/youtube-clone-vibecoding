import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import subscriptions as subs_repo
from app.schemas.schemas import PaginatedResponse, SubscriptionOut, UserOut
from app.services import videos as videos_service


def _clamp(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


async def list_subscriptions(
    db: AsyncSession, *, user, page: int, page_size: int
) -> PaginatedResponse:
    page, page_size = _clamp(page, page_size)
    subscriptions, total = await subs_repo.list_subscribed_channels(
        db, user.id, offset=(page - 1) * page_size, limit=page_size
    )
    items = [
        SubscriptionOut(
            id=sub.id,
            channel_id=sub.channel_id,
            created_at=sub.created_at,
            channel=UserOut.model_validate(sub.channel) if sub.channel else None,
        )
        for sub in subscriptions
    ]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def subscription_feed(
    db: AsyncSession, *, user, page: int, page_size: int
) -> PaginatedResponse:
    page, page_size = _clamp(page, page_size)
    videos, total = await subs_repo.get_subscription_feed(
        db, user.id, offset=(page - 1) * page_size, limit=page_size
    )
    items = await videos_service.serialize_videos(db, videos, user)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
