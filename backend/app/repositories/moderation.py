from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import ModerationAction, Report, Video, Visibility


async def get(db: AsyncSession, action_id: str) -> ModerationAction | None:
    result = await db.execute(
        select(ModerationAction)
        .options(selectinload(ModerationAction.moderator))
        .where(ModerationAction.id == action_id)
    )
    return result.scalar_one_or_none()


async def list_actions(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
) -> tuple[list[ModerationAction], int]:
    total = await db.scalar(select(func.count(ModerationAction.id)))
    result = await db.execute(
        select(ModerationAction)
        .options(selectinload(ModerationAction.moderator))
        .order_by(ModerationAction.created_at.desc(), ModerationAction.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def apply_action(
    db: AsyncSession,
    *,
    video: Video,
    action: str,
    reason: str | None,
    moderator_id: str,
) -> ModerationAction:
    """Change visibility, resolve the video's open reports and log the action."""
    video.visibility = (
        Visibility.hidden if action == "hide" else Visibility.public
    )
    await db.execute(
        update(Report)
        .where(Report.video_id == video.id, Report.status == "open")
        .values(status="resolved")
    )
    row = ModerationAction(
        video_id=video.id,
        moderator_id=moderator_id,
        action=action,
        reason=reason,
    )
    db.add(row)
    await db.commit()
    return await get(db, row.id)