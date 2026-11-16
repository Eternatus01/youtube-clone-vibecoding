import asyncio
import json
import logging
import os
import shutil
import socket
import tempfile
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.db import async_session
from app.core.s3_client import get_s3_client
from app.models.models import (
    JobStatus,
    Video,
    VideoAsset,
    VideoStatus,
)
from app.repositories import jobs as jobs_repo

logger = logging.getLogger("worker")

MAX_ATTEMPTS = 3
MAX_HEIGHT = 720
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"


async def _run(*cmd: str) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out, err


async def ffprobe_media(path: str) -> dict:
    """Validate a media file and return its probe summary."""
    code, out, err = await _run(
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    )
    if code != 0:
        raise RuntimeError(f"ffprobe failed: {err.decode(errors='replace')[:500]}")
    data = json.loads(out or b"{}")
    video_streams = [
        s for s in data.get("streams", []) if s.get("codec_type") == "video"
    ]
    if not video_streams:
        raise RuntimeError("No video stream found")
    stream = video_streams[0]
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("Invalid media duration")
    return {
        "duration": duration,
        "height": int(stream.get("height") or 0),
        "width": int(stream.get("width") or 0),
        "codec": stream.get("codec_name"),
    }


async def transcode_to_mp4(source: str, target: str, target_height: int) -> None:
    if target_height % 2:
        target_height -= 1
    code, _, err = await _run(
        "ffmpeg",
        "-y",
        "-i",
        source,
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-vf",
        f"scale=-2:{target_height}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        target,
    )
    if code != 0 or not os.path.exists(target):
        raise RuntimeError(f"ffmpeg transcode failed: {err.decode(errors='replace')[:500]}")


async def extract_poster(source: str, target: str, duration: float) -> None:
    seek = "2" if duration >= 3 else f"{max(duration / 2, 0):.2f}"
    code, _, err = await _run(
        "ffmpeg",
        "-y",
        "-ss",
        seek,
        "-i",
        source,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        target,
    )
    if code != 0 or not os.path.exists(target):
        raise RuntimeError(f"ffmpeg poster failed: {err.decode(errors='replace')[:500]}")


def _upsert_asset(
    existing: dict[str, VideoAsset],
    video_id: str,
    quality: str,
    object_key: str,
    size_bytes: int,
    content_type: str,
) -> None:
    asset = existing.get(quality)
    if asset is None:
        asset = VideoAsset(
            video_id=video_id,
            quality=quality,
            object_key=object_key,
            size_bytes=size_bytes,
            content_type=content_type,
        )
        existing[quality] = asset
    else:
        asset.object_key = object_key
        asset.size_bytes = size_bytes
        asset.content_type = content_type


async def _process(db, job) -> None:
    payload = job.payload or {}
    video_id = payload.get("video_id")
    object_key = payload.get("object_key")
    if not video_id or not object_key:
        raise RuntimeError("Job payload missing video_id/object_key")

    video = await db.get(Video, video_id)
    if video is None:
        raise RuntimeError(f"Video {video_id} not found")

    s3 = get_s3_client()
    workdir = tempfile.mkdtemp(prefix="yt-transcode-")
    try:
        source = os.path.join(workdir, "source")
        await asyncio.to_thread(
            s3.download_file, settings.s3_bucket, object_key, source
        )

        probe = await ffprobe_media(source)
        source_height = probe["height"] or MAX_HEIGHT
        target_height = min(source_height, MAX_HEIGHT)
        quality = f"{target_height}p"

        rendition = os.path.join(workdir, f"{quality}.mp4")
        poster = os.path.join(workdir, "poster.jpg")
        await transcode_to_mp4(source, rendition, target_height)
        await extract_poster(source, poster, probe["duration"])

        rendition_key = f"videos/{video_id}/{quality}.mp4"
        poster_key = f"videos/{video_id}/poster.jpg"
        await asyncio.to_thread(
            s3.upload_file,
            rendition,
            settings.s3_bucket,
            rendition_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        await asyncio.to_thread(
            s3.upload_file,
            poster,
            settings.s3_bucket,
            poster_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

        result = await db.execute(
            select(VideoAsset).where(VideoAsset.video_id == video_id)
        )
        existing = {asset.quality: asset for asset in result.scalars().all()}
        _upsert_asset(
            existing,
            video_id,
            quality,
            rendition_key,
            os.path.getsize(rendition),
            "video/mp4",
        )
        _upsert_asset(
            existing,
            video_id,
            "poster",
            poster_key,
            os.path.getsize(poster),
            "image/jpeg",
        )
        db.add_all(list(existing.values()))

        video.duration_seconds = max(1, int(round(probe["duration"])))
        video.status = VideoStatus.ready
        await db.commit()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def process_job(job_id: str) -> None:
    """Process one claimed job. Never raises: failures are recorded on the job."""
    async with async_session() as db:
        job = await jobs_repo.get(db, job_id)
        if job is None or job.status != JobStatus.running:
            return
    try:
        async with async_session() as db:
            job = await jobs_repo.get(db, job_id)
            await _process(db, job)
            await jobs_repo.mark_done(db, job)
    except Exception as exc:  # noqa: BLE001 - worker must not die on a bad file
        logger.exception("Job %s failed", job_id)
        async with async_session() as db:
            job = await jobs_repo.get(db, job_id)
            if job is None:
                return
            await jobs_repo.mark_failed(db, job, str(exc), max_attempts=MAX_ATTEMPTS)
            video_id = (job.payload or {}).get("video_id")
            video = await db.get(Video, video_id) if video_id else None
            if video is not None and job.status == JobStatus.failed:
                video.status = VideoStatus.failed
                await db.commit()


async def run_worker() -> None:
    logging.basicConfig(level=settings.log_level.upper())
    logger.info("Worker %s starting (bucket=%s)", WORKER_ID, settings.s3_bucket)
    while True:
        job = None
        try:
            async with async_session() as db:
                job = await jobs_repo.claim_next_transcode(db, WORKER_ID)
            if job is not None:
                await process_job(job.id)
                continue
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep polling
            logger.exception("Worker loop error")
        await asyncio.sleep(2)