import asyncio
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.minio_client import get_s3_client
from app.routers import (
    admin,
    auth,
    channels,
    comments,
    moderation,
    playlists,
    reports,
    search,
    uploads,
    videos,
)

MODE = os.environ.get("MODE", "api")


def create_app() -> FastAPI:
    app = FastAPI(
        title="YouTube Clone API",
        version="0.1.0",
        description="YouTube clone backend: upload, transcode, stream, comment, moderate.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for r in (
        auth.router,
        uploads.router,
        videos.router,
        comments.router,
        channels.router,
        playlists.router,
        search.router,
        reports.router,
        moderation.router,
        admin.router,
    ):
        app.include_router(r)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "mode": MODE}

    return app


app = create_app()


async def startup():
    # Create bucket if missing
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        s3.create_bucket(Bucket=settings.minio_bucket)

    # Run migrations
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def run_api():
    import uvicorn

    asyncio.run(startup())
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, log_level=settings.log_level.lower())


def run_worker():
    import asyncio

    from app.worker.worker import run_worker

    asyncio.run(run_worker())


def run_seed():
    import asyncio

    from app.scripts.seed import run_seed

    asyncio.run(run_seed())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        run_seed()
    elif MODE == "worker":
        run_worker()
    else:
        run_api()