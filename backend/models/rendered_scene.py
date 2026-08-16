"""
Rendered Scene cache.

A Manim render is the most expensive thing this pipeline does - roughly a
minute of CPU plus several model calls to write the scene code, and it is
paid again every single time a lesson happens to cover the same ground.
Six photosynthesis lessons meant six separate renders of the Calvin cycle.

This table lets a finished animation be found again by what it teaches, so
the second lesson to need it plays the first one's file.

Reuse is keyed on the scene's title embedding rather than on a concept id,
because concepts are extracted AFTER a lesson is built (see
tasks/review_tasks.py) and the reuse decision has to be made during
generation, before any of that exists.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, DateTime, ForeignKey, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base
from .concept import EMBEDDING_DIM

if TYPE_CHECKING:
    from .user import User


# Cosine similarity above which two scene titles are treated as teaching the
# same thing. Measured on this project's own rendered topics: titles for the
# same idea score 0.63-0.96, titles for different ideas 0.22-0.50.
#
# 0.80 sits well clear of the highest false pair (0.50) rather than splitting
# the gap, because the two errors are not symmetric. A miss costs one
# re-render, which is exactly the status quo. A false hit drops a Calvin
# cycle animation into a binary search lesson, which is worse than anything
# the cache saves.
SCENE_REUSE_THRESHOLD = 0.80

# Words that appear in scene titles regardless of subject. Two titles that
# only share these have nothing in common, however the embedding scores them.
GENERIC_TITLE_WORDS = {
    "animation", "animated", "visual", "visualisation", "visualization",
    "walkthrough", "step", "steps", "process", "explained", "explanation",
    "how", "what", "why", "works", "working", "introduction", "intro",
    "overview", "guide", "demo", "scene", "the", "and", "for", "with",
    "into", "through", "using", "diagram", "illustration",
}


class RenderedScene(Base):
    """One finished animation, findable by what it teaches."""

    __tablename__ = "rendered_scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    video_path: Mapped[str] = mapped_column(String(500), nullable=False)
    poster_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Where it came from. SET NULL so deleting that lesson does not throw
    # away a perfectly good render every later lesson could still use.
    source_lesson_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )

    use_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="rendered_scenes")

    __table_args__ = (
        Index("ix_rendered_scenes_user_slug", "user_id", "slug"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "video_path": self.video_path,
            "poster_path": self.poster_path,
            "use_count": self.use_count,
        }

    def __repr__(self) -> str:
        return f"<RenderedScene(id={self.id}, title={self.title!r}, uses={self.use_count})>"


def meaningful_tokens(title: str) -> set:
    """Content words from a scene title, generic scene vocabulary removed."""
    import re
    return {
        t for t in re.split(r"[^a-z0-9]+", (title or "").lower())
        if t and len(t) > 2 and t not in GENERIC_TITLE_WORDS
    }
