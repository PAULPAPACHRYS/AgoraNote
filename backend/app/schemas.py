"""Pydantic models for request and response bodies."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Response models that can be filled straight from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    id: int
    email: str | None


class StudySetCreated(BaseModel):
    id: int


class StudySetListItem(ORMModel):
    id: int
    title: str | None
    status: str
    created_at: datetime


class StudySetDetail(ORMModel):
    id: int
    title: str | None
    status: str
    status_message: str
    error: str | None
    overview: str
    created_at: datetime
