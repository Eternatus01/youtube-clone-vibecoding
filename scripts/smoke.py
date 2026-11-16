"""M3 smoke: privacy matrix + shares + reports + moderation/admin role checks, over HTTP.

Generates a tiny mp4 with ffmpeg (lavfi), registers an owner + viewer, uploads a
private video, then asserts the access matrix and report/role endpoints. No seed
data required. Exit code 0 = pass.
"""
import os
import subprocess
import sys
import time
import uuid

import httpx

BASE = "http://localhost"
MP4 = os.path.join(os.path.dirname(__file__), "smoke.mp4")


def gen_mp4() -> None:
    if os.path.exists(MP4):
        return
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "testsrc=duration=2:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
            "-movflags", "faststart", MP4,
        ],
        capture_output=True, check=True,
    )


def register(c: httpx.Client, uname: str) -> None:
    r = c.post("/api/auth/register", json={
        "username": uname, "email": f"{uname}@t.co", "password": "secret123",
    })
    assert r.status_code == 201, f"register {uname}: {r.status_code} {r.text}"


def upload_private(c: httpx.Client, title: str) -> str:
    with open(MP4, "rb") as f:
        data = f.read()
    r = c.post("/api/uploads/init", json={
        "filename": "smoke.mp4", "content_type": "video/mp4",
        "size_bytes": len(data), "title": title, "description": None,
        "visibility": "private",
    })
    assert r.status_code == 201, f"init: {r.status_code} {r.text}"
    init = r.json()
    put = httpx.put(f"http://localhost{init['upload_url']}", content=data,
                    headers={"Content-Type": "video/mp4"}, timeout=60)
    assert put.status_code in (200, 204), f"put: {put.status_code}"
    r = c.post("/api/uploads/complete", json={"upload_session_id": init["upload_session_id"]})
    assert r.status_code == 200, f"complete: {r.status_code} {r.text}"
    video_id = init["video_id"]
    for _ in range(60):
        st = c.get(f"/api/videos/{video_id}").json().get("status")
        if st == "ready":
            return video_id
        assert st != "failed", "transcode failed"
        time.sleep(1)
    raise AssertionError("timeout waiting for ready")


def expect(client: httpx.Client, method: str, url: str, code: int, **kw) -> None:
    r = client.request(method, url, **kw)
    assert r.status_code == code, f"{method} {url}: expected {code}, got {r.status_code} {r.text[:200]}"


def main() -> int:
    gen_mp4()
    uniq = uuid.uuid4().hex[:8]
    owner = httpx.Client(base_url=BASE, timeout=30)
    viewer = httpx.Client(base_url=BASE, timeout=30)
    register(owner, f"smoke_o_{uniq}")
    register(viewer, f"smoke_v_{uniq}")

    video_id = upload_private(owner, f"smoke private {uniq}")
    vid = f"/api/videos/{video_id}"
    stream = f"/api/videos/{video_id}/stream"
    anon = httpx.Client(base_url=BASE, timeout=30)

    # --- access matrix: private ---
    expect(anon, "GET", vid, 403)
    expect(viewer, "GET", vid, 403)
    expect(viewer, "GET", stream, 403)
    expect(owner, "GET", vid, 200)
    expect(owner, "GET", stream, 200)

    # --- share to viewer ---
    share = owner.post(f"{vid}/shares", json={"username": f"smoke_v_{uniq}"})
    assert share.status_code == 201, f"share: {share.status_code} {share.text}"
    expect(owner, "GET", f"{vid}/shares", 200)
    expect(viewer, "GET", vid, 200)
    expect(viewer, "GET", stream, 200)
    expect(anon, "GET", vid, 403)

    # --- remove share ---
    shared_user_id = share.json()["user_id"]
    expect(owner, "DELETE", f"{vid}/shares/{shared_user_id}", 204)
    expect(viewer, "GET", vid, 403)

    # --- my videos (owner sees private) ---
    mine = owner.get("/api/videos/mine").json()["items"]
    assert any(v["id"] == video_id for v in mine), "private video missing from /mine"

    # --- reports: viewer reports, duplicate 409, owner self-report 400 ---
    rep = viewer.post("/api/reports/", json={"video_id": video_id, "reason": "spam"})
    assert rep.status_code == 201, f"report: {rep.status_code} {rep.text}"
    expect(viewer, "POST", "/api/reports/", 409, json={"video_id": video_id, "reason": "again"})
    expect(owner, "POST", "/api/reports/", 400, json={"video_id": video_id, "reason": "own"})
    expect(viewer, "GET", "/api/reports/mine", 200)

    # --- role checks: normal user blocked from moderation/admin ---
    expect(viewer, "GET", "/api/moderation/reports", 403)
    expect(viewer, "POST", "/api/moderation/resolve", 403, json={"video_id": video_id, "action": "hide"})
    expect(viewer, "GET", "/api/admin/users", 403)
    expect(anon, "GET", "/api/admin/users", 401)

    print("✅ M3 smoke PASSED: private matrix, share/unshare, my videos, reports, role checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
