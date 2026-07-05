"""Pydantic schemas for the file upload / listing feature."""
from datetime import datetime

from pydantic import BaseModel, Field


def human_size(num: int) -> str:
    """Render a byte count as a human-readable string (e.g. '12.4 MB')."""
    size = float(num or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class FileUpdateRequest(BaseModel):
    """Edit a file's metadata (name / description). Both optional."""
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class FileResponse(BaseModel):
    id: int
    owner_id: int
    owner_username: str | None = None
    display_name: str
    original_filename: str
    content_type: str
    size: int
    size_human: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    download_url: str | None = None

    model_config = {"from_attributes": True}


class StorageStatus(BaseModel):
    configured: bool
    bucket: str | None = None
    file_count: int
    used_bytes: int
    used_human: str
    quota_bytes: int
    quota_human: str
    free_bytes: int
    free_human: str
    percent: float
    max_upload_bytes: int
    max_upload_human: str
    live: dict | None = None
