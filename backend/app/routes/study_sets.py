import io
import logging
import os
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, storage
from app.auth import get_current_user
from app.db import get_db
from app.models import SourceFile, StudySet, User
from app.schemas import StudySetCreated, StudySetDetail, StudySetListItem

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/study-sets")

TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".webm", ".mp4"}
MAX_TITLE_CHARS = 200


def safe_filename(name: str) -> str:
    """Keep storage keys to plain ASCII; the original name is stored separately for display."""
    base, ext = os.path.splitext(os.path.basename(name))
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")[:80] or "file"
    return base + ext.lower()


def get_owned_set(db: Session, user: User, set_id: int) -> StudySet:
    """The study set if it belongs to this user; 404 otherwise (don't reveal others' sets exist)."""
    study_set = db.scalar(select(StudySet).where(StudySet.id == set_id, StudySet.user_id == user.id))
    if study_set is None:
        raise HTTPException(status_code=404, detail="Study set not found.")
    return study_set


def validate_upload(upload: UploadFile) -> str:
    """Check extension and size of one uploaded file; returns its kind (text | audio)."""
    name = upload.filename or ""
    ext = os.path.splitext(name)[1].lower()
    if ext in TEXT_EXTENSIONS:
        kind = "text"
    elif ext in AUDIO_EXTENSIONS:
        kind = "audio"
    else:
        allowed = ", ".join(sorted(TEXT_EXTENSIONS | AUDIO_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f'"{name}" has an unsupported type. Allowed: {allowed}.')
    if not upload.size:
        raise HTTPException(status_code=400, detail=f'"{name}" is empty.')
    if upload.size > config.MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f'"{name}" is larger than {config.MAX_FILE_MB} MB.')
    return kind


@router.post("", response_model=StudySetCreated, status_code=201)
def create_study_set(
    title: Annotated[str | None, Form()] = None,
    text: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files = files or []
    text = (text or "").strip()
    title = (title or "").strip() or None

    # Validate everything before storing anything.
    if not files and not text:
        raise HTTPException(status_code=400, detail="Upload at least one file or paste some text.")
    if len(files) > config.MAX_FILES_PER_SET:
        raise HTTPException(status_code=400, detail=f"You can upload at most {config.MAX_FILES_PER_SET} files.")
    if len(text) > config.MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=400, detail=f"Pasted text is too long (max {config.MAX_INPUT_CHARS:,} characters)."
        )
    if title and len(title) > MAX_TITLE_CHARS:
        raise HTTPException(status_code=400, detail=f"Title is too long (max {MAX_TITLE_CHARS} characters).")
    kinds = [validate_upload(f) for f in files]

    study_set = StudySet(user_id=user.id, title=title, status="queued")
    db.add(study_set)
    db.flush()  # assigns study_set.id, needed for the storage keys

    # Pasted text becomes a .txt source file, so every input follows the same path later.
    sources = [(f.filename, kind, f.content_type or "", f.size, f.file) for f, kind in zip(files, kinds)]
    if text:
        data = text.encode("utf-8")
        sources.append(("pasted-text.txt", "text", "text/plain", len(data), io.BytesIO(data)))

    saved_keys = []
    try:
        for position, (filename, kind, content_type, size, fileobj) in enumerate(sources, start=1):
            key = f"users/{user.id}/sets/{study_set.id}/{position}-{safe_filename(filename)}"
            storage.save(key, fileobj)
            saved_keys.append(key)
            db.add(SourceFile(
                study_set_id=study_set.id, position=position, original_filename=filename, kind=kind,
                content_type=content_type, size_bytes=size, storage_key=key,
            ))
        db.commit()
    except Exception:
        # Don't leave orphaned files behind when the upload fails half-way.
        db.rollback()
        for key in saved_keys:
            storage.delete(key)
        raise

    # Processing (a Celery task) is enqueued here from Phase 2 on.
    return {"id": study_set.id}


@router.get("", response_model=list[StudySetListItem])
def list_study_sets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(StudySet).where(StudySet.user_id == user.id).order_by(StudySet.created_at.desc())
    ).all()


@router.get("/{set_id}", response_model=StudySetDetail)
def get_study_set(set_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_owned_set(db, user, set_id)


@router.delete("/{set_id}", status_code=204)
def delete_study_set(set_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    study_set = get_owned_set(db, user, set_id)
    keys = [f.storage_key for f in study_set.source_files]
    db.delete(study_set)  # rows below it are removed by ON DELETE CASCADE
    db.commit()
    # Files go after the commit: a leftover file is harmless, a row pointing at a missing file is not.
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            log.exception("Could not delete stored file %s", key)
