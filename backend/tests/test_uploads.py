from app.core.config import settings
from app.models.models import Job, JobStatus, UploadSession, Video, VideoStatus
from tests.conftest import register_user

UPLOAD = {
    "filename": "clip.mp4",
    "content_type": "video/mp4",
    "size_bytes": 1024,
    "title": "My clip",
    "description": "desc",
    "visibility": "public",
}


async def _init(client, **overrides):
    payload = {**UPLOAD, **overrides}
    return await client.post("/api/uploads/init", json=payload)


async def test_init_rejects_too_large_and_bad_types(client):
    await register_user(client, "alice")

    too_large = await _init(client, size_bytes=settings.upload_max_size + 1)
    assert too_large.status_code == 413

    bad_type = await _init(client, content_type="application/pdf")
    assert bad_type.status_code == 415

    bad_ext = await _init(client, filename="malware.exe")
    assert bad_ext.status_code == 415

    traversal = await _init(client, filename="../../etc/passwd.mp4")
    assert traversal.status_code == 201
    upload_url = traversal.json()["upload_url"]
    assert "/passwd.mp4?" in upload_url
    assert "etc" not in upload_url


async def test_init_creates_video_and_upload_session(client, fake_s3, session_factory):
    await register_user(client, "alice")
    response = await _init(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["upload_url"].startswith("/storage/videos/uploads/")
    assert body["upload_fields"] == {}
    assert body["upload_session_id"] and body["video_id"]

    async with session_factory() as db:
        video = await db.get(Video, body["video_id"])
        assert video.status == VideoStatus.uploading
        assert video.title == "My clip"
        assert video.visibility.value == "public"
        session = await db.get(UploadSession, body["upload_session_id"])
        assert session.completed is False
        assert session.object_key == f"uploads/{body['video_id']}/clip.mp4"
        assert session.size_bytes == 1024


async def test_init_requires_auth(make_client):
    anonymous = await make_client()
    response = await _init(anonymous)
    assert response.status_code == 401


async def test_complete_enqueues_transcode_job(client, fake_s3, session_factory):
    await register_user(client, "alice")
    init = (await _init(client)).json()
    object_key = f"uploads/{init['video_id']}/clip.mp4"
    fake_s3.put(object_key, b"fake-video-bytes")

    response = await client.post(
        "/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "processing"
    assert body["video_id"] == init["video_id"]

    async with session_factory() as db:
        video = await db.get(Video, init["video_id"])
        assert video.status == VideoStatus.processing
        session = await db.get(UploadSession, init["upload_session_id"])
        assert session.completed is True
        job = await db.get(Job, body["job_id"])
        assert job.status == JobStatus.pending
        assert job.payload == {
            "video_id": init["video_id"],
            "object_key": object_key,
            "content_type": "video/mp4",
            "session_id": init["upload_session_id"],
        }


async def test_complete_missing_object_and_double_complete(client, fake_s3):
    await register_user(client, "alice")
    init = (await _init(client)).json()

    missing = await client.post(
        "/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]}
    )
    assert missing.status_code == 400

    fake_s3.put(f"uploads/{init['video_id']}/clip.mp4", b"data")
    first = await client.post(
        "/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]}
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]}
    )
    assert second.status_code == 400


async def test_complete_foreign_session_not_found(client, make_client, fake_s3):
    await register_user(client, "alice")
    init = (await _init(client)).json()
    fake_s3.put(f"uploads/{init['video_id']}/clip.mp4", b"data")

    bob = await make_client()
    await register_user(bob, "bob")
    response = await bob.post(
        "/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]}
    )
    assert response.status_code == 404

    unknown = await client.post(
        "/api/uploads/complete", json={"upload_session_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert unknown.status_code == 404