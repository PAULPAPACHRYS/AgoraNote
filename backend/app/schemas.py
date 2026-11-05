"""
Pydantic models: the exact shape of JSON going in and out

Pydantic checks data against these classes: wrong types, missing fields or failed rules raise a ValidationError
They are used for 3 things:
1. **API responses/requests**: an endpoint's `response_model=...` makes FastAPI send exactly these
   fields and nothing else, so e.g. a question's answer can never leak by accident
2. **LLM output contracts**: the JSON the LLM must produce. Its replies are validated against these
   models (see ai/generate.py), and the same models are turned into JSON Schemas that tell the LLM
   server which shape to produce (structured output)
3. **What the LLM actually writes** (the *Draft* classes at the bottom): an easier format for small
   models, converted in code into the contract format
"""
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app import config


# --- API responses ----------------------------------------------------------------------------

class ORMModel(BaseModel):
    #response models that can be filled straight from SQLAlchemy objects

    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    # GET /api/me

    id: int
    email: str | None


class StudySetCreated(BaseModel):
    # POST /api/study-sets: the new set's id (processing continues in the background)

    id: int


class Progress(BaseModel):
    # points earned vs. points available across all chapters (the overall progress bar)

    earned: int
    total: int
    percent: int


class StudySetListItem(BaseModel):
    # one card on the dashboard (GET /api/study-sets)

    id: int
    title: str | None
    status: str
    progress: Progress
    created_at: datetime


class ChapterScore(BaseModel):
    # chapter's points and lock state (see gamification.score_chapters)

    id: int
    position: int
    title: str
    earned: int
    max: int
    unlock_threshold: int
    quiz_unlocked: bool
    completed: bool


class StudySetDetail(BaseModel):
    # GET /api/study-sets/{id}: status while processing, overview + chapter list when ready

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
    # one chapter's points, returned after each answer so the quiz can update its bar

    earned: int
    max: int
    unlock_threshold: int


class QuizQuestion(ORMModel):
    # an unanswered question as the player sees it: never the answer or the explanation

    id: int
    prompt: str
    options: list[str]


class QuizTopic(BaseModel):
    # one scoring slot of the quiz with its current question (None when mastered or preparing)

    id: int
    name: str
    points: int
    mastered: bool
    preparing: bool  # a replacement question is being generated
    question: QuizQuestion | None


class QuizState(BaseModel):
    # GET /api/chapters/{id}/quiz: the chapter's points and every topic's state

    chapter_id: int
    earned: int
    max: int
    unlock_threshold: int
    progress: Progress
    topics: list[QuizTopic]


class AnswerIn(BaseModel):
    # body of POST /api/questions/{id}/answer. ge/le: FastAPI rejects anything outside 0-3 (422)

    selected_index: int = Field(ge=0, le=3)


class ChapterLinkOut(BaseModel):
    # just enough to link to a chapter (previous/next chapter, newly unlocked chapter)

    id: int
    title: str


class AnswerOut(BaseModel):
    # the result of answering: now the correct answer and explanation may be shown

    correct: bool
    correct_index: int
    explanation: str
    points_awarded: int
    chapter: ChapterPoints
    progress: Progress
    unlocked_chapter: ChapterLinkOut | None  #only on the answer that crosses the threshold
    replacement_pending: bool


class SearchResult(BaseModel):
    # one hit of GET /api/search: which chapter matched, with a highlighted snippet

    study_set_id: int
    study_set_title: str | None
    chapter_id: int
    chapter_position: int
    chapter_title: str
    snippet: str  # matches wrapped in [[ ]]


# --- LLM output contracts (see prompts.py) ----------------------------------------------------
# field(...) rules like min_length/ge also end up in the JSON Schema sent to the LLM server, which then forces the model to respect them (e.g. exactly 4 options)

class ChapterSpan(BaseModel):
    # one chapter as a range of numbered text blocks (inclusive): blocks start_block..end_block

    title: str = Field(min_length=1)
    start_block: int = Field(ge=0)
    end_block: int = Field(ge=0)


class StructureOut(BaseModel):
    # the structuring step: title and overview of the whole set, and where each chapter starts and ends

    title: str = Field(min_length=1)
    overview: str
    chapters: list[ChapterSpan] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def chapters_cover_all_blocks(self, info: ValidationInfo):
        #chapters must be in order, contiguous, non-overlapping and cover every block
        #the number of blocks is passed in as validation context: {"n_blocks": N}
        
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
    # reject option lists with duplicates (compared ignoring case and surrounding spaces)
    if len({o.strip().casefold() for o in options}) != 4:
        raise ValueError("the 4 options must all be different")
    return options


#reusable field type: "a list of exactly 4 strings, all different"
FourOptions = Annotated[list[str], Field(min_length=4, max_length=4), AfterValidator(_four_distinct_options)]


class QuestionOut(BaseModel):
    #finished multiple-choice question as it is stored (see models.Question)

    question: str = Field(min_length=1)
    options: FourOptions
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1)


class QuizItem(QuestionOut):
    # question plus the short name of the topic it covers (becomes a models.Topic)

    topic: str = Field(min_length=1)


class KeyConcept(BaseModel):
    # one entry of the "Key concepts" tab

    term: str
    explanation: str


class QAPair(BaseModel):
    # one flashcard of the "Q&A practice" tab

    question: str
    answer: str


class OutlineSection(BaseModel):
    # one heading of the outline in the "Study aids" tab, with its bullet points

    heading: str
    points: list[str]


class StudyAids(BaseModel):
    # everything in the "Study aids" tab

    outline: list[OutlineSection]
    review_checklist: list[str]
    memory_tips: list[str]


class ChapterOut(BaseModel):
    # all study materials of one chapter, as stored (the mock produces this shape directly)

    summary: list[str] = Field(min_length=1)
    key_concepts: list[KeyConcept] = Field(min_length=1)
    qa_pairs: list[QAPair] = Field(min_length=1)
    study_aids: StudyAids
    #each quiz item becomes a scoring slot (topic), so the count and distinct topics matter
    quiz: list[QuizItem] = Field(min_length=config.QUESTIONS_PER_CHAPTER, max_length=config.QUESTIONS_PER_CHAPTER)

    @field_validator("quiz")
    @classmethod
    def one_item_per_topic(cls, quiz: list[QuizItem]) -> list[QuizItem]:
        # every quiz item must be about a different topic (topic names compared ignoring case)
        if len({item.topic.strip().casefold() for item in quiz}) != len(quiz):
            raise ValueError("every quiz item must cover a different topic")
        return quiz


# --- Chapter page (reuses the content models above) -------------------------------------------

class ChapterDetail(BaseModel):
    # GET /api/chapters/{id}: the chapter page (materials, points, lock state, prev/next links)

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
    points_to_unlock: int  #more points needed in the previous chapter, 0 when unlocked
    summary: list[str]
    key_concepts: list[KeyConcept]
    qa_pairs: list[QAPair]
    study_aids: StudyAids
    prev_chapter: ChapterLinkOut | None
    next_chapter: ChapterLinkOut | None


# --- What the LLM actually writes ----------------------------------------------------------------
'''
small models often point correct_index at the wrong option, 
so the LLM writes the correct answer and the wrong answers separately, 
and the code builds options + correct_index from them (the worker shuffles the options afterwards)
'''

class QuestionDraft(BaseModel):
    """
    a question as the LLM writes it: the correct answer and 3 wrong ones as separate fields
    the field order matters a little: the model writes the fields in this order, 
    so it states the correct answer and why it is right before inventing the wrong answers
    """

    question: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    wrong_answers: list[str] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def answers_all_different(self):
        #The correct answer and the 3 wrong ones must be 4 different texts
        _four_distinct_options([self.correct_answer, *self.wrong_answers])
        return self

    @field_validator("question")
    @classmethod
    def is_a_question(cls, question: str) -> str:
        # small models sometimes write a topic label ("Vector length") instead of a question
        # "?" or the Greek question mark (";" or U+037E)
        if not question.strip().endswith(("?", ";", ";")):
            raise ValueError("must be a complete question ending with a question mark")
        return question

    def to_question(self) -> QuestionOut:
        #convert to the stored format: correct answer first (index 0), the worker shuffles later 
        return QuestionOut(
            question=self.question,
            options=[self.correct_answer, *self.wrong_answers],
            correct_index=0,
            explanation=self.explanation,
        )


class QuizItemDraft(QuestionDraft):
    # draft question plus its topic name

    topic: str = Field(min_length=1)


class ChapterDraft(ChapterOut):
    # chapter's materials as the LLM writes them: like ChapterOut, but with draft quiz questions

    quiz: list[QuizItemDraft] = Field(
        min_length=config.QUESTIONS_PER_CHAPTER, max_length=config.QUESTIONS_PER_CHAPTER
    )

    def to_chapter(self) -> ChapterOut:
        #convert to the stored format (only the quiz items change)
        quiz = [QuizItem(topic=item.topic, **item.to_question().model_dump()) for item in self.quiz]
        return ChapterOut(**self.model_dump(exclude={"quiz"}), quiz=quiz)
