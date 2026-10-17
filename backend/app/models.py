"""All database tables. Created with Base.metadata.create_all() when the API starts."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app import config


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    auth_id: Mapped[str] = mapped_column(Text, unique=True)  # the JWT "sub" claim
    email: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudySet(Base):
    __tablename__ = "study_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # None until the user types one or the LLM generates one; a typed title always wins.
    title: Mapped[str | None] = mapped_column(Text)
    # queued | extracting | transcribing | structuring | generating | ready | failed
    status: Mapped[str] = mapped_column(String(20), default="queued")
    status_message: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text)  # user-readable
    source_text: Mapped[str] = mapped_column(Text, default="")
    overview: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source_files: Mapped[list["SourceFile"]] = relationship(
        back_populates="study_set", order_by="SourceFile.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="study_set", order_by="Chapter.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_set_id: Mapped[int] = mapped_column(ForeignKey("study_sets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(10))  # text | audio
    content_type: Mapped[str] = mapped_column(Text, default="")
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    study_set: Mapped[StudySet] = relationship(back_populates="source_files")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("study_set_id", "position"),
        # 'simple' config: no language-specific stemming, so Greek and English both work.
        Index("ix_chapters_search", text("to_tsvector('simple', search_text)"), postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_set_id: Mapped[int] = mapped_column(ForeignKey("study_sets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # 1..N
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)  # this chapter's part of the source text
    summary: Mapped[list] = mapped_column(JSONB, default=list)  # list of paragraphs
    key_concepts: Mapped[list] = mapped_column(JSONB, default=list)
    qa_pairs: Mapped[list] = mapped_column(JSONB, default=list)
    study_aids: Mapped[dict] = mapped_column(JSONB, default=dict)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    study_set: Mapped[StudySet] = relationship(back_populates="chapters")
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="chapter", order_by="Topic.position",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class Topic(Base):
    """One scoring slot in a chapter's quiz. Its points are earned once, when mastered."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, default=config.POINTS_PER_QUESTION)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="topics")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="topic", order_by="Question.id",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        # A topic has at most one question waiting to be answered.
        Index(
            "uq_questions_one_active_per_topic", "topic_id",
            unique=True, postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSONB)  # exactly 4 strings
    correct_index: Mapped[int] = mapped_column(Integer)  # 0-3
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | correct | wrong
    selected_index: Mapped[int | None] = mapped_column(Integer)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topic: Mapped[Topic] = relationship(back_populates="questions")
