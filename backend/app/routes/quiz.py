import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.gamification import load_chapter_scores, newly_unlocked, points_to_unlock, progress
from app.models import Chapter, Question, StudySet, Topic, User
from app.routes.chapters import get_owned_chapter
from app.schemas import AnswerIn, AnswerOut, QuizState
from app.worker import generate_replacement_question

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def require_unlocked(scores: list[dict], chapter: Chapter) -> dict:
    """This chapter's score; 403 with the unlock requirement if its quiz is still locked."""
    score = next(s for s in scores if s["id"] == chapter.id)
    if not score["quiz_unlocked"]:
        needed = points_to_unlock(scores, chapter.id)
        raise HTTPException(
            status_code=403,
            detail=f"Earn {needed} more points in Chapter {chapter.position - 1} to unlock this quiz.",
        )
    return score


@router.get("/chapters/{chapter_id}/quiz", response_model=QuizState)
def get_quiz(chapter_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chapter = get_owned_chapter(db, user, chapter_id)
    scores = load_chapter_scores(db, chapter.study_set_id)
    score = require_unlocked(scores, chapter)

    topics = []
    for topic in chapter.topics:
        mastered = topic.mastered_at is not None
        active = next((q for q in topic.questions if q.status == "active"), None)
        topics.append({
            "id": topic.id,
            "name": topic.name,
            "points": topic.points,
            "mastered": mastered,
            "preparing": not mastered and active is None,
            # Only id, prompt and options: the response model has no room for the answer.
            "question": active if active and not mastered else None,
        })
    return {
        "chapter_id": chapter.id,
        "earned": score["earned"],
        "max": score["max"],
        "unlock_threshold": score["unlock_threshold"],
        "progress": progress(scores),
        "topics": topics,
    }


@router.post("/questions/{question_id}/answer", response_model=AnswerOut)
def answer_question(
    question_id: int, body: AnswerIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    # FOR UPDATE locks the question row until we commit, so a double-click can't score twice:
    # the second request waits here and then finds the question already answered.
    question = db.scalar(
        select(Question)
        .join(Topic).join(Chapter).join(StudySet)
        .where(Question.id == question_id, StudySet.user_id == user.id)
        .with_for_update(of=Question)
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    if question.status != "active":
        raise HTTPException(status_code=409, detail="This question has already been answered.")

    topic = question.topic
    chapter = topic.chapter
    before = load_chapter_scores(db, chapter.study_set_id)
    require_unlocked(before, chapter)

    correct = body.selected_index == question.correct_index
    now = datetime.now(timezone.utc)
    question.status = "correct" if correct else "wrong"
    question.selected_index = body.selected_index
    question.answered_at = now
    if correct:
        topic.mastered_at = now
    db.commit()

    # Only after the commit, so the task sees this question as answered (and not active).
    if not correct:
        try:
            generate_replacement_question.delay(topic.id)
        except Exception:
            log.exception("Could not enqueue a replacement question for topic %s", topic.id)

    after = load_chapter_scores(db, chapter.study_set_id)
    score = next(s for s in after if s["id"] == chapter.id)
    return {
        "correct": correct,
        "correct_index": question.correct_index,
        "explanation": question.explanation,
        "points_awarded": topic.points if correct else 0,
        "chapter": score,
        "progress": progress(after),
        "unlocked_chapter": newly_unlocked(before, after),
        "replacement_pending": not correct,
    }
