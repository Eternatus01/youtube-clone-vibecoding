from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.schemas.schemas import HistoryRecordRequest, PaginatedResponse

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/", response_model=PaginatedResponse)
async def list_history(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated watch history, newest first.
    Excludes videos the current user can no longer access.
    """
    from app.services import history as history_service

    return await history_service.list_history(
        db, user=current_user, page=page, page_size=page_size
    )


@router.post("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def record_history(
    video_id: str,
    body: HistoryRecordRequest | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record or update watch history for a video.
    Ignores if the user is the video owner or cannot access it.
    """
    from app.services import history as history_service

    await history_service.record_history(
        db,
        user=current_user,
        video_id=video_id,
        progress_seconds=body.progress_seconds if body else None,
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_history_item(
    video_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a single video from watch history."""
    from app.services import history as history_service

    await history_service.remove_history_item(db, user=current_user, video_id=video_id)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all watch history for the current user."""
    from app.services import history as history_service

    await history_service.clear_history(db, user=current_user)