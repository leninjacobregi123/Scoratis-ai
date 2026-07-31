"""
Conversation Model
"""

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .chat_message import ChatMessage


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Set when the user shares this conversation - grants unauthenticated
    # read-only access via GET /shared/{token} (see api/routes/transcripts.py)
    share_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)

    # Learning intent for this session: 'exam_prep' (fast, direct answers) or
    # 'deep_learning' (full Socratic method). NULL = not yet chosen by the
    # user - resolved to 'deep_learning' at the application layer (see
    # chat_stream in main.py), not defaulted here, so this column has zero
    # effect on any conversation created before it existed.
    learning_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Optional freeform context typed by the user in exam_prep mode, e.g.
    # "Physics midterm Friday" - used to keep the tutor's pacing/priorities
    # aligned with what they're actually studying for.
    mode_context: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, session_id={self.session_id})>"
