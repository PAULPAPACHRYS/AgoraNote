from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.auth import get_current_user
from app.db import engine
from app.models import Base, User
from app.routes import study_sets
from app.schemas import UserOut

# Dev auth trusts everyone as the same user, so it must never reach production.
if config.ENV == "production" and config.AUTH_MODE == "dev":
    raise RuntimeError("Refusing to start: AUTH_MODE=dev is not allowed when ENV=production.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only the API creates tables (not the worker). No migrations yet: reset the DB on schema changes.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="AgoraNote API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(study_sets.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
