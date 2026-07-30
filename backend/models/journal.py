"""
Journal Model with pgvector embedding support
"""

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from typing import Optional, List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .folder import Folder


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    folder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    # pgvector embedding for semantic search (384 dimensions for all-MiniLM-L6-v2)
    embedding = mapped_column(Vector(384), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="journals")
    folder: Mapped[Optional["Folder"]] = relationship("Folder", back_populates="journals")

    __table_args__ = (
        Index(
            "ix_journals_embedding",
            embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Journal(id={self.id}, title={self.title[:30]}...)>"
