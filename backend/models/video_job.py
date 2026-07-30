"""
VideoJob Model
Tracks Manim video-generation jobs run by the Celery worker (tasks/video_tasks.py).

Replaces the old in-memory `VideoGenerationService.tasks` dict in video_service.py,
which lost all state on process restart and couldn't be shared across multiple
API/worker instances - a real problem once this runs on more than one dyno.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import enum

from sqlalchemy import Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

if TYPE_CHECKING:
    from .user import User


class VideoJobStatus(str, enum.Enum):
    """Coarse status for control flow (mirrors the DocumentStatus pattern)."""
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoJob(Base):
    """
    A single video-generation job.

    Status is split into two things on purpose:
    - `status`: coarse enum for control flow / filtering (pending/rendering/completed/failed)
    - `stage` + `progress_percent` + `message`: free-text fields for fine-grained UI
      feedback (matches the stage vocabulary the frontend already polls for:
      content -> narration -> animation -> merge -> completed)
    """
    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # What to generate
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    quality: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    auto_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Conversation context used for LLM script/code generation (key_concepts,
    # visualization_type, conversation_summary, etc. - see video_service.py's
    # EnhancedVideoGenerator for the shape of this dict)
    context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Progress tracking
    status: Mapped[VideoJobStatus] = mapped_column(
        # values_callable: SQLAlchemy's Enum type stores the Python enum
        # MEMBER NAME by default (e.g. "PENDING"), not its .value - without
        # this, it mismatches the lowercase labels the migration actually
        # creates in Postgres ('pending', 'rendering', ...) and every write
        # fails with InvalidTextRepresentationError.
        SQLEnum(VideoJobStatus, name="video_job_status", create_type=True,
                values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=VideoJobStatus.PENDING,
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="content")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Output
    video_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    script: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # scene breakdown, for debugging/export

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<VideoJob(id={self.id}, topic='{self.topic[:30]}', status={self.status.value})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status.value,
            "stage": self.stage,
            "progress": self.progress_percent,
            "message": self.message,
            "error": self.error_message,
            "video_path": self.video_path,
            "duration_seconds": self.duration_seconds,
            "quality": self.quality,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
