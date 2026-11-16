import asyncio
import os
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from botocore.exceptions import ClientError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.db import Base, get_db
from app.core.rate_limit import reset_rate_limits
from app.main import app
from app.models.models import User

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_DB = "postgresql+asyncpg://yt:change_me@db:5432/yt_test"


def _sync_dsn(async_url: str) -> str:
    return async_url.replace("+asyncpg", "").replace("+aiosqlite", "")


def _ensure_database(pg_url: str) -> None:
    import psycopg2
    from sqlalchemy.engine import make_url

    url = make_url(pg_url)
    db_name = url.database or ""
    if not db_name.endswith("_test"):
        raise RuntimeError(f"Refusing to use non-test database '{db_name}'")
    admin = url.set(database="postgres")
    dsn = admin.render_as_string(hide_password=False).replace("+asyncpg", "")
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        conn.close()


def _run_migrations(pg_url: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = pg_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"alembic upgrade failed: {result.stderr[-2000:]}")


@pytest.fixture(scope="session")
def database_url() -> str:
    pg_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DB)
    try:
        _ensure_database(pg_url)
        _run_migrations(pg_url)
        return pg_url
    except Exception as exc:  # noqa: BLE001 - fall back to SQLite for unit runs
        try:
            import aiosqlite  # noqa: F401
        except ImportError:
            pytest.exit(
                f"Postgres test database unavailable ({exc}); "
                "start the stack or install aiosqlite for the SQLite fallback",
                returncode=1,
            )
        sqlite_dir = Path(tempfile.mkdtemp(prefix="yt-tests-"))
        return f"sqlite+aiosqlite:///{sqlite_dir / 'test.db'}"


@pytest_asyncio.fixture
async def db_engine(database_url):
    is_sqlite = database_url.startswith("sqlite")
    engine = create_async_engine(database_url, poolclass=NullPool)
    if is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        tables = ", ".join(
            f'"{t.name}"' for t in Base.metadata.sorted_tables if t.name != "alembic_version"
        )
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _reset_limits():
    reset_rate_limits()
    yield


@pytest.fixture
def app_with_db(session_factory):
    async def _get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_client(app_with_db):
    clients: list[httpx.AsyncClient] = []

    async def _make() -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        clients.append(client)
        return client

    yield _make
    for client in clients:
        await client.aclose()


@pytest_asyncio.fixture
async def client(make_client):
    return await make_client()


class FakeS3:
    """Minimal in-memory S3 stand-in covering the operations the app uses."""

    def __init__(self) -> None:
        self.objects: dict[str, dict] = {}

    def put(self, key: str, data: bytes, content_type: str = "video/mp4") -> None:
        self.objects[key] = {"data": data, "content_type": content_type}

    def generate_presigned_url(self, operation, Params, ExpiresIn=3600, **kwargs):
        return (
            f"http://seaweedfs:8333/{Params['Bucket']}/{Params['Key']}"
            f"?X-Amz-Signature=fake&X-Amz-Expires={ExpiresIn}"
        )

    def _missing(self, key: str) -> ClientError:
        return ClientError({"Error": {"Code": "NoSuchKey", "Message": key}}, "GetObject")

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise self._missing(Key)
        return {"ContentLength": len(self.objects[Key]["data"])}

    def delete_objects(self, Bucket, Delete):
        for item in Delete["Objects"]:
            self.objects.pop(item["Key"], None)
        return {"Deleted": Delete["Objects"]}

    def get_object(self, Bucket, Key, Range=None):
        if Key not in self.objects:
            raise self._missing(Key)
        record = self.objects[Key]
        data = record["data"]
        headers = {
            "ContentType": record["content_type"],
            "ContentLength": len(data),
            "Body": BytesIO(data),
        }
        if Range:
            start, _, end = Range.replace("bytes=", "").partition("-")
            start_i = int(start or 0)
            end_i = int(end) if end else len(data) - 1
            chunk = data[start_i : end_i + 1]
            headers.update(
                {
                    "Body": BytesIO(chunk),
                    "ContentLength": len(chunk),
                    "ContentRange": f"bytes {start_i}-{start_i + len(chunk) - 1}/{len(data)}",
                }
            )
        return headers

    def download_file(self, Bucket, Key, Filename):
        with open(Filename, "wb") as fh:
            fh.write(self.objects[Key]["data"])

    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None):
        with open(Filename, "rb") as fh:
            content_type = (ExtraArgs or {}).get("ContentType", "application/octet-stream")
            self.put(Key, fh.read(), content_type)


@pytest.fixture
def fake_s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr("app.core.s3_client.get_s3_client", lambda: fake)
    monkeypatch.setattr("app.services.uploads.get_s3_client", lambda: fake)
    monkeypatch.setattr("app.services.videos.get_s3_client", lambda: fake)
    monkeypatch.setattr("app.worker.worker.get_s3_client", lambda: fake)
    return fake


async def register_user(client: httpx.AsyncClient, username: str, email: str | None = None):
    response = await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email or f"{username}@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_video_record(
    session_factory,
    *,
    owner: User,
    title: str = "Video",
    visibility: str = "public",
    status: str = "ready",
    assets: list[tuple[str, str, bytes]] | None = None,
):
    from app.models.models import Video, VideoAsset, VideoStatus, Visibility

    async with session_factory() as db:
        video = Video(
            owner_id=owner.id,
            title=title,
            visibility=Visibility(visibility),
            status=VideoStatus(status),
            duration_seconds=12,
        )
        db.add(video)
        await db.flush()
        for quality, key, data in assets or []:
            db.add(
                VideoAsset(
                    video_id=video.id,
                    quality=quality,
                    object_key=key,
                    size_bytes=len(data),
                    content_type="video/mp4" if quality != "poster" else "image/jpeg",
                )
            )
        await db.commit()
        await db.refresh(video)
        return video


async def get_user(session_factory, username: str) -> User:
    from sqlalchemy import select

    async with session_factory() as db:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one()


async def set_role(session_factory, username: str, role: str) -> None:
    from sqlalchemy import select

    from app.models.models import Role

    async with session_factory() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one()
        user.role = Role(role)
        await db.commit()