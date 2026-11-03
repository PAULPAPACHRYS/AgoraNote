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


class Progress(BaseModel):
    earned: int
    total: int
    percent: int


class StudySetListItem(BaseModel):
    id: int
    title: str | None
    status: str
    progress: Progress
    created_at: datetime


class ChapterScore(BaseModel):
    """A chapter's points and lock state (see gamification.score_chapters)."""

    id: int
    position: int
    title: str
    earned: int
    max: int
    unlock_threshold: int
    quiz_unlocked: bool
    completed: bool


class StudySetDetail(BaseModel):
    id: int
    title: str | None
    status: str
    status_message: str
    error: str | None
    overview: str
    created_at: datetime
    progress: Progress
    chapters: list[ChapterScore]


class ChapterPoints(BaseModel):
    earned: int
    max: int
    unlock_threshold: int


class QuizQuestion(ORMModel):
    """An unanswered question as the player sees it: never the answer or the explanation."""

    id: int
    prompt: str
    options: list[str]


class QuizTopic(BaseModel):
    id: int
    name: str
    points: int
    mastered: bool
    preparing: bool  # a replacement question is being generated
    question: QuizQuestion | None


class QuizState(BaseModel):
    chapter_id: int
    earned: int
    max: int
    unlock_threshold: int
    progress: Progress
    topics: list[QuizTopic]


class AnswerIn(BaseModel):
    selected_index: int = Field(ge=0, le=3)


class ChapterLinkOut(BaseModel):
    id: int
    title: str


class AnswerOut(BaseModel):
    correct: bool
    correct_index: int
    explanation: str
    points_awarded: int
    chapter: ChapterPoints
    progress: Progress
    unlocked_chapter: ChapterLinkOut | None  # only on the answer that crosses the threshold
    replacement_pending: bool


class SearchResult(BaseModel):
    study_set_id: int
    study_set_title: str | None
    chapter_id: int
    chapter_position: int
    chapter_title: str
    snippet: str  # matches wrapped in [[ ]]


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


# --- Chapter page (reuses the content models above) -------------------------------------------

class ChapterDetail(BaseModel):
    id: int
    position: int
    title: str
    study_set_id: int
    study_set_title: str | None
    chapter_count: int
    earned: int
    max: int
    unlock_threshold: int
    quiz_unlocked: bool
    completed: bool
    points_to_unlock: int  # more points needed in the previous chapter; 0 when unlocked
    summary: list[str]
    key_concepts: list[KeyConcept]
    qa_pairs: list[QAPair]
    study_aids: StudyAids
    prev_chapter: ChapterLinkOut | None
    next_chapter: ChapterLinkOut | None
