"""
Services for Scoratis
"""

from .embedding_service import EmbeddingService, get_embedding_service
from .rag_service import RAGService, RAGResult, get_rag_service
from .web_search_service import WebSearchService, SearchResult, get_web_search_service
from .memory_service import MemoryService, MemoryContext, Message, get_memory_service

__all__ = [
    # Embedding
    "EmbeddingService",
    "get_embedding_service",
    # RAG
    "RAGService",
    "RAGResult",
    "get_rag_service",
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
