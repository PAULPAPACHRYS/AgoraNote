"""
Endpoints for study sets: create (upload), list, view, retry and delete

    POST   /api/study-sets              upload files and/or pasted text -> {"id": ...}
    GET    /api/study-sets              the dashboard list
    GET    /api/study-sets/{id}         one set: status while processing, chapters when ready
    POST   /api/study-sets/{id}/retry   run processing again after a failure
    DELETE /api/study-sets/{id}         delete the set, its rows and its stored files

Creating a set only stores the files and queues a background task; the actual work (text
extraction, transcription, AI generation) happens in the worker (see worker.py)
The browser polls GET /api/study-sets/{id} to show the progress
"""
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
from app.gamification import load_chapter_scores, progress
from app.models import SourceFile, StudySet, User
from app.schemas import StudySetCreated, StudySetDetail, StudySetListItem
from app.worker import process_study_set

log = logging.getLogger(__name__)
#every route below is relative to this prefix: @router.get("") is GET /api/study-sets
router = APIRouter(prefix="/api/study-sets")

# accepted file types. "text" files are read directly; "audio" (also video) files are transcribed
TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".webm", ".mp4"}
MAX_TITLE_CHARS = 200


def safe_filename(name: str) -> str:
    """
    keep storage keys to plain ASCII; the original name is stored separately for display
    E.g. "Σημειώσεις 1.pdf" -> "file.pdf" and "My notes (v2).docx" -> "My_notes_v2.docx"
    """
    base, ext = os.path.splitext(os.path.basename(name))  # basename: ignore any folder in the name
    # every run of other characters becomes one "_"; at most 80 characters; never empty
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")[:80] or "file"
    return base + ext.lower()


def get_owned_set(db: Session, user: User, set_id: int) -> StudySet:
    #The study set if it belongs to this user, 404 otherwise (don't reveal others' sets exist)
    study_set = db.scalar(select(StudySet).where(StudySet.id == set_id, StudySet.user_id == user.id))
    if study_set is None:
        raise HTTPException(status_code=404, detail="Study set not found.")
    return study_set


def validate_upload(upload: UploadFile) -> str:
    """
    check extension and size of one uploaded file; returns its kind (text | audio)
    raises a 400 error with a message the frontend shows as-is
    `upload.size` is known because FastAPI has already received the whole file (into a temporary file) before calling the endpoint
    """
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


def enqueue_processing(db: Session, study_set: StudySet) -> None:
    #hand the set to the worker. If Redis is unreachable, mark it failed so the user can retry
    try:
        # .delay() doesn't run the task here: it puts a message on the Redis queue, which a worker
        # process picks up. Only the id is sent, the worker loads everything else from the database
        process_study_set.delay(study_set.id)
    except Exception:
        log.exception("Could not enqueue study set %s", study_set.id)
        study_set.status = "failed"
        study_set.error = "Processing could not be started. Please try again."
        db.commit()


@router.post("", response_model=StudySetCreated, status_code=201)
def create_study_set(
    title: Annotated[str | None, Form()] = None,
    text: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    create a study set from a multipart form: optional `title`, `files` and/or `text`
    Steps: 
    -validate everything 
    -create the StudySet row 
    -save each file to storage and add a SourceFile row for it
    -commit 
    -queue the processing task
    -returns right away with the id
    """
    files = files or []
    text = (text or "").strip()
    title = (title or "").strip() or None

    # validate everything before storing anything
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

    # pasted text becomes a .txt source file, so every input follows the same path later
    # each source is (filename, kind, content type, size in bytes, readable file object)
    sources = [(f.filename, kind, f.content_type or "", f.size, f.file) for f, kind in zip(files, kinds)]
    if text:
        data = text.encode("utf-8")
        sources.append(("pasted-text.txt", "text", "text/plain", len(data), io.BytesIO(data)))

    saved_keys = []
    try:
        for position, (filename, kind, content_type, size, fileobj) in enumerate(sources, start=1):
            # e.g. "users/1/sets/7/2-notes.pdf": unique per set, and the position keeps names apart
            key = f"users/{user.id}/sets/{study_set.id}/{position}-{safe_filename(filename)}"
            storage.save(key, fileobj)
            saved_keys.append(key)
            db.add(SourceFile(
                study_set_id=study_set.id, position=position, original_filename=filename, kind=kind,
                content_type=content_type, size_bytes=size, storage_key=key,
            ))
        db.commit()
    except Exception:
        #do not leave orphaned files behind when the upload fails half-way
        db.rollback()
        for key in saved_keys:
            storage.delete(key)
        raise

    enqueue_processing(db, study_set)
    return {"id": study_set.id}


def set_detail(db: Session, study_set: StudySet) -> dict:
    # StudySetDetail response: the set's fields plus every chapter's points and lock state
    scores = load_chapter_scores(db, study_set.id)
    return {
        "id": study_set.id,
        "title": study_set.title,
        "status": study_set.status,
        "status_message": study_set.status_message,
        "error": study_set.error,
        "overview": study_set.overview,
        "created_at": study_set.created_at,
        "progress": progress(scores),
        "chapters": scores,
    }


@router.get("", response_model=list[StudySetListItem])
def list_study_sets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # current user's study sets, newest first, each with its progress (for the dashboard)
    sets = db.scalars(
        select(StudySet).where(StudySet.user_id == user.id).order_by(StudySet.created_at.desc())
    ).all()
    return [
        {
            "id": s.id, "title": s.title, "status": s.status, "created_at": s.created_at,
            "progress": progress(load_chapter_scores(db, s.id)),
        }
        for s in sets
    ]


@router.get("/{set_id}", response_model=StudySetDetail)
def get_study_set(set_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # one study set. The study set page polls this every 3 s while the set is being processed
    return set_detail(db, get_owned_set(db, user, set_id))


@router.post("/{set_id}/retry", response_model=StudySetDetail)
def retry_study_set(set_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # "Retry" button: reset a failed set to "queued" and run the processing task again
    study_set = get_owned_set(db, user, set_id)
    if study_set.status != "failed":
        raise HTTPException(status_code=409, detail="Only a failed study set can be retried.")
    study_set.status = "queued"
    study_set.status_message = ""
    study_set.error = None
    db.commit()
    enqueue_processing(db, study_set)
    return set_detail(db, study_set)


@router.delete("/{set_id}", status_code=204)
def delete_study_set(set_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # delete a set with all its chapters, quizzes and stored files. 204 = done
    study_set = get_owned_set(db, user, set_id)
    keys = [f.storage_key for f in study_set.source_files]
    db.delete(study_set)  # rows below it are removed by ON DELETE CASCADE
    db.commit()
    # files go after the commit: a leftover file is harmless, a row pointing at a missing file is not
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            log.exception("Could not delete stored file %s", key)
