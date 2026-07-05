"""User ban handling backed by Redis.

A ban is stored with a TTL equal to its duration, so it auto-expires. A
permanent ban uses no TTL.

Key layout:  ban:{user_id} -> {"reason": ..., "banned_at": ..., "until": ...}
"""
import json
from datetime import datetime, timedelta, timezone

from app.core.redis_client import get_redis


def _key(user_id: int | str) -> str:
    return f"ban:{user_id}"


def ban(user_id: int | str, reason: str, minutes: int | None = None) -> dict:
    """Ban a user for `minutes` (None = permanent). Returns the ban record."""
    r = get_redis()
    now = datetime.now(timezone.utc)
    record = {
        "reason": reason,
        "banned_at": now.isoformat(timespec="seconds"),
        "until": (
            (now + timedelta(minutes=minutes)).isoformat(timespec="seconds")
            if minutes else None
        ),
    }
    payload = json.dumps(record)
    if minutes:
        r.setex(_key(user_id), minutes * 60, payload)
    else:
        r.set(_key(user_id), payload)
    return record


def unban(user_id: int | str) -> None:
    get_redis().delete(_key(user_id))


def get_ban(user_id: int | str) -> dict | None:
    """Return the ban record (with remaining seconds) or None if not banned."""
    r = get_redis()
    raw = r.get(_key(user_id))
    if not raw:
        return None
    try:
        record = json.loads(raw)
    except (ValueError, TypeError):
        record = {"reason": "banned"}
    ttl = r.ttl(_key(user_id))
    record["expires_in"] = ttl if ttl and ttl > 0 else None  # None => permanent
    return record


def is_banned(user_id: int | str) -> bool:
    return get_redis().exists(_key(user_id)) == 1
