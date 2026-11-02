from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.gamification import load_chapter_scores, points_to_unlock
from app.models import Chapter, StudySet, User
from app.schemas import ChapterDetail

router = APIRouter(prefix="/api/chapters")


def get_owned_chapter(db: Session, user: User, chapter_id: int) -> Chapter:
    """The chapter if its study set belongs to this user; 404 otherwise."""
    chapter = db.scalar(
        select(Chapter).join(StudySet).where(Chapter.id == chapter_id, StudySet.user_id == user.id)
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found.")
    return chapter


def _link(chapter: Chapter | None) -> dict | None:
    return {"id": chapter.id, "title": chapter.title} if chapter else None


@router.get("/{chapter_id}", response_model=ChapterDetail)
def get_chapter(chapter_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chapter = get_owned_chapter(db, user, chapter_id)
    siblings = chapter.study_set.chapters  # ordered by position
    index = siblings.index(chapter)
    scores = load_chapter_scores(db, chapter.study_set_id)
    score = next(s for s in scores if s["id"] == chapter.id)
    return {
        "id": chapter.id,
        "position": chapter.position,
        "title": chapter.title,
        "study_set_id": chapter.study_set_id,
        "study_set_title": chapter.study_set.title,
        "chapter_count": len(siblings),
        "earned": score["earned"],
        "max": score["max"],
        "unlock_threshold": score["unlock_threshold"],
        "quiz_unlocked": score["quiz_unlocked"],
        "completed": score["completed"],
        "points_to_unlock": points_to_unlock(scores, chapter.id),
        "summary": chapter.summary,
        "key_concepts": chapter.key_concepts,
        "qa_pairs": chapter.qa_pairs,
        "study_aids": chapter.study_aids,
        "prev_chapter": _link(siblings[index - 1] if index > 0 else None),
        "next_chapter": _link(siblings[index + 1] if index + 1 < len(siblings) else None),
    }
