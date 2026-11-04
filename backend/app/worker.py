"""Celery app and background tasks. Start with: celery -A app.worker worker --loglevel=info"""
import logging
import os
import random
import tempfile
import time

import httpx
from celery import Celery
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app import config, storage
from app.ai import generate
from app.ai.extract import ProcessingError, extract_text, split_into_blocks
from app.ai.prompts import detect_language
from app.ai.transcribe import transcribe
from app.db import SessionLocal
from app.models import Chapter, Question, StudySet, Topic

log = logging.getLogger(__name__)

celery = Celery("agoranote", broker=config.REDIS_URL, backend=config.REDIS_URL)
celery.conf.broker_connection_retry_on_startup = True
# Two queues, each with its own worker (see docker-compose.yml): study sets are processed one at a
# time, and replacement quiz questions never wait behind a long transcription.
celery.conf.task_default_queue = "processing"
celery.conf.task_routes = {"app.worker.generate_replacement_question": {"queue": "quick"}}

MIN_INPUT_CHARS = 500
GENERIC_ERROR = "Something went wrong while processing this study set. Please try again."
UNREACHABLE_ERROR = "The AI service could not be reached or took too long to answer. Please try again later."


@celery.task
def ping():
    """Trivial task used to check that the worker is wired up."""
    return "pong"


def set_status(db, study_set: StudySet, status: str, message: str = "") -> None:
    study_set.status = status
    study_set.status_message = message
    db.commit()


def shuffle_options(options: list[str], correct_index: int) -> tuple[list[str], int]:
    """Shuffle the options in code (LLMs put the right answer first far too often)."""
    order = list(range(len(options)))
    random.shuffle(order)
    return [options[i] for i in order], order.index(correct_index)


def build_search_text(chapter: Chapter) -> str:
    parts = [chapter.title, *chapter.summary]
    parts += [f"{c['term']}: {c['explanation']}" for c in chapter.key_concepts]
    parts += [f"{qa['question']} {qa['answer']}" for qa in chapter.qa_pairs]
    parts.append(chapter.content)
    return "\n".join(parts)


@celery.task(
    bind=True, autoretry_for=(httpx.HTTPError,), retry_backoff=True, max_retries=3,
)
def process_study_set(self, study_set_id: int):
    """Turn a study set's uploaded files into chapters with study materials and quizzes."""
    with SessionLocal() as db:
        study_set = db.get(StudySet, study_set_id)
        if study_set is None:
            return  # deleted before we got to it
        try:
            run_pipeline(db, study_set)
        except Exception as exc:
            db.rollback()
            if isinstance(exc, httpx.HTTPError) and self.request.retries < self.max_retries:
                log.warning("Provider error on study set %s, will retry: %s", study_set_id, exc)
                set_status(db, study_set, study_set.status, "The AI service had a hiccup, retrying…")
                raise  # autoretry_for re-queues the task with backoff
            log.exception("Processing study set %s failed", study_set_id)
            if isinstance(exc, ProcessingError):
                study_set.error = str(exc)
            elif isinstance(exc, httpx.HTTPError):
                study_set.error = UNREACHABLE_ERROR
            else:
                study_set.error = GENERIC_ERROR
            set_status(db, study_set, "failed")


@celery.task(
    bind=True, autoretry_for=(httpx.HTTPError,), retry_backoff=True, max_retries=3,
)
def generate_replacement_question(self, topic_id: int):
    """After a wrong answer: a new question on the same topic, different from all previous ones."""
    with SessionLocal() as db:
        topic = db.get(Topic, topic_id)
        # Dedupe: nothing to do if the topic is gone, mastered, or already has a question waiting.
        if topic is None or topic.mastered_at or any(q.status == "active" for q in topic.questions):
            return
        previous = topic.questions  # ordered by id, so the last one is the most recent

        try:
            language = detect_language(topic.chapter.study_set.source_text)
            new = generate.replacement_question(
                topic.chapter.content, topic.name, [q.prompt for q in previous], language
            )
            prompt, explanation = new.question, new.explanation
            options, correct_index = shuffle_options(new.options, new.correct_index)
        except Exception as exc:
            if isinstance(exc, httpx.HTTPError) and self.request.retries < self.max_retries:
                raise  # autoretry_for re-queues the task with backoff
            # Never leave the player stuck: ask the most recent question again, options reshuffled.
            log.exception("Replacement question for topic %s failed; reusing the last one", topic_id)
            last = previous[-1]
            prompt, explanation = last.prompt, last.explanation
            options, correct_index = shuffle_options(last.options, last.correct_index)

        db.add(Question(
            topic_id=topic.id, prompt=prompt, options=options, correct_index=correct_index,
            explanation=explanation, status="active",
        ))
        try:
            db.commit()
        except IntegrityError:
            # Another run got there first: the unique index allows one active question per topic.
            db.rollback()


def run_pipeline(db, study_set: StudySet) -> None:
    started = time.monotonic()
    # Idempotent: a retry starts from a clean slate.
    db.execute(delete(Chapter).where(Chapter.study_set_id == study_set.id))
    study_set.error = None
    study_set.overview = ""
    set_status(db, study_set, "extracting", "Reading your files")

    files = study_set.source_files
    texts = {}  # position -> text
    with tempfile.TemporaryDirectory() as tmp:
        local = {}
        for f in files:
            local[f.position] = os.path.join(tmp, f"{f.position}-{os.path.basename(f.storage_key)}")
            storage.download(f.storage_key, local[f.position])
            if f.kind == "text":
                try:
                    texts[f.position] = extract_text(local[f.position], f.original_filename)
                except ProcessingError:
                    raise
                except Exception as exc:  # e.g. a corrupt .docx: tell the user which file
                    raise ProcessingError(f'"{f.original_filename}" could not be read.') from exc

        audio = [f for f in files if f.kind == "audio"]
        for i, f in enumerate(audio, start=1):
            label = f"Transcribing recording {i} of {len(audio)}"
            set_status(db, study_set, "transcribing", label)
            texts[f.position] = transcribe(
                local[f.position], f.original_filename,
                on_progress=lambda part, parts: set_status(db, study_set, "transcribing", f"{label} (part {part} of {parts})"),
            )
            if not texts[f.position].strip():
                raise ProcessingError(f'No speech was found in "{f.original_filename}".')

    # Join the files in upload order; with several files, a heading line marks where each starts.
    if len(files) == 1:
        source_text = texts[files[0].position]
    else:
        source_text = "\n\n".join(f"=== {f.original_filename} ===\n\n{texts[f.position]}" for f in files)
    if len(source_text) > config.MAX_INPUT_CHARS:
        raise ProcessingError(
            f"The material is too long ({len(source_text):,} characters; the limit is "
            f"{config.MAX_INPUT_CHARS:,}). Try splitting it into several study sets."
        )
    if len(source_text.strip()) < MIN_INPUT_CHARS:
        raise ProcessingError("Not enough material to build a study set.")
    study_set.source_text = source_text

    set_status(db, study_set, "structuring", "Finding the chapters")
    blocks = split_into_blocks(source_text)
    structure = generate.structure(blocks)
    if not study_set.title:  # a title the user typed wins over the generated one
        study_set.title = structure.title
    study_set.overview = structure.overview

    language = detect_language(source_text)  # the whole set's language, passed to every chapter
    total = len(structure.chapters)
    for position, span in enumerate(structure.chapters, start=1):
        set_status(db, study_set, "generating", f"Generating chapter {position} of {total}")
        content = "\n\n".join(blocks[span.start_block : span.end_block + 1])
        materials = generate.chapter_materials(span.title, content, language)

        chapter = Chapter(
            study_set_id=study_set.id,
            position=position,
            title=span.title,
            content=content,
            summary=materials.summary,
            key_concepts=[c.model_dump() for c in materials.key_concepts],
            qa_pairs=[qa.model_dump() for qa in materials.qa_pairs],
            study_aids=materials.study_aids.model_dump(),
        )
        chapter.search_text = build_search_text(chapter)
        for topic_position, item in enumerate(materials.quiz, start=1):
            options, correct_index = shuffle_options(item.options, item.correct_index)
            topic = Topic(position=topic_position, name=item.topic)
            topic.questions.append(Question(
                prompt=item.question, options=options, correct_index=correct_index,
                explanation=item.explanation, status="active",
            ))
            chapter.topics.append(topic)
        db.add(chapter)
        db.commit()

    set_status(db, study_set, "ready")
    log.info("Study set %s ready: %d chapters in %.0fs", study_set.id, total, time.monotonic() - started)
