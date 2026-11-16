"""M1 smoke: register -> upload init -> PUT -> complete -> worker -> ready -> feed."""
import sys
import time
import uuid

import httpx

BASE = "http://localhost"  # nginx: /api + /storage
import os
MP4 = os.path.join(os.path.dirname(__file__), "smoke.mp4")


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=30)
    uniq = uuid.uuid4().hex[:8]
    uname = f"smoke_{uniq}"

    # 1. register
    r = c.post("/api/auth/register", json={"username": uname, "email": f"{uname}@t.co", "password": "secret123"})
    print("register", r.status_code)
    if r.status_code != 201:
        print(r.text)
        return 1

    # 2. upload init
    with open(MP4, "rb") as f:
        data = f.read()
    r = c.post("/api/uploads/init", json={"filename": "smoke.mp4", "content_type": "video/mp4", "size_bytes": len(data), "title": "smoke test", "description": None, "visibility": "public"})
    print("init", r.status_code)
    if r.status_code != 201:
        print(r.text)
        return 1
    init = r.json()
    video_id = init["video_id"]
    session_id = init["upload_session_id"]
    upload_url = init["upload_url"]

    # 3. PUT to presigned URL (relative /storage path, via nginx)
    put_url = f"http://localhost{upload_url}"
    r = httpx.put(put_url, content=data, headers={"Content-Type": "video/mp4"}, timeout=60)
    print("put", r.status_code)

    # 4. complete
    r = c.post("/api/uploads/complete", json={"upload_session_id": session_id})
    print("complete", r.status_code)
    if r.status_code != 200:
        print(r.text)
        return 1

    # 5. poll video until ready
    for _ in range(60):
        r = c.get(f"/api/videos/{video_id}")
        st = r.json().get("status")
        if st == "ready":
            print("status ready", r.json().get("duration_seconds"))
            break
        if st == "failed":
            print("FAILED")
            return 1
        time.sleep(1)
    else:
        print("timeout waiting for ready")
        return 1

    # 6. feed
    r = c.get("/api/videos/", params={"page": 1, "page_size": 20})
    titles = [v["title"] for v in r.json().get("items", [])]
    print("feed", r.status_code, "smoke in feed:", "smoke test" in titles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
