"""Unit tests for the pure game rules in app/gamification.py (no database needed)."""
from app import config
from app.gamification import newly_unlocked, points_to_unlock, progress, score_chapters, unlock_threshold

P = config.POINTS_PER_QUESTION


def chapter(chapter_id, mastered_count, topics=config.QUESTIONS_PER_CHAPTER):
    """A chapter with `topics` topics, the first `mastered_count` of them mastered."""
    return {
        "id": chapter_id,
        "position": chapter_id,
        "title": f"Chapter {chapter_id}",
        "topics": [(P, i < mastered_count) for i in range(topics)],
    }


def test_unlock_threshold_rounds_up():
    assert unlock_threshold(50) == 35
    assert unlock_threshold(10) == 7
    assert unlock_threshold(15) == 11  # 10.5 -> 11
    assert unlock_threshold(0) == 0


def test_unlock_threshold_ignores_floating_point_noise():
    # 0.7 * 40 == 28.000000000000004 in floating point; the threshold must still be 28.
    assert unlock_threshold(40) == 28
    assert unlock_threshold(70) == 49


def test_chapter_points():
    [score] = score_chapters([chapter(1, mastered_count=2)])
    assert score["earned"] == 2 * P
    assert score["max"] == config.QUESTIONS_PER_CHAPTER * P
    assert score["unlock_threshold"] == unlock_threshold(score["max"])
    assert score["completed"] is False


def test_completed_only_when_every_topic_is_mastered():
    [score] = score_chapters([chapter(1, mastered_count=config.QUESTIONS_PER_CHAPTER)])
    assert score["completed"] is True
    [empty] = score_chapters([chapter(1, mastered_count=0, topics=0)])
    assert empty["completed"] is False


def test_first_chapter_is_always_unlocked():
    scores = score_chapters([chapter(1, 0), chapter(2, 0), chapter(3, 0)])
    assert [s["quiz_unlocked"] for s in scores] == [True, False, False]


def test_next_chapter_unlocks_at_the_threshold():
    # 5 topics x 10 points: threshold 35, so 3 mastered (30) is not enough and 4 (40) is.
    below = score_chapters([chapter(1, 3), chapter(2, 0)])
    at = score_chapters([chapter(1, 4), chapter(2, 0)])
    assert below[1]["quiz_unlocked"] is False
    assert at[1]["quiz_unlocked"] is True


def test_progression_is_linear():
    # Chapter 3 depends on chapter 2 only, and chapter 2 on chapter 1.
    scores = score_chapters([chapter(1, 4), chapter(2, 0), chapter(3, 0)])
    assert [s["quiz_unlocked"] for s in scores] == [True, True, False]


def test_points_to_unlock():
    scores = score_chapters([chapter(1, 1), chapter(2, 0)])
    assert points_to_unlock(scores, 1) == 0
    assert points_to_unlock(scores, 2) == unlock_threshold(5 * P) - P  # 35 - 10 = 25


def test_progress_is_earned_over_total_across_chapters():
    scores = score_chapters([chapter(1, 5), chapter(2, 1), chapter(3, 0)])
    assert progress(scores) == {"earned": 6 * P, "total": 15 * P, "percent": 40}


def test_progress_rounds_down_and_handles_no_chapters():
    scores = score_chapters([chapter(1, 1, topics=3)])  # 10 / 30 = 33.3%
    assert progress(scores)["percent"] == 33
    assert progress([]) == {"earned": 0, "total": 0, "percent": 0}


def test_newly_unlocked_reports_only_the_chapter_that_just_opened():
    before = score_chapters([chapter(1, 3), chapter(2, 0)])
    after = score_chapters([chapter(1, 4), chapter(2, 0)])
    assert newly_unlocked(before, after) == {"id": 2, "title": "Chapter 2"}
    later = score_chapters([chapter(1, 5), chapter(2, 0)])
    assert newly_unlocked(after, later) is None
