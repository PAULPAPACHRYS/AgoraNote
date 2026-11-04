"""All configuration, read once from environment variables."""
import os

# general
ENV = os.environ.get("ENV", "development")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# database / queue
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://agoranote:agoranote@db:5432/agoranote"
)
# Railway hands out "postgresql://…", but SQLAlchemy needs to be told to use psycopg 3.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# auth
AUTH_MODE = os.environ.get("AUTH_MODE", "dev")
AUTH_JWKS_URL = os.environ.get("AUTH_JWKS_URL", "")
AUTH_ISSUER = os.environ.get("AUTH_ISSUER", "")

# storage
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
LOCAL_STORAGE_DIR = os.environ.get("LOCAL_STORAGE_DIR", "/data/uploads")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")

# AI
# LLM_PROVIDER: "mock" (offline, for development and tests) or "openai" = any OpenAI-compatible
# Chat Completions API: Ollama's /v1 endpoint locally, OpenAI or OpenRouter when hosted.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")
# Local models are slow: allow minutes per call, not seconds.
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "600"))
# Sent as "reasoning_effort" when set. "none" switches off a model's hidden thinking (much faster on
# Ollama); leave empty for models/providers that don't accept the field.
LLM_REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "")
# TRANSCRIBE_PROVIDER: "mock" or "openai" = any OpenAI-compatible /audio/transcriptions API:
# speaches (local faster-whisper) or OpenAI itself when hosted.
TRANSCRIBE_PROVIDER = os.environ.get("TRANSCRIBE_PROVIDER", "mock")
TRANSCRIBE_API_KEY = os.environ.get("TRANSCRIBE_API_KEY", "")
TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "")
TRANSCRIBE_BASE_URL = os.environ.get("TRANSCRIBE_BASE_URL", "").rstrip("/")
TRANSCRIBE_TIMEOUT_SECONDS = int(os.environ.get("TRANSCRIBE_TIMEOUT_SECONDS", "600"))
# speaches-only: skip silence before transcribing (faster, and Whisper doesn't "hear" words in silence).
# OpenAI's API doesn't know this field, so keep it off there.
TRANSCRIBE_VAD_FILTER = os.environ.get("TRANSCRIBE_VAD_FILTER", "false").lower() == "true"

# Local LLM and Whisper share one small GPU: when true, every GPU call takes a lock in Redis and the
# local LLM (Ollama) is unloaded before transcribing. Keep false for hosted APIs.
SHARED_GPU = os.environ.get("SHARED_GPU", "false").lower() == "true"

# limits
MAX_FILES_PER_SET = int(os.environ.get("MAX_FILES_PER_SET", "5"))
MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", "200"))
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "200000"))

# game constants (not configurable per environment on purpose)
POINTS_PER_QUESTION = 10
QUESTIONS_PER_CHAPTER = 5
UNLOCK_RATIO = 0.7
