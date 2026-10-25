"""Deterministic offline stand-ins for every LLM step.

They build plausible output from the input text itself (no network, no API key), and go through the
same Pydantic contracts as real LLM output, so the whole app and the tests work offline.
"""
import re
from collections import Counter

from app import config
from app.ai.extract import split_sentences
from app.schemas import ChapterOut, QuestionOut, StructureOut


def _first_words(text: str, n: int) -> str:
    words = text.split()
    return " ".join(words[:n]).rstrip(".,;:!?") + ("…" if len(words) > n else "")


def _without_file_headings(text: str) -> str:
    """Drop the "=== filename ===" lines the worker puts between files."""
    return re.sub(r"^=== .* ===$", "", text, flags=re.MULTILINE).strip()


def _trim(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _terms(text: str, count: int) -> list[str]:
    """Pick 'key terms': the most frequent long words (letters of any script, so Greek works too)."""
    words = re.findall(r"[^\W\d_]+", text)
    counts = Counter(w.casefold() for w in words)
    first_form = {}
    for w in words:
        first_form.setdefault(w.casefold(), w)
    order = list(first_form)  # first-appearance order breaks ties, so output is deterministic
    terms = []
    for min_len in (7, 4):
        ranked = sorted(
            (w for w in order if len(w) >= min_len and first_form[w] not in terms),
            key=lambda w: (-counts[w], order.index(w)),
        )
        terms += [first_form[w] for w in ranked[: count - len(terms)]]
    terms += [f"topic {i}" for i in range(len(terms) + 1, count + 1)]
    return terms[:count]


def _sentence_about(term: str, sentences: list[str], avoid: set[str] = frozenset()) -> str:
    matches = [s for s in sentences if term.casefold() in s.casefold()] or sentences
    fresh = [s for s in matches if s not in avoid]
    return (fresh or matches)[0]


def _options(sentence: str, term: str, other_term: str) -> list[str]:
    """One real sentence (index 0) and three altered versions of it."""
    correct = _trim(sentence)
    swapped = re.sub(re.escape(term), other_term, correct, count=1, flags=re.IGNORECASE)
    candidates = [
        correct,
        "It is not true that " + correct[:1].lower() + correct[1:],
        swapped if swapped != correct else correct.rstrip(".") + ", but only in rare cases.",
        f'The chapter says that "{term}" has nothing to do with "{other_term}".',
    ]
    options, seen = [], set()
    for i, option in enumerate(candidates):
        while option.strip().casefold() in seen:
            option = f"{option} ({i})"
        seen.add(option.strip().casefold())
        options.append(option)
    return options


def _even_spans(n_blocks: int, n_chapters: int) -> list[tuple[int, int]]:
    base, extra = divmod(n_blocks, n_chapters)
    spans, start = [], 0
    for i in range(n_chapters):
        size = base + (1 if i < extra else 0)
        spans.append((start, start + size - 1))
        start += size
    return spans


def structure(blocks: list[str]) -> StructureOut:
    """Evenly sized chapters of about 2 blocks each; titles from each chapter's first words."""
    n_chapters = min(10, max(1, round(len(blocks) / 2)))
    first_text = _without_file_headings(blocks[0]) or blocks[0]
    first_sentences = split_sentences(first_text) or [first_text]
    chapters = [
        {
            "title": _first_words(_without_file_headings(blocks[start]) or blocks[start], 6),
            "start_block": start,
            "end_block": end,
        }
        for start, end in _even_spans(len(blocks), n_chapters)
    ]
    return StructureOut.model_validate(
        {
            "title": _first_words(first_sentences[0], 8),
            "overview": " ".join(first_sentences[:3]),
            "chapters": chapters,
        },
        context={"n_blocks": len(blocks)},
    )


def chapter_materials(title: str, text: str) -> ChapterOut:
    text = _without_file_headings(text) or text
    sentences = split_sentences(text) or [text]
    terms = _terms(text, max(6, config.QUESTIONS_PER_CHAPTER + 1))
    third = max(1, len(sentences) // 3)
    groups = [g for g in (sentences[:third], sentences[third : 2 * third], sentences[2 * third :]) if g]

    quiz, used = [], set()
    for i, term in enumerate(terms[: config.QUESTIONS_PER_CHAPTER]):
        sentence = _sentence_about(term, sentences, used)
        used.add(sentence)
        quiz.append({
            "topic": term,
            "question": f'Which statement about "{term}" appears in this chapter?',
            "options": _options(sentence, term, terms[(i + 1) % len(terms)]),
            "correct_index": 0,
            "explanation": f'The chapter says: "{_trim(sentence)}"',
        })

    return ChapterOut.model_validate({
        "summary": [p for p in (" ".join(sentences[:3]), " ".join(sentences[3:6])) if p],
        "key_concepts": [
            {"term": t, "explanation": _trim(_sentence_about(t, sentences))} for t in terms
        ],
        "qa_pairs": [
            {"question": f'What does this chapter say about "{t}"?', "answer": _trim(_sentence_about(t, sentences))}
            for t in terms[:5]
        ],
        "study_aids": {
            "outline": [
                {"heading": _first_words(g[0], 6), "points": [_trim(s, 120) for s in g[:3]]} for g in groups
            ],
            "review_checklist": [f'I can explain "{t}" in my own words.' for t in terms[:3]],
            "memory_tips": [
                f'Link "{terms[0]}" and "{terms[1]}" in one sentence of your own.',
                "Close the page and say the three main points of this chapter out loud.",
            ],
        },
        "quiz": quiz,
    })


def replacement_question(chapter_text: str, topic: str, previous: list[str]) -> QuestionOut:
    sentences = split_sentences(chapter_text) or [chapter_text]
    matches = [s for s in sentences if topic.casefold() in s.casefold()] or sentences
    version = len(previous) + 1  # previous includes the first question, which counts as version 1
    sentence = matches[(version - 1) % len(matches)]
    other_term = next((t for t in _terms(chapter_text, 6) if t.casefold() != topic.casefold()), "something else")
    question = f'Which statement about "{topic}" appears in this chapter? (version {version})'
    while question in previous:
        version += 1
        question = f'Which statement about "{topic}" appears in this chapter? (version {version})'
    return QuestionOut.model_validate({
        "question": question,
        "options": _options(sentence, topic, other_term),
        "correct_index": 0,
        "explanation": f'The chapter says: "{_trim(sentence)}"',
    })
