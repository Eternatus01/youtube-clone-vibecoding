# Plan. Lead reads only the requested stage + Global + Status.

## Global
Stack — backend: Python 3.12, FastAPI, SQLAlchemy 2 async (asyncpg), Alembic, Pydantic v2, argon2-cffi, PyJWT, boto3 (or minio-py), pytest+httpx. DB: PostgreSQL. Storage: MinIO. Worker: same backend image, PG queue (FOR UPDATE SKIP LOCKED), ffmpeg/ffprobe.
Frontend: Vue 3, TS, Vite, Pinia, vue-router, openapi-typescript + openapi-fetch, plain CSS variables (no UI framework). Add other libs only with a clear need.

### Deployability (graded: clean Ubuntu, ONE command)
- `sudo ./install.sh`: installs Docker if missing, generates .env with random secrets if absent, `docker compose up -d --build`, migrations run in the api entrypoint, bucket auto-created, waits for health, seeds demo data (idempotent), prints URL + demo logins. Safe to re-run. No host deps except Docker.
- Works on plain HTTP / bare IP: cookie `Secure` flag is env-driven (COOKIE_SECURE, default false). No hardcoded hostnames.
- Windows dev machine: `.gitattributes` with `*.sh text eol=lf`; install.sh committed executable (`git update-index --chmod=+x`).
- Prod compose: no bind mounts, no reload. `docker-compose.dev.yml` override for dev. Frontend built in multi-stage Dockerfile, served by nginx. Only nginx publishes a port (80); db/minio not published. Healthchecks + depends_on conditions.
- Upload limit via env (default 500MB), nginx client_max_body_size matches.
- Media path: bucket private. Browser uploads (single presigned PUT) and plays via nginx `/storage/` → MinIO. Recommended trick: sign against the internal endpoint (minio:9000), return a relative `/storage/<path>?<query>` URL; nginx strips `/storage`, sets Host minio:9000, proxy_buffering/request_buffering off. Prove with a real file in M0. Fallback: stream through API with Range support.
- Seed generates demo videos with ffmpeg (lavfi testsrc), no binaries in repo.

### Security (graded)
Server-side authz on every endpoint incl. media URL issuance; roles user/moderator/admin via dependency; argon2; short JWT + httpOnly SameSite refresh cookie; login rate limit; upload validation (ext + ffprobe + size); same-origin only (no open CORS); nginx security headers; no v-html with user content; pagination limits everywhere; no secrets in repo; hidden/private/unlisted never leak via feed, search, channel, comments or media.

### Verification policy
Developers: affected tests only; full backend suite once at stage end. Lead: `scripts/smoke.py` (API-level: register → upload → ready → view → like → comment; private denied to others) at M3, M4 and on integration failure.

## M0 Foundation (Lead alone, day 1)
- docs/architecture.md (≤40 lines: decisions + why), repo skeleton, .gitattributes, .env.example.
- docker-compose.yml (db, minio, api, worker, nginx) + dev override, Dockerfiles, nginx conf, a working minimal install.sh.
- SQLAlchemy models + first Alembic migration: users, videos, video_assets, upload_sessions, jobs, video_shares, comments, likes, subscriptions, playlists, playlist_items, reports, moderation_actions. Indexes for feed, search (title: pg_trgm/ILIKE), comments.
- Pydantic schemas + route stubs for: auth, uploads, videos, comments, likes, subscriptions, channels, playlists, search, reports, moderation/admin → /openapi.json, /docs.
- Frontend skeleton (Vite, Pinia, router, `npm run gen:api`).
DoD: stack starts from compose, /docs opens, migration applied, frontend builds, presigned PUT + Range GET via /storage proven with a real mp4. Commits.

## M1 Auth + upload + processing + feed (BE ∥ FE, days 2-3)
BE: register/login/refresh/logout/me, role dependency, upload init → complete, worker (ffprobe validation, transcode ≤720p H.264 faststart, poster, duration, status uploaded/processing/ready/failed, retries ≤3), videos list/get, media URL with authz. Tests: auth, upload→ready.
FE: layout (top bar, collapsible sidebar, dark/light theme), login/register, auth store + guards, home feed grid (thumb, duration, title, channel, views, age), upload page (file select, XHR progress, metadata form, status polling).
DoD: register → upload small mp4 → ready → shows on home.

## M2 Watch, interactions, channel, search (BE ∥ FE, days 4-5)
BE: video detail + view counter, like toggle (idempotent), comments (paginated, create, delete own), subscriptions, channel endpoints, playlists CRUD + items, title search, simple recommendations.
FE: watch page (player, like, subscribe, description, comments, recommendations column), channel page (Videos/Playlists tabs, subscribe), playlist page, search results.
DoD: full scenario register → upload → watch → like → comment → subscribe → search.

## M3 Privacy, roles, moderation (BE ∥ FE, day 6)
BE: visibility public/unlisted/private + video_shares (owner manages allowed users), reports (create/list/resolve), hide/unhide by moderator (moderation_status, not delete), admin sets roles, owner edit/delete. Tests: access matrix (anonymous / other user / shared / owner / moderator / admin × public / unlisted / private / hidden × metadata / media / comments / search / feed). Must pass.
FE: visibility selector + share management, "my videos" edit/delete, report button, moderation screen, minimal admin roles screen.
DoD: matrix green + smoke.py.

## M4 Delivery (Lead, days 7-8)
- scripts/seed.py (idempotent): admin, moderator, 3 users, ~10 videos (incl. private, unlisted, hidden), comments, likes, subscriptions, a playlist, a report.
- install.sh hardened, README (quick start, demo logins, tests), docs/: architecture.md, DB schema (mermaid ER, ≤1 page), security.md (≤1 page).
- Full backend suite once; smoke.py.
- USER tests on a clean Ubuntu VM and sends the error output; Lead fixes.
DoD: one command on clean Ubuntu → scenario works with seed data.

## M5 Polish + TZ check (day 9, day 10 = buffer)
FE: YouTube look (spacing, typography, skeletons, responsive, empty/error states). Lead: checklist TZ screens/requirements vs implemented, fix gaps, final README. No new features beyond TZ.

## Status
- M0 ✅: skeleton. Stack up: PostgreSQL, SeaweedFS 4.53 (S3), api, worker, nginx. Migration 0001 (14 tables). /docs + /openapi.json 200. Frontend builds (Vite+TS).
- M1 ✅: auth (register/login/refresh/logout/me/change-password, JWT httpOnly cookies, rate limit), upload (presigned init→complete→transcode job), worker (ffprobe validate, ≤720p H.264 faststart + poster, retries ≤3), videos feed + get/stream/poster with visibility authz (private/unlisted 403, hidden 404 except mod/admin), owner/mod/admin role checks server-side. Layered routers→services→repositories. Tests 22 (auth/upload/video/worker, yt_test + fake S3).
- FE: top bar + collapsible sidebar + dark/light theme, login/register, auth store + guards, home feed grid, upload page (presigned PUT + progress + polling).
- ✅ Verified E2E: register→init→PUT→complete→ready(2s)→feed; private video 403 meta/stream/poster to others, 200 to owner; /docs + /openapi.json (34 paths) 200; S3 port 8333 not published.
- ⚠ SeaweedFS S3 root returns 403 (no auth) → healthcheck uses `nc -z 8333`. Old CloudServer `s3_data` volume orphaned (harmless).
- ⚠ Worker image has no bind mount (prod build) — rebuild after backend changes: `docker compose build worker && docker compose up -d worker`.
- Not done (M2+): like/unlike, comments, subscriptions, channel, playlists, search, moderation, admin, seed (still no-op stub).
- Next M2: watch page, interactions, channel, search, recommendations.