import os
from pathlib import PurePosixPath

from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.s3_client import generate_presigned_put, get_s3_client
from app.models.models import (
    UploadSession,
    Video,
    VideoStatus,
    Visibility,
    gen_uuid,
)
from app.repositories import uploads as uploads_repo

ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "video/x-msvideo",
}
ALLOWED_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}


def _safe_filename(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    if not name or name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename"
        )
    return name


def _validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    if size_bytes > settings.upload_max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds upload limit of {settings.upload_max_size} bytes",
        )
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file extension",
        )
    base_type = content_type.split(";")[0].strip().lower()
    if base_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported content type",
        )


async def init_upload(db: AsyncSession, body, user) -> dict:
    filename = _safe_filename(body.filename)
    _validate_upload(filename, body.content_type, body.size_bytes)
    try:
        visibility = Visibility(body.visibility)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visibility"
        )

    video_id = gen_uuid()
    object_key = f"uploads/{video_id}/{filename}"
    upload_url = await run_in_threadpool(generate_presigned_put, object_key)

    video = Video(
        id=video_id,
        owner_id=user.id,
        title=body.title,
        description=body.description,
        visibility=visibility,
        status=VideoStatus.uploading,
    )
    session = UploadSession(
        user_id=user.id,
        video_id=video_id,
        filename=filename,
        object_key=object_key,
        size_bytes=body.size_bytes,
        content_type=body.content_type,
        completed=False,
    )
    db.add(video)
    await db.flush()
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "upload_url": upload_url,
        "upload_fields": {},
        "upload_session_id": session.id,
        "video_id": video_id,
    }


async def complete_upload(db: AsyncSession, session_id: str, user) -> dict:
    session = await uploads_repo.get_upload_session(db, session_id, user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found"
        )
    if session.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Upload already completed"
        )
    video = await db.get(Video, session.video_id) if session.video_id else None
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    s3 = get_s3_client()
    try:
        await run_in_threadpool(
            s3.head_object, Bucket=settings.s3_bucket, Key=session.object_key
        )
    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded object not found in storage",
        )

    job = await uploads_repo.create_transcode_job(
        db, session=session, video_id=video.id
    )
    video.status = VideoStatus.processing
    session.completed = True
    await db.commit()
    await db.refresh(job)

    return {"status": "processing", "video_id": video.id, "job_id": job.id}