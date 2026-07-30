"""
SubjectProgress Model
One row per (user_id, subject), upserted incrementally as chat turns and
quiz attempts happen - avoids an expensive live group-by over conversations/
messages/learning_states every time the dashboard loads.
"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .user import User


class SubjectProgress(Base):
    __tablename__ = "subject_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "subject", name="uq_subject_progress_user_subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quizzes_taken: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quiz_average: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scaffold_step: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    last_active_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User")

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "mastery_score": round(self.mastery_score, 1),
            "total_turns": self.total_turns,
            "total_sessions": self.total_sessions,
            "quizzes_taken": self.quizzes_taken,
            "quiz_average": round(self.quiz_average, 1),
            "scaffold_step": self.scaffold_step,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
