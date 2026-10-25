"""Pydantic models: API request/response bodies, and the JSON contracts for LLM output."""
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app import config


# --- API responses ----------------------------------------------------------------------------

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


class ChapterListItem(ORMModel):
    id: int
    position: int
    title: str


class StudySetDetail(ORMModel):
    id: int
    title: str | None
    status: str
    status_message: str
    error: str | None
    overview: str
    created_at: datetime
    chapters: list[ChapterListItem]


# --- LLM output contracts (see prompts.py) ----------------------------------------------------

class ChapterSpan(BaseModel):
    title: str = Field(min_length=1)
    start_block: int = Field(ge=0)
    end_block: int = Field(ge=0)


class StructureOut(BaseModel):
    title: str = Field(min_length=1)
    overview: str
    chapters: list[ChapterSpan] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def chapters_cover_all_blocks(self, info: ValidationInfo):
        """Chapters must be in order, contiguous, non-overlapping and cover every block.

        The number of blocks is passed in as validation context: {"n_blocks": N}.
        """
        n_blocks = (info.context or {}).get("n_blocks")
        if n_blocks is None:
            return self
        expected_start = 0
        for i, chapter in enumerate(self.chapters):
            if chapter.start_block != expected_start or chapter.end_block < chapter.start_block:
                raise ValueError(
                    f"chapter {i} must start at block {expected_start} and end at or after its start"
                )
            expected_start = chapter.end_block + 1
        if expected_start != n_blocks:
            raise ValueError(f"the last chapter must end at block {n_blocks - 1}")
        return self


def _four_distinct_options(options: list[str]) -> list[str]:
    if len({o.strip().casefold() for o in options}) != 4:
        raise ValueError("the 4 options must all be different")
    return options


FourOptions = Annotated[list[str], Field(min_length=4, max_length=4), AfterValidator(_four_distinct_options)]


class QuestionOut(BaseModel):
    question: str = Field(min_length=1)
    options: FourOptions
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1)


class QuizItem(QuestionOut):
    topic: str = Field(min_length=1)


class KeyConcept(BaseModel):
    term: str
    explanation: str


class QAPair(BaseModel):
    question: str
    answer: str


class OutlineSection(BaseModel):
    heading: str
    points: list[str]


class StudyAids(BaseModel):
    outline: list[OutlineSection]
    review_checklist: list[str]
    memory_tips: list[str]


class ChapterOut(BaseModel):
    summary: list[str] = Field(min_length=1)
    key_concepts: list[KeyConcept] = Field(min_length=1)
    qa_pairs: list[QAPair] = Field(min_length=1)
    study_aids: StudyAids
    quiz: list[QuizItem]

    @field_validator("quiz")
    @classmethod
    def one_item_per_topic(cls, quiz: list[QuizItem]) -> list[QuizItem]:
        # Each quiz item becomes a scoring slot (topic), so the count and distinct topics matter.
        if len(quiz) != config.QUESTIONS_PER_CHAPTER:
            raise ValueError(f"quiz must have exactly {config.QUESTIONS_PER_CHAPTER} items")
        if len({item.topic.strip().casefold() for item in quiz}) != len(quiz):
            raise ValueError("every quiz item must cover a different topic")
        return quiz
