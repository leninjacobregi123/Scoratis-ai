"""
Lesson Model
A generated interactive lesson: an ordered set of scenes, each holding either
slide JSON (the @maic/dsl contract the frontend renderer consumes) or a
reference to a Manim render from the existing video pipeline.

Follows VideoJob's split-status pattern (see models/video_job.py): a coarse
enum for control flow, plus stage/progress/message for UI feedback, because
generation is a multi-minute Celery job the frontend polls.

Scenes live in a single JSONB column rather than their own table: they are
always read as a whole lesson, never queried individually, and the shape is a
contract owned by the renderer - not something to normalise into columns that
would have to change every time the DSL does.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import enum

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

if TYPE_CHECKING:
    from .user import User


class LessonStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Lesson(Base):
    """One generated lesson."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # What the learner asked for, verbatim - kept for regeneration/debugging.
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    # LLM-authored, from the outline stage.
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Two separate gotchas here, both the same as VideoJobStatus:
    #  - `name`: without it SQLAlchemy derives the type name from the class
    #    ("lessonstatus"), which does NOT match the "lesson_status" type the
    #    migration creates -> DatatypeMismatchError on every insert.
    #  - `values_callable`: the Enum type stores the member NAME ("PENDING")
    #    by default, not the lowercase .value the migration's labels use.
    status: Mapped[LessonStatus] = mapped_column(
        SQLEnum(LessonStatus, name="lesson_status", create_type=False,
                values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=LessonStatus.PENDING,
        index=True,
    )
    stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stage-1 output, kept so a failed later stage can be retried without
    # paying for outline generation again.
    outline: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Final payload the player consumes: [{id, type, title, slide, actions}, ...]
    scenes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Conversation this was generated from, when triggered from chat.
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # --- Learner progress (distinct from progress_percent, which tracks
    # GENERATION). Kept on the lesson rather than a separate progress table
    # because a lesson has exactly one owner - there is no cohort/enrolment
    # concept here, so a join table would buy nothing.
    completed_scene_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    last_scene_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="lessons")

    def to_dict(self, include_scenes: bool = True) -> dict:
        """Serialise for the API. `include_scenes=False` keeps list responses
        small - a full lesson's slide JSON is large enough that returning it
        for every row in a listing is wasteful."""
        data = {
            "id": self.id,
            "requirement": self.requirement,
            "title": self.title,
            "summary": self.summary,
            "status": self.status.value if isinstance(self.status, LessonStatus) else self.status,
            "stage": self.stage,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "error_message": self.error_message,
            "scene_count": len(self.scenes or []),
            "completed_scene_ids": self.completed_scene_ids or [],
            "completed_count": len(self.completed_scene_ids or []),
            "last_scene_index": self.last_scene_index or 0,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_scenes:
            data["scenes"] = self.scenes or []
            data["outline"] = self.outline
        return data
