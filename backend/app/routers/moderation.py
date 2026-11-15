from fastapi import APIRouter, Depends, status

from app.dependencies.auth import require_moderator
from app.schemas.schemas import ModerationActionOut, ModerationResolve, PaginatedResponse, ReportOut

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


@router.get("/reports", response_model=PaginatedResponse)
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    moderator=Depends(require_moderator),
):
    raise NotImplementedError


@router.post("/resolve", response_model=ModerationActionOut)
async def resolve_report(body: ModerationResolve, moderator=Depends(require_moderator)):
    raise NotImplementedError


@router.get("/actions", response_model=PaginatedResponse)
async def list_actions(
    page: int = 1,
    page_size: int = 20,
    moderator=Depends(require_moderator),
):
    raise NotImplementedError