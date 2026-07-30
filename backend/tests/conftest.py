"""
Pytest Configuration and Fixtures for Scoratis Tests

Provides shared fixtures for:
- Database sessions (sync and async)
- Test client for API endpoints
- Mock services
- Sample data factories
"""

import os
import sys
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.base import Base


# =============================================================================
# Database Fixtures
# =============================================================================

# Test database URL - honors DATABASE_URL from the environment (ci.yml points
# this at a real Postgres service container for integration tests) and only
# falls back to SQLite when nothing is set. Several models use Postgres-only
# JSONB columns, which SQLite's compiler cannot render at all - hardcoding
# sqlite here unconditionally made any test touching table creation fail
# with a CompileError, regardless of what DATABASE_URL the environment
# actually provided.
TEST_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def sync_engine():
    """Create a synchronous test database engine."""
    # check_same_thread/StaticPool are SQLite-only concerns (a single shared
    # in-memory connection); psycopg2 raises TypeError on an unrecognized
    # check_same_thread connect_arg, so these can't be passed unconditionally
    # once TEST_DATABASE_URL can point at a real Postgres service container.
    if TEST_DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(TEST_DATABASE_URL)
        # Base.metadata.create_all() below creates tables directly from ORM
        # metadata - it does not run Alembic migrations, so migration 001's
        # `CREATE EXTENSION vector`/`pg_trgm` calls never happen here. A
        # fresh Postgres service container (e.g. ci.yml's) has neither
        # extension, and several models declare Vector(384) columns -
        # without this, create_all() fails with "type vector does not
        # exist" the moment it reaches the first such table.
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            conn.commit()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(sync_engine) -> Generator[Session, None, None]:
    """Create a synchronous database session for tests."""
    SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_client(db_session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""
    # Import here to avoid circular imports
    from main import app

    with TestClient(app) as client:
        yield client


# =============================================================================
# Mock Service Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_service():
    """Mock LLM service for tests."""
    service = MagicMock()
    service.generate = AsyncMock(return_value="This is a test response from the LLM.")
    service.generate_stream = AsyncMock(return_value=iter(["This ", "is ", "a ", "test."]))
    service.generate_with_tools = AsyncMock(return_value={
        "content": "Test response",
        "tool_calls": []
    })
    service.get_current_config = MagicMock(return_value={"model": "test-model"})
    return service


@pytest.fixture
def mock_rag_service():
    """Mock RAG service for tests."""
    service = MagicMock()
    service.get_context_with_citations = AsyncMock(return_value={
        "context_xml": "<context><chunk id='1'>Test content</chunk></context>",
        "sources": [
            {
                "citation_number": 1,
                "chunk_id": 1,
                "document_title": "Test Document",
                "content_preview": "This is test content...",
                "source_type": "upload"
            }
        ],
        "chunk_mapping": {"1": 1}
    })
    service.hybrid_chunk_search = AsyncMock(return_value=[])
    service.search_journals = AsyncMock(return_value=[])
    service.search_conversations = AsyncMock(return_value=[])
    # create_search_knowledge_base_tool() prefers enhanced_search() over
    # get_context_with_citations() whenever hasattr(rag_service,
    # 'enhanced_search') is true - which a plain MagicMock() always
    # satisfies via attribute auto-vivification, regardless of whether this
    # is actually mocked. Without an explicit AsyncMock here, that always
    # takes the "enhanced" branch in tests and awaits an un-mocked
    # auto-generated MagicMock, failing with "object MagicMock can't be
    # used in 'await' expression" - not what any of these tests intended
    # to exercise.
    service.enhanced_search = AsyncMock(return_value={
        "sources": [
            {
                "citation_number": 1,
                "chunk_id": 1,
                "document_title": "Test Document",
                "content_preview": "This is test content...",
                "source_type": "upload",
                "rrf_score": 0.9,
            }
        ],
        "search_info": {"reformulated_query": None, "reranked": True, "grouped": False},
        "context_xml": "<context><chunk id='1'>Test content</chunk></context>",
    })
    return service


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for tests."""
    import numpy as np

    service = MagicMock()
    service.embed_text = MagicMock(return_value=np.random.rand(384).tolist())
    service.embed_texts = MagicMock(return_value=[np.random.rand(384).tolist() for _ in range(5)])
    return service


@pytest.fixture
def mock_web_search_service():
    """Mock web search service for tests."""
    service = MagicMock()
    service.search = AsyncMock(return_value=[
        {
            "title": "Test Search Result",
            "url": "https://example.com",
            "snippet": "This is a test search result."
        }
    ])
    return service


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_user_data():
    """Sample user data for tests."""
    return {
        "username": "test_user",
        "email": "test@example.com",
        "hashed_password": "test_password_hash"
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for tests."""
    return {
        "title": "Test Document",
        "content": "This is a test document about machine learning. "
                   "Machine learning is a subset of artificial intelligence.",
        "source_type": "upload",
        "file_type": "txt",
        "file_size": 1024
    }


@pytest.fixture
def sample_chunk_data():
    """Sample chunk data for tests."""
    return {
        "content": "This is a test chunk of content for RAG testing.",
        "chunk_index": 0,
        "start_char": 0,
        "end_char": 50,
        "metadata": {"page": 1}
    }


@pytest.fixture
def sample_journal_data():
    """Sample journal entry for tests."""
    return {
        "title": "My Learning Notes",
        "content": "Today I learned about neural networks and how they work.",
        "folder_id": None,
        "metadata": {"tags": ["ai", "learning"]}
    }


@pytest.fixture
def sample_conversation_messages():
    """Sample conversation messages for tests."""
    return [
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is a type of AI..."},
        {"role": "user", "content": "Can you explain neural networks?"},
    ]


# =============================================================================
# Golden Dataset Fixture for Agent Evaluation
# =============================================================================

@pytest.fixture
def golden_dataset():
    """Golden dataset for agent evaluation."""
    return [
        {
            "id": "eval_001",
            "query": "What is machine learning?",
            "expected_topics": ["machine learning", "AI", "artificial intelligence"],
            "expected_format": "definition",
            "min_length": 50,
            "quality_criteria": {
                "factual_accuracy": True,
                "relevance": True,
                "completeness": True
            }
        },
        {
            "id": "eval_002",
            "query": "Explain the difference between supervised and unsupervised learning",
            "expected_topics": ["supervised learning", "unsupervised learning", "labeled data"],
            "expected_format": "comparison",
            "min_length": 100,
            "quality_criteria": {
                "factual_accuracy": True,
                "relevance": True,
                "completeness": True,
                "comparison_clarity": True
            }
        },
    ]


# =============================================================================
# Environment Setup
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    yield
    # Cleanup if needed
