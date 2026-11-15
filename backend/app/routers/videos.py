from fastapi import APIRouter, Depends, Response, status

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import (
    LikeInfo,
    PaginatedResponse,
    VideoOut,
    VideoUpdate,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("/", response_model=PaginatedResponse)
async def list_videos(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    current_user=Depends(get_current_user_optional),
):
    raise NotImplementedError


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(video_id: str, current_user=Depends(get_current_user_optional)):
    raise NotImplementedError


@router.patch("/{video_id}", response_model=VideoOut)
async def update_video(video_id: str, body: VideoUpdate, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(video_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.get("/{video_id}/stream")
async def stream_video(video_id: str, response: Response, quality: str | None = None):
    """Proxies a range request to MinIO for the video asset."""
    raise NotImplementedError


@router.post("/{video_id}/like", response_model=LikeInfo)
async def like_video(video_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.delete("/{video_id}/like", response_model=LikeInfo)
async def unlike_video(video_id: str, current_user=Depends(get_current_user)):
    raise NotImplementedError