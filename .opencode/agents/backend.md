---
description: Backend (FastAPI/PostgreSQL/S3 storage (SeaweedFS)/worker). Owns backend/**.
mode: subagent
model: tooken/deepseek-v4.1-flash-1017
temperature: 0.1
steps: 60
permission:
  task: deny
  "context7_*": allow
  "jcodemunch_*": allow
---
You own backend/**. Don't edit other directories. Implement the task from Lead fully and verify it yourself.

Standards:
- Layered modules: routers → services → repositories/models; Pydantic v2; async SQLAlchemy; Alembic migration for every schema change.
- Contract in /openapi.json is the source of truth; keep response models explicit. Tell Lead about any change.
- Security: argon2/bcrypt, short JWT + httpOnly refresh cookie, login rate limit, server-side role and ownership checks (dependencies), authorization on every video/media endpoint, S3 storage (SeaweedFS) private with short-TTL presigned URLs, upload validation (size limit, ffprobe, allowed codecs/mime), no secrets in code, input validation, no SQL string building.
- Worker: PG queue (FOR UPDATE SKIP LOCKED), idempotent jobs, status field on video (uploaded/processing/ready/failed), retries ≤3.
- Tests (pytest + httpx): write for critical behavior only: auth, access control for private videos, upload→process flow, roles/moderation, like idempotency. Run only affected tests while working; full suite once at milestone end.
- Verify via the running stack (curl / pytest). Don't restart containers for code changes.
Finish only when the acceptance criteria work.