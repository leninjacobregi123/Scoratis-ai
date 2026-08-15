"""
Notebook Model

A student's container for study: it owns conversations and the lessons
generated from them, so work done weeks apart on the same subject stays
together instead of scattering across one flat per-user list.

Notebooks nest via a self-referential parent_id. That is the whole of the
hierarchy - no closure table, no materialised path - because the tree is
small (a student's own folders), read whole, and rendered as a sidebar.
Two things the nesting costs, both enforced in the API layer rather than
here: a move must not make a notebook its own descendant, and depth is
capped so the UI cannot be walked off the side of the screen.

Deletion is deliberately NOT wired as a cascade from here. A notebook can
hold hours of generated courses, and "delete folder" quietly destroying
them is the kind of thing a student does once and never forgives, so the
route archives instead - see api/routes/notebooks.py.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .conversation import Conversation
    from .lesson import Lesson


# Deep enough for Subject > Course > Module > Topic, shallow enough that
# breadcrumbs still fit. Enforced on create and on move.
MAX_NOTEBOOK_DEPTH = 5


class Notebook(Base):
    """One study notebook, optionally nested inside another."""

    __tablename__ = "notebooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL = top level. Deleting a parent nulls its children rather than
    # destroying them, so a mis-click promotes a subtree instead of
    # erasing it; the route handles intentional recursive removal.
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Drives "resume where you left off" on sign-in. Kept here rather than
    # as users.last_notebook_id so it survives the notebook being removed
    # without leaving a dangling pointer on the user row.
    last_opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # Soft delete: hidden from the tree, contents still intact.
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="notebooks")
    children: Mapped[List["Notebook"]] = relationship(
        "Notebook",
        back_populates="parent",
        remote_side=None,
        foreign_keys=[parent_id],
    )
    parent: Mapped[Optional["Notebook"]] = relationship(
        "Notebook",
        back_populates="children",
        remote_side=[id],
        foreign_keys=[parent_id],
    )

    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="notebook"
    )
    lessons: Mapped[List["Lesson"]] = relationship("Lesson", back_populates="notebook")

    __table_args__ = (
        # The tree is always fetched per user, filtered to the live rows.
        Index("ix_notebooks_user_archived", "user_id", "archived_at"),
    )

    def to_dict(self, counts: Optional[dict] = None) -> dict:
        data = {
            "id": self.id,
            "parent_id": self.parent_id,
            "name": self.name,
            "description": self.description,
            "archived": self.archived_at is not None,
            "last_opened_at": self.last_opened_at.isoformat() if self.last_opened_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if counts is not None:
            data["counts"] = counts
        return data

    def __repr__(self) -> str:
        return f"<Notebook(id={self.id}, name={self.name!r}, parent_id={self.parent_id})>"
