"""The AI steps the worker calls. In mock mode they return offline output from mock.py."""
import logging

from pydantic import BaseModel

from app import config
from app.ai import llm, mock, prompts
from app.schemas import ChapterOut, QuestionOut, StructureOut

log = logging.getLogger(__name__)


def _ask(system: str, user: str, model: type[BaseModel], context: dict | None = None):
    """Ask the LLM for JSON and validate it. One retry, telling the model what was wrong.

    Provider/network errors are not caught here: the Celery task retries those.
    """
    data = llm.complete_json(system, user)
    try:
        return model.model_validate(data, context=context)
    except ValueError as error:  # pydantic's ValidationError is a ValueError
        log.warning("LLM reply did not match %s, retrying: %s", model.__name__, error)
        data = llm.complete_json(system, user + prompts.fix_request(error))
        return model.model_validate(data, context=context)


def structure(blocks: list[str]) -> StructureOut:
    """Title, overview and chapter boundaries for the numbered blocks."""
    if config.LLM_PROVIDER == "mock":
        return mock.structure(blocks)
    try:
        return _ask(
            prompts.STRUCTURE_SYSTEM, prompts.structure_user(blocks), StructureOut,
            context={"n_blocks": len(blocks)},
        )
    except ValueError:
        # Still no valid chapters: fall back to evenly sized chapters so the user isn't stuck.
        log.exception("Structuring failed twice; falling back to even chapters")
        return mock.structure(blocks)


def chapter_materials(title: str, text: str) -> ChapterOut:
    """Summary, key concepts, Q&A pairs, study aids and quiz for one chapter."""
    if config.LLM_PROVIDER == "mock":
        return mock.chapter_materials(title, text)
    return _ask(prompts.CHAPTER_SYSTEM, prompts.chapter_user(title, text), ChapterOut)


def replacement_question(chapter_text: str, topic: str, previous: list[str]) -> QuestionOut:
    """A new question on `topic` that differs from every previous one."""
    if config.LLM_PROVIDER == "mock":
        return mock.replacement_question(chapter_text, topic, previous)
    return _ask(
        prompts.REPLACEMENT_SYSTEM, prompts.replacement_user(chapter_text, topic, previous), QuestionOut
    )
