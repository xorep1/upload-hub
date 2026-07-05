"""File upload / listing / search routes.

Any authenticated user can:
  - upload a file (with a display name) up to MAX_UPLOAD_BYTES
  - list & search everyone's files
  - view details and download (via a short-lived presigned URL)
  - edit / delete their OWN files (admins can edit / delete any)

The binary is stored in the ArvanCloud bucket; only metadata lives in the DB.
"""
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.file import FileObject
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.files import FileResponse, FileUpdateRequest, StorageStatus, human_size
from app.services import storage

router = APIRouter(prefix="/files", tags=["files"])


# ---------- helpers ----------
def _usernames(db: Session, owner_ids: set[int]) -> dict[int, str]:
    if not owner_ids:
        return {}
    rows = db.execute(
        select(User.id, User.username).where(User.id.in_(owner_ids))
    ).all()
    return {uid: uname for uid, uname in rows}


def _serialize(obj: FileObject, username: str | None, with_url: bool = True) -> FileResponse:
    url = None
    if with_url:
        try:
            url = storage.object_url(obj.object_key, obj.original_filename)
        except storage.StorageError:
            url = None
    return FileResponse(
        id=obj.id,
        owner_id=obj.owner_id,
        owner_username=username,
        display_name=obj.display_name,
        original_filename=obj.original_filename,
        content_type=obj.content_type,
        size=obj.size,
        size_human=human_size(obj.size),
        description=obj.description,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        download_url=url,
    )


def used_bytes(db: Session) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(FileObject.size), 0))) or 0)


def compute_storage_status(db: Session, live: bool = False) -> StorageStatus:
    used = used_bytes(db)
    count = int(db.scalar(select(func.count(FileObject.id))) or 0)
    quota = settings.bucket_quota_bytes
    free = max(quota - used, 0)
    pct = round(used / quota * 100, 2) if quota else 0.0
    return StorageStatus(
        configured=storage.is_configured(),
        bucket=settings.s3_bucket or None,
        file_count=count,
        used_bytes=used,
        used_human=human_size(used),
        quota_bytes=quota,
        quota_human=human_size(quota),
        free_bytes=free,
        free_human=human_size(free),
        percent=pct,
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_human=human_size(settings.max_upload_bytes),
        live=storage.bucket_ping() if live else None,
    )


def _can_manage(user: User, obj: FileObject) -> bool:
    return user.is_admin or obj.owner_id == user.id


# ---------- upload ----------
@router.post("", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    name: str = Form(..., min_length=1, max_length=255),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not storage.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Object storage is not configured")

    # Determine size without loading the whole file into memory.
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    if size > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File too large. Max is {human_size(settings.max_upload_bytes)}.",
        )

    # Quota check (used + this file must stay within the bucket quota).
    if used_bytes(db) + size > settings.bucket_quota_bytes:
        raise HTTPException(
            status.HTTP_507_INSUFFICIENT_STORAGE,
            f"Bucket quota exceeded ({human_size(settings.bucket_quota_bytes)}).",
        )

    key = storage.make_key(file.filename)
    try:
        storage.upload_fileobj(file.file, key, file.content_type)
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    obj = FileObject(
        owner_id=current_user.id,
        display_name=name.strip(),
        original_filename=file.filename or "file",
        object_key=key,
        content_type=file.content_type or "application/octet-stream",
        size=size,
        description=(description or None),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _serialize(obj, current_user.username)


# ---------- list / search ----------
@router.get("", response_model=list[FileResponse])
def list_files(
    q: str | None = None,
    mine: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    stmt = select(FileObject)
    if mine:
        stmt = stmt.where(FileObject.owner_id == current_user.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                FileObject.display_name.ilike(like),
                FileObject.original_filename.ilike(like),
                FileObject.description.ilike(like),
            )
        )
    stmt = stmt.order_by(FileObject.created_at.desc()).offset(skip).limit(limit)
    objs = db.scalars(stmt).all()
    names = _usernames(db, {o.owner_id for o in objs})
    return [_serialize(o, names.get(o.owner_id)) for o in objs]


# ---------- storage status ----------
@router.get("/storage", response_model=StorageStatus)
def storage_status(
    live: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return compute_storage_status(db, live=live)


# ---------- details / download ----------
@router.get("/{file_id}", response_model=FileResponse)
def file_details(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    names = _usernames(db, {obj.owner_id})
    return _serialize(obj, names.get(obj.owner_id))


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    try:
        url = storage.object_url(obj.object_key, obj.original_filename)
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return RedirectResponse(url)


# ---------- edit / delete ----------
@router.patch("/{file_id}", response_model=FileResponse)
def update_file(
    file_id: int,
    data: FileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if not _can_manage(current_user, obj):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to edit this file")

    updates = data.model_dump(exclude_unset=True)
    if "display_name" in updates and updates["display_name"]:
        obj.display_name = updates["display_name"].strip()
    if "description" in updates:
        obj.description = updates["description"] or None

    db.add(obj)
    db.commit()
    db.refresh(obj)
    names = _usernames(db, {obj.owner_id})
    return _serialize(obj, names.get(obj.owner_id))


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if not _can_manage(current_user, obj):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to delete this file")

    # Best-effort remove from the bucket, then drop the DB row.
    try:
        storage.delete_object(obj.object_key)
    except storage.StorageError:
        pass  # Even if the object is already gone, we still clear the record.

    db.delete(obj)
    db.commit()
    return {"message": "File deleted."}
