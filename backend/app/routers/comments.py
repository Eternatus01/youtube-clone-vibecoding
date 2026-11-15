from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import (
    CommentCreate,
    CommentOut,
    CommentUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/videos/{video_id}/comments", tags=["comments"])


@router.get("/", response_model=PaginatedResponse)
async def list_comments(
    video_id: str,
    page: int = 1,
    page_size: int = 20,
    sort: str = "newest",
    current_user=Depends(get_current_user_optional),
):
    raise NotImplementedError


@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    video_id: str,
    body: CommentCreate,
    current_user=Depends(get_current_user),
):
    raise NotImplementedError


@router.patch("/{comment_id}", response_model=CommentOut)
async def update_comment(
    video_id: str,
    comment_id: str,
    body: CommentUpdate,
    current_user=Depends(get_current_user),
):
    raise NotImplementedError


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    video_id: str,
    comment_id: str,
    current_user=Depends(get_current_user),
):
    raise NotImplementedError