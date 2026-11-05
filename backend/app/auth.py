"""
The get_current_user dependency answers "Who is making this request?" for every endpoint

Endpoints declare `user: User = Depends(get_current_user)` FastAPI then calls get_current_user first
and passes the result in, if it raises an HTTPException, the endpoint never runs

AUTH_MODE=dev (now): there is no login yet, every request is the same fixed "dev-user"
"""
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.models import User

# in dev mode every request is this one user, so the app works without an auth provider
DEV_AUTH_ID = "dev-user"


def get_or_create_user(db: Session, auth_id: str, email: str | None = None) -> User:
    #The user with this auth_id, creating the row on their very first request
    user = db.scalar(select(User).where(User.auth_id == auth_id))
    if user is None:
        # ON CONFLICT DO NOTHING: two first requests arriving at once must not both fail.
        # (The second insert simply does nothing; both then read the same row below.)
        db.execute(
            insert(User).values(auth_id=auth_id, email=email).on_conflict_do_nothing(index_elements=["auth_id"])
        )
        db.commit()
        user = db.scalar(select(User).where(User.auth_id == auth_id))
    return user


def get_current_user(db: Session = Depends(get_db)) -> User:
    # FastAPI dependency: the user making the request or an HTTP error
    if config.AUTH_MODE == "dev":
        return get_or_create_user(db, DEV_AUTH_ID)
    #real verification will be added with user auth later
    raise HTTPException(status_code=501, detail=f"AUTH_MODE={config.AUTH_MODE} is not implemented yet.")
