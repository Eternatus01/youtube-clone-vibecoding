import boto3
from botocore.config import Config as BotoConfig
from urllib.parse import urlparse

from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.s3_endpoint}",
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def generate_presigned_put(key: str, expires: int = 3600) -> str:
    """Generate presigned PUT URL, convert to relative /storage/ path."""
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires,
    )
    return _to_storage_path(url)


def generate_presigned_get(key: str, expires: int = 3600) -> str:
    """Generate presigned GET URL, convert to relative /storage/ path."""
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires,
    )
    return _to_storage_path(url)


def _to_storage_path(url: str) -> str:
    """Convert full S3 URL to /storage/ relative path."""
    parsed = urlparse(url)
    if parsed.query:
        return f"/storage{parsed.path}?{parsed.query}"
    return f"/storage{parsed.path}"