"""
All database tables, as SQLAlchemy ORM classes. Created with Base.metadata.create_all() when the API starts

How the tables relate (each arrow is "has many"; deleting a parent deletes its children):

    User ─> StudySet ─> SourceFile (the uploaded files)
                      ─> Chapter ──> Topic ──> Question

- **StudySet** is one upload (one or more files, or pasted text) and its processing status
- **Chapter** holds the study materials the AI wrote for one part of the material
- **Topic** is one scoring slot of a chapter's quiz (5 per chapter, see config.QUESTIONS_PER_CHAPTER)
- **Question** is one multiple-choice question for a topic, after a wrong answer a new question is
  added to the same topic, so a topic collects its question history; at most one is "active"

`Mapped[int]` is the Python type of a column, `mapped_column(...)` describes the database
column, and `relationship(...)` gives easy access to related rows (e.g. `study_set.chapters`)
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app import config

class Base(DeclarativeBase):
    # parent class of all tables; `Base.metadata` knows every table (used by create_all)
    pass


class User(Base):
    # person using AgoraNote, created automatically on their first request (see auth.py)

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    auth_id: Mapped[str] = mapped_column(Text, unique=True)  # the JWT "sub" claim
    email: Mapped[str | None] = mapped_column(Text)
    # server_default=func.now(): the database fills in the current time when the row is inserted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudySet(Base):
    # one upload and everything generated from it. `status` follows the processing pipeline

    __tablename__ = "study_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ondelete="CASCADE": when a user row is deleted, the database deletes their study sets too
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # none until the user types one or the LLM generates one; a typed title always wins
    title: Mapped[str | None] = mapped_column(Text)
    # queued | extracting | transcribing | structuring | generating | ready | failed
    status: Mapped[str] = mapped_column(String(20), default="queued")
    status_message: Mapped[str] = mapped_column(Text, default="")  # e.g. "Generating chapter 2 of 5"
    error: Mapped[str | None] = mapped_column(Text)  # user-readable
    source_text: Mapped[str] = mapped_column(Text, default="")  # all files' text joined together
    overview: Mapped[str] = mapped_column(Text, default="")  # short summary of the whole material
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # cascade + passive_deletes: deleting a study set also deletes its files' rows and chapters
    # the actual deleting is left to the database's ON DELETE CASCADE (faster than loading every child)
    source_files: Mapped[list["SourceFile"]] = relationship(
        back_populates="study_set", order_by="SourceFile.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="study_set", order_by="Chapter.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class SourceFile(Base):
    # one uploaded file (pasted text is stored as a .txt file too)

    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_set_id: Mapped[int] = mapped_column(ForeignKey("study_sets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # upload order, 1..N; texts are joined in this order
    original_filename: Mapped[str] = mapped_column(Text)  # as the user named it, for display
    kind: Mapped[str] = mapped_column(String(10))  # text | audio
    content_type: Mapped[str] = mapped_column(Text, default="")
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(Text)  # where the bytes are, see storage.py
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    study_set: Mapped[StudySet] = relationship(back_populates="source_files")


class Chapter(Base):
    #One chapter of a study set with the AI-written study materials (JSONB = JSON stored in Postgres) 

    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("study_set_id", "position"),  # no two "chapter 3"s in one set full-text search index
        # 'simple' config: no language-specific stemming, so Greek and english both work
        # GIN index lets Postgres find matching chapters without reading them all
        Index("ix_chapters_search", text("to_tsvector('simple', search_text)"), postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_set_id: Mapped[int] = mapped_column(ForeignKey("study_sets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # 1..N
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)  # this chapter's part of the source text
    summary: Mapped[list] = mapped_column(JSONB, default=list)  # list of paragraphs
    key_concepts: Mapped[list] = mapped_column(JSONB, default=list)  # [{"term", "explanation"}]
    qa_pairs: Mapped[list] = mapped_column(JSONB, default=list)  # [{"question", "answer"}] (flashcards)
    study_aids: Mapped[dict] = mapped_column(JSONB, default=dict)  # outline, review_checklist, memory_tips
    # title + summary + concepts + Q&A + content in one string, used only for search (see worker.py)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    study_set: Mapped[StudySet] = relationship(back_populates="chapters")
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="chapter", order_by="Topic.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class Topic(Base):
    #One scoring slot in a chapter's quiz. Its points are earned once, when mastered

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(Text)  # short topic name written by the LLM
    points: Mapped[int] = mapped_column(Integer, default=config.POINTS_PER_QUESTION)
    # set when the topic's question is answered correctly; from then on it can't earn points again
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="topics")
    # oldest first: the last one is the most recent question on this topic
    questions: Mapped[list["Question"]] = relationship(
        back_populates="topic", order_by="Question.id",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class Question(Base):
    # one multiple-choice question, `correct_index` and `explanation` are never sent before answering

    __tablename__ = "questions"
    __table_args__ = (
        # a topic has at most one question waiting to be answered,
        # *partial* unique index: the uniqueness only applies to rows where status = 'active', so old answered questions don't count
        Index(
            "uq_questions_one_active_per_topic", "topic_id",
            unique=True, postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)  # the question text
    options: Mapped[list] = mapped_column(JSONB)  # exactly 4 strings
    correct_index: Mapped[int] = mapped_column(Integer)  # 0-3
    explanation: Mapped[str] = mapped_column(Text)  # why the correct answer is right
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | correct | wrong
    selected_index: Mapped[int | None] = mapped_column(Integer)  # what the user picked
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topic: Mapped[Topic] = relationship(back_populates="questions")
