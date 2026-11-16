from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Report, Video


def _with_relations():
    return (
        selectinload(Report.reporter),
        selectinload(Report.video).selectinload(Video.owner),
    )


async def get(db: AsyncSession, report_id: str) -> Report | None:
    result = await db.execute(
        select(Report).options(*_with_relations()).where(Report.id == report_id)
    )
    return result.scalar_one_or_none()


async def get_by_video_reporter(
    db: AsyncSession, video_id: str, reporter_id: str
) -> Report | None:
    result = await db.execute(
        select(Report).where(
            Report.video_id == video_id, Report.reporter_id == reporter_id
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession, *, video_id: str, reporter_id: str, reason: str
) -> Report:
    report = Report(video_id=video_id, reporter_id=reporter_id, reason=reason)
    db.add(report)
    await db.commit()
    return await get(db, report.id)


async def list_by_reporter(db: AsyncSession, reporter_id: str) -> list[Report]:
    result = await db.execute(
        select(Report)
        .options(*_with_relations())
        .where(Report.reporter_id == reporter_id)
        .order_by(Report.created_at.desc(), Report.id.desc())
    )
    return list(result.scalars().all())


async def list_paginated(
    db: AsyncSession,
    *,
    status_filter: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Report], int]:
    conditions = []
    if status_filter:
        conditions.append(Report.status == status_filter)
    total = await db.scalar(select(func.count(Report.id)).where(*conditions))
    result = await db.execute(
        select(Report)
        .options(*_with_relations())
        .where(*conditions)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)