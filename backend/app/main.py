from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config

# Dev auth trusts everyone as the same user, so it must never reach production.
if config.ENV == "production" and config.AUTH_MODE == "dev":
    raise RuntimeError("Refusing to start: AUTH_MODE=dev is not allowed when ENV=production.")

app = FastAPI(title="AgoraNote API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
