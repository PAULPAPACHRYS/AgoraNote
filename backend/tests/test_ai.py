"""Unit tests for the pure helpers around the LLM (no network, no database)."""
import math

import pytest

from app.ai import generate, prompts
from app.ai.extract import strip_repeated_lines
from app.ai.llm import strip_fences
from app.schemas import ChapterSpan, QuestionDraft


def test_repair_keeps_start_blocks_and_fixes_overlaps_and_gaps():
    chapters = [
        {"title": "B", "start_block": 4, "end_block": 9},  # out of order, overlapping end
        {"title": "A", "start_block": 1, "end_block": 4},  # doesn't start at 0
        {"title": "dup", "start_block": 4, "end_block": 6},  # same start as B: dropped
        {"title": "bad", "start_block": 42, "end_block": 50},  # out of range: dropped
    ]
    repaired = generate._repair_chapters(chapters, n_blocks=8)
    assert [(c["title"], c["start_block"], c["end_block"]) for c in repaired] == [("A", 0, 3), ("B", 4, 7)]


def test_repair_without_usable_chapters_raises():
    with pytest.raises(ValueError):
        generate._repair_chapters([{"title": "x", "start_block": 99, "end_block": 100}], n_blocks=5)


def test_large_chapters_are_split_into_parts_that_fit():
    blocks = ["x" * 1000] * 50  # 50,000 characters
    spans = generate._split_large_chapters([ChapterSpan(title="Big", start_block=0, end_block=49)], blocks)
    parts = math.ceil(50_000 / generate.MAX_CHAPTER_CHARS)
    assert [s.title for s in spans] == [f"Big ({n}/{parts})" for n in range(1, parts + 1)]
    assert spans[0].start_block == 0 and spans[-1].end_block == 49
    for a, b in zip(spans, spans[1:]):
        assert b.start_block == a.end_block + 1  # contiguous
    for s in spans:
        assert (s.end_block - s.start_block + 1) * 1000 <= generate.MAX_CHAPTER_CHARS


def test_small_chapters_are_left_alone():
    span = ChapterSpan(title="Small", start_block=0, end_block=2)
    assert generate._split_large_chapters([span], ["x" * 1000] * 3) == [span]


def test_structure_previews_always_fit_the_budget():
    few = prompts.structure_user(["word " * 400] * 10)
    assert "Block 9: " in few and len(few) < 10 * (prompts.PREVIEW_MAX_CHARS + 20) + 500
    many = prompts.structure_user(["word " * 200] * 200)  # a 200,000-character upload
    assert "Block 199: " in many
    assert len(many) < prompts.PREVIEW_BUDGET_CHARS + 200 * 20 + 500


def test_detect_language():
    assert prompts.detect_language("Η φωτοσύνθεση είναι η διαδικασία με την οποία τα φυτά") == "Greek"
    # Greek lecture full of English terms and formulas is still Greek.
    assert prompts.detect_language("Το SDN controller χρησιμοποιεί OpenFlow API για switches και routers") == "Greek"
    assert prompts.detect_language("Photosynthesis turns light into chemical energy") is None
    assert prompts.detect_language("12345 + 678") is None


def test_strip_fences():
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_fences('```\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_fences('  {"a": 1}  ') == '{"a": 1}'


def test_question_draft_puts_the_correct_answer_first():
    draft = QuestionDraft(question="Q?", correct_answer="right", explanation="because", wrong_answers=["a", "b", "c"])
    question = draft.to_question()
    assert question.options == ["right", "a", "b", "c"] and question.correct_index == 0


def test_question_draft_rejects_duplicate_answers():
    with pytest.raises(ValueError):
        QuestionDraft(question="Q?", correct_answer="same", explanation="e", wrong_answers=["Same", "b", "c"])


def test_question_draft_must_be_a_question():
    QuestionDraft(question="Τι είναι διάνυσμα;", correct_answer="a", explanation="e", wrong_answers=["b", "c", "d"])
    with pytest.raises(ValueError):
        QuestionDraft(question="Vector length", correct_answer="a", explanation="e", wrong_answers=["b", "c", "d"])


def test_tiny_chapters_are_merged_into_a_neighbour():
    blocks = ["x" * 50, "x" * 1000, "x" * 1000, "x" * 1000, "x" * 60]
    spans = [
        ChapterSpan(title="Cover page", start_block=0, end_block=0),
        ChapterSpan(title="Main", start_block=1, end_block=3),
        ChapterSpan(title="Page number", start_block=4, end_block=4),
    ]
    assert generate._merge_small_chapters(spans, blocks) == [ChapterSpan(title="Main", start_block=0, end_block=4)]


def test_target_chapters():
    assert prompts.target_chapters(3) == 1
    assert prompts.target_chapters(41) == 8
    assert prompts.target_chapters(200) == 10


def test_repeated_page_headers_and_page_numbers_are_removed():
    topics = ["Vectors", "Planes", "Curves", "Limits", "Derivatives", "Integrals"]
    pages = [f"HY-111 Spring 2019\n{topic} are explained here\n{n}" for n, topic in enumerate(topics, start=1)]
    pages[2] += "\nPage 3 of 6"
    cleaned = strip_repeated_lines(pages)
    assert cleaned[0] == "Vectors are explained here"
    assert all("HY-111" not in page for page in cleaned)
    assert "Page 3 of 6" in cleaned[2]  # appears on one page only: kept


def test_short_documents_are_left_alone():
    pages = ["Title\nIntro", "Title\nMore"]
    assert strip_repeated_lines(pages) == pages
