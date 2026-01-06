"""
Document Model for RAG System
Stores uploaded documents and migrated content (journals, conversations)
"""

from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import enum

from .base import Base


class SourceType(enum.Enum):
    """Source type for documents"""
    JOURNAL = "journal"
    CHAT = "chat"
    UPLOAD = "upload"


class DocumentStatus(enum.Enum):
    """Processing status for documents"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """
    Document model for the professional RAG system.

    Stores full documents with:
    - Original content (full text)
    - Summary for document-level search
    - Summary embedding for semantic search
    - Metadata including source type, file info
    - Processing status
    """
    __tablename__ = "documents"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to user
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Document metadata
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # Full original content

    # Source tracking
    source_type = Column(
        SQLEnum(SourceType),
        nullable=False,
        default=SourceType.UPLOAD
    )
    source_id = Column(Integer, nullable=True)  # Original journal/chat ID for migrations

    # File information (for uploads)
    file_path = Column(String(1000), nullable=True)
    file_type = Column(String(50), nullable=True)  # pdf, docx, txt, html
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Document metadata as JSONB
    document_metadata = Column(
        JSONB,
        nullable=True,
        default=dict
    )  # {author, page_count, word_count, language, tags, etc.}

    # Summary for document-level search
    summary = Column(Text, nullable=True)

    # Summary embedding for document-level semantic search (384-dim for all-MiniLM-L6-v2)
    embedding = Column(Vector(384), nullable=True)

    # Processing status
    status = Column(
        SQLEnum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.PENDING
    )
    error_message = Column(Text, nullable=True)  # Store error details if processing fails

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Subject for topic isolation (physics, chemistry, biology, etc.)
    subject = Column(String(100), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Indexes for efficient querying
    __table_args__ = (
        # HNSW index for vector similarity search on summary embedding
        Index(
            "idx_documents_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # Composite index for user filtering
        Index("idx_documents_user_status", user_id, status),
        # Composite index for subject-scoped RAG queries
        Index("idx_documents_user_subject_status", user_id, "subject", status),
        # Index for source tracking
        Index("idx_documents_source", source_type, source_id),
        # Full-text search index
        Index(
            "idx_documents_content_fts",
            "content",
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title[:30]}...', status={self.status.value})>"

    def to_dict(self, chunk_count: int = None) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content_preview": self.content[:500] if self.content else None,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "metadata": self.document_metadata,
            "summary": self.summary,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "subject": self.subject,
            "chunk_count": chunk_count,  # Pass explicitly to avoid lazy loading
        }

    @property
    def word_count(self) -> int:
        """Calculate word count from content"""
        if not self.content:
            return 0
        return len(self.content.split())

    @property
    def is_processed(self) -> bool:
        """Check if document has been fully processed"""
        return self.status == DocumentStatus.COMPLETED
