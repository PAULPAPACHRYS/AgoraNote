"""
Keeps the local LLM (Ollama) and Whisper (speaches) from being on the GPU at the same time

Both don't fit in 8 GB together
With SHARED_GPU=true:
- every single GPU call (one LLM request, or one audio segment of at most 10 minutes) holds a lock in
  Redis, so calls from different Celery tasks take turns instead of overlapping
- before transcribing, Ollama is told to unload its model (keep_alive 0)
- Whisper unloads itself after every request (speaches runs with WHISPER__TTL=0; its unload endpoint
  DELETE /api/ps/{model} deadlocks in the version we use)

Locking per call (not per study set) means a replacement quiz question waits at most for the current segment,
never behind a whole hour-long transcription
"""
import logging
from contextlib import contextmanager

import httpx
import redis

from app import config

log = logging.getLogger(__name__)

# longer than any single call may take (timeouts are 600 s), so a crashed worker can't block forever
LOCK_TIMEOUT_SECONDS = 1200

#Redis client (connects lazily, on first use). Redis is shared by all worker containers, 
# so a lock stored there is seen by every task in every worker
_redis = redis.Redis.from_url(config.REDIS_URL)


def _unload_ollama() -> None:
    """
    ask Ollama to drop the LLM from GPU memory now. Harmless when it isn't loaded
    a generate request with no prompt and keep_alive 0 means "keep this model loaded for 0 seconds"
    """
    root = config.LLM_BASE_URL.removesuffix("/v1")  # Ollama's own API sits next to its /v1 API
    try:
        httpx.post(f"{root}/api/generate", json={"model": config.LLM_MODEL, "keep_alive": 0}, timeout=60)
    except httpx.HTTPError as error:
        log.warning("Could not unload the LLM before transcribing: %s", error)


@contextmanager
def use_gpu(task: str):
    """
    wrap one GPU call: `with use_gpu("llm"): ...` or `with use_gpu("transcribe"): ...`
    a context manager: the code before `yield` runs when the `with` block starts, the code after it
    when the block ends. Here: wait for the lock, (unload Ollama,) run the block, release the lock
    """
    if not config.SHARED_GPU:  # hosted APIs: nothing to coordinate, run the call straight away
        yield
        return
    # blocks until no other task holds the lock, `timeout` makes Redis drop the lock automatically if the holder crashes,
    # so a dead worker can't block the GPU forever
    with _redis.lock("agoranote:gpu", timeout=LOCK_TIMEOUT_SECONDS):
        if task == "transcribe" and config.LLM_PROVIDER != "mock":
            _unload_ollama()
        yield
