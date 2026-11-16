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

## M6 Navigation, History, Subscriptions
Goal: finish missing user-facing functionality before UI polish.

Backend:
- Inspect existing channel, views and subscription implementations first; reuse them instead of creating duplicate endpoints or tables.
- Own channel endpoint: resolve the authenticated user's channel/profile.
- Watch history for authenticated users:
  - record a video when playback/view is registered;
  - repeated views update `last_watched_at`, not create duplicate rows;
  - store progress_seconds if frontend sends playback progress;
  - paginated newest-first history endpoint;
  - remove one item and clear own history;
  - exclude videos the current user can no longer access.
- Subscriptions:
  - idempotent subscribe/unsubscribe;
  - list channels subscribed to by current user;
  - paginated feed containing ready public videos from subscribed channels, newest first;
  - correct subscriber count;
  - private, hidden and processing videos never appear.
- Add an Alembic migration only if the current schema lacks the required history data.
- Add targeted tests for authorization, idempotency, filtering and pagination.

Frontend:
- User/avatar menu: working “Мой канал” link for the authenticated user.
- Sidebar: working “История” and “Подписки” routes; active states.
- History page: newest first, progress indicator when available, remove item, clear history, loading/empty/error states.
- Subscriptions page: subscribed-channel list and video feed; subscribe buttons update without reload and correctly reflect server state.
- Guests clicking protected links are redirected to login and then returned to the requested page.
- Use generated OpenAPI types; do not duplicate API interfaces.

DoD:
1. User menu → “Мой канал” opens the current user's channel.
2. Watching a video makes it appear once in History; watching again moves it to the top.
3. Removing and clearing history work only for its owner.
4. Subscribe → channel appears in Subscriptions and its public ready videos appear in the feed.
5. Unsubscribe removes the channel/feed items without a page reload.
6. Private, hidden and processing videos never leak.
7. Backend affected tests, vue-tsc and frontend build pass.

## M7 Design (per docs/design.md, days 11-13)
Goal: match YouTube 2024 look from design spec. Anti-slop rules (no gradients, no glassmorphism, no hover scale, no card borders, no emoji icons). lucide-vue-next icons, @fontsource/roboto self-hosted, CSS tokens per spec.

Phases (max 2 parallel per phase):
- Phase A: CSS tokens rewrite + @fontsource/roboto + lucide-vue-next setup + global styles
- Phase B: App.vue (header, sidebar 240px, search, user menu, theme) + Toast system
- Phase C: HomePage (chips row) + VideoCard (avatar, no hover scale, proper layout) + skeleton precision
- Phase D: WatchPage, ChannelPage, SearchPage full redesign
- Phase E: UploadPage (drag-drop, 840px max), Auth pages (centered 380px), SubscriptionsPage, HistoryPage polish
- Phase F: ModerationPage + AdminPage (dense table, status pills)
- Phase G: Empty/error states, confirm dialogs, responsive pass (1312/1015/792 breakpoints)

## Status
- M0–M7 ✅ (see earlier plan or git log).
- Feature batch ✅ (2026-11-16):
  - Like/dislike: separate POST/DELETE /api/videos/{id}/like|dislike, like_status: "like"|"dislike"|null, optimistic UI.
  - Video tags: JSONB column, tag filter on feed, chips row wired on HomePage, tags input on UploadPage.
  - Custom poster: POST /api/uploads/{id}/poster (image), served by get_poster when set.
  - Channel: cover_url + description on User, PATCH /api/channels/me, avatar/cover multipart upload.
  - Comment delete: restricted to moderators only (owner check removed).
  - Bigger VideoCards: min 320px grid, larger fonts, 12px border-radius.
  - ChannelEditPage: username edit, avatar + cover upload with preview.
  - Migration 0003: users.cover_url, users.description, videos.tags, videos.custom_poster_url.
  - 46 tests pass. Backend + frontend built. vue-tsc clean.

- ⚠ SeaweedFS S3 root returns 403 (no auth) → healthcheck uses `nc -z 8333`.
- ⚠ Clean Ubuntu VM test not done (no VM available on Windows dev machine).