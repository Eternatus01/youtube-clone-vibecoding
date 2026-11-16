# Database Schema (≤1 page)

13 tables, PostgreSQL. UUIDs as primary keys, `created_at` with timezone.

## Entity-Relationship Diagram

```mermaid
erDiagram
    User ||--o{ Video : owns
    User ||--o{ Comment : writes
    User ||--o{ Like : likes
    User ||--o{ Subscription : subscribes
    User ||--o{ Subscription : subscribed_to
    User ||--o{ Playlist : owns
    User ||--o{ Report : files
    User ||--o{ ModerationAction : performs
    User ||--o{ VideoShare : receives
    Video ||--o{ VideoAsset : has
    Video ||--o{ Comment : has
    Video ||--o{ Like : has
    Video ||--o{ VideoShare : shared_with
    Video ||--o{ Report : reported
    Video ||--o{ ModerationAction : moderated
    Video ||--o{ PlaylistItem : included_in
    Playlist ||--o{ PlaylistItem : contains
    Comment ||--o{ Comment : replies_to

    User {
        uuid id PK
        string username UK
        string email UK
        string password_hash
        enum role "user|moderator|admin"
        string avatar_url nullable
        bool is_active
        timestamp created_at
    }

    Video {
        uuid id PK
        uuid owner_id FK
        string title
        text description nullable
        enum visibility "public|private|unlisted|hidden"
        enum status "uploading|processing|ready|failed"
        bigint views
        int duration_seconds nullable
        timestamp created_at
    }

    VideoAsset {
        uuid id PK
        uuid video_id FK
        string quality "360p|720p|1080p|poster"
        string key "S3 object key"
        bigint size_bytes
        string mime_type
        int width nullable
        int height nullable
    }

    UploadSession {
        uuid id PK
        uuid video_id FK "unique"
        string upload_key "presigned PUT key"
        timestamp expires_at
    }

    Job {
        uuid id PK
        uuid video_id FK
        enum job_type "transcode"
        enum status "pending|running|done|failed"
        int attempts
        jsonb meta nullable
        timestamp created_at
        timestamp updated_at
    }

    VideoShare {
        uuid id PK
        uuid video_id FK
        uuid user_id FK
        timestamp created_at
    }

    Comment {
        uuid id PK
        uuid video_id FK
        uuid author_id FK
        uuid parent_id FK nullable
        text body
        timestamp created_at
    }

    Like {
        uuid id PK
        uuid video_id FK
        uuid user_id FK
        timestamp created_at
    }

    Subscription {
        uuid id PK
        uuid subscriber_id FK
        uuid subscribed_to_id FK
        timestamp created_at
    }

    Playlist {
        uuid id PK
        uuid owner_id FK
        string title
        text description nullable
        enum visibility "public|private|unlisted"
        timestamp created_at
        timestamp updated_at
    }

    PlaylistItem {
        uuid id PK
        uuid playlist_id FK
        uuid video_id FK
        int position
        timestamp added_at
    }

    Report {
        uuid id PK
        uuid video_id FK
        uuid reporter_id FK
        string reason
        enum status "open|resolved"
        timestamp created_at
    }

    ModerationAction {
        uuid id PK
        uuid video_id FK
        uuid moderator_id FK
        string action "hide|restore|delete"
        text reason nullable
        timestamp created_at
    }
```

## Indexes & Constraints

- Unique: `(video_id, user_id)` on likes, shares, subscriptions; `(video_id, quality)` on assets.
- Partial unique: upload session `video_id` where active.
- Case-insensitive unique on `LOWER(username)` and `LOWER(email)`.
- Composite index on `(visibility, status)` for feed queries.
- Fulltext index: `tsvector` on `title || ' ' || description` for search.

## Enums

| Enum | Values |
|------|--------|
| Role | user, moderator, admin |
| Visibility | public, private, unlisted, hidden |
| VideoStatus | uploading, processing, ready, failed |
| JobStatus | pending, running, done, failed |
| JobType | transcode |