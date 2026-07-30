"""
User Model
"""

from sqlalchemy import Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .folder import Folder
    from .journal import Journal
    from .conversation import Conversation
    from .learning_state import LearningState
    from .llm_provider import LLMProviderConfig
    from .document import Document


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    folders: Mapped[List["Folder"]] = relationship(
        "Folder", back_populates="user", cascade="all, delete-orphan"
    )
    journals: Mapped[List["Journal"]] = relationship(
        "Journal", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    learning_states: Mapped[List["LearningState"]] = relationship(
        "LearningState", back_populates="user", cascade="all, delete-orphan"
    )
    llm_providers: Mapped[List["LLMProviderConfig"]] = relationship(
        "LLMProviderConfig", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
