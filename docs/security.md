# Security Design (≤1 page)

## Authentication

- **Password hashing**: argon2id (memory-hard, salt per hash)
- **Tokens**: JWT access (15 min, HS256) + JWT refresh (30 days, HS256, separate secret)
- **Transport**: both tokens in httpOnly, SameSite=Lax cookies (no localStorage)
- **Secure flag**: env-driven (`COOKIE_SECURE`, default false for HTTP dev)
- **Rate limiting**: login endpoint rate-limited (5 req/s per IP)
- **Refresh rotation**: refresh via cookie AND request body accepted

## Authorization

- **Server-side enforcement**: every protected endpoint checks ownership or role via FastAPI dependencies
- **Roles**: user < moderator < admin
- **Video privacy**:
  - `public`: anyone can view
  - `private`: only owner + explicitly shared users
  - `unlisted`: anyone with the link (no feed/search listing)
  - `hidden`: moderation-removed, no one can view (return 404)
- **Media access**: stream/poster endpoints enforce same privacy rules as metadata
- **Self-guard**: admins cannot deactivate or demote themselves

## Storage Security

- **SeaweedFS port 8333 not published** — reachable only from internal Docker network
- **nginx proxy**: `/storage/...` routes to SeaweedFS, stripping the prefix; no direct S3 access
- **Presigned uploads**: client PUTs to a time-limited presigned URL (signed for `seaweedfs:8333`)
- **No temp files on API nodes** — uploads go directly to S3
- **Short-TTL presigned GET** for streaming (minutes, not hours)

## Input Validation

- **Pydantic v2** validates all request bodies, query params, and path params
- **Upload size limit**: 500 MB max (`UPLOAD_MAX_SIZE`)
- **Allowed MIME**: video/* only (validated at upload init)
- **SQL injection**: not possible (SQLAlchemy ORM, no raw SQL string building)
- **XSS**: no `v-html` with user content; CSP via nginx `X-Content-Type-Options: nosniff`

## Secrets & Config

- All secrets in `.env` (gitignored)
- `.env.example` has placeholder values only
- `install.sh` generates random 32-char hex secrets on first run
- No hardcoded credentials, API keys, or hostnames

## Headers (nginx)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

## Worker

- Jobs dequeued via `SELECT ... FOR UPDATE SKIP LOCKED` — no races
- Max 3 retry attempts per job, then marked `failed`
- Worker runs same image as API — no separate attack surface