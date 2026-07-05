"""File (uploaded object) ORM model.

Each row is metadata for one object stored in the ArvanCloud bucket. The binary
itself lives in object storage; only the key + descriptive fields live in the DB
so we can list, search, edit and delete efficiently.
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FileObject(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Who uploaded it.
    owner_id: Mapped[int] = mapped_column( Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    # User-given display name (searchable).
    display_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    # Original filename as uploaded by the client.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Key of the object inside the bucket (unique).
    object_key: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)

    content_type: Mapped[str] = mapped_column(String(150), nullable=False, default="application/octet-stream")
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FileObject id={self.id} name={self.display_name!r} size={self.size}>"
