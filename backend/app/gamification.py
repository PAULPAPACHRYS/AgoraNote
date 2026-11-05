"""
Game rules: points, unlock thresholds and progress

the rules are small pure functions working on plain numbers, so they are easy to unit-test
load_chapter_scores() at the bottom reads those numbers from the database and applies them

Rules in short:
- each chapter has a fixed set of topics (scoring slots), a topic's points are earned once
- chapter 1's quiz is always open; chapter k's quiz opens once chapter k-1 has earned at least ceil(UNLOCK_RATIO x its max points) 
- points never go down, so an unlock is permanent

Example with the defaults (5 topics x 10 points, ratio 0.7): a chapter is worth 50 points, its
threshold is 35, so mastering 4 of its 5 topics (40 points) opens the next chapter's quiz
"""
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import Chapter, Topic


def unlock_threshold(max_points: int) -> int:
    # points a chapter needs before the next chapter's quiz opens: UNLOCK_RATIO of its max, rounded up
    # round() first: in floating point 0.7 * 40 is 28.000000000000004, which ceil() would turn into 29
    return math.ceil(round(config.UNLOCK_RATIO * max_points, 6))


def score_chapters(chapters: list[dict]) -> list[dict]:
    """
    points and lock state for each chapter of a study set

    `chapters` is in position order: [{"id", "position", "title", "topics": [(points, mastered), ...]}]
    returns one dict per chapter with: id, position, title, earned, max, unlock_threshold, quiz_unlocked, completed
    """
    scored = []
    for chapter in chapters:
        # each topic is (points, mastered?): earned counts mastered topics, max counts all of them
        earned = sum(points for points, mastered in chapter["topics"] if mastered)
        maximum = sum(points for points, _ in chapter["topics"])
        previous = scored[-1] if scored else None  # the chapter before this one (None for chapter 1)
        scored.append({
            "id": chapter["id"],
            "position": chapter["position"],
            "title": chapter["title"],
            "earned": earned,
            "max": maximum,
            "unlock_threshold": unlock_threshold(maximum),
            # chapter 1 is always open, any other chapter opens through the chapter before it
            "quiz_unlocked": previous is None or previous["earned"] >= previous["unlock_threshold"],
            "completed": maximum > 0 and earned == maximum,
        })
    return scored


def points_to_unlock(scored: list[dict], chapter_id: int) -> int:
    # how many more points the previous chapter needs before this chapter's quiz opens (0 if open)
    index = next(i for i, c in enumerate(scored) if c["id"] == chapter_id)  # position in the list
    if scored[index]["quiz_unlocked"]:
        return 0
    previous = scored[index - 1]
    return previous["unlock_threshold"] - previous["earned"]


def progress(scored: list[dict]) -> dict:
    #points earned vs points available across all chapters (the overall progress bar of the study set)
    earned = sum(c["earned"] for c in scored)
    total = sum(c["max"] for c in scored)
    # rounded down, so 100% means every topic is really mastered
    return {"earned": earned, "total": total, "percent": earned * 100 // total if total else 0}


def newly_unlocked(before: list[dict], after: list[dict]) -> dict | None:
    """
    the chapter whose quiz became unlocked between two scorings, if any
    used after an answer: comparing the scores before and after shows whether this very answer
    crossed a threshold, so the quiz can show "You unlocked the quiz of ..." exactly once
    """
    for old, new in zip(before, after):
        if new["quiz_unlocked"] and not old["quiz_unlocked"]:
            return {"id": new["id"], "title": new["title"]}
    return None


def load_chapter_scores(db: Session, study_set_id: int) -> list[dict]:
    """
    score_chapters() for a study set, with the topic points read from the database
    one query returns a row per (chapter, topic) pair, the loop groups them back into chapters
    """
    rows = db.execute(
        select(Chapter.id, Chapter.position, Chapter.title, Topic.points, Topic.mastered_at)
        .outerjoin(Topic, Topic.chapter_id == Chapter.id)
        .where(Chapter.study_set_id == study_set_id)
        .order_by(Chapter.position, Topic.position)
    ).all()
    chapters = {}  # chapter id -> {"id", "position", "title", "topics": [...]}, in position order
    for row in rows:
        chapter = chapters.setdefault(
            row.id, {"id": row.id, "position": row.position, "title": row.title, "topics": []}
        )
        if row.points is not None:  # a chapter without topics still appears (outer join)
            chapter["topics"].append((row.points, row.mastered_at is not None))
    return score_chapters(list(chapters.values()))
