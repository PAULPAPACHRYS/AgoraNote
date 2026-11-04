"""Prompt templates for every LLM step. Tuned on real Greek and English lectures (Phase 6).

Small local models follow short, concrete rules best, and follow what comes last most closely, so the
language instruction is repeated at the end of every user message.
"""
import re

from pydantic import ValidationError

from app import config

RULES = """Rules:
- Use ONLY the material provided. Do not add outside facts.
- The text was extracted from slides or documents: ignore repeated headers, footers, page numbers,
  course codes and other layout leftovers.
- All strings are plain text: no Markdown, no HTML, no bullet characters.
- Reply with a single JSON object that matches the contract exactly, and nothing else."""

QUIZ_RULES = """Quiz questions:
- Ask about the ideas of the subject (definitions, properties, causes, how and why), not about course
  administration (schedules, instructors, grading, room numbers) and not about exact wording.
- question: a complete question sentence that ends with a question mark (in Greek: ";"), never just
  a topic label.
- correct_answer: the one clearly correct answer, supported by the material, in your own short words
  (do not copy a whole sentence from the material and do not repeat the question).
- wrong_answers: exactly 3 wrong answers that a student who misunderstood the material might pick.
  Make each one by changing one important detail of the correct answer (a term, a number, a cause, a
  relationship), so all four answers have the same form and about the same length and the correct one
  does not stand out. Each must be clearly wrong according to the material.
- No answer may use giveaway words such as "only", "always", "never", "all", "none" (or their
  equivalents in the material's language).
- explanation: 1-3 sentences on why the correct answer is right, based on the material."""


STRUCTURE_SYSTEM = f"""You organise study material into chapters.
The material is cut into numbered blocks of about 1,000 characters; you see the beginning of each block.
Group consecutive blocks into chapters (the user message says how many to aim for, at most 10). Each
chapter is one coherent topic; chapters are roughly balanced in size and keep the original order. The first
chapter starts at block 0, every next chapter starts at the block right after the previous chapter's
end_block, and the last chapter ends at the last block. Use the block numbers given, never page or
slide numbers that appear inside the text.

{RULES}

JSON contract:
{{
  "title": "Short title for the whole study set (2-8 words)",
  "overview": "3-5 sentence overview of the whole material",
  "chapters": [{{"title": "Short chapter title (2-6 words)", "start_block": 0, "end_block": 11}}]
}}"""


# The structure step sees only the beginning of each block. That is enough to find topic boundaries,
# keeps block numbers easy to follow for a small model (with the full text it mixed them up with slide
# numbers), and always fits the context window: 18,000 characters is ~8k tokens even in Greek (~2.3
# characters per token), leaving room in a 16k window for instructions and the reply.
PREVIEW_BUDGET_CHARS = 18_000
PREVIEW_MAX_CHARS = 300
PREVIEW_MIN_CHARS = 80


# About one chapter per 5 blocks (~5,000 characters), so each chapter gets its own 5-question quiz.
# Small models ignore vague size hints but follow an explicit number.
BLOCKS_PER_CHAPTER = 5


def target_chapters(n_blocks: int) -> int:
    return max(1, min(10, round(n_blocks / BLOCKS_PER_CHAPTER)))


def structure_user(blocks: list[str]) -> str:
    size = max(PREVIEW_MIN_CHARS, min(PREVIEW_MAX_CHARS, PREVIEW_BUDGET_CHARS // len(blocks)))
    previews = []
    for i, block in enumerate(blocks):
        text = " ".join(block.split())
        previews.append(f"Block {i}: {text[:size]}{'…' if len(text) > size else ''}")
    return (
        f"The material has {len(blocks)} blocks, numbered 0 to {len(blocks) - 1}.\n\n"
        + "\n".join(previews)
        + f"\n\nMake about {target_chapters(len(blocks))} chapters."
        + f"\n{language_instruction(' '.join(blocks))}"
    )


CHAPTER_SYSTEM = f"""You write study materials for one chapter of a lecture.

Produce:
- summary: 2-4 short paragraphs.
- key_concepts: 5-10 important terms from the chapter, each with a short explanation.
- qa_pairs: 5-10 question/answer pairs for self-testing.
- study_aids: an outline (headings with short points), a review checklist of "I can ..." statements,
  and 2-4 memory tips.
- quiz: exactly {config.QUESTIONS_PER_CHAPTER} multiple-choice questions, each on a DIFFERENT topic of
  the chapter, each with a short topic name (1-4 words).

{RULES}

{QUIZ_RULES}

JSON contract:
{{
  "summary": ["paragraph", "paragraph"],
  "key_concepts": [{{"term": "...", "explanation": "..."}}],
  "qa_pairs": [{{"question": "...", "answer": "..."}}],
  "study_aids": {{
    "outline": [{{"heading": "...", "points": ["..."]}}],
    "review_checklist": ["I can explain ..."],
    "memory_tips": ["..."]
  }},
  "quiz": [
    {{"topic": "...", "question": "...", "correct_answer": "...", "explanation": "...",
      "wrong_answers": ["...", "...", "..."]}}
  ]
}}"""


def chapter_user(title: str, text: str, language: str | None) -> str:
    return f"Chapter title: {title}\n\nChapter text:\n{text}\n\n{language_instruction(text, language)}"


REPLACEMENT_SYSTEM = f"""You write one new multiple-choice question on a given topic of a lecture chapter.

{RULES}

{QUIZ_RULES}
- The new question must not repeat or rephrase any of the previous questions listed; ask about a
  different aspect of the topic.

JSON contract:
{{"question": "...", "correct_answer": "...", "explanation": "...", "wrong_answers": ["...", "...", "..."]}}"""


def replacement_user(chapter_text: str, topic: str, previous: list[str], language: str | None) -> str:
    listed = "\n".join(f"- {p}" for p in previous) or "- (none)"
    return (
        f"Topic: {topic}\n\n"
        f"Previous questions on this topic (do not repeat or rephrase these):\n{listed}\n\n"
        f"Chapter text:\n{chapter_text}\n\n{language_instruction(chapter_text, language)}"
    )


# --- language -----------------------------------------------------------------------------------

_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_LETTER = re.compile(r"[^\W\d_]")


def detect_language(text: str) -> str | None:
    """'Greek' when a good share of the letters are Greek, else None (= "the material's language").

    Greek lectures are full of English terms, formulas and code, so 30% Greek letters is plenty.
    """
    letters = len(_LETTER.findall(text))
    return "Greek" if letters and len(_GREEK.findall(text)) / letters >= 0.3 else None


def language_instruction(text: str, language: str | None = None) -> str:
    language = language or detect_language(text)
    if language:
        return (
            f"IMPORTANT: The material is in {language}. Write every string of the JSON in {language}, "
            "even where the material quotes English terms (keep those terms, formulas and names as they are)."
        )
    return "IMPORTANT: Write every string of the JSON in the same language as the material."


def fix_request(error: Exception) -> str:
    """Appended to the prompt when the model's reply didn't match the contract."""
    if isinstance(error, ValidationError):
        # Just "where: what" for each problem; str(error) would echo the whole reply back.
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'reply'}: {e['msg']}" for e in error.errors()
        )
    else:
        problems = str(error)
    return (
        f"\n\nYour previous reply was not valid: {problems}\n"
        "Reply again with a single JSON object that matches the contract exactly."
    )
