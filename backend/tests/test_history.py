from datetime import datetime

from tests.conftest import create_video_record, get_user, register_user


async def _user(client, session_factory, username):
    await register_user(client, username)
    return await get_user(session_factory, username)


async def _history(client):
    response = await client.get("/api/history/")
    assert response.status_code == 200, response.text
    return response.json()


async def test_history_requires_auth(make_client):
    anon = await make_client()
    assert (await anon.get("/api/history/")).status_code == 401
    assert (await anon.delete("/api/history/")).status_code == 401
    assert (
        await anon.post("/api/history/00000000-0000-0000-0000-000000000000")
    ).status_code == 401


async def test_history_empty_initially(client):
    await register_user(client, "alice")
    body = await _history(client)
    assert body["items"] == []
    assert body["total"] == 0


async def test_watch_records_history_idempotent(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    video = await create_video_record(session_factory, owner=owner, title="Watched")

    viewer = await make_client()
    await _user(viewer, session_factory, "bob")

    # Viewing the detail endpoint records history.
    assert (await viewer.get(f"/api/videos/{video.id}")).status_code == 200
    first = await _history(viewer)
    assert first["total"] == 1
    entry = first["items"][0]
    assert entry["video_id"] == video.id
    assert entry["video"]["title"] == "Watched"
    first_seen = entry["last_watched_at"]

    # Watching again keeps one row and bumps last_watched_at.
    assert (await viewer.get(f"/api/videos/{video.id}")).status_code == 200
    second = await _history(viewer)
    assert second["total"] == 1
    assert len(second["items"]) == 1
    later = second["items"][0]["last_watched_at"]
    assert datetime.fromisoformat(later) >= datetime.fromisoformat(first_seen)

    # Explicit POST stays idempotent and stores progress.
    recorded = await viewer.post(
        f"/api/history/{video.id}", json={"progress_seconds": 7}
    )
    assert recorded.status_code == 204, recorded.text
    third = await _history(viewer)
    assert third["total"] == 1
    assert third["items"][0]["progress_seconds"] == 7


async def test_history_remove_and_clear(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    one = await create_video_record(session_factory, owner=owner, title="One")
    two = await create_video_record(session_factory, owner=owner, title="Two")

    viewer = await make_client()
    await _user(viewer, session_factory, "bob")
    await viewer.get(f"/api/videos/{one.id}")
    await viewer.get(f"/api/videos/{two.id}")
    assert (await _history(viewer))["total"] == 2

    removed = await viewer.delete(f"/api/history/{one.id}")
    assert removed.status_code == 204
    remaining = await _history(viewer)
    assert remaining["total"] == 1
    assert remaining["items"][0]["video_id"] == two.id

    cleared = await viewer.delete("/api/history/")
    assert cleared.status_code == 204
    assert (await _history(viewer))["total"] == 0


async def test_history_excludes_private_and_hidden(
    client, make_client, session_factory
):
    owner = await _user(client, session_factory, "alice")
    public = await create_video_record(session_factory, owner=owner, title="Public")
    private = await create_video_record(
        session_factory, owner=owner, visibility="private", title="Private"
    )
    hidden = await create_video_record(
        session_factory, owner=owner, visibility="hidden", title="Hidden"
    )

    viewer = await make_client()
    await _user(viewer, session_factory, "bob")

    assert (await viewer.get(f"/api/videos/{public.id}")).status_code == 200
    # Another user's private / hidden videos cannot be viewed or recorded.
    assert (await viewer.get(f"/api/videos/{private.id}")).status_code == 403
    assert (await viewer.get(f"/api/videos/{hidden.id}")).status_code == 404
    assert (await viewer.post(f"/api/history/{private.id}")).status_code == 403
    assert (await viewer.post(f"/api/history/{hidden.id}")).status_code == 404

    body = await _history(viewer)
    assert body["total"] == 1
    assert [item["video_id"] for item in body["items"]] == [public.id]


async def test_owner_watch_not_in_history(client, make_client, session_factory):
    owner_client = await make_client()
    owner = await _user(owner_client, session_factory, "alice")
    video = await create_video_record(session_factory, owner=owner, title="Mine")

    assert (await owner_client.get(f"/api/videos/{video.id}")).status_code == 200
    body = await _history(owner_client)
    assert body["total"] == 0
    assert body["items"] == []
