"""
Talking to the LLM: one implementation of the OpenAI-compatible Chat Completions API

The same code works with Ollama running locally (its /v1 endpoint), OpenAI and OpenRouter;
only LLM_BASE_URL, LLM_MODEL and LLM_API_KEY change. Plain httpx, no vendor SDK

One call = one HTTP POST to {LLM_BASE_URL}/chat/completions with a "system" message (the
instructions, see prompts.py) and a "user" message (the material). The reply's text is parsed as JSON

Every call is logged with its token counts and speed, so the cost/time of a study set is visible
"""
import json
import logging
import re
import time

import httpx

from app import config
from app.ai.gpu import use_gpu

log = logging.getLogger(__name__)

'''
upper limit for one reply, hidden "thinking" included. Our biggest reply (a chapter's materials) is ~2,000-3,500 tokens, plus ~1,000 when the model thinks,
the cap stops a runaway reply together with generate.MAX_CHAPTER_CHARS it keeps every call inside a 16k-token context window
'''
MAX_COMPLETION_TOKENS = 7000

# matches a whole reply wrapped in ``` or ```json fences and captures what is inside
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def strip_fences(text: str) -> str:
    #remove a ```json ... ``` wrapper, which some models add even when asked for bare JSON
    match = _FENCE.match(text)
    return match.group(1) if match else text.strip()


def complete_json(system: str, user: str, schema: dict | None = None, name: str = "result") -> dict:
    """
    send a system + user prompt and return the reply parsed as a JSON object

    with `schema` (a JSON Schema), the provider is asked for structured output: the model can then
    only produce JSON of that shape (Ollama enforces it with a grammar). Without it, plain JSON mode

    raises httpx errors for network problems, timeouts, rate limits and 5xx (the Celery task retries those),
    RuntimeError for other HTTP errors (retrying won't help), 
    and ValueError when the reply isn't valid JSON (generate._ask retries that once)
    """

    # request body of the OpenAI Chat Completions API
    body = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.3,  # fairly deterministic: we want faithful summaries, not creativity
        "max_tokens": MAX_COMPLETION_TOKENS,
        "response_format": (
            {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}
            if schema
            else {"type": "json_object"}
        ),
    }
    if config.LLM_REASONING_EFFORT:
        body["reasoning_effort"] = config.LLM_REASONING_EFFORT
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}
    #up to LLM_TIMEOUT_SECONDS for the reply, but give up after 10 s if the server can't be reached
    timeout = httpx.Timeout(config.LLM_TIMEOUT_SECONDS, connect=10)

    with use_gpu("llm"):  # waits while Whisper is transcribing a segment (local GPU only)
        started = time.monotonic()
        response = httpx.post(f"{config.LLM_BASE_URL}/chat/completions", json=body, headers=headers, timeout=timeout)
        seconds = time.monotonic() - started  # measured inside the lock: waiting for the GPU doesn't count

    # 429 = rate limited, 5xx = server trouble: temporary, so raise an httpx error (retried by Celery)
    if response.status_code == 429 or response.status_code >= 500:
        response.raise_for_status()  # temporary: let the task retry
    if response.status_code >= 400:
        raise RuntimeError(f"LLM request failed ({response.status_code}): {response.text[:500]}")

    data = response.json()
    # token counts as reported by the provider
    usage = data.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    log.info(
        "LLM %s: %d prompt + %d completion tokens in %.1fs (%.1f tokens/s)",
        name, prompt_tokens, completion_tokens, seconds, completion_tokens / seconds if seconds else 0,
    )

    choice = data["choices"][0]  # we ask for one reply, so there is one choice
    # finish_reason "length" means the reply stopped because it ran out of room, not because it was done
    if choice.get("finish_reason") == "length":
        if completion_tokens < MAX_COMPLETION_TOKENS:
            # cut off before our own cap: the model's context window is full. Retrying can't help
            raise RuntimeError(
                f"The LLM's context window is too small: the reply was cut off at {prompt_tokens} + "
                f"{completion_tokens} = {prompt_tokens + completion_tokens} tokens. AgoraNote needs 16384; "
                "for Ollama set OLLAMA_CONTEXT_LENGTH=16384 and restart Ollama (check with `ollama ps`)."
            )
        raise ValueError(f"the reply was cut off after {completion_tokens} tokens")
    try:
        return json.loads(strip_fences(choice["message"].get("content") or ""))
    except json.JSONDecodeError as error:
        raise ValueError(f"the reply is not valid JSON: {error}") from error
