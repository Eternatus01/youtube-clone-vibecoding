from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.schemas.schemas import PaginatedResponse

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=PaginatedResponse)
async def list_subscriptions(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List channels the current user is subscribed to."""
    from app.services import subscriptions as subs_service

    return await subs_service.list_subscriptions(
        db, user=current_user, page=page, page_size=page_size
    )


@router.get("/feed", response_model=PaginatedResponse)
async def subscriptions_feed(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Feed of public ready videos from subscribed channels, newest first.
    Private, hidden, and processing videos never appear.
    """
    from app.services import subscriptions as subs_service

    return await subs_service.subscription_feed(
        db, user=current_user, page=page, page_size=page_size
    )