import math
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ModerationAction
from app.repositories import moderation as moderation_repo
from app.repositories import reports as reports_repo
from app.repositories import videos as videos_repo
from app.schemas.schemas import (
    ModerationActionOut,
    PaginatedResponse,
    UserOut,
)
from app.services import reports as reports_service

REPORT_STATUSES = ("open", "resolved", "dismissed")
ACTIONS = ("hide", "restore")


def _serialize_action(action: ModerationAction) -> ModerationActionOut:
    out = ModerationActionOut.model_validate(action)
    return out.model_copy(
        update={
            "moderator": (
                UserOut.model_validate(action.moderator)
                if action.moderator is not None
                else None
            )
        }
    )


async def list_reports(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status_filter: str | None,
    moderator,
) -> PaginatedResponse:
    if status_filter is not None and status_filter not in REPORT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
        )
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    reports, total = await reports_repo.list_paginated(
        db,
        status_filter=status_filter,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    items = await reports_service.serialize_reports(db, reports, moderator)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


async def resolve(
    db: AsyncSession, body, moderator
) -> ModerationActionOut:
    if body.action not in ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be hide or restore",
        )
    try:
        UUID(body.video_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )
    video = await videos_repo.get(db, body.video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )
    action = await moderation_repo.apply_action(
        db,
        video=video,
        action=body.action,
        reason=body.reason,
        moderator_id=moderator.id,
    )
    return _serialize_action(action)


async def list_actions(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
) -> PaginatedResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    actions, total = await moderation_repo.list_actions(
        db, offset=(page - 1) * page_size, limit=page_size
    )
    return PaginatedResponse(
        items=[_serialize_action(action) for action in actions],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )