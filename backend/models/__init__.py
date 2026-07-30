"""
SQLAlchemy Models for Scoratis
"""

from .base import Base
from .user import User
from .folder import Folder
from .journal import Journal
from .conversation import Conversation
from .chat_message import ChatMessage
from .learning_state import LearningState
from .llm_provider import LLMProviderConfig, ProviderType, PROVIDER_INFO
from .document import Document, SourceType, DocumentStatus
from .chunk import Chunk
from .video_job import VideoJob, VideoJobStatus
from .quiz import Quiz, QuizQuestion, QuizAttempt
from .subject_progress import SubjectProgress
from .review_item import ReviewItem, ReviewSourceType

__all__ = [
    "Base",
    "User",
    "Folder",
    "Journal",
    "Conversation",
    "ChatMessage",
    "LearningState",
    "LLMProviderConfig",
    "ProviderType",
    "PROVIDER_INFO",
    # New RAG models
    "Document",
    "SourceType",
    "DocumentStatus",
    "Chunk",
    "VideoJob",
    "VideoJobStatus",
    # Content features
    "Quiz",
    "QuizQuestion",
    "QuizAttempt",
    "SubjectProgress",
    "ReviewItem",
    "ReviewSourceType",
]
