import shutil
import subprocess

import pytest
from sqlalchemy import select

from app.models.models import Job, JobStatus, Video, VideoAsset, VideoStatus
from app.repositories.jobs import claim_next_transcode
from app.worker import worker
from tests.conftest import register_user

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)

INIT_PAYLOAD = {
    "filename": "source.mp4",
    "content_type": "video/mp4",
    "size_bytes": 2048,
    "title": "Worker clip",
}


async def _queued_upload(client, fake_s3, session_factory, data: bytes):
    await register_user(client, "alice")
    init = (await client.post("/api/uploads/init", json=INIT_PAYLOAD)).json()
    key = f"uploads/{init['video_id']}/source.mp4"
    fake_s3.put(key, data)
    complete = await client.post(
        "/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]}
    )
    assert complete.status_code == 200, complete.text
    return init["video_id"], complete.json()["job_id"]


async def test_process_job_transcodes_and_marks_ready(
    client, fake_s3, session_factory, monkeypatch, tmp_path
):
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=25",
            "-t",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    video_id, job_id = await _queued_upload(
        client, fake_s3, session_factory, source.read_bytes()
    )
    monkeypatch.setattr(worker, "async_session", session_factory)

    async with session_factory() as db:
        job = await claim_next_transcode(db, "test-worker")
    assert job is not None and job.id == job_id

    await worker.process_job(job_id)

    async with session_factory() as db:
        job = await db.get(Job, job_id)
        video = await db.get(Video, video_id)
        assets = (
            await db.execute(select(VideoAsset).where(VideoAsset.video_id == video_id))
        ).scalars().all()
    assert job.status == JobStatus.done
    assert video.status == VideoStatus.ready
    assert video.duration_seconds >= 1
    qualities = {asset.quality: asset for asset in assets}
    assert "240p" in qualities and "poster" in qualities
    assert qualities["240p"].object_key == f"videos/{video_id}/240p.mp4"
    assert qualities["poster"].object_key == f"videos/{video_id}/poster.jpg"
    assert all(asset.size_bytes > 0 for asset in assets)
    assert f"videos/{video_id}/240p.mp4" in fake_s3.objects
    assert f"videos/{video_id}/poster.jpg" in fake_s3.objects

    ready = await client.get(f"/api/videos/{video_id}")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


async def test_process_job_fails_after_three_attempts(
    client, fake_s3, session_factory, monkeypatch
):
    video_id, job_id = await _queued_upload(
        client, fake_s3, session_factory, b"definitely not a video"
    )
    monkeypatch.setattr(worker, "async_session", session_factory)

    for attempt in (1, 2, 3):
        async with session_factory() as db:
            job = await claim_next_transcode(db, "test-worker")
        assert job is not None and job.id == job_id
        await worker.process_job(job_id)

        async with session_factory() as db:
            job = await db.get(Job, job_id)
            video = await db.get(Video, video_id)
        assert job.attempts == attempt
        if attempt < 3:
            assert job.status == JobStatus.pending
            assert video.status == VideoStatus.processing
        else:
            assert job.status == JobStatus.failed
            assert video.status == VideoStatus.failed
            assert job.error