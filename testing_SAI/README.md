# Scoratis AI Testing Suite

Comprehensive test suite for the Scoratis AI Socratic Learning Platform.

## Directory Structure

```
testing_SAI/
├── pytest.ini              # Pytest configuration
├── conftest.py             # Global fixtures and test setup
├── README.md               # This file
│
├── unit/                   # Unit tests (fast, isolated)
│   ├── test_query_classifier.py
│   ├── test_agent_state.py
│   ├── test_verifier.py
│   └── test_agent_tools.py
│
├── integration/            # Integration tests
│   ├── test_agent_graph.py
│   └── test_rag_pipeline.py
│
├── evaluation/             # Quality evaluation tests
│   ├── evaluator.py
│   ├── golden_dataset.py
│   └── test_agent_evaluation.py
│
├── e2e/                    # End-to-end tests
│   └── test_full_workflow.py
│
└── fixtures/               # Test data and fixtures
    ├── sample_documents/
    │   ├── physics_notes.txt
    │   ├── biology_chapter.md
    │   └── chemistry_summary.md
    ├── sample_embeddings.json
    └── sample_conversations.json
```

## Running Tests

### All Tests
```bash
cd testing_SAI
pytest
```

### By Category (using markers)
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Evaluation tests
pytest -m evaluation

# End-to-end tests
pytest -m e2e

# RAG-related tests
pytest -m rag

# Agent-related tests
pytest -m agent

# Tool-related tests
pytest -m tools
```

### Skip Slow Tests
```bash
pytest -m "not slow"
```

### Run Specific Test File
```bash
pytest unit/test_query_classifier.py
pytest integration/test_rag_pipeline.py -v
```

### Run with Coverage
```bash
pytest --cov=backend --cov-report=html
```

## Test Categories

### Unit Tests (`unit/`)
Fast, isolated tests for individual components:
- **test_query_classifier.py**: Tests for trivial vs substantive query classification
- **test_agent_state.py**: Tests for Scratchpad, StopCondition, SearchTrail, AgentPhase
- **test_verifier.py**: Tests for QuickVerifier and ResponseVerifier
- **test_agent_tools.py**: Tests for tool definitions and registry

### Integration Tests (`integration/`)
Tests for component interactions:
- **test_agent_graph.py**: LangGraph state machine, node transitions, tool execution
- **test_rag_pipeline.py**: Document ingestion, embedding, hybrid search, RRF fusion

### Evaluation Tests (`evaluation/`)
Quality assessment tests:
- **test_agent_evaluation.py**: Tool selection accuracy, Socratic method quality, citation usage
- **golden_dataset.py**: Reference test cases with expected behaviors

### E2E Tests (`e2e/`)
Full workflow tests:
- **test_full_workflow.py**: Complete chat sessions, RAG integration, error recovery

## Fixtures

### Mock Services (in conftest.py)
- `mock_llm_service`: Mocked LLM for predictable responses
- `mock_rag_service`: Mocked RAG service with sample data
- `mock_embedding_service`: Mocked embeddings (384 dimensions)
- `mock_web_search_service`: Mocked web search results
- `mock_empty_rag_service`: RAG service returning empty results

### Sample Data (in fixtures/)
- **sample_documents/**: Real content for testing document processing
- **sample_embeddings.json**: Pre-computed embeddings for search tests
- **sample_conversations.json**: Sample chat histories

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests |
| `@pytest.mark.integration` | Integration tests |
| `@pytest.mark.evaluation` | Quality evaluation tests |
| `@pytest.mark.e2e` | End-to-end tests |
| `@pytest.mark.slow` | Tests that take longer to run |
| `@pytest.mark.rag` | RAG-related tests |
| `@pytest.mark.agent` | Agent-related tests |
| `@pytest.mark.tools` | Tool-related tests |
| `@pytest.mark.asyncio` | Async tests |

## Writing New Tests

### Unit Test Example
```python
import pytest
from services.agent.query_classifier import QueryClassifier

class TestMyComponent:
    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_some_behavior(self, classifier):
        result = classifier.classify("Hello")
        assert result == "trivial"
```

### Integration Test Example
```python
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

class TestMyIntegration:
    async def test_component_interaction(self, mock_llm_service, mock_rag_service):
        # Test multiple components working together
        pass
```

### Using Fixtures
```python
def test_with_sample_data(self, sample_document, sample_chunks):
    # sample_document and sample_chunks are defined in conftest.py
    assert sample_document["title"] == "Test Physics Notes"
```

## Environment Setup

1. Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

2. Set environment variables (optional):
```bash
export TEST_DATABASE_URL="postgresql://test:test@localhost/test_db"
```

3. Run tests:
```bash
cd testing_SAI
pytest -v
```

## CI/CD Integration

Example GitHub Actions workflow:
```yaml
- name: Run Tests
  run: |
    cd testing_SAI
    pytest -m "not slow" --cov=backend --cov-report=xml
```

## Troubleshooting

### Import Errors
Tests automatically add `backend/` to the Python path. If you see import errors:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../backend"
```

### Async Test Issues
Ensure `pytest-asyncio` is installed and tests are marked with `@pytest.mark.asyncio`.

### Database Tests
Integration tests use mocked database sessions. For real DB tests, ensure test database is configured.
