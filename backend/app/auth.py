from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.models import User

# In dev mode every request is this one user, so the app works without an auth provider.
DEV_AUTH_ID = "dev-user"


def get_or_create_user(db: Session, auth_id: str, email: str | None = None) -> User:
    user = db.scalar(select(User).where(User.auth_id == auth_id))
    if user is None:
        # ON CONFLICT DO NOTHING: two first requests arriving at once must not both fail.
        db.execute(
            insert(User).values(auth_id=auth_id, email=email).on_conflict_do_nothing(index_elements=["auth_id"])
        )
        db.commit()
        user = db.scalar(select(User).where(User.auth_id == auth_id))
    return user


def get_current_user(db: Session = Depends(get_db)) -> User:
    if config.AUTH_MODE == "dev":
        return get_or_create_user(db, DEV_AUTH_ID)
    # Real JWT verification is added once the auth provider is chosen (Phase 8).
    raise HTTPException(status_code=501, detail=f"AUTH_MODE={config.AUTH_MODE} is not implemented yet.")
