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
    from .notebook import Notebook


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    # Which notebook this chat belongs to. Nullable so an archived or
    # removed notebook leaves the conversation intact and unfiled rather
    # than taking the student's history down with it.
    notebook_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True, index=True
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

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    notebook: Mapped[Optional["Notebook"]] = relationship(
        "Notebook", back_populates="conversations"
    )
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, session_id={self.session_id})>"
