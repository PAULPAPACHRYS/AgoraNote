"""
All configuration, read once from environment variables

-Every setting lives here, so the rest of the code just does `from app import config` and reads `config.SOMETHING`
-Values come from the environment: locally Docker Compose loads them from `.env`
(see `.env.example` for every variable with an explanation); on Railway they are set per service
-Each `os.environ.get(NAME, default)` falls back to a development-friendly default, so the app starts
even when a variable is missing
"""
import os

# --- general --------------------------------------------------------------------------------------

# "development" or "production", in production some unsafe shortcuts are refused (see main.py)
ENV = os.environ.get("ENV", "development")
# the address the browser app is served from, only this origin may call the API (CORS, see main.py)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# --- database / queue -----------------------------------------------------------------------------

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://agoranote:agoranote@db:5432/agoranote"
)
# Railway hands out "postgresql://…", but SQLAlchemy needs to be told to use psycopg 3
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
# Redis is the Celery message broker (the queue of background tasks) and also holds the GPU lock
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# --- auth -----------------------------------------------------------------------------------------

# "dev" = no login yet, every request is one fixed development user (see auth.py)
AUTH_MODE = os.environ.get("AUTH_MODE", "dev")
AUTH_JWKS_URL = os.environ.get("AUTH_JWKS_URL", "")
AUTH_ISSUER = os.environ.get("AUTH_ISSUER", "")

# --- storage --------------------------------------------------------------------------------------

# where uploaded files are kept: "local" = a folder on disk (a Docker volume shared by the API and the workers)
#r2 = Cloudflare R2 object storage for account data after authentication is implemented
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
LOCAL_STORAGE_DIR = os.environ.get("LOCAL_STORAGE_DIR", "/data/uploads")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")

# --- study materials LLM --------------------------------------------------

# LLM_PROVIDER: local, will switch to API before deployment
# Chat Completions API: Ollama's /v1 endpoint locally
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
# The trailing "/" is removed so code can always write f"{LLM_BASE_URL}/chat/completions"
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")
#local models are slow, allow minutes per call, not seconds
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "600"))
# Sent as "reasoning_effort" when set, "none" switches off a model's hidden thinking (much faster on Ollama)
LLM_REASONING_EFFORT = os.environ.get("LLM_REASONING_EFFORT", "")

# --- speech to text LLM ----------------------------------------------------

# TRANSCRIBE_PROVIDER: local, will switch to API before deployment
TRANSCRIBE_PROVIDER = os.environ.get("TRANSCRIBE_PROVIDER", "mock")
TRANSCRIBE_API_KEY = os.environ.get("TRANSCRIBE_API_KEY", "")
TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "")
TRANSCRIBE_BASE_URL = os.environ.get("TRANSCRIBE_BASE_URL", "").rstrip("/")
#audio segment (at most 10 minutes of audio each)
TRANSCRIBE_TIMEOUT_SECONDS = int(os.environ.get("TRANSCRIBE_TIMEOUT_SECONDS", "600"))
# speaches-only: skip silence before transcribing (faster, and Whisper doesn't "hear" words in silence)
TRANSCRIBE_VAD_FILTER = os.environ.get("TRANSCRIBE_VAD_FILTER", "false").lower() == "true"

#local LLM and Whisper share one small GPU: when true, every GPU call takes a lock in Redis and the
#local LLM (Ollama) is unloaded before transcribing (see ai/gpu.py), switch to false for hosted APIs
SHARED_GPU = os.environ.get("SHARED_GPU", "false").lower() == "true"

# --- limits on what users may upload ---------------------------------------------------------------

# max 5 files per study set, 200 MB each file
MAX_FILES_PER_SET = int(os.environ.get("MAX_FILES_PER_SET", "5"))
MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", "200"))
# upper limit for the combined text of a study set (all files, after extraction/transcription)
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", "200000"))

# --- game constants ----------------------------------

POINTS_PER_QUESTION = 10  # points for mastering one quiz topic
QUESTIONS_PER_CHAPTER = 5  # quiz topics (scoring slots) per chapter
UNLOCK_RATIO = 0.7  # precent of a chapter's points needed to unlock access to the next chapter
