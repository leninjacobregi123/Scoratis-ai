"""
User Model
"""

from sqlalchemy import Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .conversation import Conversation
    from .learning_state import LearningState
    from .llm_provider import LLMProviderConfig
    from .document import Document
    from .lesson import Lesson
    from .notebook import Notebook
    from .concept import Concept, ConceptMastery
    from .review import ReviewItem
    from .rendered_scene import RenderedScene


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
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson", back_populates="user", cascade="all, delete-orphan"
    )
    notebooks: Mapped[List["Notebook"]] = relationship(
        "Notebook", back_populates="user", cascade="all, delete-orphan"
    )
    concepts: Mapped[List["Concept"]] = relationship(
        "Concept", back_populates="user", cascade="all, delete-orphan"
    )
    concept_mastery: Mapped[List["ConceptMastery"]] = relationship(
        "ConceptMastery", back_populates="user", cascade="all, delete-orphan"
    )
    review_items: Mapped[List["ReviewItem"]] = relationship(
        "ReviewItem", back_populates="user", cascade="all, delete-orphan"
    )
    rendered_scenes: Mapped[List["RenderedScene"]] = relationship(
        "RenderedScene", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
