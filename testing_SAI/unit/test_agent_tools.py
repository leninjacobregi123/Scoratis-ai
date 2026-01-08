"""
Unit Tests for Agent Tools

Tests the tool definitions and factory functions:
- Tool schema generation (OpenAI format)
- Tool factory functions
- Tool execution
- Tool registry operations

Location: testing_SAI/unit/test_agent_tools.py
"""

import pytest
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from services.agent.tools import (
    ToolDefinition,
    ToolParameter,
    ToolCategory,
    TOOL_REGISTRY,
    get_tool_by_name,
    get_tools_by_category,
    get_all_tool_schemas,
    create_search_knowledge_base_tool,
    create_search_journals_tool,
    create_web_search_tool,
    create_think_tool,
    create_plan_tool,
    create_finalize_response_tool,
    create_verify_response_tool,
    create_request_clarification_tool,
    create_delegate_tool,
)

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# ToolDefinition Tests
# =============================================================================

class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""

    def test_tool_definition_creation(self):
        """Test creating a tool definition."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool for testing",
            category=ToolCategory.KNOWLEDGE,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                )
            ],
            factory=lambda: None
        )

        assert tool.name == "test_tool"
        assert tool.category == ToolCategory.KNOWLEDGE
        assert len(tool.parameters) == 1

    def test_tool_definition_to_openai_schema(self):
        """Test conversion to OpenAI function schema."""
        tool = ToolDefinition(
            name="search_tool",
            description="Search for information",
            category=ToolCategory.SEARCH,
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

        # Check structure
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search_tool"
        assert "Search for information" in schema["function"]["description"]

        # Check parameters
        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "query" in params["properties"]
        assert "limit" in params["properties"]
        assert "query" in params["required"]
        assert "limit" not in params["required"]

    def test_tool_with_enum_parameter(self):
        """Test tool with enum parameter."""
        tool = ToolDefinition(
            name="enum_tool",
            description="Tool with enum",
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(
                    name="quality",
                    type="string",
                    description="Quality level",
                    required=True,
                    enum=["low", "medium", "high"]
                )
            ],
            factory=lambda: None
        )

        schema = tool.to_openai_schema()
        quality_param = schema["function"]["parameters"]["properties"]["quality"]

        assert "enum" in quality_param
        assert quality_param["enum"] == ["low", "medium", "high"]


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolRegistry:
    """Tests for the tool registry."""

    def test_registry_not_empty(self):
        """Registry should have tools."""
        assert len(TOOL_REGISTRY) > 0

    def test_registry_has_required_tools(self):
        """Registry should have essential tools."""
        required_tools = [
            "search_knowledge_base",
            "search_journals",
            "web_search",
            "think",
            "plan",
            "finalize_response",
        ]

        tool_names = [t.name for t in TOOL_REGISTRY]

        for tool_name in required_tools:
            assert tool_name in tool_names, f"Missing required tool: {tool_name}"

    def test_get_tool_by_name(self):
        """Test getting tool by name."""
        tool = get_tool_by_name("search_knowledge_base")

        assert tool is not None
        assert tool.name == "search_knowledge_base"
        assert tool.category == ToolCategory.KNOWLEDGE

    def test_get_tool_by_name_not_found(self):
        """Test getting non-existent tool returns None."""
        tool = get_tool_by_name("nonexistent_tool_xyz")

        assert tool is None

    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        knowledge_tools = get_tools_by_category(ToolCategory.KNOWLEDGE)

        assert len(knowledge_tools) > 0
        assert all(t.category == ToolCategory.KNOWLEDGE for t in knowledge_tools)

    def test_get_all_tool_schemas(self):
        """Test getting all tool schemas."""
        schemas = get_all_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) > 0
        assert all(s["type"] == "function" for s in schemas)
        assert all("function" in s for s in schemas)


# =============================================================================
# Search Knowledge Base Tool Tests
# =============================================================================

class TestSearchKnowledgeBaseTool:
    """Tests for search_knowledge_base tool."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def tool_function(self, mock_db, mock_rag_service):
        """Create the tool function."""
        return create_search_knowledge_base_tool(
            db_session=mock_db,
            rag_service=mock_rag_service,
            user_id=1,
            subject="physics"
        )

    @pytest.mark.asyncio
    async def test_search_returns_success(self, tool_function, mock_rag_service):
        """Test successful search."""
        result = await tool_function(query="Newton's laws", limit=5)

        assert result["success"] is True
        assert "sources" in result
        assert "query" in result
        assert result["query"] == "Newton's laws"

    @pytest.mark.asyncio
    async def test_search_calls_rag_service(self, tool_function, mock_rag_service):
        """Test that RAG service is called."""
        await tool_function(query="test query", limit=3)

        # Should call either get_context_with_citations or enhanced_search
        assert (
            mock_rag_service.get_context_with_citations.called or
            mock_rag_service.enhanced_search.called
        )

    @pytest.mark.asyncio
    async def test_search_handles_error(self, mock_db, mock_rag_service):
        """Test error handling."""
        mock_rag_service.get_context_with_citations.side_effect = Exception("DB Error")
        mock_rag_service.enhanced_search.side_effect = Exception("DB Error")

        tool = create_search_knowledge_base_tool(mock_db, mock_rag_service, user_id=1)
        result = await tool(query="test", limit=5)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_converts_limit_to_int(self, tool_function):
        """Test limit parameter conversion."""
        # Should not raise even if limit is string
        result = await tool_function(query="test", limit="5")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_db, mock_empty_rag_service):
        """Test handling of empty results."""
        tool = create_search_knowledge_base_tool(
            mock_db, mock_empty_rag_service, user_id=1
        )
        result = await tool(query="nonexistent topic", limit=5)

        assert result["success"] is True
        assert result["results_count"] == 0
        assert "NO_RESULTS" in result.get("message", "")


# =============================================================================
# Search Journals Tool Tests
# =============================================================================

class TestSearchJournalsTool:
    """Tests for search_journals tool."""

    @pytest.fixture
    def tool_function(self, mock_rag_service):
        mock_db = AsyncMock()
        return create_search_journals_tool(mock_db, mock_rag_service, user_id=1)

    @pytest.mark.asyncio
    async def test_journal_search_success(self, tool_function, mock_rag_service):
        """Test successful journal search."""
        result = await tool_function(query="learning notes", limit=5)

        assert result["success"] is True
        assert "journals" in result
        mock_rag_service.search_journals.assert_called_once()

    @pytest.mark.asyncio
    async def test_journal_search_handles_error(self, mock_rag_service):
        """Test error handling."""
        mock_db = AsyncMock()
        mock_rag_service.search_journals.side_effect = Exception("Search failed")

        tool = create_search_journals_tool(mock_db, mock_rag_service, user_id=1)
        result = await tool(query="test", limit=5)

        assert result["success"] is False
        assert "error" in result


# =============================================================================
# Web Search Tool Tests
# =============================================================================

class TestWebSearchTool:
    """Tests for web_search tool."""

    @pytest.fixture
    def tool_function(self, mock_web_search_service):
        return create_web_search_tool(mock_web_search_service)

    @pytest.mark.asyncio
    async def test_web_search_success(self, tool_function, mock_web_search_service):
        """Test successful web search."""
        result = await tool_function(query="latest AI news", max_results=5)

        assert result["success"] is True
        assert "results" in result
        assert result["results_count"] > 0
        mock_web_search_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_web_search_handles_error(self, mock_web_search_service):
        """Test error handling."""
        mock_web_search_service.search.side_effect = Exception("Network error")

        tool = create_web_search_tool(mock_web_search_service)
        result = await tool(query="test")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_web_search_empty_results(self, mock_empty_web_search_service):
        """Test handling empty results."""
        tool = create_web_search_tool(mock_empty_web_search_service)
        result = await tool(query="very specific query")

        assert result["success"] is True
        assert result["results_count"] == 0
        assert "NO_RESULTS" in result.get("message", "")


# =============================================================================
# Agentic Tools Tests
# =============================================================================

class TestThinkTool:
    """Tests for think tool."""

    @pytest.mark.asyncio
    async def test_think_records_thought(self):
        """Test thinking tool records thought."""
        think = create_think_tool()
        result = await think(
            thought="I need to search the knowledge base first",
            confidence=0.7,
            needs_more_info=True
        )

        assert result["success"] is True
        assert result["thought_recorded"] is True
        assert result["thought"] == "I need to search the knowledge base first"
        assert result["confidence"] == 0.7
        assert result["needs_more_info"] is True

    @pytest.mark.asyncio
    async def test_think_default_values(self):
        """Test think with default values."""
        think = create_think_tool()
        result = await think(thought="Simple thought")

        assert result["success"] is True
        assert result["confidence"] == 0.5
        assert result["needs_more_info"] is False


class TestPlanTool:
    """Tests for plan tool."""

    @pytest.mark.asyncio
    async def test_plan_creation(self):
        """Test plan creation."""
        plan = create_plan_tool()
        result = await plan(
            goal="Explain photosynthesis",
            steps=["Search knowledge base", "Analyze results", "Build explanation"],
            current_step=0
        )

        assert result["success"] is True
        assert result["plan_created"] is True
        assert result["goal"] == "Explain photosynthesis"
        assert result["total_steps"] == 3
        assert result["current_step"] == 0
        assert "Search knowledge base" in result["next_step"]

    @pytest.mark.asyncio
    async def test_plan_step_progression(self):
        """Test plan step progression."""
        plan = create_plan_tool()

        result = await plan(
            goal="Test goal",
            steps=["Step 1", "Step 2", "Step 3"],
            current_step=2
        )

        assert result["current_step"] == 2
        assert "Step 3" in result["next_step"]

    @pytest.mark.asyncio
    async def test_plan_complete(self):
        """Test plan completion."""
        plan = create_plan_tool()

        result = await plan(
            goal="Test goal",
            steps=["Step 1"],
            current_step=1  # Beyond last step
        )

        assert "complete" in result["next_step"].lower()


class TestFinalizeResponseTool:
    """Tests for finalize_response tool."""

    @pytest.mark.asyncio
    async def test_finalize_response(self):
        """Test response finalization."""
        finalize = create_finalize_response_tool()
        result = await finalize(
            response="Here is my complete answer about photosynthesis...",
            confidence=0.9,
            verification_passed=True
        )

        assert result["success"] is True
        assert result["finalized"] is True
        assert result["confidence"] == 0.9
        assert result["verification_passed"] is True

    @pytest.mark.asyncio
    async def test_finalize_default_values(self):
        """Test finalize with default values."""
        finalize = create_finalize_response_tool()
        result = await finalize(response="Answer")

        assert result["success"] is True
        assert result["confidence"] == 0.8
        assert result["verification_passed"] is True


class TestVerifyResponseTool:
    """Tests for verify_response tool."""

    @pytest.mark.asyncio
    async def test_verify_without_verifier(self):
        """Test verify_response without verifier (quick mode)."""
        verify = create_verify_response_tool(verifier=None)
        result = await verify(
            response="Test response that is long enough to pass basic checks and contains good information.",
            query="What is the test about?",
            check_facts=True
        )

        assert result["success"] is True
        assert result["mode"] == "quick"
        assert "score" in result

    @pytest.mark.asyncio
    async def test_verify_with_verifier(self):
        """Test verify_response with verifier."""
        mock_verifier = MagicMock()
        mock_verifier.verify = AsyncMock(return_value=MagicMock(
            verified=True,
            result="approved",
            confidence_score=0.85,
            feedback="Good response",
            issues=[],
            suggestions=[]
        ))

        verify = create_verify_response_tool(verifier=mock_verifier)
        result = await verify(
            response="Test response",
            query="Test query"
        )

        assert result["success"] is True
        assert result["mode"] == "full"


class TestRequestClarificationTool:
    """Tests for request_clarification tool."""

    @pytest.mark.asyncio
    async def test_request_clarification(self):
        """Test clarification request."""
        clarify = create_request_clarification_tool()
        result = await clarify(
            reason="Could not find information in knowledge base or web",
            suggestions=["Can you provide more context?", "What specific aspect interests you?"],
            search_trail=["knowledge_base: 0 results", "web_search: 0 results"]
        )

        assert result["success"] is True
        assert result["action"] == "clarification_requested"
        assert result["reason"] == "Could not find information in knowledge base or web"
        assert len(result["suggestions"]) == 2
        assert len(result["search_trail"]) == 2


class TestDelegateTool:
    """Tests for delegate tool."""

    @pytest.mark.asyncio
    async def test_delegate_without_orchestrator(self):
        """Test delegate without orchestrator."""
        delegate = create_delegate_tool(orchestrator=None)
        result = await delegate(
            agent_type="research",
            task="Find information about quantum physics"
        )

        assert result["success"] is False
        assert "not available" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_delegate_invalid_agent_type(self):
        """Test delegate with invalid agent type."""
        mock_orchestrator = MagicMock()

        delegate = create_delegate_tool(orchestrator=mock_orchestrator)
        result = await delegate(
            agent_type="invalid_type",
            task="Some task"
        )

        assert result["success"] is False
        assert "unknown" in result["error"].lower()


# =============================================================================
# Tool Category Tests
# =============================================================================

class TestToolCategories:
    """Tests for tool categories."""

    def test_all_categories_exist(self):
        """Test all categories exist."""
        categories = [
            ToolCategory.KNOWLEDGE,
            ToolCategory.SEARCH,
            ToolCategory.MEMORY,
            ToolCategory.LEARNING,
            ToolCategory.UTILITY,
        ]

        for cat in categories:
            assert cat is not None
            assert isinstance(cat.value, str)

    def test_tools_have_valid_categories(self):
        """Test all registered tools have valid categories."""
        valid_categories = set(ToolCategory)

        for tool in TOOL_REGISTRY:
            assert tool.category in valid_categories


# =============================================================================
# Tool Parameter Tests
# =============================================================================

class TestToolParameter:
    """Tests for ToolParameter dataclass."""

    def test_required_parameter(self):
        """Test required parameter."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )

        assert param.required is True
        assert param.default is None

    def test_optional_parameter_with_default(self):
        """Test optional parameter with default."""
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Max results",
            required=False,
            default=10
        )

        assert param.required is False
        assert param.default == 10

    def test_enum_parameter(self):
        """Test parameter with enum values."""
        param = ToolParameter(
            name="quality",
            type="string",
            description="Quality level",
            required=True,
            enum=["low", "medium", "high"]
        )

        assert param.enum == ["low", "medium", "high"]
