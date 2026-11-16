"""Small in-process rate limiter for authentication endpoints.

The application runs as a single API process behind nginx, so an in-memory
sliding window is sufficient. Keys are scoped by client IP and login value.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, limit: int = 10, window_seconds: int = 60) -> None:
    """Raise HTTP 429 when ``key`` exceeded ``limit`` hits in the window."""
    now = time.monotonic()
    bucket = _ATTEMPTS[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, try again later",
            headers={"Retry-After": str(window_seconds)},
        )
    bucket.append(now)


def reset_rate_limits() -> None:
    """Clear all counters (used by tests)."""
    _ATTEMPTS.clear()