from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import PaginatedResponse, SubscriptionOut

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("/{channel_id}", response_model=dict)
async def get_channel(channel_id: str, current_user=Depends(get_current_user_optional)):
    raise NotImplementedError


@router.get("/{channel_id}/videos", response_model=PaginatedResponse)
async def channel_videos(
    channel_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user_optional),
):
    raise NotImplementedError


@router.post("/{channel_id}/subscribe", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def subscribe(channel_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.delete("/{channel_id}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(channel_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.get("/{channel_id}/subscribers/count")
async def subscriber_count(channel_id: str):
    raise NotImplementedError