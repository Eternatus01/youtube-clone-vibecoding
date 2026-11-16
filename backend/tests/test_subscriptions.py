from tests.conftest import create_video_record, get_user, register_user


async def _user(client, session_factory, username):
    await register_user(client, username)
    return await get_user(session_factory, username)


async def _feed(client):
    response = await client.get("/api/subscriptions/feed")
    assert response.status_code == 200, response.text
    return response.json()


async def test_subscriptions_require_auth(make_client):
    anon = await make_client()
    assert (await anon.get("/api/subscriptions/")).status_code == 401
    assert (await anon.get("/api/subscriptions/feed")).status_code == 401


async def test_subscription_list_and_pagination(client, make_client, session_factory):
    alice = await _user(client, session_factory, "alice")
    bob_client = await make_client()
    await _user(bob_client, session_factory, "bob")
    await _user(client, session_factory, "carol")

    empty = await bob_client.get("/api/subscriptions/")
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 0

    bob_user = await get_user(session_factory, "bob")
    carol_user = await get_user(session_factory, "carol")
    assert (
        await bob_client.post(f"/api/channels/{alice.id}/subscribe")
    ).status_code == 201
    assert (
        await bob_client.post(f"/api/channels/{carol_user.id}/subscribe")
    ).status_code == 201

    response = await bob_client.get(
        "/api/subscriptions/", params={"page": 1, "page_size": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["pages"] == 2
    assert len(body["items"]) == 1
    # Ordered by channel username ascending.
    assert body["items"][0]["channel"]["username"] == "alice"
    assert body["items"][0]["channel_id"] == alice.id
    assert bob_user.id != body["items"][0]["channel_id"]


async def test_feed_only_subscribed_channels(client, make_client, session_factory):
    alice = await _user(client, session_factory, "alice")
    bob_client = await make_client()
    bob = await _user(bob_client, session_factory, "bob")
    carol = await _user(client, session_factory, "carol")

    bob_video = await create_video_record(session_factory, owner=bob, title="Bob clip")
    await create_video_record(session_factory, owner=carol, title="Carol clip")
    await create_video_record(session_factory, owner=alice, title="Alice clip")

    # Not subscribed yet: empty feed.
    assert (await _feed(bob_client))["total"] == 0

    assert (
        await bob_client.post(f"/api/channels/{alice.id}/subscribe")
    ).status_code == 201

    body = await _feed(bob_client)
    feed_ids = [item["id"] for item in body["items"]]
    assert body["total"] == 1
    assert feed_ids == [body["items"][0]["id"]]
    assert body["items"][0]["title"] == "Alice clip"

    # Unsubscribe: the feed empties again.
    assert (
        await bob_client.delete(f"/api/channels/{alice.id}/subscribe")
    ).status_code == 204
    assert (await _feed(bob_client))["total"] == 0
    assert bob_video.id not in feed_ids


async def test_feed_excludes_non_public_or_unready(
    client, make_client, session_factory
):
    creator = await _user(client, session_factory, "alice")
    public = await create_video_record(
        session_factory, owner=creator, title="Public ready"
    )
    await create_video_record(
        session_factory, owner=creator, visibility="private", title="Private"
    )
    await create_video_record(
        session_factory, owner=creator, visibility="hidden", title="Hidden"
    )
    await create_video_record(
        session_factory, owner=creator, status="processing", title="Processing"
    )
    await create_video_record(
        session_factory, owner=creator, visibility="unlisted", title="Unlisted"
    )

    viewer = await make_client()
    await _user(viewer, session_factory, "bob")
    assert (
        await viewer.post(f"/api/channels/{creator.id}/subscribe")
    ).status_code == 201

    body = await _feed(viewer)
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [public.id]
    for item in body["items"]:
        assert item["visibility"] == "public"
        assert item["status"] == "ready"
