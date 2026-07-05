"""Extract client metadata (IP, browser, OS, device) from a request."""
from datetime import datetime, timezone

from fastapi import Request
from user_agents import parse as parse_ua


def _client_ip(request: Request) -> str:
    """Best-effort real client IP, honoring common proxy headers."""
    # X-Forwarded-For: client, proxy1, proxy2 -> take the first entry.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


def _device_type(ua) -> str:
    if ua.is_bot:
        return "bot"
    if ua.is_tablet:
        return "tablet"
    if ua.is_mobile:
        return "mobile"
    if ua.is_pc:
        return "desktop"
    return "other"


def client_meta(request: Request) -> dict:
    """Return a JSON-serializable dict describing the current client."""
    raw_ua = request.headers.get("user-agent", "")
    ua = parse_ua(raw_ua)
    return {
        "login_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ip": _client_ip(request),
        "device": _device_type(ua),
        "os": (f"{ua.os.family} {ua.os.version_string}".strip()) or "unknown",
        "browser": (f"{ua.browser.family} {ua.browser.version_string}".strip()) or "unknown",
        "user_agent": raw_ua[:400],
    }
