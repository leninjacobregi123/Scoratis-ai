"""
Services for Scoratis

Enhanced RAG Pipeline includes:
- Query Reformulation Service: Optimizes search queries using LLM
- Re-ranker Service: Cross-encoder for improved relevance scoring
- Enhanced filters: Date range, file type, source type filtering
- Contextual Grouping: Groups chunks by parent document
"""

from .embedding_service import EmbeddingService, get_embedding_service
from .rag_service import RAGService, RAGResult, get_rag_service, SearchFilters, ChunkResult
from .web_search_service import WebSearchService, SearchResult, get_web_search_service
from .memory_service import MemoryService, MemoryContext, Message, get_memory_service
from .query_service import QueryReformulationService, ReformulatedQuery, get_query_service
from .reranker_service import RerankerService, RerankedResult, get_reranker_service

__all__ = [
    # Embedding
    "EmbeddingService",
    "get_embedding_service",
    # RAG
    "RAGService",
    "RAGResult",
    "ChunkResult",
    "SearchFilters",
    "get_rag_service",
    # Query Reformulation
    "QueryReformulationService",
    "ReformulatedQuery",
    "get_query_service",
    # Re-ranker
    "RerankerService",
    "RerankedResult",
    "get_reranker_service",
    # Web Search
    "WebSearchService",
    "SearchResult",
    "get_web_search_service",
    # Memory
    "MemoryService",
    "MemoryContext",
    "Message",
    "get_memory_service",
]
