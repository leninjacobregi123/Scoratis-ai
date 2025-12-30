"""
Chunk Model for RAG System
Stores document chunks for granular semantic search
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .base import Base


class Chunk(Base):
    """
    Chunk model for granular document search.

    Each document is split into chunks for:
    - More precise semantic search
    - Better citation granularity
    - Efficient retrieval
    """
    __tablename__ = "chunks"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to document
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Chunk position within document
    chunk_index = Column(Integer, nullable=False)  # Order within document (0-indexed)

    # Chunk content
    content = Column(Text, nullable=False)

    # Chunk metadata as JSONB
    chunk_metadata = Column(
        JSONB,
        nullable=True,
        default=dict
    )  # {start_char, end_char, page_number, section_title, etc.}

    # Chunk embedding for semantic search (384-dim for all-MiniLM-L6-v2)
    embedding = Column(Vector(384), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    # Indexes for efficient querying
    __table_args__ = (
        # HNSW index for vector similarity search
        Index(
            "idx_chunks_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # Composite index for document + chunk order
        Index("idx_chunks_document_order", document_id, chunk_index),
        # Full-text search index using GIN with trgm
        Index(
            "idx_chunks_content_fts",
            "content",
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] if self.content else ""
        return f"<Chunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index}, content='{content_preview}...')>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "chunk_id": f"chunk_{self.id}",  # For citation references
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "metadata": self.chunk_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_citation_dict(self) -> dict:
        """Convert to citation format for LLM context"""
        return {
            "chunk_id": f"chunk_{self.id}",
            "document_id": self.document_id,
            "content": self.content,
            "start_char": self.chunk_metadata.get("start_char") if self.chunk_metadata else None,
            "end_char": self.chunk_metadata.get("end_char") if self.chunk_metadata else None,
            "page": self.chunk_metadata.get("page_number") if self.chunk_metadata else None,
        }

    @property
    def content_length(self) -> int:
        """Get content length in characters"""
        return len(self.content) if self.content else 0

    @property
    def citation_id(self) -> str:
        """Generate citation ID for this chunk"""
        return f"chunk_{self.id}"
