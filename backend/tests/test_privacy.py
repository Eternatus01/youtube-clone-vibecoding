import uuid

from tests.conftest import (
    create_video_record,
    get_user,
    register_user,
    set_role,
)


async def _user(client, session_factory, username: str, role: str | None = None):
    await register_user(client, username)
    if role is not None:
        await set_role(session_factory, username, role)
    return await get_user(session_factory, username)


async def _make_video(session_factory, fake_s3, owner, visibility, title=None):
    key = f"videos/{visibility}/{uuid.uuid4()}/720p.mp4"
    fake_s3.put(key, b"data")
    return await create_video_record(
        session_factory,
        owner=owner,
        title=title or f"{visibility} video",
        visibility=visibility,
        assets=[("720p", key, b"data")],
    )


EXPECTED = {
    "public": {
        "anon": 200,
        "other": 200,
        "shared": 200,
        "owner": 200,
        "moderator": 200,
        "admin": 200,
    },
    "unlisted": {
        "anon": 200,
        "other": 200,
        "shared": 200,
        "owner": 200,
        "moderator": 200,
        "admin": 200,
    },
    "private": {
        "anon": 403,
        "other": 403,
        "shared": 200,
        "owner": 200,
        "moderator": 200,
        "admin": 200,
    },
    "hidden": {
        "anon": 404,
        "other": 404,
        "shared": 404,
        "owner": 404,
        "moderator": 200,
        "admin": 200,
    },
}


async def test_visibility_access_matrix(
    client, make_client, fake_s3, session_factory
):
    owner = await _user(client, session_factory, "owner")

    anon = await make_client()
    other_client = await make_client()
    await _user(other_client, session_factory, "other")
    shared_client = await make_client()
    shared = await _user(shared_client, session_factory, "shareduser")
    moderator_client = await make_client()
    await _user(moderator_client, session_factory, "mod", role="moderator")
    admin_client = await make_client()
    await _user(admin_client, session_factory, "adm", role="admin")

    videos = {}
    for visibility in ("public", "unlisted", "private", "hidden"):
        videos[visibility] = await _make_video(
            session_factory, fake_s3, owner, visibility
        )

    private = videos["private"]
    add = await client.post(
        f"/api/videos/{private.id}/shares", json={"username": shared.username}
    )
    assert add.status_code == 201, add.text

    actors = {
        "anon": anon,
        "other": other_client,
        "shared": shared_client,
        "owner": client,
        "moderator": moderator_client,
        "admin": admin_client,
    }

    for visibility, video in videos.items():
        for actor, http in actors.items():
            expected = EXPECTED[visibility][actor]
            label = f"{visibility} as {actor}"

            metadata = await http.get(f"/api/videos/{video.id}")
            assert metadata.status_code == expected, f"metadata {label}: {metadata.text}"

            stream = await http.get(f"/api/videos/{video.id}/stream")
            assert stream.status_code == expected, f"stream {label}: {stream.text}"

            comments = await http.get(f"/api/videos/{video.id}/comments/")
            assert comments.status_code == expected, f"comments {label}: {comments.text}"

    # A shared user may comment on the private video; an unrelated user may not.
    allowed = await shared_client.post(
        f"/api/videos/{private.id}/comments/", json={"body": "nice"}
    )
    assert allowed.status_code == 201, allowed.text
    denied = await other_client.post(
        f"/api/videos/{private.id}/comments/", json={"body": "nope"}
    )
    assert denied.status_code == 403


async def test_list_mine_returns_all_owner_videos(
    client, make_client, fake_s3, session_factory
):
    owner = await _user(client, session_factory, "owner")
    other_client = await make_client()
    await _user(other_client, session_factory, "other")

    created = []
    for visibility in ("public", "unlisted", "private", "hidden"):
        created.append(
            await _make_video(session_factory, fake_s3, owner, visibility)
        )
    created.append(
        await create_video_record(
            session_factory, owner=owner, title="Still processing", status="processing"
        )
    )

    response = await client.get("/api/videos/mine", params={"page_size": 100})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == len(created)
    ids = {item["id"] for item in body["items"]}
    assert ids == {video.id for video in created}
    assert {item["visibility"] for item in body["items"]} == {
        "public",
        "unlisted",
        "private",
        "hidden",
    }
    assert any(item["status"] == "processing" for item in body["items"])
    timestamps = [item["created_at"] for item in body["items"]]
    assert timestamps == sorted(timestamps, reverse=True)

    empty = await other_client.get("/api/videos/mine")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    anon = await make_client()
    assert (await anon.get("/api/videos/mine")).status_code == 401


async def test_share_endpoints(client, make_client, fake_s3, session_factory):
    owner = await _user(client, session_factory, "owner")
    other_client = await make_client()
    await _user(other_client, session_factory, "other")
    target_client = await make_client()
    target = await _user(target_client, session_factory, "target")

    video = await _make_video(session_factory, fake_s3, owner, "private")

    assert (await target_client.get(f"/api/videos/{video.id}")).status_code == 403

    denied = await other_client.post(
        f"/api/videos/{video.id}/shares", json={"username": target.username}
    )
    assert denied.status_code == 403

    unknown = await client.post(
        f"/api/videos/{video.id}/shares", json={"username": "ghostuser"}
    )
    assert unknown.status_code == 404

    own = await client.post(
        f"/api/videos/{video.id}/shares", json={"username": owner.username}
    )
    assert own.status_code == 400

    added = await client.post(
        f"/api/videos/{video.id}/shares", json={"username": target.username}
    )
    assert added.status_code == 201, added.text
    assert added.json()["user"]["username"] == target.username

    duplicate = await client.post(
        f"/api/videos/{video.id}/shares", json={"username": target.username}
    )
    assert duplicate.status_code == 400

    assert (await target_client.get(f"/api/videos/{video.id}")).status_code == 200

    listing = await client.get(f"/api/videos/{video.id}/shares")
    assert listing.status_code == 200
    assert [item["user_id"] for item in listing.json()] == [target.id]

    assert (await other_client.get(f"/api/videos/{video.id}/shares")).status_code == 403

    moderator_client = await make_client()
    await _user(moderator_client, session_factory, "mod", role="moderator")
    assert (
        await moderator_client.get(f"/api/videos/{video.id}/shares")
    ).status_code == 200

    assert (
        await other_client.delete(f"/api/videos/{video.id}/shares/{target.id}")
    ).status_code == 403
    assert (
        await client.delete(f"/api/videos/{video.id}/shares/{uuid.uuid4()}")
    ).status_code == 404

    removed = await client.delete(f"/api/videos/{video.id}/shares/{target.id}")
    assert removed.status_code == 204
    assert (await target_client.get(f"/api/videos/{video.id}")).status_code == 403


async def test_reports_create_and_mine(
    client, make_client, fake_s3, session_factory
):
    owner = await _user(client, session_factory, "owner")
    reporter_client = await make_client()
    reporter = await _user(reporter_client, session_factory, "reporter")
    video = await _make_video(session_factory, fake_s3, owner, "public")

    anon = await make_client()
    assert (
        await anon.post("/api/reports/", json={"video_id": video.id, "reason": "spam"})
    ).status_code == 401

    own = await client.post(
        "/api/reports/", json={"video_id": video.id, "reason": "spam"}
    )
    assert own.status_code == 400

    missing = await reporter_client.post(
        "/api/reports/", json={"video_id": str(uuid.uuid4()), "reason": "spam"}
    )
    assert missing.status_code == 400

    created = await reporter_client.post(
        "/api/reports/", json={"video_id": video.id, "reason": "misleading"}
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["video_id"] == video.id
    assert payload["reporter_id"] == reporter.id
    assert payload["status"] == "open"
    assert payload["video"]["id"] == video.id
    assert payload["reporter"]["username"] == reporter.username

    duplicate = await reporter_client.post(
        "/api/reports/", json={"video_id": video.id, "reason": "again"}
    )
    assert duplicate.status_code == 409

    mine = await reporter_client.get("/api/reports/mine")
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()] == [payload["id"]]

    empty = await client.get("/api/reports/mine")
    assert empty.status_code == 200
    assert empty.json() == []


async def test_moderation_list_resolve_and_actions(
    client, make_client, fake_s3, session_factory
):
    owner = await _user(client, session_factory, "owner")
    reporter_client = await make_client()
    await _user(reporter_client, session_factory, "reporter")
    moderator_client = await make_client()
    moderator = await _user(moderator_client, session_factory, "mod", role="moderator")
    admin_client = await make_client()
    await _user(admin_client, session_factory, "adm", role="admin")

    video = await _make_video(session_factory, fake_s3, owner, "public")
    report = await reporter_client.post(
        "/api/reports/", json={"video_id": video.id, "reason": "abuse"}
    )
    assert report.status_code == 201

    assert (await client.get("/api/moderation/reports")).status_code == 403
    assert (await client.post("/api/moderation/resolve", json={
        "video_id": video.id, "action": "hide", "reason": "x"
    })).status_code == 403

    listed = await moderator_client.get(
        "/api/moderation/reports", params={"status_filter": "open"}
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["video"]["id"] == video.id
    assert listed.json()["items"][0]["reporter"]["username"] == "reporter"

    assert (
        await moderator_client.get(
            "/api/moderation/reports", params={"status_filter": "bogus"}
        )
    ).status_code == 400

    bad_action = await moderator_client.post(
        "/api/moderation/resolve",
        json={"video_id": video.id, "action": "delete", "reason": "x"},
    )
    assert bad_action.status_code == 400

    missing_video = await moderator_client.post(
        "/api/moderation/resolve",
        json={"video_id": str(uuid.uuid4()), "action": "hide", "reason": "x"},
    )
    assert missing_video.status_code == 404

    hidden = await moderator_client.post(
        "/api/moderation/resolve",
        json={"video_id": video.id, "action": "hide", "reason": "abuse"},
    )
    assert hidden.status_code == 200, hidden.text
    action = hidden.json()
    assert action["action"] == "hide"
    assert action["reason"] == "abuse"
    assert action["moderator"]["username"] == moderator.username

    assert (await client.get(f"/api/videos/{video.id}")).status_code == 404
    assert (
        await moderator_client.get(f"/api/videos/{video.id}")
    ).status_code == 200

    open_reports = await moderator_client.get(
        "/api/moderation/reports", params={"status_filter": "open"}
    )
    assert open_reports.json()["total"] == 0
    resolved = await moderator_client.get(
        "/api/moderation/reports", params={"status_filter": "resolved"}
    )
    assert resolved.json()["total"] == 1

    actions = await moderator_client.get("/api/moderation/actions")
    assert actions.status_code == 200
    assert actions.json()["total"] == 1
    assert actions.json()["items"][0]["id"] == action["id"]

    assert (await admin_client.get("/api/moderation/actions")).status_code == 200

    restored = await moderator_client.post(
        "/api/moderation/resolve",
        json={"video_id": video.id, "action": "restore", "reason": "appeal"},
    )
    assert restored.status_code == 200
    assert restored.json()["action"] == "restore"
    assert (await client.get(f"/api/videos/{video.id}")).status_code == 200


async def test_admin_users_roles_and_deactivation(
    client, make_client, fake_s3, session_factory
):
    admin_client = await make_client()
    await _user(admin_client, session_factory, "adm", role="admin")
    target_client = await make_client()
    target = await _user(target_client, session_factory, "target")

    assert (await target_client.get("/api/admin/users")).status_code == 403
    assert (
        await target_client.patch(
            "/api/admin/users/role", json={"user_id": target.id, "role": "admin"}
        )
    ).status_code == 403

    users = await admin_client.get("/api/admin/users", params={"page_size": 100})
    assert users.status_code == 200, users.text
    body = users.json()
    assert body["total"] >= 2
    assert any(item["username"] == "target" for item in body["users"])

    promoted = await admin_client.patch(
        "/api/admin/users/role", json={"user_id": target.id, "role": "moderator"}
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "moderator"
    assert (
        await target_client.get("/api/moderation/actions")
    ).status_code == 200

    invalid = await admin_client.patch(
        "/api/admin/users/role", json={"user_id": target.id, "role": "owner"}
    )
    assert invalid.status_code == 400

    me = await admin_client.get("/api/auth/me")
    self_change = await admin_client.patch(
        "/api/admin/users/role", json={"user_id": me.json()["id"], "role": "user"}
    )
    assert self_change.status_code == 400

    unknown = await admin_client.patch(
        "/api/admin/users/role",
        json={"user_id": str(uuid.uuid4()), "role": "user"},
    )
    assert unknown.status_code == 404

    deactivated = await admin_client.delete(f"/api/admin/users/{target.id}")
    assert deactivated.status_code == 204
    assert (await target_client.get("/api/auth/me")).status_code == 401

    self_delete = await admin_client.delete(f"/api/admin/users/{me.json()['id']}")
    assert self_delete.status_code == 400
    assert (
        await admin_client.delete(f"/api/admin/users/{uuid.uuid4()}")
    ).status_code == 404