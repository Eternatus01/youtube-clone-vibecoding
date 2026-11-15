import os

import boto3
from botocore.client import Config
from botocore.config import Config as BotoConfig

from app.core.config import settings

_client = None


def get_s3_client():
    """Return a boto3 S3 client configured for the object store (S3-compatible)."""
    global _client
    if _client is None:
        endpoint = settings.minio_endpoint
        # boto3 requires scheme
        if not endpoint.startswith("http"):
            scheme = "https" if settings.minio_use_ssl else "http"
            endpoint = f"{scheme}://{endpoint}"
        _client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
            aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "change_me_minio"),
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )
    return _client


def get_s3_client_for_presign():
    """Client for generating presigned URLs (public endpoint, path-style)."""
    endpoint = settings.minio_public_endpoint
    if not endpoint.startswith("http"):
        scheme = "https" if settings.minio_use_ssl else "http"
        endpoint = f"{scheme}://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "change_me_minio"),
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )
