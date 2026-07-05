"""Password hashing and JWT helpers (access + refresh tokens)."""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt has a hard 72-byte limit on the password input.
_BCRYPT_MAX_BYTES = 72

# Token "type" claim values. We tag every token so a refresh token can never
# be used where an access token is expected (and vice-versa).
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# ---------- Password ----------
def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT ----------
def create_access_token(subject: str | int, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict = {"sub": str(subject), "exp": expire, "type": ACCESS_TOKEN_TYPE}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | int) -> tuple[str, str]:
    """Create a refresh token.

    Returns (token, jti). The jti (unique id) is stored server-side in Redis so
    the token can be revoked / rotated.
    """
    jti = uuid.uuid4().hex
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": REFRESH_TOKEN_TYPE,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti


def decode_token(token: str) -> dict | None:
    """Decode and verify a token's signature/expiry. Returns payload or None."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


# Backwards-compatible alias used elsewhere in the codebase.
def decode_access_token(token: str) -> dict | None:
    return decode_token(token)
