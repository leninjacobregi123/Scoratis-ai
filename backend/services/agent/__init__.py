"""
Scoratis Agentic Workflow System

This module implements a sophisticated agentic workflow with enhanced features:

1. **Agentic Loop**: Think → Act → Observe → Verify loop with stop conditions
2. **Sub-Agent Delegation**: Orchestrator for specialized sub-agent tasks
3. **Verification Pattern**: Quality checking before response finalization
4. **Stateful Graph**: LangGraph-based reasoning with cyclical tool use
5. **Memory Persistence**: PostgreSQL-backed conversation checkpointing
6. **Modular Tools**: Registry-based tool system with dependency injection
7. **Dynamic Prompts**: Configurable prompt engineering for different contexts

Agentic Concepts Implemented:
- Agentic loops with scratchpad for reasoning persistence
- Sub-agent delegation (Research, Analysis, Summary, Expert, Fact-Check)
- Verifier pattern for response quality assurance
- Stop conditions (max iterations, confidence threshold, verification)

Usage:
    from services.agent import create_agent, ScoratisAgent

    # Create the agent with agentic features
    agent = create_agent(
        llm_service=llm_service,
        rag_service=rag_service,
        web_search_service=web_search_service,
        database_url=settings.DATABASE_URL,  # psycopg-compatible, not DATABASE_URL_ASYNC
        enable_verification=True,
        enable_delegation=True
    )

    # Initialize (sets up checkpointing and agentic components)
    await agent.initialize()

    # Non-streaming invocation
    result = await agent.invoke(
        session_id="conv_123",
        message="Explain photosynthesis",
        db_session=db_session
    )

    # Streaming invocation with agentic events
    async for event in agent.stream(
        session_id="conv_123",
        message="Explain photosynthesis",
        db_session=db_session
    ):
        if event["type"] == "token":
            print(event["content"], end="")
        elif event["type"] == "tool_start":
            print(f"\\nUsing tool: {event['tool']}")
        elif event["type"] == "tool_end":
            print(f"\\nTool result: {event['result']}")
        elif event["type"] == "phase":
            print(f"\\nPhase: {event['phase']}")
        elif event["type"] == "done":
            print(f"\\n\\nDone! Model: {event['metadata']['model']}")
"""

# State (core + agentic)
from .state import (
    AgentState,
    Message,
    MessageRole,
    LearningContext,
    LearningState,
    RAGContext,
    VideoAnalysis,
    ToolCall,
    ToolResult,
    create_initial_state,
    # Agentic loop components
    Scratchpad,
    StopCondition,
    VerificationState,
    SubAgentResult,
    AgentPhase,
    SubAgentType,
    VerificationResult,
)

# Tools
from .tools import (
    ToolDefinition,
    ToolParameter,
    ToolCategory,
    TOOL_REGISTRY,
    get_tool_by_name,
    get_tools_by_category,
    get_all_tool_schemas,
)

# Builder
from .builder import (
    ToolDependencies,
    ToolBuilder,
    BuiltTool,
    build_tools,
    get_tool_execution_map,
)

# Prompts
from .prompts import (
    PromptConfig,
    PromptSection,
    PromptBuilder,
    build_system_prompt,
    build_minimal_prompt,
)

# Graph (main agent)
from .graph import (
    ScoratisAgent,
    create_agent,
    get_agent,
)

# Orchestrator (sub-agent delegation)
from .orchestrator import (
    SubAgentOrchestrator,
    SubAgentExecutor,
    DelegationDecision,
    DelegationCriteria,
    decide_delegation,
    create_orchestrator,
    get_orchestrator,
    SUBAGENT_CONFIGS,
)

# Verifier (response quality checking)
from .verifier import (
    ResponseVerifier,
    QuickVerifier,
    VerificationConfig,
    create_verifier,
    get_verifier,
    get_quick_verifier,
)

__all__ = [
    # State (core)
    "AgentState",
    "Message",
    "MessageRole",
    "LearningContext",
    "LearningState",
    "RAGContext",
    "VideoAnalysis",
    "ToolCall",
    "ToolResult",
    "create_initial_state",
    # State (agentic)
    "Scratchpad",
    "StopCondition",
    "VerificationState",
    "SubAgentResult",
    "AgentPhase",
    "SubAgentType",
    "VerificationResult",
    # Tools
    "ToolDefinition",
    "ToolParameter",
    "ToolCategory",
    "TOOL_REGISTRY",
    "get_tool_by_name",
    "get_tools_by_category",
    "get_all_tool_schemas",
    # Builder
    "ToolDependencies",
    "ToolBuilder",
    "BuiltTool",
    "build_tools",
    "get_tool_execution_map",
    # Prompts
    "PromptConfig",
    "PromptSection",
    "PromptBuilder",
    "build_system_prompt",
    "build_minimal_prompt",
    # Agent
    "ScoratisAgent",
    "create_agent",
    "get_agent",
    # Orchestrator
    "SubAgentOrchestrator",
    "SubAgentExecutor",
    "DelegationDecision",
    "DelegationCriteria",
    "decide_delegation",
    "create_orchestrator",
    "get_orchestrator",
    "SUBAGENT_CONFIGS",
    # Verifier
    "ResponseVerifier",
    "QuickVerifier",
    "VerificationConfig",
    "create_verifier",
    "get_verifier",
    "get_quick_verifier",
]
