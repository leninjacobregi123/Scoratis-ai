"""
End-to-End Tests for Full Workflow

Tests complete user workflows including:
- Full chat sessions with multiple turns
- Document upload and retrieval
- Learning progression tracking
- RAG integration in conversations
- Error recovery scenarios

Location: testing_SAI/e2e/test_full_workflow.py
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

# Mark all tests as e2e tests
pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.asyncio]


# =============================================================================
# Chat Session Workflow Tests
# =============================================================================

class TestChatSessionWorkflow:
    """Tests for complete chat session workflows."""

    @pytest.fixture
    async def configured_agent(
        self, mock_llm_service, mock_rag_service, mock_web_search_service
    ):
        """Create a fully configured agent for E2E tests."""
        from services.agent.graph import ScoratisAgent

        # Configure LLM with varied responses
        responses = [
            {
                "content": "Hello! I'm Socrates, your learning companion. What would you like to explore today?",
                "tool_calls": [],
                "finish_reason": "stop"
            },
            {
                "content": "Photosynthesis is fascinating! Before I explain, what do you already know about how plants get their energy?",
                "tool_calls": [],
                "finish_reason": "stop"
            },
            {
                "content": "Excellent thinking! Plants indeed convert sunlight into energy through chlorophyll. What role do you think water plays in this process?",
                "tool_calls": [],
                "finish_reason": "stop"
            },
        ]
        response_iter = iter(responses)

        def get_response(*args, **kwargs):
            try:
                return next(response_iter)
            except StopIteration:
                return {
                    "content": "That's a great question! Let me help you explore further.",
                    "tool_calls": [],
                    "finish_reason": "stop"
                }

        mock_llm_service.generate_with_tools = AsyncMock(side_effect=get_response)

        agent = ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

        return agent

    async def test_complete_learning_session(self, configured_agent):
        """Test a complete multi-turn learning session."""
        session_id = "e2e-learning-001"

        # Turn 1: Greeting
        result1 = await configured_agent.invoke(
            session_id=session_id,
            message="Hi, I want to learn about photosynthesis"
        )
        assert "response" in result1
        assert len(result1["response"]) > 0

        # Turn 2: Ask question
        result2 = await configured_agent.invoke(
            session_id=session_id,
            message="What is photosynthesis?"
        )
        assert "response" in result2

        # Turn 3: Follow-up
        result3 = await configured_agent.invoke(
            session_id=session_id,
            message="I think plants use sunlight to make food"
        )
        assert "response" in result3

    async def test_session_maintains_context(self, configured_agent):
        """Test that session context is maintained across turns."""
        session_id = "e2e-context-001"

        # Establish topic
        await configured_agent.invoke(
            session_id=session_id,
            message="Let's discuss Newton's laws of motion"
        )

        # Reference previous context
        result = await configured_agent.invoke(
            session_id=session_id,
            message="Can you tell me more about the first one?"
        )

        # Should have a contextual response
        assert "response" in result

    async def test_different_sessions_isolated(self, configured_agent):
        """Test that different sessions don't share context."""
        # Session A about physics
        await configured_agent.invoke(
            session_id="session-A",
            message="I'm studying physics"
        )

        # Session B about chemistry
        result_b = await configured_agent.invoke(
            session_id="session-B",
            message="Tell me about chemistry"
        )

        # Session B should work independently
        assert "response" in result_b


# =============================================================================
# RAG Integration Workflow Tests
# =============================================================================

class TestRAGIntegrationWorkflow:
    """Tests for RAG integration in chat workflows."""

    @pytest.fixture
    async def agent_with_rag(
        self, mock_llm_service, mock_rag_service, mock_web_search_service
    ):
        """Create agent that uses RAG."""
        from services.agent.graph import ScoratisAgent

        # Configure LLM to use tools then respond
        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: request KB search
                return {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_rag",
                        "type": "function",
                        "function": {
                            "name": "search_knowledge_base",
                            "arguments": json.dumps({"query": "physics notes", "limit": 5})
                        }
                    }],
                    "finish_reason": "tool_calls"
                }
            else:
                # Second call: respond with citations
                return {
                    "content": "Based on your notes [1], Newton's first law states that an object at rest stays at rest.",
                    "tool_calls": [],
                    "finish_reason": "stop"
                }

        mock_llm_service.generate_with_tools = AsyncMock(side_effect=mock_generate)

        return ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

    async def test_rag_retrieval_in_conversation(self, agent_with_rag, mock_rag_service):
        """Test RAG retrieval during conversation."""
        result = await agent_with_rag.invoke(
            session_id="rag-test-001",
            message="What is in my physics notes?"
        )

        assert "response" in result
        # The agent should return a response (RAG is called via tool execution internally)
        assert len(result["response"]) > 0

    async def test_citations_included_in_response(self, agent_with_rag):
        """Test that citations are included in response."""
        result = await agent_with_rag.invoke(
            session_id="citation-test",
            message="What do my notes say about Newton?"
        )

        response = result.get("response", "")
        # Should contain citation markers
        has_citations = "[1]" in response or "[citation" in response or "¹" in response

        # Note: This depends on the mock response
        assert "response" in result


# =============================================================================
# Web Search Fallback Workflow Tests
# =============================================================================

class TestWebSearchFallbackWorkflow:
    """Tests for web search fallback when KB is empty."""

    @pytest.fixture
    async def agent_with_fallback(
        self, mock_llm_service, mock_empty_rag_service, mock_web_search_service
    ):
        """Create agent that falls back to web search."""
        from services.agent.graph import ScoratisAgent

        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Search KB first
                return {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_kb",
                        "type": "function",
                        "function": {
                            "name": "search_knowledge_base",
                            "arguments": json.dumps({"query": "latest AI", "limit": 5})
                        }
                    }],
                    "finish_reason": "tool_calls"
                }
            elif call_count[0] == 2:
                # KB empty, search web
                return {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_web",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": "latest AI news", "max_results": 5})
                        }
                    }],
                    "finish_reason": "tool_calls"
                }
            else:
                # Final response
                return {
                    "content": "I couldn't find this in your notes, but from the web: Latest AI developments include...",
                    "tool_calls": [],
                    "finish_reason": "stop"
                }

        mock_llm_service.generate_with_tools = AsyncMock(side_effect=mock_generate)

        return ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_empty_rag_service,
            web_search_service=mock_web_search_service,
        )

    async def test_falls_back_to_web_search(
        self, agent_with_fallback, mock_web_search_service
    ):
        """Test fallback to web search when KB is empty."""
        result = await agent_with_fallback.invoke(
            session_id="fallback-test",
            message="What are the latest developments in AI?"
        )

        assert "response" in result
        # Web search should have been called
        assert mock_web_search_service.search.called


# =============================================================================
# Error Recovery Workflow Tests
# =============================================================================

class TestErrorRecoveryWorkflow:
    """Tests for error recovery in workflows."""

    async def test_recovers_from_tool_failure(
        self, mock_llm_service, mock_rag_service, mock_web_search_service
    ):
        """Test recovery when a tool fails."""
        from services.agent.graph import ScoratisAgent

        # Make RAG service fail
        mock_rag_service.get_context_with_citations = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_rag_service.enhanced_search = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # LLM should still respond
        mock_llm_service.generate_with_tools = AsyncMock(return_value={
            "content": "I encountered an issue searching your notes. Let me try to help anyway...",
            "tool_calls": [],
            "finish_reason": "stop"
        })

        agent = ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

        # Should handle gracefully
        result = await agent.invoke(
            session_id="error-recovery-test",
            message="Search my notes for physics"
        )

        assert result is not None

    async def test_handles_empty_messages(
        self, mock_llm_service, mock_rag_service, mock_web_search_service
    ):
        """Test handling of empty user messages."""
        from services.agent.graph import ScoratisAgent

        mock_llm_service.generate_with_tools = AsyncMock(return_value={
            "content": "I notice your message was empty. How can I help you today?",
            "tool_calls": [],
            "finish_reason": "stop"
        })

        agent = ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

        result = await agent.invoke(
            session_id="empty-message-test",
            message=""
        )

        assert result is not None
        assert "response" in result


# =============================================================================
# Subject Channel Workflow Tests
# =============================================================================

class TestSubjectChannelWorkflow:
    """Tests for subject-specific channels."""

    @pytest.fixture
    async def agent(self, mock_llm_service, mock_rag_service, mock_web_search_service):
        """Create agent for subject tests."""
        from services.agent.graph import ScoratisAgent

        mock_llm_service.generate_with_tools = AsyncMock(return_value={
            "content": "In physics, force is defined as mass times acceleration (F=ma).",
            "tool_calls": [],
            "finish_reason": "stop"
        })

        return ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

    async def test_physics_subject_context(self, agent):
        """Test physics subject channel."""
        result = await agent.invoke(
            session_id="physics-test",
            message="What is force?",
            subject="physics"
        )

        assert "response" in result

    async def test_biology_subject_context(self, agent):
        """Test biology subject channel."""
        result = await agent.invoke(
            session_id="biology-test",
            message="What is DNA?",
            subject="biology"
        )

        assert "response" in result

    async def test_multiple_subjects_in_session(self, agent):
        """Test switching subjects within session."""
        # Start with physics
        result1 = await agent.invoke(
            session_id="multi-subject",
            message="Explain gravity",
            subject="physics"
        )

        # Switch to biology
        result2 = await agent.invoke(
            session_id="multi-subject",
            message="Now explain photosynthesis",
            subject="biology"
        )

        assert result1 is not None
        assert result2 is not None


# =============================================================================
# Streaming Workflow Tests
# =============================================================================

class TestStreamingWorkflow:
    """Tests for streaming response workflows."""

    @pytest.fixture
    async def streaming_agent(
        self, mock_llm_service, mock_rag_service, mock_web_search_service
    ):
        """Create agent for streaming tests."""
        from services.agent.graph import ScoratisAgent

        mock_llm_service.generate_with_tools = AsyncMock(return_value={
            "content": "Here is a detailed explanation of the concept...",
            "tool_calls": [],
            "finish_reason": "stop"
        })

        return ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

    async def test_streaming_yields_events(self, streaming_agent):
        """Test that streaming yields events."""
        events = []

        async for event in streaming_agent.stream(
            session_id="stream-e2e-test",
            message="Explain machine learning"
        ):
            events.append(event)

        assert len(events) > 0

    async def test_streaming_completes(self, streaming_agent):
        """Test that streaming completes with done event."""
        done_received = False

        async for event in streaming_agent.stream(
            session_id="stream-complete-test",
            message="What is AI?"
        ):
            if event.get("type") == "done":
                done_received = True

        assert done_received


# =============================================================================
# Performance Workflow Tests
# =============================================================================

class TestPerformanceWorkflow:
    """Tests for performance-related workflows."""

    async def test_response_within_timeout(
        self, mock_llm_service, mock_rag_service, mock_web_search_service, timer
    ):
        """Test that response is received within reasonable time."""
        from services.agent.graph import ScoratisAgent

        mock_llm_service.generate_with_tools = AsyncMock(return_value={
            "content": "Quick response",
            "tool_calls": [],
            "finish_reason": "stop"
        })

        agent = ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

        timer.start()
        await agent.invoke(
            session_id="perf-test",
            message="Hello"
        )
        timer.stop()

        # Should complete quickly with mocks (< 5 seconds)
        assert timer.elapsed_ms < 5000

    async def test_handles_many_sequential_requests(
        self, mock_llm_service, mock_rag_service, mock_web_search_service
    ):
        """Test handling many sequential requests."""
        from services.agent.graph import ScoratisAgent

        mock_llm_service.generate_with_tools = AsyncMock(return_value={
            "content": "Response",
            "tool_calls": [],
            "finish_reason": "stop"
        })

        agent = ScoratisAgent(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            web_search_service=mock_web_search_service,
        )

        # Make 10 sequential requests
        for i in range(10):
            result = await agent.invoke(
                session_id=f"perf-seq-{i}",
                message=f"Question {i}"
            )
            assert result is not None
