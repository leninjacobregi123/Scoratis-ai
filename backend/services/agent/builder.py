"""
Agent Tool Builder
Assembles tools with injected dependencies at runtime.

This module implements the dependency injection pattern for agent tools:
1. Takes tool definitions from the registry
2. Injects required dependencies (database, services, etc.)
3. Returns executable tool functions ready for the agent to use
"""

import logging
from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from .tools import (
    TOOL_REGISTRY,
    ToolDefinition,
    get_tool_by_name,
    create_search_knowledge_base_tool,
    create_search_journals_tool,
    create_search_past_conversations_tool,
    create_web_search_tool,
    create_get_learning_context_tool,
    create_remember_discovery_tool,
    # Agentic loop tools
    create_think_tool,
    create_plan_tool,
    create_delegate_tool,
    create_verify_response_tool,
    create_finalize_response_tool,
    create_request_clarification_tool,
    # Multimedia tools
    create_manim_animation_tool,
    create_link_preview_tool,
    create_display_image_tool,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolDependencies:
    """
    Container for all dependencies that tools might need.
    Pass this to build_tools() to inject dependencies into tool factories.
    """
    db_session: Optional[AsyncSession] = None
    rag_service: Any = None
    web_search_service: Any = None
    langgraph_service: Any = None
    llm_service: Any = None
    session_id: str = ""
    subject: str = "general"
    user_id: int = 1
    # Agentic components
    orchestrator: Any = None
    verifier: Any = None
    # Multimedia services (optional - tools work without them)
    animation_service: Any = None  # For Manim animations
    preview_service: Any = None    # For link previews
    image_service: Any = None      # For image display


@dataclass
class BuiltTool:
    """A tool that has been built with its dependencies injected"""
    name: str
    description: str
    function: Callable[..., Awaitable[Any]]
    schema: Dict[str, Any]


class ToolBuilder:
    """
    Builds executable tools from definitions by injecting dependencies.

    Usage:
        deps = ToolDependencies(db_session=db, rag_service=rag, ...)
        builder = ToolBuilder(deps)
        tools = builder.build_all()

        # Or build specific tools
        search_tool = builder.build_tool("search_knowledge_base")
    """

    def __init__(self, dependencies: ToolDependencies):
        self.deps = dependencies
        self._built_tools: Dict[str, BuiltTool] = {}

    def build_tool(self, tool_name: str) -> Optional[BuiltTool]:
        """
        Build a single tool by name with dependencies injected.

        Args:
            tool_name: Name of the tool to build

        Returns:
            BuiltTool with executable function, or None if tool not found
        """
        # Check cache
        if tool_name in self._built_tools:
            return self._built_tools[tool_name]

        tool_def = get_tool_by_name(tool_name)
        if not tool_def:
            logger.warning(f"Tool not found: {tool_name}")
            return None

        # Build based on tool name (each tool has specific dependency needs)
        try:
            func = self._create_tool_function(tool_def)
            if func is None:
                logger.warning(f"Could not create function for tool: {tool_name}")
                return None

            built_tool = BuiltTool(
                name=tool_def.name,
                description=tool_def.description,
                function=func,
                schema=tool_def.to_openai_schema()
            )

            self._built_tools[tool_name] = built_tool
            return built_tool

        except Exception as e:
            logger.error(f"Error building tool {tool_name}: {e}")
            return None

    def _create_tool_function(self, tool_def: ToolDefinition) -> Optional[Callable]:
        """Create the actual tool function with dependencies injected"""
        name = tool_def.name

        # Map tool names to their factory invocations
        if name == "search_knowledge_base":
            if not self.deps.db_session or not self.deps.rag_service:
                logger.warning(f"Missing dependencies for {name}")
                return self._create_unavailable_tool(name, "Database or RAG service not available")
            return create_search_knowledge_base_tool(
                self.deps.db_session,
                self.deps.rag_service,
                self.deps.user_id,
                subject=self.deps.subject  # Subject-filtered RAG
            )

        elif name == "search_journals":
            if not self.deps.db_session or not self.deps.rag_service:
                return self._create_unavailable_tool(name, "Database or RAG service not available")
            return create_search_journals_tool(
                self.deps.db_session,
                self.deps.rag_service,
                self.deps.user_id
            )

        elif name == "search_past_conversations":
            if not self.deps.db_session or not self.deps.rag_service:
                return self._create_unavailable_tool(name, "Database or RAG service not available")
            return create_search_past_conversations_tool(
                self.deps.db_session,
                self.deps.rag_service,
                self.deps.session_id,
                self.deps.user_id
            )

        elif name == "web_search":
            if not self.deps.web_search_service:
                return self._create_unavailable_tool(name, "Web search service not available")
            return create_web_search_tool(self.deps.web_search_service)

        elif name == "get_learning_context":
            if not self.deps.langgraph_service:
                return self._create_unavailable_tool(name, "LangGraph service not available")
            return create_get_learning_context_tool(
                self.deps.langgraph_service,
                self.deps.session_id
            )

        elif name == "remember_discovery":
            if not self.deps.langgraph_service:
                return self._create_unavailable_tool(name, "LangGraph service not available")
            return create_remember_discovery_tool(
                self.deps.langgraph_service,
                self.deps.session_id
            )

        # === Agentic Loop Tools ===
        elif name == "think":
            return create_think_tool()

        elif name == "plan":
            return create_plan_tool()

        elif name == "delegate":
            # Orchestrator is optional - tool handles None gracefully
            return create_delegate_tool(self.deps.orchestrator)

        elif name == "verify_response":
            # Verifier is optional - tool handles None with quick fallback
            return create_verify_response_tool(self.deps.verifier)

        elif name == "finalize_response":
            return create_finalize_response_tool()

        elif name == "request_clarification":
            return create_request_clarification_tool()

        # === Multimedia Tools ===
        elif name == "create_manim_animation":
            # Animation service is optional - tool works without it (returns queued status)
            return create_manim_animation_tool(self.deps.animation_service)

        elif name == "link_preview":
            # Preview service is optional - tool has built-in fallback
            return create_link_preview_tool(self.deps.preview_service)

        elif name == "display_image":
            # Image service is optional - tool works without it
            return create_display_image_tool(self.deps.image_service)

        else:
            logger.warning(f"Unknown tool: {name}")
            return None

    def _create_unavailable_tool(
        self,
        tool_name: str,
        reason: str
    ) -> Callable[..., Awaitable[Dict[str, Any]]]:
        """Create a placeholder tool that returns an error"""
        async def unavailable_tool(**kwargs) -> Dict[str, Any]:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is unavailable: {reason}",
                "tool": tool_name
            }
        return unavailable_tool

    def build_all(self) -> List[BuiltTool]:
        """Build all tools from the registry"""
        built = []
        for tool_def in TOOL_REGISTRY:
            tool = self.build_tool(tool_def.name)
            if tool:
                built.append(tool)
        return built

    def build_selected(self, tool_names: List[str]) -> List[BuiltTool]:
        """Build only the specified tools"""
        built = []
        for name in tool_names:
            tool = self.build_tool(name)
            if tool:
                built.append(tool)
        return built

    def get_tool_schemas(self, tools: Optional[List[BuiltTool]] = None) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for built tools"""
        if tools is None:
            tools = self.build_all()
        return [tool.schema for tool in tools]

    def get_tool_map(self, tools: Optional[List[BuiltTool]] = None) -> Dict[str, Callable]:
        """Get a map of tool name to function for easy execution"""
        if tools is None:
            tools = self.build_all()
        return {tool.name: tool.function for tool in tools}


def build_tools(
    db_session: Optional[AsyncSession] = None,
    rag_service: Any = None,
    web_search_service: Any = None,
    langgraph_service: Any = None,
    llm_service: Any = None,
    session_id: str = "",
    subject: str = "general",
    user_id: int = 1,
    tool_names: Optional[List[str]] = None,
    orchestrator: Any = None,
    verifier: Any = None,
    # Multimedia services
    animation_service: Any = None,
    preview_service: Any = None,
    image_service: Any = None
) -> List[BuiltTool]:
    """
    Convenience function to build tools with dependencies.

    Args:
        db_session: Database session for DB operations
        rag_service: RAG service for knowledge base search
        web_search_service: Web search service
        langgraph_service: LangGraph service for state management
        llm_service: LLM service for AI operations
        session_id: Current session identifier
        subject: Current subject channel
        user_id: Current user ID
        tool_names: Optional list of specific tools to build (builds all if None)
        orchestrator: Sub-agent orchestrator for delegation
        verifier: Response verifier for quality checking
        animation_service: Manim animation rendering service
        preview_service: Link preview generation service
        image_service: Image handling service

    Returns:
        List of BuiltTool objects ready for use
    """
    deps = ToolDependencies(
        db_session=db_session,
        rag_service=rag_service,
        web_search_service=web_search_service,
        langgraph_service=langgraph_service,
        llm_service=llm_service,
        session_id=session_id,
        subject=subject,
        user_id=user_id,
        orchestrator=orchestrator,
        verifier=verifier,
        animation_service=animation_service,
        preview_service=preview_service,
        image_service=image_service
    )

    builder = ToolBuilder(deps)

    if tool_names:
        return builder.build_selected(tool_names)
    return builder.build_all()


def get_tool_execution_map(
    db_session: Optional[AsyncSession] = None,
    rag_service: Any = None,
    web_search_service: Any = None,
    langgraph_service: Any = None,
    session_id: str = "",
    user_id: int = 1,
) -> Dict[str, Callable]:
    """
    Get a simple map of tool_name -> function for execution.
    Useful when you need to execute tools by name from LLM responses.
    """
    deps = ToolDependencies(
        db_session=db_session,
        rag_service=rag_service,
        web_search_service=web_search_service,
        langgraph_service=langgraph_service,
        session_id=session_id,
        user_id=user_id
    )

    builder = ToolBuilder(deps)
    return builder.get_tool_map()
