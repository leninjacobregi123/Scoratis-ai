"""
Pytest Configuration and Fixtures for Scoratis AI Testing Suite

This is the main configuration file for all tests. It provides:
- Database fixtures (sync and async, SQLite for speed)
- Mock service fixtures (LLM, RAG, Embedding, Web Search)
- Sample data factories
- Test client for API endpoints
- Golden dataset fixtures for evaluation

Directory: testing_SAI/
"""

import os
import sys
import asyncio
import json
import numpy as np
from typing import AsyncGenerator, Generator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add backend to Python path
BACKEND_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, BACKEND_PATH)

from models.base import Base


# =============================================================================
# Configuration Constants
# =============================================================================

TEST_DATABASE_URL = "sqlite:///./test_scoratis.db"
TEST_USER_ID = 1
TEST_SESSION_ID = "test-session-001"
EMBEDDING_DIMENSION = 384


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def sync_engine():
    """Create a synchronous test database engine (SQLite in-memory)."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


@pytest.fixture(scope="function")
def async_db_session():
    """Create a mock async database session for tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_client(db_session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""
    from main import app

    with TestClient(app) as client:
        yield client


# =============================================================================
# Mock LLM Service
# =============================================================================

@pytest.fixture
def mock_llm_service():
    """
    Mock LLM service for tests.

    Provides:
    - generate(): Returns simple text response
    - generate_stream(): Returns token iterator
    - generate_with_tools(): Returns response with optional tool calls
    """
    service = MagicMock()

    # Basic generation
    service.generate = AsyncMock(return_value="This is a test response from the LLM.")

    # Streaming generation
    async def mock_stream(*args, **kwargs):
        for token in ["This ", "is ", "a ", "test ", "response."]:
            yield {"type": "token", "content": token}
        yield {"type": "done", "content": "This is a test response."}
    service.generate_stream = mock_stream

    # Generation with tools (function calling)
    service.generate_with_tools = AsyncMock(return_value={
        "content": "Based on my analysis, here is the answer...",
        "tool_calls": [],
        "finish_reason": "stop"
    })

    # Configuration
    service.get_current_config = MagicMock(return_value={
        "provider": "test",
        "model": "test-model-v1",
        "temperature": 0.7
    })

    return service


@pytest.fixture
def mock_llm_with_tool_calls(mock_llm_service):
    """Mock LLM that returns tool calls."""
    mock_llm_service.generate_with_tools = AsyncMock(return_value={
        "content": "",
        "tool_calls": [{
            "id": "call_test_001",
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "arguments": json.dumps({"query": "test query", "limit": 5})
            }
        }],
        "finish_reason": "tool_calls"
    })
    return mock_llm_service


# =============================================================================
# Mock RAG Service
# =============================================================================

@pytest.fixture
def mock_rag_service():
    """
    Mock RAG service for tests.

    Provides:
    - get_context_with_citations(): Returns context XML and sources
    - hybrid_chunk_search(): Returns chunk results
    - search_journals(): Returns journal entries
    - search_conversations(): Returns past conversations
    - enhanced_search(): Returns enhanced search results
    """
    service = MagicMock()

    # Standard context retrieval
    service.get_context_with_citations = AsyncMock(return_value={
        "context_xml": """<context>
<chunk citation_number="1" document_title="Physics Notes" source_type="upload">
Newton's first law states that an object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force.
</chunk>
<chunk citation_number="2" document_title="Physics Notes" source_type="upload">
The second law defines force as mass times acceleration (F=ma).
</chunk>
</context>""",
        "sources": [
            {
                "citation_number": 1,
                "chunk_id": 101,
                "document_title": "Physics Notes",
                "content_preview": "Newton's first law states that an object at rest...",
                "source_type": "upload",
                "rrf_score": 0.85
            },
            {
                "citation_number": 2,
                "chunk_id": 102,
                "document_title": "Physics Notes",
                "content_preview": "The second law defines force as mass times...",
                "source_type": "upload",
                "rrf_score": 0.72
            }
        ],
        "chunk_mapping": {101: 1, 102: 2}
    })

    # Enhanced search
    service.enhanced_search = AsyncMock(return_value={
        "sources": [
            {
                "citation_number": 1,
                "chunk_id": 101,
                "document_title": "Test Document",
                "content_preview": "Test content preview...",
                "source_type": "upload",
                "rrf_score": 0.85
            }
        ],
        "context_xml": "<context><chunk>Test content</chunk></context>",
        "search_info": {
            "reformulated_query": "test query reformulated",
            "reranked": True,
            "grouped": True
        }
    })

    # Chunk search
    service.hybrid_chunk_search = AsyncMock(return_value=[
        MagicMock(
            id=101,
            content="Test chunk content",
            document_id=1,
            similarity=0.85
        )
    ])

    # Journal search
    service.search_journals = AsyncMock(return_value=[
        MagicMock(
            id=1,
            title="My Learning Notes",
            content="Today I learned about neural networks...",
            similarity=0.78,
            metadata={"tags": ["ai", "learning"]}
        )
    ])

    # Conversation search
    service.search_conversations = AsyncMock(return_value=[
        MagicMock(
            content="We discussed photosynthesis last time...",
            title="Biology Session",
            similarity=0.72,
            metadata={"sender": "assistant"}
        )
    ])

    return service


@pytest.fixture
def mock_empty_rag_service():
    """Mock RAG service that returns empty results (for fallback testing)."""
    service = MagicMock()

    service.get_context_with_citations = AsyncMock(return_value={
        "context_xml": "",
        "sources": [],
        "chunk_mapping": {}
    })
    service.enhanced_search = AsyncMock(return_value={
        "sources": [],
        "context_xml": "",
        "search_info": {}
    })
    service.hybrid_chunk_search = AsyncMock(return_value=[])
    service.search_journals = AsyncMock(return_value=[])
    service.search_conversations = AsyncMock(return_value=[])

    return service


# =============================================================================
# Mock Embedding Service
# =============================================================================

@pytest.fixture
def mock_embedding_service():
    """
    Mock embedding service for tests.

    Returns random 384-dimensional vectors to simulate embeddings.
    """
    service = MagicMock()

    def generate_embedding():
        return np.random.rand(EMBEDDING_DIMENSION).tolist()

    service.embed_text = MagicMock(side_effect=lambda text: generate_embedding())
    service.embed_texts = MagicMock(
        side_effect=lambda texts: [generate_embedding() for _ in texts]
    )

    # Async versions
    service.aembed_text = AsyncMock(side_effect=lambda text: generate_embedding())
    service.aembed_texts = AsyncMock(
        side_effect=lambda texts: [generate_embedding() for _ in texts]
    )

    return service


# =============================================================================
# Mock Web Search Service
# =============================================================================

@pytest.fixture
def mock_web_search_service():
    """
    Mock web search service for tests.

    Returns simulated DuckDuckGo-style results.
    """
    service = MagicMock()

    service.search = AsyncMock(return_value=[
        {
            "title": "Machine Learning - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Machine_learning",
            "snippet": "Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience."
        },
        {
            "title": "What is Machine Learning? | IBM",
            "url": "https://www.ibm.com/topics/machine-learning",
            "snippet": "Machine learning is a branch of AI and computer science that focuses on using data and algorithms to imitate the way humans learn."
        },
        {
            "title": "Machine Learning Tutorial - GeeksforGeeks",
            "url": "https://www.geeksforgeeks.org/machine-learning/",
            "snippet": "Machine Learning tutorial covers basic and advanced concepts including supervised and unsupervised learning, regression, classification."
        }
    ])

    return service


@pytest.fixture
def mock_empty_web_search_service():
    """Mock web search service that returns empty results."""
    service = MagicMock()
    service.search = AsyncMock(return_value=[])
    return service


# =============================================================================
# Mock LangGraph Service
# =============================================================================

@pytest.fixture
def mock_langgraph_service():
    """Mock LangGraph service for session management."""
    service = MagicMock()

    service._fallback_states = {}

    service.get_session_context = AsyncMock(return_value={
        "topics_discussed": ["physics", "Newton's laws"],
        "turn_count": 5,
        "current_topic": "forces",
        "learning_state": "engaged",
        "key_discoveries": [
            {"discovery": "Understood F=ma", "topic": "Newton's second law", "turn": 3}
        ]
    })

    return service


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for tests."""
    return {
        "id": TEST_USER_ID,
        "username": "test_student",
        "email": "student@scoratis.test",
        "hashed_password": "hashed_test_password_123",
        "preferences": {"theme": "light", "subject": "physics"}
    }


@pytest.fixture
def sample_document_data() -> Dict[str, Any]:
    """Sample document data for tests."""
    return {
        "id": 1,
        "user_id": TEST_USER_ID,
        "title": "Introduction to Physics",
        "content": """
        Chapter 1: Newton's Laws of Motion

        Newton's First Law (Law of Inertia):
        An object at rest stays at rest and an object in motion stays in motion
        with the same speed and in the same direction unless acted upon by an
        unbalanced force.

        Newton's Second Law:
        The acceleration of an object depends on the mass of the object and the
        amount of force applied. F = ma (Force equals mass times acceleration).

        Newton's Third Law:
        For every action, there is an equal and opposite reaction.
        """,
        "source_type": "upload",
        "file_type": "txt",
        "file_size": 2048,
        "status": "completed",
        "subject": "physics"
    }


@pytest.fixture
def sample_chunks_data(sample_document_data) -> List[Dict[str, Any]]:
    """Sample chunk data for tests."""
    return [
        {
            "id": 101,
            "document_id": sample_document_data["id"],
            "content": "Newton's First Law (Law of Inertia): An object at rest stays at rest and an object in motion stays in motion with the same speed and in the same direction unless acted upon by an unbalanced force.",
            "chunk_index": 0,
            "embedding": np.random.rand(EMBEDDING_DIMENSION).tolist(),
            "chunk_metadata": {"start_char": 0, "end_char": 200, "page": 1}
        },
        {
            "id": 102,
            "document_id": sample_document_data["id"],
            "content": "Newton's Second Law: The acceleration of an object depends on the mass of the object and the amount of force applied. F = ma (Force equals mass times acceleration).",
            "chunk_index": 1,
            "embedding": np.random.rand(EMBEDDING_DIMENSION).tolist(),
            "chunk_metadata": {"start_char": 200, "end_char": 400, "page": 1}
        },
        {
            "id": 103,
            "document_id": sample_document_data["id"],
            "content": "Newton's Third Law: For every action, there is an equal and opposite reaction.",
            "chunk_index": 2,
            "embedding": np.random.rand(EMBEDDING_DIMENSION).tolist(),
            "chunk_metadata": {"start_char": 400, "end_char": 500, "page": 1}
        }
    ]


@pytest.fixture
def sample_journal_data() -> Dict[str, Any]:
    """Sample journal entry for tests."""
    return {
        "id": 1,
        "user_id": TEST_USER_ID,
        "title": "My Physics Learning Notes",
        "content": """
        Today I learned about Newton's laws of motion. The key insight is that
        F=ma connects force, mass, and acceleration. This explains why heavier
        objects need more force to accelerate.

        Questions to explore:
        - How does friction affect these laws?
        - What about objects in space with no gravity?
        """,
        "folder_id": None,
        "metadata": {"tags": ["physics", "newton", "learning"]},
        "embedding": np.random.rand(EMBEDDING_DIMENSION).tolist()
    }


@pytest.fixture
def sample_conversation_messages() -> List[Dict[str, Any]]:
    """Sample conversation messages for tests."""
    return [
        {
            "role": "user",
            "content": "I want to learn about Newton's laws of motion"
        },
        {
            "role": "assistant",
            "content": "Great choice! Newton's laws form the foundation of classical mechanics. Let's start with a question: Have you ever wondered why a ball keeps rolling after you push it? What do you think keeps it moving?"
        },
        {
            "role": "user",
            "content": "Is it because of inertia?"
        },
        {
            "role": "assistant",
            "content": "Exactly! You've identified Newton's First Law - the Law of Inertia. An object in motion tends to stay in motion unless acted upon by an external force. What external forces might eventually stop the ball?"
        },
        {
            "role": "user",
            "content": "Friction and air resistance?"
        }
    ]


# =============================================================================
# Agent Fixtures
# =============================================================================

@pytest.fixture
def mock_agent(mock_llm_service, mock_rag_service, mock_web_search_service):
    """Create a mock agent for testing."""
    agent = MagicMock()

    async def mock_invoke(session_id, message, **kwargs):
        return {
            "response": f"Test response to: {message[:50]}...",
            "sources": [],
            "tools_used": [],
            "model": "test-model",
            "session_id": session_id
        }

    agent.invoke = AsyncMock(side_effect=mock_invoke)

    async def mock_stream(session_id, message, **kwargs):
        yield {"type": "sources", "sources": []}
        yield {"type": "token", "content": "Test "}
        yield {"type": "token", "content": "response"}
        yield {"type": "done", "response": "Test response", "metadata": {}}

    agent.stream = mock_stream

    return agent


@pytest.fixture
def query_classifier():
    """Create a real query classifier instance."""
    from services.agent.query_classifier import QueryClassifier
    return QueryClassifier()


@pytest.fixture
def quick_verifier():
    """Create a real quick verifier instance."""
    from services.agent.verifier import QuickVerifier
    return QuickVerifier(min_length=50, max_length=5000)


# =============================================================================
# Golden Dataset Fixtures
# =============================================================================

@pytest.fixture
def golden_dataset():
    """Golden dataset for agent evaluation."""
    from evaluation.golden_dataset import GOLDEN_DATASET
    return GOLDEN_DATASET


@pytest.fixture
def simple_golden_cases():
    """Simplified golden test cases for quick tests."""
    return [
        {
            "id": "quick_001",
            "query": "What is machine learning?",
            "expected_topics": ["machine learning", "AI"],
            "min_length": 50,
            "category": "definitions"
        },
        {
            "id": "quick_002",
            "query": "Hello!",
            "expected_topics": [],
            "min_length": 10,
            "category": "greetings"
        },
        {
            "id": "quick_003",
            "query": "What's in my notes about physics?",
            "expected_topics": ["physics", "notes"],
            "min_length": 30,
            "category": "personal_knowledge",
            "requires_rag": True
        }
    ]


# =============================================================================
# Environment Setup
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()

    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LOG_LEVEL"] = "WARNING"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture and analyze logs."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def timer():
    """Fixture to time test execution."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return 0

    return Timer()


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_files():
    """Clean up test database and files after all tests."""
    yield

    # Cleanup
    import glob
    test_files = glob.glob("*.db") + glob.glob("test_*.db")
    for f in test_files:
        try:
            os.remove(f)
        except:
            pass
