"""
Concept Models

A lesson is currently an opaque blob of scenes: nothing in the database knows
that scene 3 of the photosynthesis lesson and scene 5 of the plant biology
lesson teach the same idea. Until something does, the system cannot tell a
student what they already know, cannot skip it, and cannot bring it back for
review at the right time.

These four tables are that missing layer:

  Concept        one idea, deduplicated across lessons by embedding similarity
  ConceptEdge    "you need A before B" - a DAG, not a tree
  SceneConcept   which scene of which lesson teaches which concept
  ConceptMastery how well one student knows one concept, right now

Concepts are per-user rather than global. A shared concept space would be
better pedagogically - one canonical "integration by parts" for everyone - but
it makes every write a cross-user write, and this codebase has already been
bitten once by a user_id that defaulted to 1. Per-user keeps the isolation
property that every other table here has; merging into a shared space later is
a migration, whereas un-leaking a shared space is an incident.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Integer, String, Text, DateTime, ForeignKey, Float, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .lesson import Lesson


# Same 384-dim space as documents and chunks, so the existing embedding
# service works unchanged and concepts can be compared against document
# content later without a second model.
EMBEDDING_DIM = 384

# Cosine similarity above which two concept names are treated as the same
# concept. Tuned to merge "Photosynthesis" / "the process of photosynthesis"
# while keeping "photosynthesis" and "cellular respiration" apart.
CONCEPT_MERGE_THRESHOLD = 0.86


class Concept(Base):
    """One idea a student can know, or not know."""

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    # Normalised form used for the cheap exact-match pass before falling back
    # to an embedding comparison.
    slug: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="concepts")
    scene_links: Mapped[List["SceneConcept"]] = relationship(
        "SceneConcept", back_populates="concept", cascade="all, delete-orphan"
    )
    mastery: Mapped[List["ConceptMastery"]] = relationship(
        "ConceptMastery", back_populates="concept", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_concepts_user_slug"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<Concept(id={self.id}, name={self.name!r})>"


class ConceptEdge(Base):
    """`prerequisite` should be understood before `dependent`.

    A DAG rather than a tree: "limits" is a prerequisite for both
    "derivatives" and "continuity", and real subjects converge as well as
    branch. Nothing enforces acyclicity in the schema - it is checked when
    edges are written, the same way notebook nesting is.
    """

    __tablename__ = "concept_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prerequisite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("prerequisite_id", "dependent_id", name="uq_concept_edge"),
    )


class SceneConcept(Base):
    """Which scene of which lesson teaches which concept.

    Keyed by the scene's string id rather than a foreign key, because scenes
    live inside the lesson's JSONB rather than in their own table - see
    models/lesson.py for why that shape was chosen.
    """

    __tablename__ = "scene_concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Whether this scene introduces the concept or merely touches it. Review
    # items are generated from primary scenes, so a passing mention does not
    # produce questions the lesson never really taught.
    is_primary: Mapped[bool] = mapped_column(default=True, nullable=False)

    concept: Mapped["Concept"] = relationship("Concept", back_populates="scene_links")
    lesson: Mapped["Lesson"] = relationship("Lesson")

    __table_args__ = (
        UniqueConstraint("lesson_id", "scene_id", "concept_id", name="uq_scene_concept"),
        Index("ix_scene_concepts_lesson_scene", "lesson_id", "scene_id"),
    )


class ConceptMastery(Base):
    """How well one student knows one concept, right now.

    Separate from ReviewSchedule on purpose. A schedule belongs to a single
    review ITEM - one question, with its own difficulty and its own due date.
    Mastery is the roll-up across every item touching a concept, and it is
    what lesson generation reads to decide whether to teach something at all.
    """

    __tablename__ = "concept_mastery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 0.0 (never seen) to 1.0 (solid). A blend of recent grades and how long
    # the knowledge has survived, not a raw success rate - answering an easy
    # item correctly five minutes running is not mastery.
    strength: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapse_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    first_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="concept_mastery")
    concept: Mapped["Concept"] = relationship("Concept", back_populates="mastery")

    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_mastery_user_concept"),
    )

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "strength": round(self.strength, 3),
            "review_count": self.review_count,
            "lapse_count": self.lapse_count,
            "last_reviewed_at": self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
        }
