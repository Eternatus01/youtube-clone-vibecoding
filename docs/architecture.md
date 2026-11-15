# Architecture (≤1 page)

## Overview
YouTube clone: upload, transcode, stream, comment, moderate.

```
Browser ──► nginx:80 ──► api:8000 ──► PostgreSQL
                   │                └─► SeaweedFS (media, S3 API)
                   └── /storage ──► SeaweedFS (public media proxy)
    Worker (same image, cron) ──► PostgreSQL + SeaweedFS + ffmpeg
```

## Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, Alembic
- **Auth**: JWT access (15 min) + refresh (30 days) in httpOnly cookies
- **DB**: PostgreSQL — users, videos, comments, likes, subs, playlists, reports
- **Storage**: SeaweedFS (S3 API on :8333) — raw uploads → worker transcodes → streamable media
- **Worker**: same backend image, PG queue (FOR UPDATE SKIP LOCKED), ffmpeg
- **Frontend**: Vue 3 + TypeScript + Vite, Pinia, openapi-fetch

## Flows
1. **Upload**: API presigns PUT (signed against internal `seaweedfs:8333`) → client PUTs to `/storage/...` (nginx strips `/storage`, Host=`seaweedfs:8333`) → API enqueues job → worker ffprobe + ffmpeg transcode (360p/720p/1080p) → mark ready
2. **Stream**: presigned GET or Range GET via `/storage/...` proxy
3. **Auth**: POST /api/auth/login → JWT pair in httpOnly cookies → middleware reads from cookies
4. **Video privacy**: API enforces: private = only owner + shared users; unlisted = with link; hidden = mod-removed
5. **Moderation**: user reports → mod review → mod hide/show video

## Key decisions
- SeaweedFS single container (`weed server -dir=/data -s3`), port not published — reachable only via nginx `/storage`
- Storage code depends only on env (S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET), fixed region
- Pre-signed uploads — no temporary files on API node
- Worker polls PG — no message broker needed
- Frontend generates typed client from /openapi.json — no manual fetch wrapping