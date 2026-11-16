from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Job, JobStatus, JobType


async def claim_next_transcode(db: AsyncSession, worker_id: str) -> Job | None:
    """Atomically claim one pending transcode job (PostgreSQL SKIP LOCKED)."""
    result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.pending, Job.type == JobType.transcode)
        .order_by(Job.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None
    job.status = JobStatus.running
    job.locked_by = worker_id
    job.locked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


async def get(db: AsyncSession, job_id: str) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def mark_done(db: AsyncSession, job: Job) -> None:
    job.status = JobStatus.done
    job.error = None
    job.locked_by = None
    job.locked_at = None
    await db.commit()


async def mark_failed(
    db: AsyncSession, job: Job, error: str, *, max_attempts: int = 3
) -> None:
    job.attempts = (job.attempts or 0) + 1
    job.error = error[:2000]
    job.locked_by = None
    job.locked_at = None
    job.status = (
        JobStatus.failed if job.attempts >= max_attempts else JobStatus.pending
    )
    await db.commit()