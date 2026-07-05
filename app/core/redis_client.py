"""Redis connection helper.

A single shared client is created lazily and reused across requests.
`decode_responses=True` makes Redis return str instead of bytes.
"""
import redis

from app.core.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client
