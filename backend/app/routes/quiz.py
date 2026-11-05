"""
quiz: show a chapter's questions and grade answers

    GET  /api/chapters/{id}/quiz          the quiz state (403 while the chapter's quiz is locked)
    POST /api/questions/{id}/answer       {"selected_index": 0-3} -> correct?, points, explanation

all grading happens here on the server; the browser never gets the right answer before answering
a wrong answer queues `generate_replacement_question` (worker.py), 
which adds a new question on the same topic in the background meanwhile the topic shows as "preparing"
"""
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
    #this chapter's score; 403 with the unlock requirement if its quiz is still locked
    score = next(s for s in scores if s["id"] == chapter.id)  # this chapter's entry in the list
    if not score["quiz_unlocked"]:
        needed = points_to_unlock(scores, chapter.id)
        raise HTTPException(
            status_code=403,
            detail=f"Earn {needed} more points in Chapter {chapter.position - 1} to unlock this quiz.",
        )
    return score


@router.get("/chapters/{chapter_id}/quiz", response_model=QuizState)
def get_quiz(chapter_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    #chapter's points and, per topic: mastered, preparing a new question, or its current question
    chapter = get_owned_chapter(db, user, chapter_id)
    scores = load_chapter_scores(db, chapter.study_set_id)
    score = require_unlocked(scores, chapter)

    topics = []
    for topic in chapter.topics:
        mastered = topic.mastered_at is not None
        #question waiting to be answered (at most one per topic, guaranteed by a unique index)
        active = next((q for q in topic.questions if q.status == "active"), None)
        topics.append({
            "id": topic.id,
            "name": topic.name,
            "points": topic.points,
            "mastered": mastered,
            #not mastered but no active question: a replacement is being generated after a wrong answer
            "preparing": not mastered and active is None,
            #only id, prompt and options: the response model has no room for the answer
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
    """
    Grade one answer 
    returns the result, the new points and whether a chapter got unlocked
    Errors: 404 not your question / doesn't exist, 409 already answered, 403 quiz still locked
    """
    # FOR UPDATE locks the question row until we commit, so a double-click can't score twice:
    # the second request waits here and then finds the question already answered
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
    #scores before the answer, to detect afterwards whether this answer unlocked the next chapter
    before = load_chapter_scores(db, chapter.study_set_id)
    require_unlocked(before, chapter)

    correct = body.selected_index == question.correct_index
    now = datetime.now(timezone.utc)
    question.status = "correct" if correct else "wrong"
    question.selected_index = body.selected_index
    question.answered_at = now
    if correct:
        topic.mastered_at = now  # the topic's points are now earned
    db.commit()  # also releases the FOR UPDATE lock

    # only after the commit, so the task sees this question as answered (and not active)
    if not correct:
        try:
            generate_replacement_question.delay(topic.id)
        except Exception:
            log.exception("Could not enqueue a replacement question for topic %s", topic.id)

    # scores after the answer: the response updates the quiz's points bar and the overall total
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
