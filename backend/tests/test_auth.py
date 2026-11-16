from tests.conftest import register_user


async def test_register_sets_httponly_cookies(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "alice"
    assert body["user"]["role"] == "user"
    assert body["access_token"] and body["refresh_token"]
    assert client.cookies.get("access_token") == body["access_token"]
    assert client.cookies.get("refresh_token") == body["refresh_token"]

    cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in c and "HttpOnly" in c for c in cookies)
    assert any("SameSite=lax" in c for c in cookies)


async def test_register_duplicate_case_insensitive(client):
    await register_user(client, "alice")

    dup_username = await client.post(
        "/api/auth/register",
        json={
            "username": "ALICE",
            "email": "other@example.com",
            "password": "secret123",
        },
    )
    assert dup_username.status_code == 409

    dup_email = await client.post(
        "/api/auth/register",
        json={
            "username": "bob",
            "email": "ALICE@example.com",
            "password": "secret123",
        },
    )
    assert dup_email.status_code == 409


async def test_login_by_username_and_email(client):
    await register_user(client, "alice", "alice@example.com")
    await client.post("/api/auth/logout")

    for login in ("alice", "alice@example.com", "ALICE"):
        response = await client.post(
            "/api/auth/login", json={"login": login, "password": "secret123"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["user"]["username"] == "alice"
        assert client.cookies.get("access_token")

    wrong = await client.post(
        "/api/auth/login", json={"login": "alice", "password": "wrong-pass"}
    )
    assert wrong.status_code == 401


async def test_me_and_logout(client):
    await register_user(client, "alice")
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "alice"

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert not client.cookies.get("access_token")
    assert not client.cookies.get("refresh_token")

    after = await client.get("/api/auth/me")
    assert after.status_code == 401


async def test_refresh_from_cookie_then_body(make_client):
    first = await make_client()
    data = await register_user(first, "alice")
    refresh_token = data["refresh_token"]

    # Cookie wins over the (empty) body value.
    response = await first.post("/api/auth/refresh", json={"refresh_token": ""})
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]

    # Fallback to the body token for a client without cookies.
    stateless = await make_client()
    body_response = await stateless.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert body_response.status_code == 200
    assert stateless.cookies.get("refresh_token")

    invalid_client = await make_client()
    invalid = await invalid_client.post(
        "/api/auth/refresh", json={"refresh_token": "not-a-token"}
    )
    assert invalid.status_code == 401


async def test_update_me_and_conflict(client, make_client):
    await register_user(client, "alice")
    response = await client.patch(
        "/api/auth/me", json={"username": "alice2", "avatar_url": "http://x/a.png"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alice2"
    assert response.json()["avatar_url"] == "http://x/a.png"

    bob = await make_client()
    await register_user(bob, "bob")
    conflict = await bob.patch("/api/auth/me", json={"username": "ALICE2"})
    assert conflict.status_code == 409


async def test_change_password(client):
    await register_user(client, "alice")

    wrong = await client.post(
        "/api/auth/change-password",
        json={"old_password": "nope", "new_password": "newsecret123"},
    )
    assert wrong.status_code == 400

    ok = await client.post(
        "/api/auth/change-password",
        json={"old_password": "secret123", "new_password": "newsecret123"},
    )
    assert ok.status_code == 204

    await client.post("/api/auth/logout")
    old_login = await client.post(
        "/api/auth/login", json={"login": "alice", "password": "secret123"}
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/auth/login", json={"login": "alice", "password": "newsecret123"}
    )
    assert new_login.status_code == 200