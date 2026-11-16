from tests.conftest import (
    create_video_record,
    get_user,
    register_user,
    set_role,
)


async def _owner(client, session_factory, username="alice"):
    await register_user(client, username)
    return await get_user(session_factory, username)


async def test_feed_only_ready_public_and_search(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    await create_video_record(session_factory, owner=owner, title="Cooking Show")
    await create_video_record(
        session_factory, owner=owner, title="Secret", visibility="private"
    )
    await create_video_record(
        session_factory, owner=owner, title="Processing", status="processing"
    )
    await create_video_record(
        session_factory, owner=owner, title="Hidden", visibility="hidden"
    )

    anon = await make_client()
    response = await anon.get("/api/videos/")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Cooking Show"
    assert body["items"][0]["owner"]["username"] == "alice"
    assert body["items"][0]["like_count"] == 0

    search = await anon.get("/api/videos/", params={"search": "cook"})
    assert [v["title"] for v in search.json()["items"]] == ["Cooking Show"]
    empty = await anon.get("/api/videos/", params={"search": "nothing"})
    assert empty.json()["items"] == []


async def test_feed_pagination(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    for index in range(3):
        await create_video_record(session_factory, owner=owner, title=f"Video {index}")

    anon = await make_client()
    page2 = await anon.get("/api/videos/", params={"page": 2, "page_size": 2})
    body = page2.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 1


async def test_private_video_access_control(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    video = await create_video_record(
        session_factory, owner=owner, title="Private", visibility="private"
    )

    anon = await make_client()
    assert (await anon.get(f"/api/videos/{video.id}")).status_code == 403

    other = await make_client()
    await register_user(other, "bob")
    assert (await other.get(f"/api/videos/{video.id}")).status_code == 403

    owner_view = await client.get(f"/api/videos/{video.id}")
    assert owner_view.status_code == 200
    assert owner_view.json()["visibility"] == "private"

    moderator = await make_client()
    await register_user(moderator, "mod")
    await set_role(session_factory, "mod", "moderator")
    assert (await moderator.get(f"/api/videos/{video.id}")).status_code == 200


async def test_hidden_video_access_control(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    video = await create_video_record(
        session_factory, owner=owner, title="Removed", visibility="hidden"
    )

    anon = await make_client()
    assert (await anon.get(f"/api/videos/{video.id}")).status_code == 404

    owner_view = await client.get(f"/api/videos/{video.id}")
    assert owner_view.status_code == 404

    moderator = await make_client()
    await register_user(moderator, "mod")
    await set_role(session_factory, "mod", "moderator")
    assert (await moderator.get(f"/api/videos/{video.id}")).status_code == 200


async def test_update_and_delete_permissions(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    key = "videos/key/720p.mp4"
    video = await create_video_record(
        session_factory,
        owner=owner,
        title="Original",
        assets=[("720p", key, b"0123456789")],
    )
    fake_s3.put(key, b"0123456789")

    other = await make_client()
    await register_user(other, "bob")
    denied_update = await other.patch(f"/api/videos/{video.id}", json={"title": "Hacked"})
    assert denied_update.status_code == 403
    denied_delete = await other.delete(f"/api/videos/{video.id}")
    assert denied_delete.status_code == 403

    moderator = await make_client()
    await register_user(moderator, "mod")
    await set_role(session_factory, "mod", "moderator")
    assert (
        await moderator.patch(f"/api/videos/{video.id}", json={"title": "Moderated"})
    ).status_code == 200
    assert (await moderator.delete(f"/api/videos/{video.id}")).status_code == 403

    updated = await client.patch(
        f"/api/videos/{video.id}", json={"title": "Renamed", "visibility": "unlisted"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"
    assert updated.json()["visibility"] == "unlisted"

    invalid = await client.patch(f"/api/videos/{video.id}", json={"visibility": "bogus"})
    assert invalid.status_code == 400

    deleted = await client.delete(f"/api/videos/{video.id}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/videos/{video.id}")).status_code == 404
    assert key not in fake_s3.objects


async def test_stream_and_poster_proxy(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    media_key = "videos/stream/720p.mp4"
    poster_key = "videos/stream/poster.jpg"
    video = await create_video_record(
        session_factory,
        owner=owner,
        assets=[("720p", media_key, b"0123456789"), ("poster", poster_key, b"jpegbytes")],
    )
    fake_s3.put(media_key, b"0123456789", "video/mp4")
    fake_s3.put(poster_key, b"jpegbytes", "image/jpeg")

    anon = await make_client()
    full = await anon.get(f"/api/videos/{video.id}/stream")
    assert full.status_code == 200
    assert full.content == b"0123456789"
    assert full.headers["accept-ranges"] == "bytes"

    partial = await anon.get(
        f"/api/videos/{video.id}/stream", headers={"Range": "bytes=0-3"}
    )
    assert partial.status_code == 206
    assert partial.content == b"0123"
    assert partial.headers["content-range"] == "bytes 0-3/10"
    assert partial.headers["content-length"] == "4"

    missing_quality = await anon.get(
        f"/api/videos/{video.id}/stream", params={"quality": "1080p"}
    )
    assert missing_quality.status_code == 404

    poster = await anon.get(f"/api/videos/{video.id}/poster")
    assert poster.status_code == 200
    assert poster.content == b"jpegbytes"
    assert poster.headers["content-type"] == "image/jpeg"


async def test_private_stream_denied(client, make_client, fake_s3, session_factory):
    owner = await _owner(client, session_factory)
    key = "videos/private/720p.mp4"
    video = await create_video_record(
        session_factory,
        owner=owner,
        visibility="private",
        assets=[("720p", key, b"data")],
    )
    fake_s3.put(key, b"data")

    anon = await make_client()
    assert (await anon.get(f"/api/videos/{video.id}/stream")).status_code == 403
    assert (await anon.get(f"/api/videos/{video.id}/poster")).status_code == 403
    assert (await client.get(f"/api/videos/{video.id}/stream")).status_code == 200