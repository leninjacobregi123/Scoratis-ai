"""
ReviewItem Model
Spaced-repetition queue using the SM-2 algorithm (SuperMemo 2). Seeded from
LearningState.key_discoveries (concepts the tutor confirmed the user
understood) and missed QuizQuestions.
"""

import enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .user import User


class ReviewSourceType(str, enum.Enum):
    KEY_DISCOVERY = "key_discovery"
    QUIZ_QUESTION = "quiz_question"


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String(1000), nullable=False)

    source_type: Mapped[ReviewSourceType] = mapped_column(
        # See VideoJob.status for why values_callable is required: without it
        # SQLAlchemy writes the enum MEMBER NAME ("QUIZ_QUESTION") instead of
        # its .value ("quiz_question"), which the Postgres enum type (created
        # with lowercase labels by the migration) rejects outright.
        SQLEnum(ReviewSourceType, name="review_source_type", create_type=True,
                values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # SM-2 state
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_reviewed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "concept": self.concept,
            "source_type": self.source_type.value,
            "ease_factor": round(self.ease_factor, 2),
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "last_reviewed_at": self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
        }
