"""
Unit Tests for Agent Tools

Tests the agent tool definitions and factories:
- Tool schema generation
- Tool factory functions
- Tool execution
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


class TestToolDefinition:
    """Tests for ToolDefinition class."""

    def test_tool_definition_to_openai_schema(self):
        """Test conversion to OpenAI function schema."""
        from services.agent.tools import (
            ToolDefinition,
            ToolParameter,
            ToolCategory,
        )

        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.KNOWLEDGE,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query",
                    required=True
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Max results",
                    required=False,
                    default=5
                )
            ],
            factory=lambda: None
        )

        schema = tool.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert "query" in schema["function"]["parameters"]["properties"]
        assert "limit" in schema["function"]["parameters"]["properties"]
        assert "query" in schema["function"]["parameters"]["required"]
        assert "limit" not in schema["function"]["parameters"]["required"]


class TestToolRegistry:
    """Tests for the tool registry."""

    def test_tool_registry_not_empty(self):
        """Test that tool registry has tools."""
        from services.agent.tools import TOOL_REGISTRY

        assert len(TOOL_REGISTRY) > 0

    def test_get_tool_by_name(self):
        """Test getting tool by name."""
        from services.agent.tools import get_tool_by_name

        tool = get_tool_by_name("search_knowledge_base")
        assert tool is not None
        assert tool.name == "search_knowledge_base"

    def test_get_tool_by_name_not_found(self):
        """Test getting non-existent tool."""
        from services.agent.tools import get_tool_by_name

        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        from services.agent.tools import get_tools_by_category, ToolCategory

        knowledge_tools = get_tools_by_category(ToolCategory.KNOWLEDGE)
        assert len(knowledge_tools) > 0
        assert all(t.category == ToolCategory.KNOWLEDGE for t in knowledge_tools)

    def test_get_all_tool_schemas(self):
        """Test getting all tool schemas."""
        from services.agent.tools import get_all_tool_schemas

        schemas = get_all_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) > 0
        assert all("type" in s and s["type"] == "function" for s in schemas)


class TestSearchKnowledgeBaseTool:
    """Tests for search_knowledge_base tool."""

    @pytest.fixture
    def tool_function(self, mock_rag_service):
        """Create search_knowledge_base tool function."""
        from services.agent.tools import create_search_knowledge_base_tool

        mock_db = AsyncMock()
        return create_search_knowledge_base_tool(mock_db, mock_rag_service, user_id=1)

    @pytest.mark.asyncio
    async def test_search_returns_results(self, tool_function, mock_rag_service):
        """Test that search returns results."""
        result = await tool_function(query="machine learning", limit=5)

        assert result["success"] is True
        assert "sources" in result
        assert "query" in result
        # create_search_knowledge_base_tool() prefers enhanced_search() over
        # get_context_with_citations() whenever the rag_service has it (real
        # RAGService always does) - that's the path a default call (use_enhanced
        # defaults to True) actually takes, not the plain fallback.
        mock_rag_service.enhanced_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_handles_error(self, mock_rag_service):
        """Test that search handles errors gracefully."""
        from services.agent.tools import create_search_knowledge_base_tool

        mock_rag_service.enhanced_search.side_effect = Exception("DB Error")
        mock_db = AsyncMock()

        tool = create_search_knowledge_base_tool(mock_db, mock_rag_service, user_id=1)
        result = await tool(query="test", limit=5)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_converts_limit_to_int(self, tool_function):
        """Test that limit parameter is converted to integer."""
        # Should not raise even if limit comes as string
        result = await tool_function(query="test", limit="5")
        assert result["success"] is True


class TestWebSearchTool:
    """Tests for web_search tool."""

    @pytest.fixture
    def tool_function(self, mock_web_search_service):
        """Create web_search tool function."""
        from services.agent.tools import create_web_search_tool
        return create_web_search_tool(mock_web_search_service)

    @pytest.mark.asyncio
    async def test_web_search_returns_results(self, tool_function, mock_web_search_service):
        """Test that web search returns results."""
        result = await tool_function(query="latest AI news", max_results=5)

        assert result["success"] is True
        assert "results" in result
        mock_web_search_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_web_search_handles_error(self, mock_web_search_service):
        """Test that web search handles errors."""
        from services.agent.tools import create_web_search_tool

        mock_web_search_service.search.side_effect = Exception("Network Error")
        tool = create_web_search_tool(mock_web_search_service)

        result = await tool(query="test")
        assert result["success"] is False
        assert "error" in result


class TestAgenticTools:
    """Tests for agentic loop tools (think, plan, finalize)."""

    @pytest.mark.asyncio
    async def test_think_tool(self):
        """Test the think tool for reasoning."""
        from services.agent.tools import create_think_tool

        think = create_think_tool()
        result = await think(
            thought="I need to search the knowledge base first",
            confidence=0.7,
            needs_more_info=True
        )

        assert result["success"] is True
        assert result["thought_recorded"] is True
        assert result["confidence"] == 0.7
        assert result["needs_more_info"] is True

    @pytest.mark.asyncio
    async def test_plan_tool(self):
        """Test the plan tool for task planning."""
        from services.agent.tools import create_plan_tool

        plan = create_plan_tool()
        result = await plan(
            goal="Explain photosynthesis",
            steps=["Search knowledge base", "Build explanation", "Add examples"],
            current_step=0
        )

        assert result["success"] is True
        assert result["plan_created"] is True
        assert result["total_steps"] == 3
        assert result["current_step"] == 0
        assert "Search knowledge base" in result["next_step"]

    @pytest.mark.asyncio
    async def test_finalize_response_tool(self):
        """Test the finalize_response tool."""
        from services.agent.tools import create_finalize_response_tool

        finalize = create_finalize_response_tool()
        result = await finalize(
            response="Here is my final answer...",
            confidence=0.9,
            verification_passed=True
        )

        assert result["success"] is True
        assert result["finalized"] is True
        assert result["confidence"] == 0.9
        assert result["verification_passed"] is True

    @pytest.mark.asyncio
    async def test_verify_response_tool_without_verifier(self):
        """Test verify_response tool without verifier (fallback mode)."""
        from services.agent.tools import create_verify_response_tool

        verify = create_verify_response_tool(verifier=None)
        result = await verify(
            response="Test response about photosynthesis",
            query="What is photosynthesis?",
            check_facts=True
        )

        assert result["success"] is True
        assert "mode" in result
        assert result["mode"] == "quick"
