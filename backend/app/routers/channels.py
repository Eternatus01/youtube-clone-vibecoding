from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import ChannelOut, PaginatedResponse, SubscriptionOut
from app.services import channels as channels_service

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("/me", response_model=ChannelOut)
async def get_my_channel(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve the authenticated user's own channel."""
    return await channels_service.get_channel(db, current_user.id, current_user)


@router.get("/{channel_id}", response_model=ChannelOut)
async def get_channel(
    channel_id: str,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return await channels_service.get_channel(db, channel_id, current_user)


@router.get("/{channel_id}/videos", response_model=PaginatedResponse)
async def channel_videos(
    channel_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return await channels_service.list_channel_videos(
        db, channel_id, page=page, page_size=page_size, user=current_user
    )


@router.get("/{channel_id}/playlists", response_model=PaginatedResponse)
async def channel_playlists(
    channel_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return await channels_service.list_channel_playlists(
        db, channel_id, page=page, page_size=page_size
    )


@router.post("/{channel_id}/subscribe", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def subscribe(
    channel_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await channels_service.subscribe(db, channel_id, current_user)


@router.delete("/{channel_id}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    channel_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await channels_service.unsubscribe(db, channel_id, current_user)


@router.get("/{channel_id}/subscribers/count")
async def subscriber_count(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await channels_service.subscriber_count(db, channel_id)