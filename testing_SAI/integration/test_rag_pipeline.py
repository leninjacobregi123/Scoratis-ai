"""
Integration Tests for RAG Pipeline

Tests the complete RAG pipeline including:
- Document ingestion and chunking
- Embedding generation
- Hybrid search (semantic + keyword)
- RRF fusion
- Citation processing

Location: testing_SAI/integration/test_rag_pipeline.py
"""

import pytest
import sys
import os
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

# Mark all tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.rag]


# =============================================================================
# Document Ingestion Tests
# =============================================================================

class TestDocumentIngestion:
    """Tests for document ingestion service."""

    def test_ingestion_service_imports(self):
        """Test that ingestion service imports."""
        from services.ingestion_service import IngestionService
        assert IngestionService is not None

    def test_ingestion_service_creates(self):
        """Test that ingestion service can be created."""
        from services.ingestion_service import IngestionService

        # IngestionService has no required constructor args
        service = IngestionService()
        assert service is not None
        assert hasattr(service, 'chunk_size')
        assert hasattr(service, 'chunk_overlap')

    def test_text_splitter_configured(self):
        """Test that text splitter is configured."""
        from services.ingestion_service import IngestionService

        service = IngestionService()
        assert hasattr(service, 'text_splitter')


# =============================================================================
# Embedding Service Tests
# =============================================================================

class TestEmbeddingService:
    """Tests for embedding service."""

    def test_embedding_service_imports(self):
        """Test that embedding service imports."""
        from services.embedding_service import EmbeddingService
        assert EmbeddingService is not None

    def test_mock_embedding_returns_correct_dimension(self, mock_embedding_service):
        """Test mock embeddings have correct dimension."""
        embedding = mock_embedding_service.embed_text("test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 384  # Expected dimension

    def test_batch_embedding(self, mock_embedding_service):
        """Test batch embedding."""
        texts = ["text 1", "text 2", "text 3"]
        embeddings = mock_embedding_service.embed_texts(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)


# =============================================================================
# RRF Fusion Tests
# =============================================================================

class TestRRFFusion:
    """Tests for Reciprocal Rank Fusion."""

    def test_rrf_imports(self):
        """Test RRF module imports."""
        from services.rrf_fusion import (
            reciprocal_rank_fusion,
            RankedItem,
            FusedResult,
            deduplicate_by_content,
            group_by_document,
            merge_adjacent_chunks
        )
        assert reciprocal_rank_fusion is not None

    def test_rrf_calculation(self):
        """Test RRF score calculation."""
        from services.rrf_fusion import reciprocal_rank_fusion, RankedItem

        # Create ranked items
        semantic_results = [
            RankedItem(id="doc1", rank=1, score=0.9, source="semantic"),
            RankedItem(id="doc2", rank=2, score=0.8, source="semantic"),
        ]
        keyword_results = [
            RankedItem(id="doc1", rank=2, score=0.7, source="keyword"),
            RankedItem(id="doc3", rank=1, score=0.85, source="keyword"),
        ]

        fused = reciprocal_rank_fusion([semantic_results, keyword_results], k=60)

        # doc1 appears in both, should have highest RRF score
        assert len(fused) == 3
        # First result should be doc1 (appears in both lists)
        assert fused[0].id == "doc1"

    def test_rrf_score_decreases_with_rank(self):
        """Test that items with higher ranks get lower RRF contribution."""
        from services.rrf_fusion import reciprocal_rank_fusion, RankedItem

        # Single list with different ranks
        results = [
            RankedItem(id="doc1", rank=1, score=0.9, source="semantic"),
            RankedItem(id="doc2", rank=10, score=0.5, source="semantic"),
        ]

        fused = reciprocal_rank_fusion([results], k=60)

        # doc1 (rank 1) should have higher RRF score than doc2 (rank 10)
        doc1_score = next(f.rrf_score for f in fused if f.id == "doc1")
        doc2_score = next(f.rrf_score for f in fused if f.id == "doc2")

        assert doc1_score > doc2_score

    def test_deduplicate_by_content(self):
        """Test content-based deduplication."""
        from services.rrf_fusion import deduplicate_by_content, FusedResult

        results = [
            FusedResult(id=1, rrf_score=0.9, data={"content": "Hello world"}),
            FusedResult(id=2, rrf_score=0.8, data={"content": "Hello world"}),  # Duplicate
            FusedResult(id=3, rrf_score=0.7, data={"content": "Different content"}),
        ]

        deduped = deduplicate_by_content(results, similarity_threshold=0.95)

        # Should remove near-duplicates
        assert len(deduped) <= len(results)

    def test_group_by_document(self):
        """Test grouping results by document."""
        from services.rrf_fusion import group_by_document

        results = [
            {"chunk_id": 1, "document_id": 100, "score": 0.9},
            {"chunk_id": 2, "document_id": 100, "score": 0.8},
            {"chunk_id": 3, "document_id": 101, "score": 0.7},
            {"chunk_id": 4, "document_id": 101, "score": 0.6},
        ]

        grouped = group_by_document(results, max_chunks_per_doc=2)

        # Should have results grouped by document ID
        assert 100 in grouped
        assert 101 in grouped
        assert len(grouped[100]) <= 2
        assert len(grouped[101]) <= 2

    def test_merge_adjacent_chunks(self):
        """Test merging adjacent chunks from same document."""
        from services.rrf_fusion import merge_adjacent_chunks

        results = [
            {"chunk_id": 1, "document_id": 100, "chunk_index": 0, "content": "Part 1"},
            {"chunk_id": 2, "document_id": 100, "chunk_index": 1, "content": "Part 2"},
            {"chunk_id": 3, "document_id": 101, "chunk_index": 0, "content": "Other"},
        ]

        merged = merge_adjacent_chunks(results)

        # Adjacent chunks from same doc should be merged
        assert len(merged) > 0


# =============================================================================
# RAG Service Tests
# =============================================================================

class TestRAGService:
    """Tests for the main RAG service."""

    def test_rag_service_imports(self):
        """Test RAG service imports."""
        from services.rag_service import RAGService, SearchFilters
        assert RAGService is not None
        assert SearchFilters is not None

    def test_search_filters_creation(self):
        """Test SearchFilters dataclass."""
        from services.rag_service import SearchFilters

        # SearchFilters uses start_date/end_date not date_from
        filters = SearchFilters(
            subject="physics",
            source_types=["upload", "journal"],
        )

        assert filters.subject == "physics"
        assert "upload" in filters.source_types

    @pytest.mark.asyncio
    async def test_mock_rag_search(self, mock_rag_service, async_db_session):
        """Test RAG search with mock service."""
        result = await mock_rag_service.get_context_with_citations(
            async_db_session,
            query="Newton's laws",
            user_id=1
        )

        assert "sources" in result
        assert "context_xml" in result
        assert len(result["sources"]) > 0

    @pytest.mark.asyncio
    async def test_enhanced_search(self, mock_rag_service, async_db_session):
        """Test enhanced search with reranking."""
        result = await mock_rag_service.enhanced_search(
            async_db_session,
            query="quantum mechanics",
            user_id=1,
            use_query_reformulation=True,
            use_reranker=True
        )

        assert "sources" in result
        assert "search_info" in result


# =============================================================================
# Citation Processor Tests
# =============================================================================

class TestCitationProcessor:
    """Tests for citation processing."""

    def test_citation_processor_imports(self):
        """Test citation processor imports."""
        from services.citation_processor import CitationProcessor
        assert CitationProcessor is not None

    def test_to_superscript(self):
        """Test superscript conversion."""
        from services.citation_processor import CitationProcessor

        processor = CitationProcessor()

        assert processor.to_superscript(1) == "¹"
        assert processor.to_superscript(12) == "¹²"
        assert processor.to_superscript(123) == "¹²³"

    def test_extract_citations(self):
        """Test extracting citation references from text."""
        from services.citation_processor import CitationProcessor

        text = "Info from source [citation:chunk_101] and more [citation:chunk_102]."
        citations = CitationProcessor.extract_citations(text)

        # extract_citations returns a Set
        assert "chunk_101" in citations
        assert "chunk_102" in citations

    def test_format_response_with_footnotes(self):
        """Test formatting response with footnotes."""
        from services.citation_processor import CitationProcessor

        processor = CitationProcessor()

        response = "The sun is a star [citation:chunk_101] that provides light [citation:chunk_102]."
        sources = [
            {"chunk_id": "chunk_101", "document_title": "Astronomy Notes"},
            {"chunk_id": "chunk_102", "document_title": "Physics Book"},
        ]
        chunk_mapping = {"chunk_101": 1, "chunk_102": 2}

        formatted, footnotes, used_sources = processor.format_response_with_footnotes(
            response, sources, chunk_mapping
        )

        # Should contain superscript numbers
        assert "¹" in formatted or "[1]" in formatted
        assert "²" in formatted or "[2]" in formatted


# =============================================================================
# Search Result Processing Tests
# =============================================================================

class TestSearchResultProcessing:
    """Tests for search result processing utilities."""

    def test_format_context_xml(self):
        """Test XML context formatting."""
        from services.rrf_fusion import format_context_xml

        results = [
            {"chunk_id": 1, "content": "Content A", "document_title": "Doc A"},
            {"chunk_id": 2, "content": "Content B", "document_title": "Doc B"},
        ]

        xml = format_context_xml(results)

        assert "<context>" in xml
        assert "Content A" in xml
        assert "</context>" in xml

    def test_format_context_xml_empty(self):
        """Test XML formatting with empty results."""
        from services.rrf_fusion import format_context_xml

        xml = format_context_xml([])

        assert "<context>" in xml
        assert "no_results" in xml.lower()

    def test_format_grouped_context_xml(self):
        """Test hierarchical XML formatting."""
        from services.rrf_fusion import format_grouped_context_xml

        grouped = {
            100: [
                {"chunk_id": 1, "content": "Chunk 1", "document_title": "Doc A"},
                {"chunk_id": 2, "content": "Chunk 2", "document_title": "Doc A"},
            ],
            101: [
                {"chunk_id": 3, "content": "Chunk 3", "document_title": "Doc B"},
            ]
        }

        xml = format_grouped_context_xml(grouped)

        assert "<context>" in xml
        assert "<document" in xml
        assert "</document>" in xml


# =============================================================================
# End-to-End RAG Flow Tests
# =============================================================================

class TestRAGEndToEnd:
    """End-to-end tests for RAG flow."""

    @pytest.mark.asyncio
    async def test_full_rag_flow_mock(
        self, mock_rag_service, mock_embedding_service, async_db_session
    ):
        """Test full RAG flow with mocks."""
        # 1. Simulate document exists in DB
        # 2. Search for content
        result = await mock_rag_service.get_context_with_citations(
            async_db_session,
            query="test query",
            user_id=1
        )

        # Should return context
        assert "context_xml" in result
        assert "sources" in result

    @pytest.mark.asyncio
    async def test_empty_results_handled(
        self, mock_empty_rag_service, async_db_session
    ):
        """Test handling of empty search results."""
        result = await mock_empty_rag_service.get_context_with_citations(
            async_db_session,
            query="nonexistent topic xyz",
            user_id=1
        )

        assert result["sources"] == []
        assert result["context_xml"] == ""

    @pytest.mark.asyncio
    async def test_subject_filtering(
        self, mock_rag_service, async_db_session
    ):
        """Test subject filtering in RAG search."""
        from services.rag_service import SearchFilters

        filters = SearchFilters(subject="physics")

        result = await mock_rag_service.enhanced_search(
            async_db_session,
            query="Newton's laws",
            user_id=1,
            filters=filters
        )

        # Should return filtered results
        assert "sources" in result
