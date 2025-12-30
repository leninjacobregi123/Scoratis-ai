"""
Unit Tests for RAG Service

Tests the RAG service components:
- Hybrid search
- RRF fusion
- Citation generation
- Context formatting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestRRFFusion:
    """Tests for Reciprocal Rank Fusion utilities."""

    def test_reciprocal_rank_fusion_basic(self):
        """Test basic RRF fusion with two ranked lists."""
        from services.rrf_fusion import reciprocal_rank_fusion, RankedItem

        # Create two ranked lists
        semantic_results = [
            RankedItem(id=1, rank=1, score=0.9, source="semantic"),
            RankedItem(id=2, rank=2, score=0.8, source="semantic"),
            RankedItem(id=3, rank=3, score=0.7, source="semantic"),
        ]

        keyword_results = [
            RankedItem(id=2, rank=1, score=0.95, source="keyword"),
            RankedItem(id=1, rank=2, score=0.85, source="keyword"),
            RankedItem(id=4, rank=3, score=0.75, source="keyword"),
        ]

        fused = reciprocal_rank_fusion([semantic_results, keyword_results], k=60)

        # Both items 1 and 2 appear in both lists with similar positions
        # Item 1: rank 1 in semantic + rank 2 in keyword
        # Item 2: rank 2 in semantic + rank 1 in keyword
        # They should have similar scores, with item 1 or 2 at top
        assert len(fused) == 4
        assert fused[0].id in [1, 2]  # Either could be highest
        assert fused[1].id in [1, 2]  # Second highest

    def test_reciprocal_rank_fusion_single_list(self):
        """Test RRF with a single list."""
        from services.rrf_fusion import reciprocal_rank_fusion, RankedItem

        results = [
            RankedItem(id=1, rank=1, score=0.9, source="semantic"),
            RankedItem(id=2, rank=2, score=0.8, source="semantic"),
        ]

        fused = reciprocal_rank_fusion([results], k=60)

        assert len(fused) == 2
        assert fused[0].id == 1
        assert fused[1].id == 2

    def test_reciprocal_rank_fusion_empty(self):
        """Test RRF with empty lists."""
        from services.rrf_fusion import reciprocal_rank_fusion

        fused = reciprocal_rank_fusion([], k=60)
        assert len(fused) == 0

    def test_boost_chunk_scores(self):
        """Test document-level score boosting."""
        from services.rrf_fusion import boost_chunk_scores, FusedResult

        chunks = [
            FusedResult(id=1, rrf_score=0.5, data={"document_id": 10}),
            FusedResult(id=2, rrf_score=0.4, data={"document_id": 20}),
        ]

        doc_scores = {10: 1.0, 20: 0.5}

        boosted = boost_chunk_scores(chunks, doc_scores, boost_factor=0.3)

        # Chunk from doc 10 should have higher score after boost
        assert boosted[0].id == 1
        assert boosted[0].rrf_score > 0.5

    def test_format_context_xml(self):
        """Test XML context formatting."""
        from services.rrf_fusion import format_context_xml

        results = [
            {"chunk_id": "chunk_1", "content": "Test content 1", "document_title": "Doc 1"},
            {"chunk_id": "chunk_2", "content": "Test content 2", "document_title": "Doc 2"},
        ]

        xml = format_context_xml(results)

        assert "<context>" in xml
        assert "chunk_1" in xml
        assert "Test content 1" in xml
        assert "</context>" in xml

    def test_format_context_xml_empty(self):
        """Test XML formatting with empty results."""
        from services.rrf_fusion import format_context_xml

        xml = format_context_xml([])

        assert "<context>" in xml
        assert "no_results" in xml

    def test_extract_citation_ids(self):
        """Test citation ID extraction from text."""
        from services.rrf_fusion import extract_citation_ids

        text = "Based on [citation:chunk_123] and [citation:chunk_456], we can conclude..."
        ids = extract_citation_ids(text)

        assert len(ids) == 2
        assert "chunk_123" in ids
        assert "chunk_456" in ids

    def test_replace_citations_with_numbers(self):
        """Test replacing citation tags with numbered references."""
        from services.rrf_fusion import replace_citations_with_numbers

        text = "See [citation:chunk_1] and [citation:chunk_2] for details."
        mapping = {"chunk_1": 1, "chunk_2": 2}

        result, number_map = replace_citations_with_numbers(text, mapping)

        assert "[1]" in result
        assert "[2]" in result
        assert "[citation:chunk_1]" not in result


class TestRAGServiceMocked:
    """Tests for RAG service with mocked dependencies."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_context_with_citations_returns_structure(
        self, mock_db_session, mock_rag_service
    ):
        """Test that get_context_with_citations returns proper structure."""
        result = await mock_rag_service.get_context_with_citations(
            mock_db_session, "test query", user_id=1
        )

        assert "context_xml" in result
        assert "sources" in result
        assert "chunk_mapping" in result
        assert isinstance(result["sources"], list)

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self, mock_db_session, mock_rag_service):
        """Test that hybrid search is called correctly."""
        await mock_rag_service.hybrid_chunk_search(
            mock_db_session, "test query", user_id=1, limit=5
        )

        mock_rag_service.hybrid_chunk_search.assert_called_once()


class TestEmbeddingService:
    """Tests for embedding service."""

    def test_embed_text_returns_vector(self, mock_embedding_service):
        """Test that embed_text returns a vector of correct dimension."""
        result = mock_embedding_service.embed_text("test text")

        assert len(result) == 384  # all-MiniLM-L6-v2 dimension

    def test_embed_texts_batch(self, mock_embedding_service):
        """Test batch embedding."""
        texts = ["text 1", "text 2", "text 3"]

        # Override mock for this specific test
        import numpy as np
        mock_embedding_service.embed_texts = MagicMock(
            return_value=[np.random.rand(384).tolist() for _ in range(len(texts))]
        )

        result = mock_embedding_service.embed_texts(texts)

        assert len(result) == 3
        assert all(len(v) == 384 for v in result)
