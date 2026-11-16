from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Report
from app.repositories import reports as reports_repo
from app.repositories import videos as videos_repo
from app.schemas.schemas import ReportOut, UserOut
from app.services import videos as videos_service


def _valid_id(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


async def serialize_reports(db: AsyncSession, reports: list[Report], viewer) -> list[ReportOut]:
    videos = [report.video for report in reports if report.video is not None]
    serialized = await videos_service.serialize_videos(db, videos, viewer)
    by_id = {video.id: video for video in serialized}
    items: list[ReportOut] = []
    for report in reports:
        out = ReportOut.model_validate(report)
        items.append(
            out.model_copy(
                update={
                    "reporter": (
                        UserOut.model_validate(report.reporter)
                        if report.reporter is not None
                        else None
                    ),
                    "video": by_id.get(report.video_id),
                }
            )
        )
    return items


async def create_report(db: AsyncSession, body, user) -> ReportOut:
    if not _valid_id(body.video_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Video not found"
        )
    video = await videos_repo.get(db, body.video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Video not found"
        )
    if video.owner_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot report your own video",
        )
    existing = await reports_repo.get_by_video_reporter(db, video.id, user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Video already reported"
        )
    report = await reports_repo.create(
        db, video_id=video.id, reporter_id=user.id, reason=body.reason
    )
    return (await serialize_reports(db, [report], user))[0]


async def list_mine(db: AsyncSession, user) -> list[ReportOut]:
    reports = await reports_repo.list_by_reporter(db, user.id)
    return await serialize_reports(db, reports, user)