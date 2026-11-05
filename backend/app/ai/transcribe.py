"""
Speech to text /audio/transcriptions API, plain httpx

The flow for one recording (transcribe):
  ffmpeg -> <=10-minute MP3 segments (extract.prepare_audio)
  -> each segment is uploaded to /audio/transcriptions (transcribe_segment), in order
  -> repetition loops are cleaned up (collapse_repeats)
  -> the segment texts are joined

With TRANSCRIBE_PROVIDER=mock a fixed placeholder transcript is returned instead
"""
import logging
import os
import tempfile
import time
from collections.abc import Callable

import httpx

from app import config
from app.ai.extract import audio_duration, prepare_audio, split_sentences
from app.ai.gpu import use_gpu

log = logging.getLogger(__name__)

# long enough (> MIN_INPUT_CHARS) for the rest of the pipeline to build a study set from it
MOCK_TRANSCRIPT = (
    "This is a placeholder transcript, because transcription runs in mock mode. "
    "In a real lecture the speaker would introduce the topic of the day and explain why it matters. "
    "Then the main ideas would follow, one after another, with examples that make them concrete. "
    "A good lecture connects every new idea to something the students already know. "
    "Definitions are given first, and then they are applied to small problems. "
    "The lecturer might pause to ask the audience a question and wait for answers. "
    "Mistakes that students often make are pointed out, together with ways to avoid them. "
    "Towards the end, the most important points are repeated as a short summary. "
    "Finally, the lecturer suggests what to read before the next session and which exercises to try. "
    "Students are encouraged to review their notes within a day, because memory fades quickly without practice. "
    "Spaced repetition and self-testing are mentioned as the most effective ways to study. "
    "The session closes with time for questions from the audience."
)


def transcribe(
    audio_path: str,
    filename: str = "",
    on_progress: Callable[[int, int], None] | None = None,
) -> str:
    """
    transcribe a whole recording (any audio/video format ffmpeg reads)
    the recording is cut into <=10-minute segments that are transcribed in order
    Whisper detects the language on the first segment that language is then passed for all other segments,
    because detection on a single segment (e.g. one full of English terms in a Greek lecture) 
    can go wrong `on_progress(i, n)` is called before segment i of n
    """
    if config.TRANSCRIBE_PROVIDER == "mock":
        return f"(Mock transcript of {filename or os.path.basename(audio_path)}.) {MOCK_TRANSCRIPT}"

    texts, language = [], None  # language stays None until the first segment has been transcribed
    with tempfile.TemporaryDirectory() as tmp:  # removed afterwards, also on errors
        segments = prepare_audio(audio_path, filename or os.path.basename(audio_path), tmp)
        for i, segment in enumerate(segments, start=1):
            if on_progress:
                on_progress(i, len(segments))
            text, detected = transcribe_segment(segment, language)
            language = language or detected  # keep the first segment's language for all others
            texts.append(collapse_repeats(text.strip()))
    return "\n\n".join(t for t in texts if t)


def collapse_repeats(text: str) -> str:
    """
    whisper sometimes gets stuck and writes the same sentence many times in a row, 
    keep one only runs of 3 or more identical sentences are collapsed: real speech rarely repeats a whole sentence three times back to back
    """
    sentences = split_sentences(text)
    kept, i = [], 0
    while i < len(sentences):
        #count how many times sentence i repeats directly after itself
        run = 1
        while i + run < len(sentences) and sentences[i + run] == sentences[i]:
            run += 1
        kept.extend(sentences[i : i + (1 if run >= 3 else run)])  # 3+ in a row: keep one; else keep all
        i += run  # continue after the run
    return " ".join(kept)


def transcribe_segment(path: str, language: str | None = None) -> tuple[str, str | None]:
    """
    transcribe one short audio file; returns (text, detected language code or None)
    raises httpx errors for network problems, timeouts, rate limits and 5xx 
    (the Celery task retries those) and RuntimeError for other HTTP errors (retrying won't help)
    
    form fields of the request. verbose_json also returns the detected language, 
    temperature 0 makes whisper pick the most likely words instead of sampling
    """
    data = {"model": config.TRANSCRIBE_MODEL, "response_format": "verbose_json", "temperature": "0"}
    if language:
        data["language"] = language
    if config.TRANSCRIBE_VAD_FILTER:
        data["vad_filter"] = "true"
    headers = {"Authorization": f"Bearer {config.TRANSCRIBE_API_KEY}"} if config.TRANSCRIBE_API_KEY else {}
    seconds_of_audio = audio_duration(path)  # only for the log line

    #hold the GPU lock while Whisper works (Ollama is unloaded first, see gpu.py)
    #file is sent as a multipart upload, like a browser form with a file field.
    with use_gpu("transcribe"), open(path, "rb") as audio:
        started = time.monotonic()
        response = httpx.post(
            f"{config.TRANSCRIBE_BASE_URL}/audio/transcriptions",
            data=data,
            files={"file": (os.path.basename(path), audio, "audio/mpeg")},
            headers=headers,
            timeout=httpx.Timeout(config.TRANSCRIBE_TIMEOUT_SECONDS, connect=10),
        )
        seconds = time.monotonic() - started

    # same error handling as llm.py: 429/5xx are temporary (retried), other 4xx are not
    if response.status_code == 429 or response.status_code >= 500:
        response.raise_for_status()  # temporary: let the task retry
    if response.status_code >= 400:
        raise RuntimeError(f"Transcription failed ({response.status_code}): {response.text[:500]}")

    result = response.json()
    # speaches returns a code ("el"), only a 2-letter code is passed on to later segments
    detected = result.get("language")
    detected = detected if isinstance(detected, str) and len(detected) == 2 else None
    log.info(
        "Transcribed %.0fs of audio in %.1fs (%.1fx real time), language=%s",
        seconds_of_audio, seconds, seconds_of_audio / seconds if seconds else 0, language or detected,
    )
    return result.get("text", ""), detected
