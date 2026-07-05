"""OTP + pending-registration handling backed by Redis.

Flow:
1. store_pending_registration() -> validate, store pending user data + generate OTP in Redis
2. verify_code()                 -> check OTP (with attempt limit)
3. regenerate_code()             -> regenerate OTP respecting cooldown
"""
import json
import secrets

from app.core.config import settings
from app.core.redis_client import get_redis


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"

def _attempts_key(phone: str) -> str:
    return f"otp:attempts:{phone}"

def _cooldown_key(phone: str) -> str:
    return f"otp:cooldown:{phone}"

def _pending_key(phone: str) -> str:
    return f"pending:{phone}"


def generate_code() -> str:
    """Cryptographically-strong numeric OTP of configured length."""
    upper = 10 ** settings.otp_length
    return str(secrets.randbelow(upper)).zfill(settings.otp_length)


def is_on_cooldown(phone: str) -> int:
    """Return remaining cooldown seconds (0 if none)."""
    r = get_redis()
    ttl = r.ttl(_cooldown_key(phone))
    return ttl if ttl and ttl > 0 else 0

def set_on_cooldown(phone: str):
    r = get_redis()
    r.setex(_cooldown_key(phone), settings.otp_resend_cooldown, "1")


def store_pending_registration(username: str, phone: str, hashed_password: str) -> str:
    """Save pending registration data + create OTP. Returns the OTP code."""
    r = get_redis()
    code = generate_code()

    r.setex(
        _pending_key(phone),
        settings.registration_ttl_seconds,
        json.dumps({"username": username, "phone": phone, "hashed_password": hashed_password}),
    )
    r.setex(_otp_key(phone), settings.otp_ttl_seconds, code)
    r.setex(_cooldown_key(phone), settings.otp_resend_cooldown, "1")
    r.delete(_attempts_key(phone))
    return code


def get_pending_registration(phone: str) -> dict | None:
    r = get_redis()
    data = r.get(_pending_key(phone))
    return json.loads(data) if data else None


def verify_code(phone: str, code: str) -> tuple[bool, str]:
    """Verify OTP. Returns (ok, message)."""
    r = get_redis()
    stored = r.get(_otp_key(phone))
    if stored is None:
        return False, "OTP expired or not found. Please request a new one."

    attempts = r.incr(_attempts_key(phone))
    r.expire(_attempts_key(phone), settings.otp_ttl_seconds)
    if attempts > settings.otp_max_attempts:
        r.delete(_otp_key(phone))
        return False, "Too many wrong attempts. Please request a new OTP."

    if not secrets.compare_digest(stored, code):
        return False, "Invalid OTP code."

    # success -> consume otp
    r.delete(_otp_key(phone))
    r.delete(_attempts_key(phone))
    return True, "OTP verified."


def clear_pending(phone: str) -> None:
    r = get_redis()
    r.delete(_pending_key(phone), _cooldown_key(phone))


def regenerate_code(phone: str) -> str:
    """Create a fresh OTP for an existing pending registration."""
    r = get_redis()
    code = generate_code()
    r.setex(_otp_key(phone), settings.otp_ttl_seconds, code)
    r.setex(_cooldown_key(phone), settings.otp_resend_cooldown, "1")
    r.delete(_attempts_key(phone))
    return code
