from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import require_moderator
from app.schemas.schemas import ModerationActionOut, ModerationResolve, PaginatedResponse
from app.services import moderation as moderation_service

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


@router.get("/reports", response_model=PaginatedResponse)
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    moderator=Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    return await moderation_service.list_reports(
        db,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        moderator=moderator,
    )


@router.post("/resolve", response_model=ModerationActionOut)
async def resolve_report(
    body: ModerationResolve,
    moderator=Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    return await moderation_service.resolve(db, body, moderator)


@router.get("/actions", response_model=PaginatedResponse)
async def list_actions(
    page: int = 1,
    page_size: int = 20,
    moderator=Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
):
    return await moderation_service.list_actions(
        db, page=page, page_size=page_size
    )