"""Prompt templates for every LLM step. Tuned on real lectures in Phase 6."""
from pydantic import ValidationError

from app import config

RULES = """Rules:
- Use ONLY the material provided. Do not add outside facts.
- Write everything in the same language as the material (for example Greek material gets Greek output).
- All strings are plain text: no Markdown, no HTML.
- Reply with a single JSON object that matches the contract exactly, and nothing else."""

QUIZ_RULES = """Quiz questions:
- Test understanding, not trivia or exact wording.
- Exactly 4 options, exactly one clearly correct; distractors are plausible and of similar length.
- correct_index is the 0-based position of the correct option.
- The explanation is 1-3 sentences on why the correct answer is right."""


STRUCTURE_SYSTEM = f"""You organise study material into chapters.
The material is given as numbered blocks. Group consecutive blocks into 1-10 chapters, each a coherent
topic, roughly balanced in size, in the original order. The first chapter starts at block 0, each next
chapter starts right after the previous one ends, and the last chapter ends at the last block.

{RULES}

JSON contract:
{{
  "title": "Short title for the whole study set",
  "overview": "3-5 sentence overview of the whole material",
  "chapters": [{{"title": "Chapter title", "start_block": 0, "end_block": 11}}]
}}"""


def structure_user(blocks: list[str]) -> str:
    numbered = "\n\n".join(f"[{i}] {block}" for i, block in enumerate(blocks))
    return f"The material has {len(blocks)} blocks, numbered 0 to {len(blocks) - 1}.\n\n{numbered}"


CHAPTER_SYSTEM = f"""You write study materials for one chapter of a lecture.

Produce:
- summary: 2-4 short paragraphs.
- key_concepts: 5-10 terms, each with a short explanation.
- qa_pairs: 5-10 question/answer pairs for self-testing.
- study_aids: an outline (headings with bullet points), a review checklist of "I can ..." statements,
  and a few memory tips.
- quiz: exactly {config.QUESTIONS_PER_CHAPTER} multiple-choice questions, each on a DIFFERENT topic,
  with a short topic name.

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
    {{"topic": "short topic name", "question": "...", "options": ["...", "...", "...", "..."],
      "correct_index": 0, "explanation": "..."}}
  ]
}}"""


def chapter_user(title: str, text: str) -> str:
    return f"Chapter title: {title}\n\nChapter text:\n{text}"


REPLACEMENT_SYSTEM = f"""You write one new multiple-choice question on a given topic of a lecture chapter.

{RULES}

{QUIZ_RULES}
- The new question must not repeat or rephrase any of the previous questions listed.

JSON contract:
{{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0, "explanation": "..."}}"""


def replacement_user(chapter_text: str, topic: str, previous: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in previous) or "- (none)"
    return (
        f"Topic: {topic}\n\n"
        f"Previous questions on this topic (do not repeat or rephrase these):\n{listed}\n\n"
        f"Chapter text:\n{chapter_text}"
    )


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
