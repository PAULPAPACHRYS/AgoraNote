"""
The FastAPI application: the entry point of the API server.

Started by `uvicorn app.main:app` (see docker-compose.yml)
1. refuses to start with unsafe settings in production
2. creates the database tables on startup
3. allows the frontend's origin to call it from the browser (CORS)
4. plugs in the routers from app/routes/ (one module per area of the API)
5. defines two small endpoints itself: /api/health and /api/me

All endpoints live under /api and return JSON. Errors are FastAPI's default {"detail": "..."}
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.auth import get_current_user
from app.db import engine
from app.models import Base, User
from app.routes import chapters, quiz, search, study_sets
from app.schemas import UserOut

# dev auth trusts everyone as the same user, so it must never reach production ( will before deployment)
if config.ENV == "production" and config.AUTH_MODE == "dev":
    raise RuntimeError("Refusing to start: AUTH_MODE=dev is not allowed when ENV=production.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    #runs once when the server starts (code before `yield`) and once when it stops (after it)
    # only the API creates tables (not the worker). No migrations yet: reset the DB on schema changes
    # create_all only creates tables that don't exist yet; it never changes existing ones
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="AgoraNote API", lifespan=lifespan)

#browsers block JavaScript from calling another origin (here: localhost:5173 -> localhost:8000)
#unless the server allows it, only the frontend's own address is allowed
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Each router adds a group of endpoints (see the modules in app/routes/)
app.include_router(study_sets.router)  # /api/study-sets...
app.include_router(chapters.router)  # /api/chapters/{id}
app.include_router(quiz.router)  # /api/chapters/{id}/quiz, /api/questions/{id}/answer
app.include_router(search.router)  # /api/search


@app.get("/api/health")
def health():
    #Liveness check for Docker/Railway: answers without touching the database or needing a login
    return {"status": "ok"}


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """The signed-in user. `Depends(get_current_user)` makes FastAPI run auth before this function."""
    return user
