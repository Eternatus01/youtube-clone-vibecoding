# Architecture (≤1 page)

## Overview
YouTube clone: upload, transcode, stream, comment, moderate.

```
Browser ──► nginx:80 ──► api:8000 ──► PostgreSQL
                   │                └─► MinIO (media)
                   └── /storage ──► MinIO (public media)
    Worker (same image, cron) ──► PostgreSQL + MinIO + ffmpeg
```

## Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, Alembic
- **Auth**: JWT access (15 min) + refresh (30 days) in httpOnly cookies
- **DB**: PostgreSQL — users, videos, comments, likes, subs, playlists, reports
- **Storage**: MinIO — raw uploads → worker transcodes → streamable media (3 qualities)
- **Worker**: same backend image, PG queue (FOR UPDATE SKIP LOCKED), ffmpeg
- **Frontend**: Vue 3 + TypeScript + Vite, Pinia, openapi-fetch

## Flows
1. **Upload**: PUT presigned URL → MinIO → API job enqueue → worker picks → ffprobe + ffmpeg transcode (360p/720p/1080p) → mark ready
2. **Stream**: static reverse-proxy `/storage` → MinIO → HLS/DASH or progressive mp4 via Range requests
3. **Auth**: POST /api/auth/login → JWT pair in httpOnly cookies → middleware reads from cookies
4. **Video privacy**: API enforces: private = only owner + shared users; unlisted = with link; hidden = mod-removed
5. **Moderation**: user reports → mod review → mod hide/show video

## Key decisions
- Worker polls PG — no message broker needed
- Pre-signed uploads — no temporary files on API node
- Frontend generates typed client from /openapi.json — no manual fetch wrapping