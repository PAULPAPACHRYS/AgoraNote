"""
Celery app and background tasks: the slow work that must not happen inside an API request

The API puts a small message on a queue in Redis (`task.delay(...)`),
a separate worker process (the `worker` / `worker-quick` services in docker-compose.yml) takes it off the queue and runs the task function
start a worker with: celery -A app.worker worker --loglevel=info

Tasks:
- process_study_set(id): the whole pipeline for a new upload, step by step (see run_pipeline):
    extracting   -> read the text of every document (and download recordings)
    transcribing -> recordings to text with Whisper, in <=10-minute segments
    structuring  -> the LLM splits the text into chapters, writes the title and overview
    generating   -> the LLM writes each chapter's materials and quiz
    ready        (or failed, with a message the user can read)
  each step updates study_set.status/status_message, which the browser polls to show progress
- generate_replacement_question(topic_id): after a wrong answer, a new question on the same topic
- ping(): a trivial task to check that the worker is running
"""
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

# broker = where task messages are queued; backend = where task results are kept (both Redis)
celery = Celery("agoranote", broker=config.REDIS_URL, backend=config.REDIS_URL)
celery.conf.broker_connection_retry_on_startup = True  # keep trying if Redis isn't up yet at start
# two queues, each with its own worker (see docker-compose.yml): study sets are processed one at a
# time, and replacement quiz questions never wait behind a long transcription
celery.conf.task_default_queue = "processing"
celery.conf.task_routes = {"app.worker.generate_replacement_question": {"queue": "quick"}}

MIN_INPUT_CHARS = 500  # less text than this is not enough to build chapters and quizzes from
# user-readable error messages, stored in study_set.error and shown on the study set page
GENERIC_ERROR = "Something went wrong while processing this study set. Please try again."
UNREACHABLE_ERROR = "The AI service could not be reached or took too long to answer. Please try again later."
TRANSCRIBE_UNREACHABLE_ERROR = (
    "The transcription service could not be reached or took too long to answer. Please try again later."
)


@celery.task
def ping():
    # trivial task used to check that the worker is wired up
    return "pong"


def set_status(db, study_set: StudySet, status: str, message: str = "") -> None:
    # save a new pipeline status right away (commit), so the polling browser sees the progress
    study_set.status = status
    study_set.status_message = message
    db.commit()


def shuffle_options(options: list[str], correct_index: int) -> tuple[list[str], int]:
    """
    shuffle the options in code (LLMs put the right answer first far too often)
    returns the shuffled options and the new position of the correct one. `order` is the shuffled list of old positions,
    e.g. [2, 0, 3, 1]: the option that was at index 0 is now at order.index(0) = 1
    """
    order = list(range(len(options)))
    random.shuffle(order)
    return [options[i] for i in order], order.index(correct_index)


def build_search_text(chapter: Chapter) -> str:
    # all searchable text of a chapter in one string (indexed for full-text search, see routes/search.py)
    parts = [chapter.title, *chapter.summary]
    parts += [f"{c['term']}: {c['explanation']}" for c in chapter.key_concepts]
    parts += [f"{qa['question']} {qa['answer']}" for qa in chapter.qa_pairs]
    parts.append(chapter.content)
    return "\n".join(parts)


# bind=True: the function gets `self` (the task) and can see how often it has been retried
# autoretry_for: when an httpx error (network, timeout, 429/5xx from an AI service) escapes the function,
# Celery runs the task again later, at most max_retries=3 times, waiting longer each time
@celery.task(
    bind=True, autoretry_for=(httpx.HTTPError,), retry_backoff=True, max_retries=3,
)
def process_study_set(self, study_set_id: int):
    """
    turn a study set's uploaded files into chapters with study materials and quizzes
    Errors: a temporary AI-service problem is retried (re-raised for autoretry_for) while retries are left, 
    anything else marks the set "failed" with a user-readable message (and logs the details)
    """
    with SessionLocal() as db:
        study_set = db.get(StudySet, study_set_id)
        if study_set is None:
            return  # deleted before we got to it
        try:
            run_pipeline(db, study_set)
        except Exception as exc:
            db.rollback()  # throw away half-done, uncommitted changes before writing the error
            if isinstance(exc, httpx.HTTPError) and self.request.retries < self.max_retries:
                log.warning("Provider error on study set %s, will retry: %s", study_set_id, exc)
                set_status(db, study_set, study_set.status, "The AI service had a hiccup, retrying…")
                raise  # autoretry_for re-queues the task with backoff
            log.exception("Processing study set %s failed", study_set_id)
            if isinstance(exc, ProcessingError):
                study_set.error = str(exc)
            elif isinstance(exc, httpx.HTTPError):
                #status still says which step was running: transcription or the LLM steps
                transcribing = study_set.status == "transcribing"
                study_set.error = TRANSCRIBE_UNREACHABLE_ERROR if transcribing else UNREACHABLE_ERROR
            else:
                study_set.error = GENERIC_ERROR
            set_status(db, study_set, "failed")


@celery.task(
    bind=True, autoretry_for=(httpx.HTTPError,), retry_backoff=True, max_retries=3,
)
def generate_replacement_question(self, topic_id: int):
    """
    after a wrong answer: a new question on the same topic, 
    different from all previous ones runs on the "quick" queue (see the task_routes setting above),
    so it never waits behind a long study set until it finishes,
    the quiz shows the topic as "preparing"
    """
    with SessionLocal() as db:
        topic = db.get(Topic, topic_id)
        #dedupe: nothing to do if the topic is gone, mastered, or already has a question waiting
        if topic is None or topic.mastered_at or any(q.status == "active" for q in topic.questions):
            return
        previous = topic.questions  # ordered by id, so the last one is the most recent

        try:
            #study set's language (e.g. "Greek"), so the new question is in the right language
            language = detect_language(topic.chapter.study_set.source_text)
            # LLM gets every previous question on this topic, so it can ask something different
            new = generate.replacement_question(
                topic.chapter.content, topic.name, [q.prompt for q in previous], language
            )
            prompt, explanation = new.question, new.explanation
            options, correct_index = shuffle_options(new.options, new.correct_index)
        except Exception as exc:
            if isinstance(exc, httpx.HTTPError) and self.request.retries < self.max_retries:
                raise  #autoretry_for re-queues the task with backoff
            #never leave the player stuck: ask the most recent question again, options reshuffled
            log.exception("Replacement question for topic %s failed; reusing the last one", topic_id)
            last = previous[-1]
            prompt, explanation = last.prompt, last.explanation
            options, correct_index = shuffle_options(last.options, last.correct_index)

        # new active question; the quiz page picks it up on its next poll
        db.add(Question(
            topic_id=topic.id, prompt=prompt, options=options, correct_index=correct_index,
            explanation=explanation, status="active",
        ))
        try:
            db.commit()
        except IntegrityError:
            # another run got there first: the unique index allows one active question per topic
            db.rollback()


def run_pipeline(db, study_set: StudySet) -> None:
    """
    processing steps for one study set (called by process_study_set, which handles errors)
    Raises ProcessingError for problems with the user's material (shown to them as-is) and lets
    httpx errors from the AI services through (they are retried)
    """
    started = time.monotonic()
    # idempotent: a retry starts from a clean slate
    db.execute(delete(Chapter).where(Chapter.study_set_id == study_set.id))
    study_set.error = None
    study_set.overview = ""
    set_status(db, study_set, "extracting", "Reading your files")

    # --- 1. extracting / 2. transcribing: every file to text -----------------------------------
    files = study_set.source_files  # in upload order (position)
    texts = {}  # position -> text
    #files are copied from storage into a temporary folder, which is deleted afterwards
    with tempfile.TemporaryDirectory() as tmp:
        local = {}  # position -> path of the local copy
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

        #recordings after the documents: transcription is the slow part, 
        # so its progress gets its own status messages ("Transcribing recording 1 of 2 (part 3 of 7)")
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

    # --- 3. combine and check the text ------------------------------------------------------------
    #join the files in upload order; with several files, a heading line marks where each starts
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

    # --- 4. structuring: find the chapters -----------------------------------------------------
    set_status(db, study_set, "structuring", "Finding the chapters")
    # ~1,000-character pieces, the LLM groups consecutive blocks into chapters
    blocks = split_into_blocks(source_text)
    structure = generate.structure(blocks)
    if not study_set.title:  # a title the user typed wins over the generated one
        study_set.title = structure.title
    study_set.overview = structure.overview

    # --- 5. generating: the study materials of every chapter -------------------------------------
    language = detect_language(source_text)  # the whole set's language, passed to every chapter
    total = len(structure.chapters)
    for position, span in enumerate(structure.chapters, start=1):
        set_status(db, study_set, "generating", f"Generating chapter {position} of {total}")
        #chapter's own text, its blocks joined back together
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
        #each quiz item becomes a Topic (scoring slot) with its first, active question
        for topic_position, item in enumerate(materials.quiz, start=1):
            options, correct_index = shuffle_options(item.options, item.correct_index)
            topic = Topic(position=topic_position, name=item.topic)
            topic.questions.append(Question(
                prompt=item.question, options=options, correct_index=correct_index,
                explanation=item.explanation, status="active",
            ))
            chapter.topics.append(topic)
        db.add(chapter)  # adding the chapter also adds its topics and questions
        db.commit()  # each chapter is saved as soon as it is done

    # --- 6. ready -----------------------------------------------------------------------------
    set_status(db, study_set, "ready")
    log.info("Study set %s ready: %d chapters in %.0fs", study_set.id, total, time.monotonic() - started)
