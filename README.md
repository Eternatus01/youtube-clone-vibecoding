# YouTube Clone

Full-stack video sharing platform: upload, transcode, stream, comment, moderate.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic |
| Database | PostgreSQL 16 |
| Storage | SeaweedFS (S3-compatible, private network) |
| Worker | PG queue (FOR UPDATE SKIP LOCKED), ffmpeg transcoding |
| Frontend | Vue 3, TypeScript, Vite, Pinia, vue-router |
| Proxy | nginx (routing, static files, storage proxy) |
| Auth | JWT access (15 min) + refresh (30 days) in httpOnly cookies |
| Infra | Docker Compose, one-command install |

## Quick Start

**Prerequisites**: Docker with Compose plugin.

```bash
git clone <repo-url> youtube-clone
cd youtube-clone
sudo ./install.sh
```

Open `http://<server-ip>` in your browser.

`install.sh` does everything: installs Docker if missing, generates `.env` with random secrets, builds containers, runs migrations, seeds demo data. Safe to re-run.

### Windows Dev

```bash
copy .env.example .env
# Edit passwords/secrets in .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
cd frontend && npm install && npm run dev
```

Frontend dev server: `http://localhost:5173` (proxies API calls to Docker).

## Demo Logins

Seeded by `install.sh` (all passwords: `secret123`):

| Username | Role | Can |
|----------|------|-----|
| `admin` | admin | Everything + user management |
| `moderator` | moderator | Review reports, hide/restore videos |
| `alice` | user | Upload, comment, subscribe |
| `bob` | user | Upload, comment, subscribe |
| `carol` | user | Upload, comment, subscribe |

## Features

- **Upload**: presigned S3 PUT, real progress, ffmpeg transcode (360p/720p/1080p)
- **Watch**: HLS streaming, quality selector, view counting
- **Video privacy**: public / private / unlisted; private video sharing
- **Interactions**: likes, comments, subscriptions, playlists
- **Search**: fulltext (PostgreSQL `websearch_to_tsquery`), channel lists
- **Moderation**: user reports, mod review, hide/restore, action log
- **Admin**: user list, role management (user/moderator/admin), deactivation
- **Auth**: register, login, JWT refresh, password change, profile update
- **API docs**: OpenAPI (Swagger) at `/docs`

## Project Structure

```
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── core/          # Config, security, DB, S3 client
│   │   ├── dependencies/  # Auth & permission dependencies
│   │   ├── models/        # SQLAlchemy models (13 tables)
│   │   ├── repositories/  # Data access layer
│   │   ├── routers/       # Route handlers (11 modules)
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Business logic
│   │   ├── worker/        # Job processor (ffmpeg transcoding)
│   │   └── main.py        # App factory, lifespan, routing
│   ├── alembic/           # DB migrations
│   └── tests/             # pytest + httpx (36 tests)
├── frontend/              # Vue 3 + TypeScript SPA
│   └── src/
│       ├── api/           # Generated typed client (openapi-fetch)
│       ├── components/    # Reusable components
│       ├── pages/         # Route views (11 pages)
│       ├── router/        # vue-router config + guards
│       ├── stores/        # Pinia stores (auth, videos, ...)
│       └── utils/         # Formatting, date helpers
├── docker/                # nginx config, SeaweedFS entrypoint
├── docs/                  # Architecture, DB schema, security, TZ
├── scripts/               # smoke.py, smoke.mp4, build helpers
├── docker-compose.yml     # Production compose
├── docker-compose.dev.yml # Development overrides
├── install.sh             # One-command Ubuntu installer
└── .env.example           # Environment variables template
```

## Architecture

```
Browser ──► nginx:80 ──► api:8000 ──► PostgreSQL
                   │                └─► SeaweedFS (media, S3 API)
                   └── /storage ──► SeaweedFS (public media proxy)
    Worker (same image, cron) ──► PostgreSQL + SeaweedFS + ffmpeg
```

See [docs/architecture.md](docs/architecture.md) for full architecture, [docs/db-schema.md](docs/db-schema.md) for database schema, and [docs/security.md](docs/security.md) for security design.

## AI Agents Used

This project was built with OpenCode using a team of specialized AI agents:

| Agent | Model | Role |
|-------|-------|------|
| **Lead** | DeepSeek V4 Pro | Architecture, DB schema, API contract, Docker/nginx/install.sh, seed, integration, git, README/docs, TZ compliance |
| **Backend** | DeepSeek V4 Pro | FastAPI routers, services, repositories, models, Alembic migrations, tests (pytest), worker |
| **Frontend** | GLM 5.3 Flash | Vue 3 pages, components, Pinia stores, typed API client, router guards, CSS |

### What Each Agent Built

**Lead** (DeepSeek V4 Pro):
- Project scaffolding, Docker Compose, nginx config, install.sh
- Database schema (13 tables: users, videos, video_assets, upload_sessions, jobs, video_shares, comments, likes, subscriptions, playlists, playlist_items, reports, moderation_actions)
- Pydantic schemas and route stubs (API contract)
- S3/SeaweedFS integration, presigned upload flow
- Seed script, smoke tests, integration verification
- docs/ (architecture, DB schema, security, plan)

**Backend** (DeepSeek V4 Pro):
- Auth system: register, login, JWT access/refresh tokens, password change
- Upload pipeline: presigned PUT init, upload session tracking, ffmpeg transcode job enqueue
- Video CRUD with privacy enforcement (public/private/unlisted/hidden)
- Comments, likes (idempotent), subscriptions, playlists
- Search (fulltext), channel lists, view counting
- Moderation: user reports, mod review, video hide/restore, action log
- Admin: user listing, role management, deactivation with self-guard
- 36 pytest tests covering auth, uploads, videos, privacy, interactions, worker

**Frontend** (GLM 5.3 Flash):
- 11 pages: Home (feed), Watch, Upload, Channel, Search, Login, Register, My Videos, Playlist, Moderation, Admin
- YouTube-style layout: top bar with search, collapsible sidebar, responsive video grid
- Dark/light theme, skeleton loaders, error/empty states
- Upload with real progress bar (XHR to presigned URL)
- Route guards by authentication and role
- Typed API client generated from `/openapi.json`

## Running Tests

```bash
# Backend tests (stack must be running)
docker compose exec api pytest -v

# Integration smoke test (privacy + roles matrix)
python scripts/smoke.py
```

## Environment Variables

See `.env.example` for all variables. Key ones:

- `POSTGRES_USER/PASSWORD/DB` — database credentials
- `JWT_SECRET`, `REFRESH_SECRET` — token signing keys
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` — SeaweedFS S3 config
- `COOKIE_SECURE` — set `true` for HTTPS (default `false` for HTTP dev)
- `CORS_ORIGINS` — comma-separated allowed origins
- `LOG_LEVEL` — Python logging level (DEBUG/INFO/WARNING)

## License

This is a test assignment project.