"""
RAG (Retrieval Augmented Generation) Service
Hybrid semantic + keyword search with RRF fusion across documents and chunks
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import Journal, ChatMessage, Conversation, Document, Chunk, DocumentStatus, SourceType
from services.embedding_service import get_embedding_service
from services.rrf_fusion import (
    reciprocal_rank_fusion,
    boost_chunk_scores,
    RankedItem,
    FusedResult,
    format_context_xml,
    deduplicate_by_content,
)
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """A single RAG search result (legacy format)"""
    content: str
    source_type: str  # 'journal' or 'conversation'
    source_id: int
    title: Optional[str]
    similarity: float
    metadata: Dict[str, Any]


@dataclass
class ChunkResult:
    """Result from chunk-level search"""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    rrf_score: float
    semantic_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": f"chunk_{self.chunk_id}",
            "document_id": self.document_id,
            "document_title": self.document_title,
            "content": self.content,
            "content_preview": self.content[:200] if self.content else "",
            "rrf_score": self.rrf_score,
            "semantic_rank": self.semantic_rank,
            "keyword_rank": self.keyword_rank,
            "page": self.metadata.get("page_number"),
            "source_type": self.metadata.get("source_type"),
        }


@dataclass
class DocumentResult:
    """Result from document-level search"""
    document_id: int
    title: str
    summary: str
    source_type: str
    rrf_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class HybridRAGService:
    """
    Professional RAG service with hybrid search capabilities.

    Features:
    - Hybrid search (semantic + keyword) with RRF fusion
    - Multi-level retrieval (document + chunk)
    - Citation support with chunk IDs
    - Backward compatibility with legacy search
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.rrf_k = settings.RRF_K
        self.chunk_limit = settings.SEARCH_CHUNK_LIMIT
        self.document_limit = settings.SEARCH_DOCUMENT_LIMIT

    async def hybrid_chunk_search(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
        limit: Optional[int] = None,
    ) -> List[ChunkResult]:
        """
        Perform hybrid search on chunks using both semantic and keyword search.

        Uses CTEs to combine:
        1. Semantic search using vector similarity
        2. Keyword search using full-text search

        Results are fused using Reciprocal Rank Fusion (RRF).

        Args:
            db: Async database session
            query: Search query
            user_id: User ID to filter documents
            limit: Maximum results (default: SEARCH_CHUNK_LIMIT)

        Returns:
            List of ChunkResult sorted by RRF score
        """
        limit = limit or self.chunk_limit

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            logger.warning("Failed to generate query embedding for chunk search")
            return []

        try:
            # Hybrid search with CTEs
            sql = text("""
                WITH semantic_search AS (
                    SELECT
                        c.id as chunk_id,
                        c.document_id,
                        c.content,
                        c.chunk_metadata,
                        d.title as document_title,
                        d.source_type,
                        ROW_NUMBER() OVER (
                            ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
                        ) as rank
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.user_id = :user_id
                        AND d.is_deleted = false
                        AND d.status = 'COMPLETED'
                        AND c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                ),
                keyword_search AS (
                    SELECT
                        c.id as chunk_id,
                        c.document_id,
                        c.content,
                        c.chunk_metadata,
                        d.title as document_title,
                        d.source_type,
                        ROW_NUMBER() OVER (
                            ORDER BY ts_rank(
                                to_tsvector('english', c.content),
                                plainto_tsquery('english', :query)
                            ) DESC
                        ) as rank
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.user_id = :user_id
                        AND d.is_deleted = false
                        AND d.status = 'COMPLETED'
                        AND to_tsvector('english', c.content) @@ plainto_tsquery('english', :query)
                    ORDER BY ts_rank(
                        to_tsvector('english', c.content),
                        plainto_tsquery('english', :query)
                    ) DESC
                    LIMIT :limit
                )
                SELECT
                    COALESCE(s.chunk_id, k.chunk_id) as chunk_id,
                    COALESCE(s.document_id, k.document_id) as document_id,
                    COALESCE(s.content, k.content) as content,
                    COALESCE(s.chunk_metadata, k.chunk_metadata) as chunk_metadata,
                    COALESCE(s.document_title, k.document_title) as document_title,
                    COALESCE(s.source_type, k.source_type) as source_type,
                    s.rank as semantic_rank,
                    k.rank as keyword_rank,
                    (
                        COALESCE(1.0 / (:rrf_k + s.rank), 0) +
                        COALESCE(1.0 / (:rrf_k + k.rank), 0)
                    ) as rrf_score
                FROM semantic_search s
                FULL OUTER JOIN keyword_search k ON s.chunk_id = k.chunk_id
                ORDER BY rrf_score DESC
                LIMIT :limit
            """)

            result = await db.execute(sql, {
                "query_embedding": str(query_embedding),
                "query": query,
                "user_id": user_id,
                "rrf_k": self.rrf_k,
                "limit": limit,
            })

            rows = result.fetchall()

            return [
                ChunkResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    document_title=row.document_title or "",
                    content=row.content,
                    rrf_score=float(row.rrf_score) if row.rrf_score else 0.0,
                    semantic_rank=row.semantic_rank,
                    keyword_rank=row.keyword_rank,
                    metadata={
                        "source_type": row.source_type,
                        **(row.chunk_metadata or {}),
                    },
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error in hybrid chunk search: {e}")
            # Rollback to clear aborted transaction
            try:
                await db.rollback()
            except:
                pass
            return []

    async def hybrid_document_search(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
        limit: Optional[int] = None,
    ) -> List[DocumentResult]:
        """
        Perform hybrid search on documents using summary embeddings.

        Args:
            db: Async database session
            query: Search query
            user_id: User ID to filter documents
            limit: Maximum results (default: SEARCH_DOCUMENT_LIMIT)

        Returns:
            List of DocumentResult sorted by RRF score
        """
        limit = limit or self.document_limit

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            logger.warning("Failed to generate query embedding for document search")
            return []

        try:
            sql = text("""
                WITH semantic_search AS (
                    SELECT
                        id,
                        title,
                        summary,
                        source_type,
                        document_metadata,
                        ROW_NUMBER() OVER (
                            ORDER BY embedding <=> CAST(:query_embedding AS vector)
                        ) as rank
                    FROM documents
                    WHERE user_id = :user_id
                        AND is_deleted = false
                        AND status = 'COMPLETED'
                        AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                ),
                keyword_search AS (
                    SELECT
                        id,
                        title,
                        summary,
                        source_type,
                        document_metadata,
                        ROW_NUMBER() OVER (
                            ORDER BY ts_rank(
                                to_tsvector('english', content),
                                plainto_tsquery('english', :query)
                            ) DESC
                        ) as rank
                    FROM documents
                    WHERE user_id = :user_id
                        AND is_deleted = false
                        AND status = 'COMPLETED'
                        AND to_tsvector('english', content) @@ plainto_tsquery('english', :query)
                    ORDER BY ts_rank(
                        to_tsvector('english', content),
                        plainto_tsquery('english', :query)
                    ) DESC
                    LIMIT :limit
                )
                SELECT
                    COALESCE(s.id, k.id) as id,
                    COALESCE(s.title, k.title) as title,
                    COALESCE(s.summary, k.summary) as summary,
                    COALESCE(s.source_type, k.source_type) as source_type,
                    COALESCE(s.document_metadata, k.document_metadata) as document_metadata,
                    s.rank as semantic_rank,
                    k.rank as keyword_rank,
                    (
                        COALESCE(1.0 / (:rrf_k + s.rank), 0) +
                        COALESCE(1.0 / (:rrf_k + k.rank), 0)
                    ) as rrf_score
                FROM semantic_search s
                FULL OUTER JOIN keyword_search k ON s.id = k.id
                ORDER BY rrf_score DESC
                LIMIT :limit
            """)

            result = await db.execute(sql, {
                "query_embedding": str(query_embedding),
                "query": query,
                "user_id": user_id,
                "rrf_k": self.rrf_k,
                "limit": limit,
            })

            rows = result.fetchall()

            return [
                DocumentResult(
                    document_id=row.id,
                    title=row.title or "",
                    summary=row.summary or "",
                    source_type=row.source_type,
                    rrf_score=float(row.rrf_score) if row.rrf_score else 0.0,
                    metadata=row.document_metadata or {},
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error in hybrid document search: {e}")
            try:
                await db.rollback()
            except:
                pass
            return []

    async def multi_level_search(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
    ) -> List[ChunkResult]:
        """
        Perform multi-level retrieval with document and chunk search.

        Process:
        1. Get top documents from document-level search
        2. Get top chunks from chunk-level hybrid search
        3. Boost chunks from top-ranked documents
        4. Return final ranked chunks

        Args:
            db: Async database session
            query: Search query
            user_id: User ID

        Returns:
            List of ChunkResult with boosted scores
        """
        # Step 1: Document-level search
        doc_results = await self.hybrid_document_search(db, query, user_id)
        doc_scores = {doc.document_id: doc.rrf_score for doc in doc_results}

        # Step 2: Chunk-level hybrid search
        chunk_results = await self.hybrid_chunk_search(db, query, user_id)

        if not chunk_results:
            return []

        # Step 3: Convert to FusedResult for boosting
        fused_chunks = [
            FusedResult(
                id=chunk.chunk_id,
                rrf_score=chunk.rrf_score,
                semantic_rank=chunk.semantic_rank,
                keyword_rank=chunk.keyword_rank,
                data={
                    "document_id": chunk.document_id,
                    "document_title": chunk.document_title,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                },
            )
            for chunk in chunk_results
        ]

        # Step 4: Boost based on document scores
        boosted_chunks = boost_chunk_scores(fused_chunks, doc_scores, boost_factor=0.3)

        # Step 5: Convert back to ChunkResult
        return [
            ChunkResult(
                chunk_id=fused.id,
                document_id=fused.data["document_id"],
                document_title=fused.data["document_title"],
                content=fused.data["content"],
                rrf_score=fused.rrf_score,
                semantic_rank=fused.semantic_rank,
                keyword_rank=fused.keyword_rank,
                metadata=fused.data["metadata"],
            )
            for fused in boosted_chunks
        ]

    async def get_context_with_citations(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Get search context formatted for LLM with citation support.

        Returns:
        - XML-formatted context string
        - Source metadata for citation rendering
        - Chunk ID to citation number mapping

        Args:
            db: Async database session
            query: Search query
            user_id: User ID

        Returns:
            Dict with context_xml, sources, and chunk_mapping
        """
        # Perform multi-level search
        results = await self.multi_level_search(db, query, user_id)

        if not results:
            return {
                "context_xml": "<context>\n  <no_results>No relevant information found.</no_results>\n</context>",
                "sources": [],
                "chunk_mapping": {},
            }

        # Deduplicate results
        fused_results = [
            FusedResult(
                id=r.chunk_id,
                rrf_score=r.rrf_score,
                data=r.to_dict(),
            )
            for r in results
        ]
        deduped = deduplicate_by_content(fused_results)

        # Build sources list and chunk mapping
        sources = []
        chunk_mapping = {}

        for i, fused in enumerate(deduped, 1):
            chunk_id = f"chunk_{fused.id}"
            chunk_mapping[chunk_id] = i

            sources.append({
                "chunk_id": chunk_id,
                "citation_number": i,
                "document_id": fused.data.get("document_id"),
                "document_title": fused.data.get("document_title"),
                "content_preview": fused.data.get("content_preview"),
                "content": fused.data.get("content"),
                "page": fused.data.get("page"),
                "source_type": fused.data.get("source_type"),
                "rrf_score": fused.rrf_score,
            })

        # Format as XML
        context_xml = format_context_xml(sources, include_metadata=True)

        return {
            "context_xml": context_xml,
            "sources": sources,
            "chunk_mapping": chunk_mapping,
        }

    # ==================== LEGACY METHODS FOR BACKWARD COMPATIBILITY ====================

    async def search_journals(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
        limit: Optional[int] = None,
    ) -> List[RAGResult]:
        """
        Legacy method: Search journals using semantic similarity.
        """
        limit = limit or settings.RAG_MAX_JOURNAL_RESULTS

        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            return []

        try:
            sql = text("""
                SELECT
                    id, title, content, tags, folder_id,
                    1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM journals
                WHERE user_id = :user_id
                    AND is_deleted = false
                    AND embedding IS NOT NULL
                    AND 1 - (embedding <=> CAST(:embedding AS vector)) > :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)

            result = await db.execute(sql, {
                "embedding": str(query_embedding),
                "user_id": user_id,
                "threshold": settings.RAG_SIMILARITY_THRESHOLD,
                "limit": limit,
            })

            rows = result.fetchall()

            return [
                RAGResult(
                    content=row.content,
                    source_type="journal",
                    source_id=row.id,
                    title=row.title,
                    similarity=row.similarity,
                    metadata={"tags": row.tags, "folder_id": row.folder_id},
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error searching journals: {e}")
            try:
                await db.rollback()
            except:
                pass
            return []

    async def search_conversations(
        self,
        db: AsyncSession,
        query: str,
        session_id: Optional[str] = None,
        exclude_session_id: Optional[str] = None,
        user_id: int = 1,
        limit: Optional[int] = None,
    ) -> List[RAGResult]:
        """
        Legacy method: Search past conversation messages.
        """
        limit = limit or settings.RAG_MAX_CONVERSATION_RESULTS

        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            return []

        try:
            sql_parts = ["""
                SELECT
                    cm.id, cm.message, cm.sender, cm.session_id, cm.timestamp,
                    c.title as conversation_title,
                    1 - (cm.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM chat_messages cm
                JOIN conversations c ON cm.conversation_id = c.id
                WHERE c.user_id = :user_id
                    AND cm.embedding IS NOT NULL
                    AND 1 - (cm.embedding <=> CAST(:embedding AS vector)) > :threshold
            """]

            params = {
                "embedding": str(query_embedding),
                "user_id": user_id,
                "threshold": settings.RAG_SIMILARITY_THRESHOLD,
                "limit": limit,
            }

            if session_id:
                sql_parts.append("AND cm.session_id = :session_id")
                params["session_id"] = session_id

            if exclude_session_id:
                sql_parts.append("AND cm.session_id != :exclude_session_id")
                params["exclude_session_id"] = exclude_session_id

            sql_parts.append("ORDER BY similarity DESC LIMIT :limit")

            sql = text(" ".join(sql_parts))
            result = await db.execute(sql, params)
            rows = result.fetchall()

            return [
                RAGResult(
                    content=row.message,
                    source_type="conversation",
                    source_id=row.id,
                    title=row.conversation_title,
                    similarity=row.similarity,
                    metadata={
                        "sender": row.sender,
                        "session_id": row.session_id,
                        "timestamp": str(row.timestamp),
                    },
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            try:
                await db.rollback()
            except:
                pass
            return []

    async def get_relevant_context(
        self,
        db: AsyncSession,
        query: str,
        current_session_id: str,
        user_id: int = 1,
    ) -> Dict[str, List[RAGResult]]:
        """
        Legacy method: Get all relevant context.
        """
        journals = await self.search_journals(db, query, user_id)
        conversations = await self.search_conversations(
            db, query, exclude_session_id=current_session_id, user_id=user_id
        )

        return {
            "journals": journals,
            "conversations": conversations,
        }

    def format_context_for_llm(self, context: Dict[str, List[RAGResult]]) -> str:
        """
        Legacy method: Format RAG results for LLM.
        """
        parts = []

        if context.get("journals"):
            parts.append("**Relevant Journal Entries:**")
            for i, result in enumerate(context["journals"], 1):
                parts.append(f"\n[Journal {i}] {result.title}")
                parts.append(f"Content: {result.content[:500]}...")
                parts.append(f"(Relevance: {result.similarity:.2f})")

        if context.get("conversations"):
            parts.append("\n**Relevant Past Discussions:**")
            for i, result in enumerate(context["conversations"], 1):
                sender = result.metadata.get("sender", "unknown")
                parts.append(f"\n[Past Message {i}] ({sender})")
                parts.append(f"{result.content[:300]}...")
                parts.append(f"(Relevance: {result.similarity:.2f})")

        return "\n".join(parts) if parts else ""


# Backward-compatible alias
RAGService = HybridRAGService

# Singleton instance
_rag_service: Optional[HybridRAGService] = None


def get_rag_service() -> HybridRAGService:
    """Get or create the RAG service singleton"""
    global _rag_service
    if _rag_service is None:
        _rag_service = HybridRAGService()
    return _rag_service
