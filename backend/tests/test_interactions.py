from tests.conftest import (
    create_video_record,
    get_user,
    register_user,
    set_role,
)


async def _user(client, session_factory, username):
    await register_user(client, username)
    return await get_user(session_factory, username)


async def test_like_is_idempotent(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    video = await create_video_record(session_factory, owner=owner, title="Liked")

    voter = await make_client()
    await _user(voter, session_factory, "bob")

    first = await voter.post(f"/api/videos/{video.id}/like")
    assert first.status_code == 200, first.text
    assert first.json() == {"liked": True}

    again = await voter.post(f"/api/videos/{video.id}/like")
    assert again.status_code == 200
    assert again.json() == {"liked": True}

    detail = await voter.get(f"/api/videos/{video.id}")
    assert detail.json()["like_count"] == 1
    assert detail.json()["user_like"] is True

    unlike = await voter.delete(f"/api/videos/{video.id}/like")
    assert unlike.status_code == 200
    assert unlike.json() == {"liked": False}

    repeat = await voter.delete(f"/api/videos/{video.id}/like")
    assert repeat.status_code == 200
    assert repeat.json() == {"liked": False}
    assert (await voter.get(f"/api/videos/{video.id}")).json()["like_count"] == 0


async def test_like_respects_visibility_and_status(
    client, make_client, session_factory
):
    owner = await _user(client, session_factory, "alice")
    private = await create_video_record(
        session_factory, owner=owner, visibility="private"
    )
    processing = await create_video_record(
        session_factory, owner=owner, status="processing"
    )

    voter = await make_client()
    await _user(voter, session_factory, "bob")
    assert (await voter.post(f"/api/videos/{private.id}/like")).status_code == 403
    assert (await voter.post(f"/api/videos/{processing.id}/like")).status_code == 409

    anon = await make_client()
    assert (await anon.post(f"/api/videos/{processing.id}/like")).status_code == 401
    assert (await anon.post("/api/videos/00000000-0000-0000-0000-000000000000/like")).status_code == 401


async def test_comments_flow_and_moderation(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    video = await create_video_record(session_factory, owner=owner, title="Talk")

    commenter = await make_client()
    await _user(commenter, session_factory, "bob")
    created = await commenter.post(
        f"/api/videos/{video.id}/comments/", json={"body": "Nice video"}
    )
    assert created.status_code == 201, created.text
    comment = created.json()
    assert comment["author"]["username"] == "bob"
    assert comment["reply_count"] == 0

    reply = await commenter.post(
        f"/api/videos/{video.id}/comments/",
        json={"body": "Replying", "parent_id": comment["id"]},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == comment["id"]

    listing = await commenter.get(f"/api/videos/{video.id}/comments/?sort=oldest")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 2
    parent = next(item for item in body["items"] if item["id"] == comment["id"])
    assert parent["reply_count"] == 1
    assert parent["author"]["username"] == "bob"
    assert (
        await commenter.get(f"/api/videos/{video.id}/comments/?sort=bad")
    ).status_code == 400

    stranger = await make_client()
    await _user(stranger, session_factory, "carol")
    denied = await stranger.patch(
        f"/api/videos/{video.id}/comments/{comment['id']}",
        json={"body": "hijack"},
    )
    assert denied.status_code == 403

    edited = await commenter.patch(
        f"/api/videos/{video.id}/comments/{comment['id']}",
        json={"body": "Edited"},
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "Edited"

    await set_role(session_factory, "carol", "moderator")
    deleted = await stranger.delete(
        f"/api/videos/{video.id}/comments/{comment['id']}"
    )
    assert deleted.status_code == 204
    remaining = await commenter.get(f"/api/videos/{video.id}/comments/")
    assert remaining.json()["total"] == 0
    assert (
        await commenter.delete(f"/api/videos/{video.id}/comments/{comment['id']}")
    ).status_code == 404


async def test_comment_on_private_video_denied(make_client, session_factory):
    owner_client = await make_client()
    owner = await _user(owner_client, session_factory, "alice")
    video = await create_video_record(
        session_factory, owner=owner, visibility="private"
    )

    stranger = await make_client()
    await _user(stranger, session_factory, "bob")
    assert (
        await stranger.get(f"/api/videos/{video.id}/comments/")
    ).status_code == 403
    assert (
        await stranger.post(f"/api/videos/{video.id}/comments/", json={"body": "hi"})
    ).status_code == 403
    assert (await owner_client.post(
        f"/api/videos/{video.id}/comments/", json={"body": "owner"}
    )).status_code == 201


async def test_subscriptions(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    await create_video_record(session_factory, owner=owner)

    viewer = await make_client()
    await _user(viewer, session_factory, "bob")

    self_sub = await viewer.post(f"/api/channels/{await _uid(session_factory, 'bob')}/subscribe")
    assert self_sub.status_code == 400

    channel = await viewer.get(f"/api/channels/{owner.id}")
    assert channel.status_code == 200
    assert channel.json()["is_subscribed"] is False
    assert channel.json()["subscriber_count"] == 0
    assert channel.json()["video_count"] == 1

    sub = await viewer.post(f"/api/channels/{owner.id}/subscribe")
    assert sub.status_code == 201, sub.text
    assert sub.json()["channel_id"] == owner.id

    again = await viewer.post(f"/api/channels/{owner.id}/subscribe")
    assert again.status_code == 201
    assert again.json()["id"] == sub.json()["id"]

    count = await viewer.get(f"/api/channels/{owner.id}/subscribers/count")
    assert count.json() == {"count": 1}
    assert (await viewer.get(f"/api/channels/{owner.id}")).json()["is_subscribed"] is True

    anon = await make_client()
    assert (await anon.get(f"/api/channels/{owner.id}")).json()["is_subscribed"] is None

    assert (await viewer.delete(f"/api/channels/{owner.id}/subscribe")).status_code == 204
    assert (
        await viewer.get(f"/api/channels/{owner.id}/subscribers/count")
    ).json() == {"count": 0}


async def _uid(session_factory, username):
    return (await get_user(session_factory, username)).id


async def test_playlist_crud_and_items(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    first = await create_video_record(session_factory, owner=owner, title="One")
    second = await create_video_record(session_factory, owner=owner, title="Two")

    created = await client.post(
        "/api/playlists/", json={"title": "Watch later", "visibility": "public"}
    )
    assert created.status_code == 201, created.text
    playlist = created.json()
    assert playlist["item_count"] == 0
    assert playlist["owner"]["username"] == "alice"

    added = await client.post(
        f"/api/playlists/{playlist['id']}/items", json={"video_id": first.id}
    )
    assert added.status_code == 201, added.text
    assert added.json()["position"] == 0
    assert added.json()["video"]["title"] == "One"

    dupe = await client.post(
        f"/api/playlists/{playlist['id']}/items", json={"video_id": first.id}
    )
    assert dupe.status_code == 409

    second_item = await client.post(
        f"/api/playlists/{playlist['id']}/items", json={"video_id": second.id}
    )
    assert second_item.json()["position"] == 1

    detail = await client.get(f"/api/playlists/{playlist['id']}")
    assert detail.status_code == 200
    assert [item["video"]["title"] for item in detail.json()["items"]] == [
        "One",
        "Two",
    ]

    moved = await client.patch(
        f"/api/playlists/{playlist['id']}/items/{second_item.json()['id']}/position",
        json={"position": 0},
    )
    assert moved.status_code == 200, moved.text
    payload = moved.json()
    ordered = payload["items"] if isinstance(payload, dict) and "items" in payload else None
    if ordered is None:
        reread = await client.get(f"/api/playlists/{playlist['id']}")
        ordered = reread.json()["items"]
    assert [item["video"]["title"] for item in ordered] == ["Two", "One"]
    assert [item["position"] for item in ordered] == [0, 1]

    assert (
        await client.delete(
            f"/api/playlists/{playlist['id']}/items/{second_item.json()['id']}"
        )
    ).status_code == 204
    after = await client.get(f"/api/playlists/{playlist['id']}")
    assert [item["position"] for item in after.json()["items"]] == [0]

    stranger = await make_client()
    await _user(stranger, session_factory, "bob")
    assert (
        await stranger.get(f"/api/playlists/{playlist['id']}")
    ).status_code == 200
    assert (
        await stranger.patch(
            f"/api/playlists/{playlist['id']}", json={"title": "Hijack"}
        )
    ).status_code == 403
    assert (
        await stranger.post(
            f"/api/playlists/{playlist['id']}/items", json={"video_id": second.id}
        )
    ).status_code == 403

    private = await client.post(
        "/api/playlists/", json={"title": "Mine", "visibility": "private"}
    )
    private_id = private.json()["id"]
    assert (await stranger.get(f"/api/playlists/{private_id}")).status_code == 403
    assert (await client.get(f"/api/playlists/{private_id}")).status_code == 200

    anon = await make_client()
    assert (await anon.get(f"/api/playlists/{private_id}")).status_code == 403

    assert (await client.delete(f"/api/playlists/{playlist['id']}")).status_code == 204
    assert (await client.get(f"/api/playlists/{playlist['id']}")).status_code == 404


async def test_search_and_related_and_views(make_client, session_factory):
    owner_client = await make_client()
    owner = await _user(owner_client, session_factory, "alice")
    public = await create_video_record(
        session_factory, owner=owner, title="Cooking Show"
    )
    private = await create_video_record(
        session_factory, owner=owner, title="Cooking Secrets", visibility="private"
    )

    other_client = await make_client()
    other = await _user(other_client, session_factory, "bob")
    other_video = await create_video_record(
        session_factory, owner=other, title="Cooking Elsewhere"
    )

    anon = await make_client()
    found = await anon.get("/api/search/?q=cooking")
    assert found.status_code == 200, found.text
    body = found.json()
    video_ids = [video["id"] for video in body["videos"]]
    assert public.id in video_ids
    assert private.id not in video_ids
    assert other_video.id in video_ids
    assert body["channels"] == []

    by_name = await anon.get("/api/search/?q=alice")
    assert by_name.status_code == 200
    channels = by_name.json()["channels"]
    assert [channel["username"] for channel in channels] == ["alice"]
    assert channels[0]["subscriber_count"] == 0

    assert (await anon.get("/api/search/?q=  ")).status_code == 400

    related = await anon.get(f"/api/videos/{public.id}/related")
    assert related.status_code == 200
    related_ids = [video["id"] for video in related.json()["items"]]
    assert public.id not in related_ids
    # The private video is excluded, so the other owner's public video comes first.
    assert related_ids[0] == other_video.id

    # Views: anonymous and non-owner views count, the owner's own view does not.
    start = (await owner_client.get(f"/api/videos/{public.id}")).json()["views"]
    await anon.get(f"/api/videos/{public.id}")
    await other_client.get(f"/api/videos/{public.id}")
    third = (await anon.get(f"/api/videos/{public.id}")).json()["views"]
    assert third == start + 3
    assert (
        await owner_client.get(f"/api/videos/{public.id}")
    ).json()["views"] == third


async def test_channel_lists(client, make_client, session_factory):
    owner = await _user(client, session_factory, "alice")
    ready = await create_video_record(session_factory, owner=owner, title="Ready")
    await create_video_record(session_factory, owner=owner, visibility="private")
    await create_video_record(session_factory, owner=owner, status="processing")
    await client.post("/api/playlists/", json={"title": "Public list"})
    await client.post(
        "/api/playlists/", json={"title": "Private list", "visibility": "private"}
    )

    videos = await client.get(f"/api/channels/{owner.id}/videos")
    assert videos.status_code == 200
    assert [video["id"] for video in videos.json()["items"]] == [ready.id]

    playlists = await client.get(f"/api/channels/{owner.id}/playlists")
    assert playlists.status_code == 200
    assert [item["title"] for item in playlists.json()["items"]] == ["Public list"]

    assert (
        await client.get("/api/channels/00000000-0000-0000-0000-000000000000")
    ).status_code == 404