"""
Review Models

Everything Scoratis generates today is passive: the student watches slides,
watches an animation, and asks questions. Nothing asks them anything back.
These tables are the active half - questions built from the lesson's own
content, scheduled so they come back just before they would be forgotten.

  ReviewItem      one question, its answer, and how to mark it
  ReviewSchedule  when that item is next due, and the FSRS state behind it
  ReviewLog       every attempt, kept forever

The schedule is split from the item because they change on completely
different clocks: an item is written once and rarely edited, while its
schedule is rewritten on every single answer. The log is separate again
because it is append-only and will outgrow both.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
import enum

from sqlalchemy import (
    Integer, String, Text, DateTime, ForeignKey, Float, Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .lesson import Lesson
    from .concept import Concept
    from .notebook import Notebook


class ReviewKind(str, enum.Enum):
    RECALL = "recall"   # free text, graded against a rubric
    MCQ = "mcq"         # options stored on the item, graded exactly
    PROBLEM = "problem" # worked answer, graded against a rubric


class ReviewItem(Base):
    """One question generated from a scene the student has actually seen."""

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Where the question came from. All nullable so an item outlives the
    # lesson that produced it - deleting a course should not silently wipe
    # weeks of a student's review history along with it.
    lesson_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    concept_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notebook_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True, index=True
    )

    kind: Mapped[ReviewKind] = mapped_column(
        SQLEnum(
            ReviewKind,
            name="review_kind",
            create_type=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
        default=ReviewKind.RECALL,
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    # MCQ options, and for graded kinds the marking guidance: which points
    # must appear for a response to count as correct.
    rubric: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Retired rather than deleted, so its history in review_log stays
    # interpretable.
    retired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="review_items")
    schedule: Mapped[Optional["ReviewSchedule"]] = relationship(
        "ReviewSchedule", back_populates="item", uselist=False,
        cascade="all, delete-orphan",
    )
    logs: Mapped[List["ReviewLog"]] = relationship(
        "ReviewLog", back_populates="item", cascade="all, delete-orphan"
    )

    def to_dict(self, include_answer: bool = False) -> dict:
        data = {
            "id": self.id,
            "kind": self.kind.value if isinstance(self.kind, ReviewKind) else self.kind,
            "prompt": self.prompt,
            "concept_id": self.concept_id,
            "lesson_id": self.lesson_id,
            "scene_id": self.scene_id,
        }
        # MCQ needs its options to be answerable at all; the rest of the
        # rubric is marking guidance and stays server-side.
        if self.rubric and "options" in self.rubric:
            data["options"] = self.rubric["options"]
        if include_answer:
            data["answer"] = self.answer
            data["rubric"] = self.rubric
        return data


class ReviewSchedule(Base):
    """FSRS state for one item: when it is next due, and why.

    `stability` is roughly how many days the memory would survive before
    recall drops to ~90%; `difficulty` is how resistant this particular item
    is to gaining stability. Both are FSRS's, stored raw so the scheduler
    stays a pure function over them.
    """

    __tablename__ = "review_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("review_items.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    stability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    item: Mapped["ReviewItem"] = relationship("ReviewItem", back_populates="schedule")

    __table_args__ = (
        # The due-queue query: this user's items, soonest first.
        Index("ix_review_schedules_user_due", "user_id", "due_at"),
    )

    def to_dict(self) -> dict:
        return {
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "stability": round(self.stability, 3),
            "difficulty": round(self.difficulty, 3),
            "reps": self.reps,
            "lapses": self.lapses,
        }


class ReviewLog(Base):
    """Every attempt, kept forever.

    Append-only. This is the raw material for retuning the scheduler, for
    judging whether the grading prompt is fair, and for showing a student
    what they actually said last time - none of which survives if only the
    latest state is kept.
    """

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("review_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    grade: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..4
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Interval actually served, in days - what the scheduler predicted would
    # survive. Needed to evaluate the scheduler against reality later.
    scheduled_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elapsed_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    item: Mapped["ReviewItem"] = relationship("ReviewItem", back_populates="logs")
