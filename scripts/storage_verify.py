"""Storage verification: presigned PUT + Range GET 206 through /storage proxy."""
import os
import subprocess
import sys

import boto3
from botocore.config import Config as BotoConfig

# Config, matching the app
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "seaweedfs:8333")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "dev_secret_key")
S3_BUCKET = os.environ.get("S3_BUCKET", "videos")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
NGINX_STORAGE = os.environ.get("NGINX_STORAGE", "http://nginx/storage")

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{S3_ENDPOINT}",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
)

# 1. Generate a tiny test mp4 (use ffmpeg if available)
test_file = "/tmp/test_verify.mp4"
os.makedirs("/tmp", exist_ok=True)
try:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-movflags", "faststart", test_file],
        capture_output=True, check=True,
    )
    print("Generated test mp4")
except Exception as e:
    print(f"ffmpeg failed: {e}")
    sys.exit(1)

key = "test/test_verify.mp4"

# 2. Generate presigned PUT (against internal s3 endpoint)
put_url = s3.generate_presigned_url(
    "put_object",
    Params={"Bucket": S3_BUCKET, "Key": key, "ContentType": "video/mp4"},
    ExpiresIn=3600,
)
print(f"Presigned PUT URL (internal): {put_url[:80]}...")

# 3. Convert to /storage relative path
from urllib.parse import urlparse
parsed = urlparse(put_url)
storage_put_url = f"{NGINX_STORAGE}{parsed.path}?{parsed.query}"
print(f"Storage PUT URL: {storage_put_url[:80]}...")

# 4. PUT the file through nginx /storage
import urllib.request
with open(test_file, "rb") as f:
    data = f.read()

req = urllib.request.Request(storage_put_url, data=data, method="PUT")
req.add_header("Content-Type", "video/mp4")
try:
    resp = urllib.request.urlopen(req)
    print(f"PUT response: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"PUT failed: {e.code} {e.reason}")
    print(e.read()[:500])
    sys.exit(1)

# 5. Generate presigned GET
get_url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": S3_BUCKET, "Key": key},
    ExpiresIn=3600,
)
parsed_get = urlparse(get_url)
storage_get_url = f"{NGINX_STORAGE}{parsed_get.path}?{parsed_get.query}"

# 6. Range GET 206
req_get = urllib.request.Request(storage_get_url)
req_get.add_header("Range", "bytes=0-1023")
try:
    resp_get = urllib.request.urlopen(req_get)
    print(f"Range GET status: {resp_get.status}")
    assert resp_get.status == 206, f"Expected 206, got {resp_get.status}"
    data_range = resp_get.read()
    assert len(data_range) == 1024, f"Expected 1024 bytes, got {len(data_range)}"
    assert data_range[0:4] == data[0:4], "Content mismatch"
    print(f"Range GET content: OK ({len(data_range)} bytes)")
except urllib.error.HTTPError as e:
    print(f"Range GET failed: {e.code} {e.reason}")
    sys.exit(1)

print("\n✅ Storage verification PASSED: presigned PUT + Range GET 206 via /storage")