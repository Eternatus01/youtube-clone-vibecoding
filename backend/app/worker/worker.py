import asyncio

from app.core.config import settings


async def run_worker():
    print(f"Worker starting... bucket={settings.s3_bucket}")
    # Will poll jobs table with FOR UPDATE SKIP LOCKED
    while True:
        await asyncio.sleep(5)
        # Placeholder: dequeue and process transcode jobs