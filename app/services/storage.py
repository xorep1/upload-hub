"""Object storage helper for the ArvanCloud (S3-compatible) bucket.

A single boto3 S3 client is created lazily and reused. Arvan uses path-style
addressing, so we force it here. All functions raise StorageError on failure so
the routers can translate them into clean HTTP responses.
"""
from __future__ import annotations

import uuid
from pathlib import PurePosixPath
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


class StorageError(RuntimeError):
    """Raised when the object storage backend fails or is misconfigured."""


_client = None


def is_configured() -> bool:
    return bool(settings.s3_access_key and settings.s3_secret_key and settings.s3_bucket)


def get_s3():
    """Return a shared, lazily-created S3 client pointed at Arvan."""
    global _client
    if not is_configured():
        raise StorageError(
            "Object storage is not configured. Set S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET."
        )
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region or "default",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": settings.s3_addressing_style},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    return _client


def public_object_url(key: str) -> str:
    """Permanent direct URL for a public-read object.

    Built to match the configured addressing style:
      - virtual : https://<bucket>.<host>/<key>
      - path    : https://<host>/<bucket>/<key>
    """
    endpoint = settings.s3_endpoint_url.rstrip("/")
    if settings.s3_addressing_style == "path":
        return f"{endpoint}/{settings.s3_bucket}/{key}"
    scheme, _, host = endpoint.partition("://")
    return f"{scheme}://{settings.s3_bucket}.{host}/{key}"


def make_key(original_filename: str | None) -> str:
    """Build a unique, collision-free object key that keeps the file extension."""
    suffix = ""
    if original_filename:
        suffix = PurePosixPath(original_filename).suffix[:20]
    return f"uploads/{uuid.uuid4().hex}{suffix}"


def upload_fileobj(fileobj: BinaryIO, key: str, content_type: str | None = None) -> None:
    s3 = get_s3()
    extra = {"ContentType": content_type or "application/octet-stream"}
    if settings.s3_public_read:
        extra["ACL"] = "public-read"
    try:
        s3.upload_fileobj(fileobj, settings.s3_bucket, key, ExtraArgs=extra)
    except (ClientError, BotoCoreError) as exc:  # noqa: BLE001
        raise StorageError(f"Upload failed: {exc}") from exc


def object_url(key: str, download_name: str | None = None) -> str:
    """Return the best URL for reading an object.

    Public-read buckets get a permanent direct link; private buckets get a
    short-lived presigned link (optionally forcing a download filename).
    """
    if settings.s3_public_read:
        return public_object_url(key)
    return presigned_download_url(key, download_name)


def delete_object(key: str) -> None:
    s3 = get_s3()
    try:
        s3.delete_object(Bucket=settings.s3_bucket, Key=key)
    except (ClientError, BotoCoreError) as exc:  # noqa: BLE001
        raise StorageError(f"Delete failed: {exc}") from exc


def presigned_download_url(key: str, download_name: str | None = None) -> str:
    """A short-lived GET URL. Optionally forces a download filename."""
    s3 = get_s3()
    params = {"Bucket": settings.s3_bucket, "Key": key}
    if download_name:
        safe = download_name.replace('"', "")
        params["ResponseContentDisposition"] = f'attachment; filename="{safe}"'
    try:
        return s3.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=settings.download_url_ttl_seconds
        )
    except (ClientError, BotoCoreError) as exc:  # noqa: BLE001
        raise StorageError(f"Could not create download link: {exc}") from exc


def bucket_ping() -> dict:
    """Best-effort live check of the bucket (used by the admin health/status)."""
    try:
        s3 = get_s3()
        s3.head_bucket(Bucket=settings.s3_bucket)
        return {"status": "up"}
    except StorageError as exc:
        return {"status": "unconfigured", "error": str(exc)}
    except (ClientError, BotoCoreError) as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}
