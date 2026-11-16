from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.schemas import (
    CommentCreate,
    CommentOut,
    CommentUpdate,
    PaginatedResponse,
)
from app.services import comments as comments_service

router = APIRouter(prefix="/api/videos/{video_id}/comments", tags=["comments"])


@router.get("/", response_model=PaginatedResponse)
async def list_comments(
    video_id: str,
    page: int = 1,
    page_size: int = 20,
    sort: str = "newest",
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    return await comments_service.list_comments(
        db,
        video_id,
        page=page,
        page_size=page_size,
        sort=sort,
        user=current_user,
    )


@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    video_id: str,
    body: CommentCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await comments_service.create_comment(db, video_id, body, current_user)


@router.patch("/{comment_id}", response_model=CommentOut)
async def update_comment(
    video_id: str,
    comment_id: str,
    body: CommentUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await comments_service.update_comment(
        db, video_id, comment_id, body, current_user
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    video_id: str,
    comment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await comments_service.delete_comment(db, video_id, comment_id, current_user)