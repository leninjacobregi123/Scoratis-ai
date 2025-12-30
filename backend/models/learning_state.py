"""
LearningState Model - Persists conversation analyzer state
"""

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .user import User


class LearningState(Base):
    """
    Persists the ConversationAnalyzer state to database.
    Previously this was only stored in memory and lost on restart.
    """

    __tablename__ = "learning_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), default=1
    )

    # Core conversation tracking
    topic: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    confusion_count: Mapped[int] = mapped_column(Integer, default=0)
    understanding_signals: Mapped[int] = mapped_column(Integer, default=0)

    # State machine
    last_state: Mapped[str] = mapped_column(String(50), default="initial")

    # JSONB fields for complex data
    topics_discussed: Mapped[Optional[List]] = mapped_column(JSONB, default=list)
    key_discoveries: Mapped[Optional[List]] = mapped_column(JSONB, default=list)

    # Content analysis
    content_richness: Mapped[str] = mapped_column(String(50), default="empty")
    content_score: Mapped[float] = mapped_column(Float, default=0.0)
    extracted_concepts: Mapped[Optional[List]] = mapped_column(JSONB, default=list)

    # Recent context for continuity
    conversation_context: Mapped[Optional[List]] = mapped_column(JSONB, default=list)

    # Timestamps
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="learning_states")

    def to_dict(self) -> dict:
        """Convert to dictionary for ConversationAnalyzer compatibility"""
        return {
            "topic": self.topic,
            "turn_count": self.turn_count,
            "confusion_count": self.confusion_count,
            "understanding_signals": self.understanding_signals,
            "last_state": self.last_state,
            "topics_discussed": self.topics_discussed or [],
            "key_discoveries": self.key_discoveries or [],
            "content_richness": self.content_richness,
            "content_score": self.content_score,
            "extracted_concepts": self.extracted_concepts or [],
            "conversation_context": self.conversation_context or [],
        }

    @classmethod
    def from_dict(cls, session_id: str, data: dict, user_id: int = 1) -> "LearningState":
        """Create from ConversationAnalyzer state dictionary"""
        return cls(
            session_id=session_id,
            user_id=user_id,
            topic=data.get("topic"),
            turn_count=data.get("turn_count", 0),
            confusion_count=data.get("confusion_count", 0),
            understanding_signals=data.get("understanding_signals", 0),
            last_state=data.get("last_state", "initial"),
            topics_discussed=data.get("topics_discussed", []),
            key_discoveries=data.get("key_discoveries", []),
            content_richness=data.get("content_richness", "empty"),
            content_score=data.get("content_score", 0.0),
            extracted_concepts=data.get("extracted_concepts", []),
            conversation_context=data.get("conversation_context", []),
        )

    def __repr__(self) -> str:
        return f"<LearningState(session_id={self.session_id}, topic={self.topic})>"
