"""
The AI steps the worker calls

Three public functions, one per kind of LLM job:
- structure(blocks)                     -> title, overview and chapter boundaries
- chapter_materials(title, text, lang)  -> summary, concepts, Q&A, study aids and 5 quiz questions
- replacement_question(...)             -> one new quiz question after a wrong answer

Each one builds a prompt (prompts.py), asks the LLM for JSON in a fixed shape (llm.py) and checks
the reply against a Pydantic model (schemas.py), retrying once with the error message if it doesn't
match. The structuring step then also cleans up the chapter boundaries in code (repair, merge, split).
"""
import logging
import math

from pydantic import BaseModel

from app import config
from app.ai import llm, mock, prompts
from app.schemas import ChapterDraft, ChapterOut, ChapterSpan, QuestionDraft, QuestionOut, StructureOut

log = logging.getLogger(__name__)


def _ask(system: str, user: str, model: type[BaseModel], context: dict | None = None):
    """
    ask the LLM for JSON and validate it. One retry, telling the model what was wrong
    provider/network errors are not caught here: the Celery task retries those
    """
    # JSON Schema of the Pydantic model doubles as the structured-output schema for the provider
    schema = model.model_json_schema()
    # first attempt, `context` is passed to the model's validators (structure checks need n_blocks)
    try:
        return model.model_validate(llm.complete_json(system, user, schema, model.__name__), context=context)
    except ValueError as error:  # bad JSON or pydantic's ValidationError (both are ValueErrors)
        log.warning("LLM reply did not match %s, retrying: %s", model.__name__, error)
        # second and last attempt, same prompt plus what was wrong. If this fails too, it raises
        data = llm.complete_json(system, user + prompts.fix_request(error), schema, model.__name__)
        return model.model_validate(data, context=context)


def _repair_chapters(chapters: list[dict], n_blocks: int) -> list[dict]:
    """
    make the model's chapter boundaries contiguous, keeping its start blocks
    small models often get end_block off by one (overlaps or gaps). The start blocks carry the real
    decision, so: sort by start, drop duplicates and out-of-range starts, begin at block 0, and end each
    chapter right before the next one starts

    # example with 10 blocks: starts [0, 3, 3, 7, 12] -> chapters 0-2, 3-6, 7-9 (duplicate 3 and
    # out-of-range 12 dropped; every end_block recomputed)
    """
    starts, kept = set(), []
    for chapter in sorted(chapters, key=lambda c: c["start_block"]):
        if 0 <= chapter["start_block"] < n_blocks and chapter["start_block"] not in starts:
            starts.add(chapter["start_block"])
            kept.append(dict(chapter))
    if not kept:
        raise ValueError("no usable chapter boundaries")
    kept[0]["start_block"] = 0  # the first chapter always starts at the beginning
    # Pair each chapter with the one after it (None for the last) to compute its end_block.
    for chapter, following in zip(kept, kept[1:] + [None]):
        chapter["end_block"] = following["start_block"] - 1 if following else n_blocks - 1
    return kept


# every chapter is sent whole to the LLM. 16,000 characters is ~7k tokens even in Greek (~2.3 characters
# per token), which leaves room in a 16k context window for the instructions (~1k) and the reply (up to llm.MAX_COMPLETION_TOKENS = 7k)
MAX_CHAPTER_CHARS = 16_000
#chapter needs enough material for 5 different quiz questions
MIN_CHAPTER_CHARS = 1_500


def _merge_small_chapters(chapters: list[ChapterSpan], blocks: list[str]) -> list[ChapterSpan]:
    # join each chapter shorter than MIN_CHAPTER_CHARS with its neighbour

    def size(chapter: ChapterSpan) -> int:
        # number of characters in the chapter's blocks
        return sum(len(b) for b in blocks[chapter.start_block : chapter.end_block + 1])

    # walk through the chapters; whenever this chapter or the one before it is too small,
    # the two become one chapter (which may be merged again with the next one)
    merged: list[ChapterSpan] = []
    for chapter in chapters:
        previous = merged[-1] if merged else None
        if previous and (size(chapter) < MIN_CHAPTER_CHARS or size(previous) < MIN_CHAPTER_CHARS):
            title = previous.title if size(previous) >= size(chapter) else chapter.title
            merged[-1] = ChapterSpan(title=title, start_block=previous.start_block, end_block=chapter.end_block)
        else:
            merged.append(chapter)
    return merged


def _split_large_chapters(chapters: list[ChapterSpan], blocks: list[str]) -> list[ChapterSpan]:
    # split any chapter longer than MAX_CHAPTER_CHARS into roughly equal parts of whole blocks
    result = []
    for chapter in chapters:
        indexes = range(chapter.start_block, chapter.end_block + 1)
        total = sum(len(blocks[i]) for i in indexes)
        parts = math.ceil(total / MAX_CHAPTER_CHARS)  # e.g. 40,000 chars -> 3 parts
        if parts <= 1:
            result.append(chapter)
            continue
        # start a new part each time the running length passes the next multiple of total/parts
        groups, size_so_far = [[]], 0
        for i in indexes:
            if groups[-1] and size_so_far >= len(groups) * total / parts:
                groups.append([])
            groups[-1].append(i)
            size_so_far += len(blocks[i])
        # every part keeps the chapter's title with "(1/3)", "(2/3)", ... appended
        for n, group in enumerate(groups, start=1):
            result.append(ChapterSpan(
                title=f"{chapter.title} ({n}/{len(groups)})", start_block=group[0], end_block=group[-1]
            ))
    return result


def structure(blocks: list[str]) -> StructureOut:
    """
    title, overview and chapter boundaries for the numbered blocks

    steps: 
    -ask the LLM 
    - repair its boundaries 
    - validate that they cover every block in order (fallback: evenly sized chapters) 
    - merge too-small and split too large chapters
    """
    if config.LLM_PROVIDER == "mock":
        return mock.structure(blocks)
    try:
        out = _ask(prompts.STRUCTURE_SYSTEM, prompts.structure_user(blocks), StructureOut)
        repaired = {**out.model_dump(), "chapters": _repair_chapters(out.model_dump()["chapters"], len(blocks))}
        result = StructureOut.model_validate(repaired, context={"n_blocks": len(blocks)})
    except ValueError:
        # still no valid chapters: fall back to evenly sized chapters so the user isn't stuck
        log.exception("Structuring failed; falling back to even chapters")
        result = mock.structure(blocks)
    #after validation on purpose: splitting may give more than the 10 chapters we ask the LLM for
    result.chapters = _split_large_chapters(_merge_small_chapters(result.chapters, blocks), blocks)
    return result


def chapter_materials(title: str, text: str, language: str | None = None) -> ChapterOut:
    """
    summary, key concepts, Q&A pairs, study aids and quiz for one chapter

    `language` is the language of the whole study set ("Greek" or None), 
    a single chapter may be mostly English quotes or formulas even in a Greek lecture
    """
    if config.LLM_PROVIDER == "mock":
        return mock.chapter_materials(title, text)
    #LLM fills in a ChapterDraft (correct answer + wrong answers); convert to the stored format
    draft = _ask(prompts.CHAPTER_SYSTEM, prompts.chapter_user(title, text, language), ChapterDraft)
    return draft.to_chapter()


def replacement_question(
    chapter_text: str, topic: str, previous: list[str], language: str | None = None
) -> QuestionOut:
    """
    new question on `topic` that differs from every previous one
    `previous` holds the texts of all earlier questions on this topic; the prompt tells the LLM not to repeat or rephrase them
    """
    if config.LLM_PROVIDER == "mock":
        return mock.replacement_question(chapter_text, topic, previous)
    draft = _ask(
        prompts.REPLACEMENT_SYSTEM,
        prompts.replacement_user(chapter_text, topic, previous, language),
        QuestionDraft,
    )
    return draft.to_question()
