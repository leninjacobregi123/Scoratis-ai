"""
SQLAlchemy Models for Scoratis
"""

from .base import Base
from .user import User
from .conversation import Conversation
from .chat_message import ChatMessage
from .learning_state import LearningState
from .llm_provider import LLMProviderConfig, ProviderType, PROVIDER_INFO
from .document import Document, SourceType, DocumentStatus
from .chunk import Chunk
from .video_job import VideoJob, VideoJobStatus
from .lesson import Lesson, LessonStatus
from .notebook import Notebook, MAX_NOTEBOOK_DEPTH
from .concept import (
    Concept, ConceptEdge, SceneConcept, ConceptMastery,
    EMBEDDING_DIM, CONCEPT_MERGE_THRESHOLD,
)
from .review import ReviewItem, ReviewSchedule, ReviewLog, ReviewKind

__all__ = [
    "Base",
    "User",
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
    "Lesson",
    "LessonStatus",
    "Notebook",
    "MAX_NOTEBOOK_DEPTH",
    "Concept",
    "ConceptEdge",
    "SceneConcept",
    "ConceptMastery",
    "EMBEDDING_DIM",
    "CONCEPT_MERGE_THRESHOLD",
    "ReviewItem",
    "ReviewSchedule",
    "ReviewLog",
    "ReviewKind",
]
