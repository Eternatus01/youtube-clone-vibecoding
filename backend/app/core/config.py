from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    database_url: str = "postgresql+asyncpg://yt:change_me@db:5432/yt"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "minio:9000"
    minio_bucket: str = "videos"
    minio_use_ssl: bool = False

    # Auth
    jwt_secret: str = "dev_secret"
    refresh_secret: str = "dev_refresh"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    # App
    cookie_secure: bool = False
    cors_origins: str = "http://localhost"
    upload_max_size: int = 524288000
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
