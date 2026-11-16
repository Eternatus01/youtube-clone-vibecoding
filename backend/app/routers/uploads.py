from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.schemas.schemas import (
    PresignedUrlResponse,
    UploadCompleteRequest,
    VideoUploadInit,
)
from app.services import uploads as uploads_service

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/init", response_model=PresignedUrlResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(
    body: VideoUploadInit,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await uploads_service.init_upload(db, body, current_user)
    return PresignedUrlResponse(**payload)


@router.post("/complete", status_code=status.HTTP_200_OK)
async def complete_upload(
    body: UploadCompleteRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await uploads_service.complete_upload(db, body.upload_session_id, current_user)


@router.post("/{video_id}/poster", status_code=status.HTTP_200_OK)
async def upload_poster(
    video_id: str,
    poster: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a custom thumbnail for a video. Owner or moderator only."""
    return await uploads_service.set_video_poster(db, video_id, poster, current_user)