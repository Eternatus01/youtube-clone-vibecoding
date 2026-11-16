from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Job, JobStatus, JobType, UploadSession


async def get_upload_session(
    db: AsyncSession, session_id: str, user_id: str
) -> UploadSession | None:
    result = await db.execute(
        select(UploadSession).where(
            UploadSession.id == session_id, UploadSession.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def upload_sessions_for_video(
    db: AsyncSession, video_id: str
) -> list[UploadSession]:
    result = await db.execute(
        select(UploadSession).where(UploadSession.video_id == video_id)
    )
    return list(result.scalars().all())


async def create_transcode_job(
    db: AsyncSession,
    *,
    session: UploadSession,
    video_id: str,
) -> Job:
    job = Job(
        type=JobType.transcode,
        status=JobStatus.pending,
        payload={
            "video_id": video_id,
            "object_key": session.object_key,
            "content_type": session.content_type,
            "session_id": session.id,
        },
    )
    db.add(job)
    await db.flush()
    return job