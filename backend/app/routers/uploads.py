from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.schemas.schemas import (
    PresignedUrlResponse,
    UploadCompleteRequest,
    VideoUploadInit,
)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/init", response_model=PresignedUrlResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(body: VideoUploadInit, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.post("/complete", status_code=status.HTTP_200_OK)
async def complete_upload(body: UploadCompleteRequest, current_user=Depends(get_current_user)):
    raise NotImplementedError