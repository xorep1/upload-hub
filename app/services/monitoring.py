"""System resource + service-health helpers for the admin panel."""
import time

import psutil
from sqlalchemy import text

from app.core.redis_client import get_redis
from app.database import engine


def system_stats() -> dict:
    """CPU, memory and disk usage of the host running the API."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "cpu_count": psutil.cpu_count(),
        "memory": {
            "total_mb": round(mem.total / 1024 / 1024, 1),
            "used_mb": round(mem.used / 1024 / 1024, 1),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
            "percent": disk.percent,
        },
    }


def _check_redis() -> dict:
    try:
        r = get_redis()
        start = time.perf_counter()
        r.ping()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {"service": "redis", "status": "up", "latency_ms": latency}
    except Exception as exc:  # noqa: BLE001
        return {"service": "redis", "status": "down", "error": str(exc)}


def _check_db() -> dict:
    try:
        start = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {"service": "database", "status": "up", "latency_ms": latency}
    except Exception as exc:  # noqa: BLE001
        return {"service": "database", "status": "down", "error": str(exc)}


def health() -> dict:
    checks = [_check_db(), _check_redis()]
    overall = "up" if all(c["status"] == "up" for c in checks) else "degraded"
    return {"overall": overall, "services": checks}
