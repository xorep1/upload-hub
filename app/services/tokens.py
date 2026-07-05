"""Refresh-token bookkeeping backed by Redis.

We keep the refresh token's unique id (jti) in Redis so we can:
  - revoke a single session (logout)
  - rotate tokens (each refresh issues a new one and invalidates the old)
  - revoke ALL sessions of a user (e.g. after a password change)

The stored value is a JSON blob of session metadata (login time, IP, browser,
device, OS) so the admin panel can display it.

Key layout:  refresh:{user_id}:{jti} -> {json meta}  (TTL == token lifetime)
"""
import json

from app.core.config import settings
from app.core.redis_client import get_redis


def _key(user_id: int | str, jti: str) -> str:
    return f"refresh:{user_id}:{jti}"


def _pattern(user_id: int | str) -> str:
    return f"refresh:{user_id}:*"

def enforce_max_sessions(user_id: int, max_sessions: int = 5) -> None:
    """Finds all active refresh sessions for a user and deletes the oldest one

    if the count exceeds the maximum allowed limit.
    """
    r = get_redis() 
    user_session_keys = list(r.scan_iter(match=f"refresh:{user_id}:*"))
    
    if len(user_session_keys) >= max_sessions:
       
        user_session_keys.sort(key=lambda k: r.ttl(k))
        
        oldest_key = user_session_keys[0]
        r.delete(oldest_key)


def store_refresh(user_id: int | str, jti: str, meta: dict | None = None) -> None:
    r = get_redis()
    ttl = settings.refresh_token_expire_days * 24 * 60 * 60
    r.setex(_key(user_id, jti), ttl, json.dumps(meta or {}))


def is_valid(user_id: int | str, jti: str) -> bool:
    r = get_redis()
    return r.exists(_key(user_id, jti)) == 1


def revoke(user_id: int | str, jti: str) -> None:
    r = get_redis()
    r.delete(_key(user_id, jti))


def revoke_all(user_id: int | str) -> int:
    """Revoke every refresh token of a user. Returns how many were removed."""
    r = get_redis()
    keys = list(r.scan_iter(match=_pattern(user_id)))
    return r.delete(*keys) if keys else 0


def rotate(user_id: int | str, old_jti: str, new_jti: str, meta: dict | None = None) -> None:
    """Invalidate the old refresh token and register the new one."""
    revoke(user_id, old_jti)
    store_refresh(user_id, new_jti, meta)


# ---------- admin / introspection ----------
def _parse_meta(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def list_all() -> list[dict]:
    """Return every active refresh session with its metadata."""
    r = get_redis()
    sessions: list[dict] = []
    
    # استفاده از match و تبدیل کلیدها به رشته (decode_responses اگر در سیستم فعال نباشد)
    for raw_key in r.scan_iter(match="refresh:*"):
        # تبدیل کلید از bytes به str (اگر از قبل رشته نباشد)
        key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
        
        parts = key.split(":", 2)  # refresh:{user_id}:{jti}
        if len(parts) != 3:
            continue
            
        _, user_id, jti = parts
        
        # دریافت دیتا از ردیس و پارس کردن آن
        raw_data = r.get(key)
        meta = _parse_meta(raw_data)
        
        # گارد امنیتی: اگر _parse_meta دیکشنری برنگرداند، آن را یک دیکشنری خالی فرض کن
        if not isinstance(meta, dict):
            meta = {}
            
        sessions.append({
            "user_id": int(user_id),
            "jti": jti,
            "expires_in": r.ttl(key),
            "login_at": meta.get("login_at"),
            "ip": meta.get("ip"),
            "device": meta.get("device"),
            "os": meta.get("os"),
            "browser": meta.get("browser"),
            "user_agent": meta.get("user_agent"),
        })
    return sessions


def count_all() -> int:
    r = get_redis()
    return sum(1 for _ in r.scan_iter(match="refresh:*"))
