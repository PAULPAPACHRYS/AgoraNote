"""
The signed-in user's display settings (theme, text size, line spacing...): GET/PUT /api/display-settings

The browser keeps its own copy too (localStorage), so the settings apply at once on the next visit,
even before signing in. Saving them here makes them follow the user to other browsers and devices.
Only the current user's own row is ever read or changed, so there is nothing to filter by user.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import DisplaySettings

router = APIRouter(prefix="/api/display-settings")


@router.get("", response_model=DisplaySettings | None)
def get_display_settings(user: User = Depends(get_current_user)):
    # null when the user never saved any: then the browser keeps the settings it has.
    # Read through the schema, so settings saved before a new setting existed get its default
    if user.display_settings is None:
        return None
    return DisplaySettings(**user.display_settings)


@router.put("", response_model=DisplaySettings)
def save_display_settings(
    settings: DisplaySettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # replaces all of them (the panel always sends the full set)
    user.display_settings = settings.model_dump()
    db.commit()
    return settings
