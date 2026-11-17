# Архитектура

## Обзор

```
Браузер ──► nginx:80 ──► api:8000 ──► PostgreSQL
                 │            └─────► SeaweedFS (S3 API)
                 └── /storage (presigned PUT/GET) ──► SeaweedFS
Worker (тот же образ, polling) ──► PostgreSQL + SeaweedFS + ffmpeg
```

## Стек

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, Alembic.
- **Auth**: JWT access (15 мин) + refresh (30 дней) в httpOnly cookies.
- **БД**: PostgreSQL — 14 таблиц: пользователи, видео, ассеты, сессии загрузки,
  задачи, доступы, комментарии, лайки, подписки, история, плейлисты, жалобы,
  действия модерации.
- **Хранилище**: SeaweedFS (S3 API на 8333) — исходники → worker транскодирует →
  готовые MP4 и превью.
- **Worker**: тот же образ, очередь в PostgreSQL (`FOR UPDATE SKIP LOCKED`),
  ffmpeg/ffprobe.
- **Frontend**: Vue 3 + TypeScript + Vite, Pinia, openapi-fetch; собирается
  multi-stage Dockerfile в nginx-образ.

## Потоки

1. **Загрузка**: API создаёт запись и presigned PUT (подпись против внутреннего
   `seaweedfs:8333`) → браузер PUT-ит файл в `/storage/...` (nginx снимает
   префикс, Host=`seaweedfs:8333`) → `complete` ставит задачу в очередь →
   worker скачивает исходник, делает ffprobe, один rendition
   (высота = min(исходная, 720p), H.264/AAC, faststart) и постер, загружает их
   в S3 и помечает видео `ready`.
2. **Просмотр**: `GET /api/videos/{id}/stream` — Range/206 через API; тот же
   контроль доступа, что и у метаданных. `GET /api/videos/{id}/poster` — превью.
3. **Auth**: `POST /api/auth/login` → пара JWT в httpOnly cookies; зависимости
   читают cookie или `Authorization: Bearer`.
4. **Приватность**: private — владелец, список доступов, модераторы; unlisted —
   по ссылке, но не в ленте и поиске; hidden — только модераторы/админы.
5. **Модерация**: пользователь создаёт жалобу → модератор скрывает или
   восстанавливает видео → действие пишется в журнал.

## Ключевые решения

- SeaweedFS одним контейнером (`weed server -dir=/data -s3`), порт 8333 не
  публикуется; снаружи доступен только nginx `/storage` с проверкой подписи.
- Storage-код зависит только от env (`S3_ENDPOINT`, `S3_ACCESS_KEY`,
  `S3_SECRET_KEY`, `S3_BUCKET`).
- Presigned upload — нет временных файлов на API-узле.
- Worker опрашивает PostgreSQL — брокер не нужен.
- Frontend генерирует типизированный клиент из `/openapi.json`.
- Production-compose без bind mounts; frontend собирается внутри nginx-образа.
