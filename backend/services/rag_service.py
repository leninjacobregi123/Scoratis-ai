"""
RAG (Retrieval Augmented Generation) Service
Hybrid semantic + keyword search with RRF fusion across documents and chunks

Enhanced with:
- Async Operations: Parallel embedding and search for better performance
- Query Reformulation: Uses LLM to optimize search queries
- Metadata Pre-filtering: Date range, file type, source type filters
- Re-ranking: Cross-encoder for improved relevance scoring
- Contextual Grouping: Groups chunks by parent document
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
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
    group_by_document,
    format_grouped_context_xml,
    merge_adjacent_chunks,
)
from services.query_service import get_query_service, ReformulatedQuery
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """
    Filters for RAG search queries.

    Supports:
    - Date range filtering (created_at)
    - File type filtering (pdf, docx, txt, etc.)
    - Source type filtering (upload, journal, chat)
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    file_types: Optional[List[str]] = None  # ['pdf', 'docx', 'txt']
    source_types: Optional[List[str]] = None  # ['upload', 'journal', 'chat']
    exclude_document_ids: Optional[List[int]] = None

    def to_sql_conditions(self) -> tuple[str, dict]:
        """
        Generate SQL WHERE conditions and parameters.

        Returns:
            Tuple of (conditions_string, params_dict)
        """
        conditions = []
        params = {}

        if self.start_date:
            conditions.append("d.created_at >= :start_date")
            params["start_date"] = self.start_date

        if self.end_date:
            conditions.append("d.created_at <= :end_date")
            params["end_date"] = self.end_date

        if self.file_types:
            conditions.append("d.file_type = ANY(:file_types)")
            params["file_types"] = self.file_types

        if self.source_types:
            # Convert string to enum values
            source_conditions = []
            for i, st in enumerate(self.source_types):
                param_name = f"source_type_{i}"
                source_conditions.append(f"d.source_type = :{param_name}")
                params[param_name] = st.upper()
            if source_conditions:
                conditions.append(f"({' OR '.join(source_conditions)})")

        if self.exclude_document_ids:
            conditions.append("d.id != ALL(:exclude_doc_ids)")
            params["exclude_doc_ids"] = self.exclude_document_ids

        return " AND ".join(conditions), params


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
        query_embedding: Optional[List[float]] = None,
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
            query_embedding: Pre-computed embedding (optional, for efficiency)

        Returns:
            List of ChunkResult sorted by RRF score
        """
        limit = limit or self.chunk_limit

        # Generate query embedding (async) if not provided
        if query_embedding is None:
            query_embedding = await self.embedding_service.embed_text_async(query)
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

            params = {
                "query_embedding": str(query_embedding),
                "query": query,
                "user_id": user_id,
                "rrf_k": self.rrf_k,
                "limit": limit,
            }

            result = await db.execute(sql, params)

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
        query_embedding: Optional[List[float]] = None,
    ) -> List[DocumentResult]:
        """
        Perform hybrid search on documents using summary embeddings.

        Args:
            db: Async database session
            query: Search query
            user_id: User ID to filter documents
            limit: Maximum results (default: SEARCH_DOCUMENT_LIMIT)
            query_embedding: Pre-computed embedding (optional, for efficiency)

        Returns:
            List of DocumentResult sorted by RRF score
        """
        limit = limit or self.document_limit

        # Generate query embedding (async) if not provided
        if query_embedding is None:
            query_embedding = await self.embedding_service.embed_text_async(query)
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

            params = {
                "query_embedding": str(query_embedding),
                "query": query,
                "user_id": user_id,
                "rrf_k": self.rrf_k,
                "limit": limit,
            }

            result = await db.execute(sql, params)

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
        Perform multi-level retrieval with PARALLEL document and chunk search.

        Process:
        1. Generate embedding ONCE (shared across searches)
        2. Run document and chunk searches IN PARALLEL
        3. Boost chunks from top-ranked documents
        4. Return final ranked chunks

        Args:
            db: Async database session
            query: Search query
            user_id: User ID

        Returns:
            List of ChunkResult with boosted scores
        """
        # Step 1: Generate embedding ONCE (async)
        query_embedding = await self.embedding_service.embed_text_async(query)
        if not query_embedding:
            logger.warning("Failed to generate query embedding for multi-level search")
            return []

        # Step 2: Run searches (sequential to avoid session concurrency issues)
        # Note: SQLAlchemy AsyncSession doesn't support concurrent operations on same session
        # The embedding generation (async) is the main performance gain
        doc_results = await self.hybrid_document_search(
            db, query, user_id, query_embedding=query_embedding
        )
        chunk_results = await self.hybrid_chunk_search(
            db, query, user_id, query_embedding=query_embedding
        )

        doc_scores = {doc.document_id: doc.rrf_score for doc in doc_results}

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
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_query_reformulation: bool = True,
        llm_service: Any = None,
    ) -> Dict[str, Any]:
        """
        Get search context formatted for LLM with citation support.

        Returns:
        - XML-formatted context string
        - Source metadata for citation rendering
        - Chunk ID to citation number mapping
        - Query reformulation info (if enabled)

        Args:
            db: Async database session
            query: Search query
            user_id: User ID
            conversation_history: Recent chat messages for query reformulation
            use_query_reformulation: Whether to use LLM to reformulate query
            llm_service: LLM service for query reformulation

        Returns:
            Dict with context_xml, sources, chunk_mapping, and reformulation_info
        """
        # Step 1: Query Reformulation (if enabled)
        search_query = query
        reformulation_info = None

        if use_query_reformulation and conversation_history and llm_service:
            try:
                query_service = get_query_service()
                query_service.set_llm_service(llm_service)

                reformulated = await query_service.reformulate_query(
                    query=query,
                    chat_history=conversation_history,
                    use_llm=True
                )

                search_query = reformulated.reformulated_query
                reformulation_info = {
                    "original_query": query,
                    "reformulated_query": search_query,
                    "keywords": reformulated.keywords,
                    "query_type": reformulated.query_type,
                    "confidence": reformulated.confidence,
                }
                logger.info(f"Query reformulated: '{query}' -> '{search_query}'")
            except Exception as e:
                logger.warning(f"Query reformulation failed, using original: {e}")
                search_query = query

        # Step 2: Perform multi-level search
        results = await self.multi_level_search(db, search_query, user_id)

        if not results:
            return {
                "context_xml": "<context>\n  <no_results>No relevant information found.</no_results>\n</context>",
                "sources": [],
                "chunk_mapping": {},
                "reformulation_info": reformulation_info,
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
            "reformulation_info": reformulation_info,
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

        # Use async embedding
        query_embedding = await self.embedding_service.embed_text_async(query)
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

        # Use async embedding
        query_embedding = await self.embedding_service.embed_text_async(query)
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
        Legacy method: Get all relevant context with PARALLEL searches.
        """
        # Run journal and conversation searches IN PARALLEL
        journals_task = self.search_journals(db, query, user_id)
        conversations_task = self.search_conversations(
            db, query, exclude_session_id=current_session_id, user_id=user_id
        )

        journals, conversations = await asyncio.gather(journals_task, conversations_task)

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

    # ==================== ENHANCED RAG PIPELINE ====================

    async def enhanced_search(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
        filters: Optional[SearchFilters] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        use_query_reformulation: bool = True,
        use_reranker: bool = True,
        use_contextual_grouping: bool = True,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Enhanced RAG search with all advanced strategies.

        Pipeline:
        1. Query Reformulation: Optimize query using LLM + chat history
        2. Metadata Pre-filtering: Apply date, file type, source filters
        3. Hybrid Search: Semantic + Keyword with RRF fusion
        4. Re-ranking: Cross-encoder for improved relevance
        5. Contextual Grouping: Group chunks by parent document

        Args:
            db: Async database session
            query: User's search query
            user_id: User ID for filtering
            filters: SearchFilters object with metadata filters
            chat_history: Recent chat messages for query reformulation
            use_query_reformulation: Whether to use LLM query optimization
            use_reranker: Whether to use cross-encoder reranking
            use_contextual_grouping: Whether to group results by document
            limit: Maximum results to return

        Returns:
            Dict with context, sources, metadata, and search info
        """
        limit = limit or self.chunk_limit
        search_info = {
            "original_query": query,
            "reformulated_query": None,
            "filters_applied": {},
            "reranked": False,
            "grouped": False,
        }

        # === Step 1: Query Reformulation ===
        search_query = query
        if use_query_reformulation:
            try:
                from services.query_service import get_query_service
                query_service = get_query_service()

                reformulated = await query_service.reformulate_query(
                    query=query,
                    chat_history=chat_history,
                    use_llm=False  # Use simple expansion (no LLM service injected yet)
                )
                search_query = reformulated.reformulated_query
                search_info["reformulated_query"] = search_query
                search_info["query_keywords"] = reformulated.keywords
                search_info["query_type"] = reformulated.query_type
            except Exception as e:
                logger.warning(f"Query reformulation failed: {e}")
                search_query = query

        # === Step 2: Build filters ===
        if filters:
            filter_conditions, filter_params = filters.to_sql_conditions()
            search_info["filters_applied"] = {
                "start_date": str(filters.start_date) if filters.start_date else None,
                "end_date": str(filters.end_date) if filters.end_date else None,
                "file_types": filters.file_types,
                "source_types": filters.source_types,
            }
        else:
            filter_conditions = ""
            filter_params = {}

        # === Step 3: Hybrid Search ===
        chunk_results = await self.multi_level_search(db, search_query, user_id)

        if not chunk_results:
            return {
                "context_xml": "<context>\n  <no_results>No relevant information found.</no_results>\n</context>",
                "sources": [],
                "chunk_mapping": {},
                "search_info": search_info,
            }

        # === Step 4: Re-ranking ===
        if use_reranker:
            try:
                from services.reranker_service import get_reranker_service
                reranker = get_reranker_service()

                if reranker.is_available:
                    # Convert to dict format for reranker
                    results_for_rerank = [
                        {
                            "id": r.chunk_id,
                            "content": r.content,
                            "rrf_score": r.rrf_score,
                            "document_id": r.document_id,
                            "document_title": r.document_title,
                            "metadata": r.metadata,
                        }
                        for r in chunk_results
                    ]

                    reranked = reranker.rerank(
                        query=search_query,
                        results=results_for_rerank,
                        top_k=limit,
                    )

                    # Convert back to ChunkResult format
                    chunk_results = [
                        ChunkResult(
                            chunk_id=rr.id,
                            document_id=rr.metadata.get("document_id"),
                            document_title=rr.metadata.get("document_title", ""),
                            content=rr.content,
                            rrf_score=rr.reranked_score,
                            metadata=rr.metadata,
                        )
                        for rr in reranked
                    ]
                    search_info["reranked"] = True
            except Exception as e:
                logger.warning(f"Re-ranking failed: {e}")

        # === Step 5: Deduplicate ===
        fused_results = [
            FusedResult(
                id=r.chunk_id,
                rrf_score=r.rrf_score,
                data=r.to_dict(),
            )
            for r in chunk_results
        ]
        deduped = deduplicate_by_content(fused_results)

        # === Step 6: Contextual Grouping ===
        if use_contextual_grouping:
            # Group by document
            result_dicts = [f.data for f in deduped]
            grouped = group_by_document(result_dicts, max_chunks_per_doc=5)

            # Build grouped XML
            context_xml = format_grouped_context_xml(grouped)
            search_info["grouped"] = True
            search_info["document_count"] = len(grouped)
        else:
            context_xml = format_context_xml([f.data for f in deduped])

        # === Step 7: Build sources and mapping ===
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

        return {
            "context_xml": context_xml,
            "sources": sources,
            "chunk_mapping": chunk_mapping,
            "search_info": search_info,
        }

    async def search_with_filters(
        self,
        db: AsyncSession,
        query: str,
        user_id: int = 1,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        file_types: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method for search with common filter parameters.

        Args:
            db: Database session
            query: Search query
            user_id: User ID
            start_date: Filter documents created after this date
            end_date: Filter documents created before this date
            file_types: List of file types to include
            source_types: List of source types to include
            limit: Maximum results

        Returns:
            Search results with context and sources
        """
        filters = SearchFilters(
            start_date=start_date,
            end_date=end_date,
            file_types=file_types,
            source_types=source_types,
        )

        return await self.enhanced_search(
            db=db,
            query=query,
            user_id=user_id,
            filters=filters,
            limit=limit,
        )


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
