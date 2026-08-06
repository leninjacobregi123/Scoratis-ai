"""
Scoratis Agentic Graph
The core reasoning engine implementing a stateful agent with tool use.

Architecture:
1. Agent Node: Calls LLM to decide actions (respond or use tools)
2. Tools Node: Executes tool calls from the agent
3. Delegation Node: Handles sub-agent delegation
4. Verification Node: Verifies response quality
5. Conditional Edges: Routes flow based on agent decisions

Enhanced Agentic Features:
- Agentic Loop with stop conditions
- Sub-agent delegation for specialized tasks
- Response verification before finalization
- Scratchpad for reasoning persistence

The graph cycles through nodes until the agent gives a verified final response.
"""

import json
import logging
import uuid
from typing import Optional, List, Dict, Any, Literal, Callable, AsyncGenerator, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from .state import (
    AgentState,
    create_initial_state,
    Message,
    MessageRole,
    LearningContext,
    RAGContext,
    Scratchpad,
    StopCondition,
    VerificationState,
    AgentPhase,
    SubAgentResult,
    SearchTrail,
    SearchAttempt,
)
from .query_classifier import get_query_classifier, QueryClassification
from .builder import build_tools, BuiltTool, ToolDependencies, ToolBuilder
from .prompts import build_system_prompt, TOOL_REGISTRY
from .tools import get_all_tool_schemas
from .orchestrator import SubAgentOrchestrator, decide_delegation, create_orchestrator
from .verifier import ResponseVerifier, create_verifier, get_quick_verifier

logger = logging.getLogger(__name__)

# Try to import LangGraph
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.checkpoint.memory import MemorySaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not installed. Using fallback agent mode.")


class ScoratisAgent:
    """
    The main agentic reasoning engine for Scoratis.

    Implements an enhanced Think -> Act -> Observe -> Verify loop:
    1. Think: LLM decides what to do (respond, call tools, or delegate)
    2. Act: Execute tool calls or delegate to sub-agents
    3. Observe: Process results and update scratchpad
    4. Verify: Check response quality before finalizing
    5. Repeat until verified response or max iterations

    Supports:
    - Streaming responses with workflow events
    - PostgreSQL-backed memory persistence
    - Multi-tool execution
    - RAG context integration
    - Sub-agent delegation for specialized tasks
    - Response verification before delivery
    - Scratchpad for reasoning persistence
    """

    def __init__(
        self,
        llm_service: Any,
        rag_service: Optional[Any] = None,
        web_search_service: Optional[Any] = None,
        langgraph_service: Optional[Any] = None,
        database_url: Optional[str] = None,
        enable_verification: bool = True,
        enable_delegation: bool = True,
    ):
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.web_search_service = web_search_service
        self.langgraph_service = langgraph_service
        self.database_url = database_url

        # Agentic features
        self.enable_verification = enable_verification
        self.enable_delegation = enable_delegation

        self.graph = None
        self.checkpointer = None
        self._pg_pool: Optional["AsyncConnectionPool"] = None
        self._initialized = False

        # Agentic components (initialized lazily)
        self._orchestrator: Optional[SubAgentOrchestrator] = None
        self._verifier: Optional[ResponseVerifier] = None

    async def initialize(self):
        """Initialize the agent graph with checkpointing and agentic components"""
        if self._initialized:
            return

        if LANGGRAPH_AVAILABLE:
            try:
                # Try PostgreSQL checkpointing first
                if self.database_url:
                    try:
                        # AsyncPostgresSaver.from_conn_string() is an
                        # @asynccontextmanager - it only yields a usable
                        # saver inside an `async with` block and closes the
                        # connection on exit, so calling .setup() on it
                        # directly (the object the un-entered context
                        # manager itself) raised
                        # "'_AsyncGeneratorContextManager' object has no
                        # attribute 'setup'" on every startup, silently
                        # falling back to in-memory checkpointing (losing
                        # Think-mode state across restarts). A long-lived
                        # AsyncConnectionPool + the AsyncPostgresSaver(conn=)
                        # constructor - LangGraph's documented pattern for
                        # apps that hold the saver open across many
                        # requests instead of one `async with` block - fixes
                        # this. autocommit/prepare_threshold/row_factory
                        # mirror exactly what from_conn_string sets on its
                        # own connection internally.
                        self._pg_pool = AsyncConnectionPool(
                            conninfo=self.database_url,
                            max_size=10,
                            open=False,
                            kwargs={
                                "autocommit": True,
                                "prepare_threshold": 0,
                                "row_factory": dict_row,
                            },
                        )
                        await self._pg_pool.open()
                        self.checkpointer = AsyncPostgresSaver(self._pg_pool)
                        await self.checkpointer.setup()
                        logger.info("Agent using PostgreSQL checkpointing")
                    except Exception as e:
                        logger.warning(f"PostgreSQL checkpointing failed, using memory: {e}")
                        self.checkpointer = MemorySaver()
                else:
                    self.checkpointer = MemorySaver()
                    logger.info("Agent using in-memory checkpointing")

                # Build the graph (not compiled here - compiled per request with tools)
                logger.info("Scoratis Agent initialized with LangGraph")

            except Exception as e:
                logger.error(f"LangGraph initialization failed: {e}")

        # Initialize agentic components
        if self.enable_delegation:
            try:
                self._orchestrator = create_orchestrator(
                    llm_service=self.llm_service,
                    tool_builder=None  # Will inject per-request
                )
                logger.info("Sub-agent orchestrator initialized")
            except Exception as e:
                logger.warning(f"Orchestrator initialization failed: {e}")

        if self.enable_verification:
            try:
                self._verifier = create_verifier(
                    llm_service=self.llm_service
                )
                logger.info("Response verifier initialized")
            except Exception as e:
                logger.warning(f"Verifier initialization failed: {e}")

        self._initialized = True

    def _build_graph(self, tool_map: Dict[str, Callable]) -> Any:
        """Build the enhanced LangGraph state graph with agentic features"""
        if not LANGGRAPH_AVAILABLE:
            return None

        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("agent", self._create_agent_node(tool_map))
        graph.add_node("tools", self._create_tools_node(tool_map))
        graph.add_node("verify", self._create_verification_node())
        graph.add_node("refine", self._create_refinement_node(tool_map))

        # Set entry point
        graph.set_entry_point("agent")

        # Add conditional edges from agent
        graph.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {
                "tools": "tools",
                "verify": "verify",
                "end": END
            }
        )

        # Tools go back to agent
        graph.add_edge("tools", "agent")

        # Verification routing
        graph.add_conditional_edges(
            "verify",
            self._route_after_verification,
            {
                "refine": "refine",
                "end": END
            }
        )

        # Refine goes back to agent
        graph.add_edge("refine", "agent")

        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_agent(self, state: AgentState) -> Literal["tools", "verify", "end"]:
        """Route after agent node based on state"""
        # Check stop conditions first
        stop_condition = state.get("stop_condition", {})
        if stop_condition.get("explicit_stop") or stop_condition.get("current_iteration", 0) >= stop_condition.get("max_iterations", 7):
            return "end"

        # Check for pending tool calls
        pending_tools = state.get("pending_tool_calls", [])
        if pending_tools:
            return "tools"

        # Check if we have a draft response that needs verification
        draft = state.get("draft_response")
        final = state.get("final_response")

        if draft and not final:
            verification = state.get("verification", {})
            if self.enable_verification and not verification.get("verified"):
                return "verify"

        # If we have a final response or verification is complete
        if final:
            return "end"

        # Default to end if nothing else matches
        return "end"

    def _route_after_verification(self, state: AgentState) -> Literal["refine", "end"]:
        """Route after verification node"""
        verification = state.get("verification", {})

        # If approved or max revisions reached, end
        if verification.get("result") == "approved":
            return "end"

        if verification.get("revision_count", 0) >= verification.get("max_revisions", 2):
            return "end"

        # If needs revision, go to refine
        if verification.get("result") == "needs_revision":
            return "refine"

        # Default to end
        return "end"

    def _create_agent_node(self, tool_map: Dict[str, Callable]):
        """Create the enhanced agent reasoning node with scratchpad support"""
        async def agent_node(state: AgentState) -> Dict[str, Any]:
            """
            The agent's brain - decides what to do next.
            Enhanced with:
            - Query classification (trivial detection)
            - Scratchpad for reasoning persistence
            - Stop condition tracking
            - Phase management
            """
            raw_messages = list(state.get("messages", []))
            rag_context = state.get("rag_context")
            learning = state.get("learning", {})
            current_input = state.get("current_input", "")

            # Check if query classification was already done
            query_classification = state.get("query_classification")
            if query_classification is None and current_input:
                # Classify the query to check if it's trivial
                classifier = get_query_classifier()
                classification = classifier.classify(current_input)
                query_classification = {
                    "is_trivial": classification.is_trivial,
                    "query_type": classification.query_type,
                    "skip_tools": classification.skip_tools,
                    "reason": classification.reason,
                    "confidence": classification.confidence
                }

            # Clean messages - convert LangChain objects to dicts
            # IMPORTANT: Preserve tool_calls and tool_call_id for Groq/OpenAI compatibility
            messages = []
            for msg in raw_messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    cleaned_msg = {
                        "role": role,
                        "content": msg.get("content", "")
                    }
                    # Preserve tool_calls for assistant messages (required by Groq)
                    if role == "assistant" and "tool_calls" in msg:
                        cleaned_msg["tool_calls"] = msg["tool_calls"]
                    # Preserve tool_call_id and name for tool response messages (required by Groq)
                    if role == "tool":
                        if "tool_call_id" in msg:
                            cleaned_msg["tool_call_id"] = msg["tool_call_id"]
                        if "name" in msg:
                            cleaned_msg["name"] = msg["name"]
                    messages.append(cleaned_msg)
                elif hasattr(msg, "content") and hasattr(msg, "type"):
                    # LangChain message object
                    role = "user" if msg.type == "human" else "assistant" if msg.type == "ai" else msg.type
                    cleaned_msg = {"role": role, "content": msg.content}
                    # Check for tool_calls on LangChain AI messages
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        cleaned_msg["tool_calls"] = msg.tool_calls
                    # Check for tool_call_id on LangChain tool messages
                    if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                        cleaned_msg["tool_call_id"] = msg.tool_call_id
                    if hasattr(msg, "name") and msg.name:
                        cleaned_msg["name"] = msg.name
                    messages.append(cleaned_msg)
                else:
                    messages.append({"role": "user", "content": str(msg)})

            # Get/update scratchpad
            scratchpad_dict = state.get("scratchpad", {})
            scratchpad = Scratchpad(**scratchpad_dict) if scratchpad_dict else Scratchpad()
            scratchpad.increment_iteration()

            # Get/update stop condition
            stop_dict = state.get("stop_condition", {})
            stop_condition = StopCondition(**stop_dict) if stop_dict else StopCondition()
            stop_condition.increment()

            # Check if we should stop
            if stop_condition.should_stop():
                # Use draft if available, otherwise generate fallback
                draft = state.get("draft_response")
                if draft:
                    return {
                        "final_response": draft,
                        "pending_tool_calls": [],
                        "phase": AgentPhase.COMPLETE.value,
                        "stop_condition": stop_condition.to_dict()
                    }

            # Determine if tools should be used based on query classification
            should_use_tools = bool(tool_map)
            if query_classification and query_classification.get("skip_tools"):
                should_use_tools = False
                logger.debug(f"Skipping tools for trivial query: {query_classification.get('reason')}")

            # Build enhanced system prompt with scratchpad context
            scratchpad_context = scratchpad.to_context_string()
            system_prompt = build_system_prompt(
                include_tools=should_use_tools,
                include_citations=True,
                rag_context_xml=rag_context.get("context_xml", "") if rag_context else "",
                learning_state=learning,
                custom_instructions=f"\n\n## YOUR REASONING STATE\n{scratchpad_context}" if scratchpad_context else ""
            )

            # Get tool schemas (only if tools are needed)
            tool_schemas = get_all_tool_schemas() if should_use_tools else []

            try:
                # Call LLM with tools
                response = await self.llm_service.generate_with_tools(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=tool_schemas
                )

                # Check for tool calls
                tool_calls = response.get("tool_calls", [])
                content = response.get("content", "")

                if tool_calls:
                    # Check for special agentic tools
                    for call in tool_calls:
                        tool_name = call.get("function", {}).get("name") or call.get("name", "")

                        # Handle think tool - update scratchpad
                        if tool_name == "think":
                            args = json.loads(call.get("function", {}).get("arguments", "{}"))
                            scratchpad.add_thought(args.get("thought", ""))
                            scratchpad.confidence = args.get("confidence", 0.5)
                            scratchpad.needs_more_info = args.get("needs_more_info", False)

                        # Handle plan tool - update scratchpad
                        elif tool_name == "plan":
                            args = json.loads(call.get("function", {}).get("arguments", "{}"))
                            scratchpad.current_goal = args.get("goal", "")
                            scratchpad.set_plan(args.get("steps", []))

                        # Handle finalize tool - set final response
                        elif tool_name == "finalize_response":
                            args = json.loads(call.get("function", {}).get("arguments", "{}"))
                            final_response = args.get("response", content)
                            stop_condition.set_confidence(args.get("confidence", 0.8))
                            if args.get("verification_passed", True):
                                stop_condition.mark_verified()
                            return {
                                "final_response": final_response,
                                "pending_tool_calls": [],
                                "phase": AgentPhase.COMPLETE.value,
                                "scratchpad": scratchpad.to_dict(),
                                "stop_condition": stop_condition.to_dict(),
                                "query_classification": query_classification,
                                "model_used": self.llm_service.get_current_config().get("model")
                            }

                    # Agent wants to use tools
                    return {
                        "pending_tool_calls": tool_calls,
                        "phase": AgentPhase.RESEARCHING.value,
                        "scratchpad": scratchpad.to_dict(),
                        "stop_condition": stop_condition.to_dict(),
                        "query_classification": query_classification,
                        "messages": [{
                            "role": "assistant",
                            "content": content,
                            "tool_calls": tool_calls
                        }]
                    }
                else:
                    # No tools - this is a draft response
                    # If verification is enabled, set as draft; otherwise set as final
                    if self.enable_verification:
                        return {
                            "draft_response": content,
                            "pending_tool_calls": [],
                            "phase": AgentPhase.DRAFTING.value,
                            "scratchpad": scratchpad.to_dict(),
                            "stop_condition": stop_condition.to_dict(),
                            "query_classification": query_classification,
                            "messages": [{
                                "role": "assistant",
                                "content": content
                            }]
                        }
                    else:
                        return {
                            "final_response": content,
                            "pending_tool_calls": [],
                            "phase": AgentPhase.COMPLETE.value,
                            "scratchpad": scratchpad.to_dict(),
                            "stop_condition": stop_condition.to_dict(),
                            "query_classification": query_classification,
                            "messages": [{
                                "role": "assistant",
                                "content": content
                            }],
                            "model_used": self.llm_service.get_current_config().get("model")
                        }

            except Exception as e:
                logger.error(f"Agent node error: {e}")
                stop_condition.force_stop(f"error: {str(e)}")
                return {
                    "error": str(e),
                    "final_response": "I apologize, but I encountered an error while processing your request. Could you please try again?",
                    "pending_tool_calls": [],
                    "phase": AgentPhase.COMPLETE.value,
                    "stop_condition": stop_condition.to_dict()
                }

        return agent_node

    def _create_tools_node(self, tool_map: Dict[str, Callable]):
        """Create the tool execution node with search trail tracking"""
        # Search tools that should be tracked
        SEARCH_TOOLS = {
            "search_knowledge_base", "web_search",
            "search_journals", "search_past_conversations"
        }

        async def tools_node(state: AgentState) -> Dict[str, Any]:
            """Execute pending tool calls and return results"""
            pending_calls = state.get("pending_tool_calls", [])
            results = []
            tool_messages = []

            # Get or create search trail
            search_trail_dict = state.get("search_trail", {})
            if search_trail_dict and "attempts" in search_trail_dict:
                search_trail = SearchTrail(
                    attempts=[SearchAttempt(**a) for a in search_trail_dict.get("attempts", [])]
                )
            else:
                search_trail = SearchTrail()

            for call in pending_calls:
                tool_name = call.get("function", {}).get("name") or call.get("name")
                tool_id = call.get("id", str(uuid.uuid4()))

                try:
                    # Parse arguments
                    args_str = call.get("function", {}).get("arguments") or call.get("arguments", "{}")
                    if isinstance(args_str, str):
                        args = json.loads(args_str)
                    else:
                        args = args_str

                    # Execute tool
                    if tool_name in tool_map:
                        result = await tool_map[tool_name](**args)
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    results.append({
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "result": result
                    })

                    # Track search attempts in search trail
                    if tool_name in SEARCH_TOOLS:
                        search_trail.add_from_tool_result(tool_name, result)

                    # Add tool message
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "content": json.dumps(result)
                    })

                except Exception as e:
                    logger.error(f"Tool execution error ({tool_name}): {e}")
                    error_result = {"error": str(e)}
                    results.append({
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "result": error_result,
                        "error": str(e)
                    })

                    # Track failed search attempts too
                    if tool_name in SEARCH_TOOLS:
                        search_trail.add_attempt(SearchAttempt(
                            source=tool_name,
                            query=args.get("query", "") if 'args' in dir() else "",
                            results_count=0,
                            success=False,
                            had_results=False,
                            error=str(e)
                        ))

                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "content": json.dumps(error_result)
                    })

            # Update scratchpad with observations
            scratchpad_dict = state.get("scratchpad", {})
            if scratchpad_dict:
                scratchpad = Scratchpad(**scratchpad_dict)
                for r in results:
                    if r.get("result") and not r.get("error"):
                        result_info = r.get("result", {})
                        if r["name"] in SEARCH_TOOLS:
                            count = result_info.get("results_count", 0)
                            scratchpad.add_observation(f"{r['name']}: {count} results")
                        else:
                            scratchpad.add_observation(f"{r['name']}: success")
                    else:
                        scratchpad.add_observation(f"{r['name']}: {r.get('error', 'failed')}")

                return {
                    "tool_results": results,
                    "pending_tool_calls": [],  # Clear pending
                    "messages": tool_messages,
                    "scratchpad": scratchpad.to_dict(),
                    "search_trail": search_trail.to_dict()
                }

            return {
                "tool_results": results,
                "pending_tool_calls": [],  # Clear pending
                "messages": tool_messages,
                "search_trail": search_trail.to_dict()
            }

        return tools_node

    def _create_verification_node(self):
        """Create the response verification node"""
        async def verify_node(state: AgentState) -> Dict[str, Any]:
            """
            Verify the draft response before finalizing.
            Uses the verifier to check quality and accuracy.
            """
            draft_response = state.get("draft_response", "")
            current_input = state.get("current_input", "")
            rag_context = state.get("rag_context", {})

            # Get current verification state
            verification_dict = state.get("verification", {})
            verification = VerificationState(**verification_dict) if verification_dict else VerificationState()

            if not draft_response:
                # No draft to verify, mark as failed
                verification.mark_verified(
                    result="needs_revision",
                    feedback="No response to verify",
                    confidence=0.0
                )
                return {
                    "verification": verification.to_dict(),
                    "phase": AgentPhase.VERIFYING.value
                }

            try:
                if self._verifier:
                    # Full verification
                    result = await self._verifier.verify(
                        user_query=current_input,
                        response=draft_response,
                        sources=rag_context.get("sources", []),
                    )
                    verification = result
                else:
                    # Quick verification fallback
                    quick = get_quick_verifier()
                    result = quick.quick_check(current_input, draft_response)
                    verification = result

                # If approved, promote draft to final
                if verification.result == "approved":
                    return {
                        "verification": verification.to_dict(),
                        "final_response": draft_response,
                        "phase": AgentPhase.COMPLETE.value,
                        "model_used": self.llm_service.get_current_config().get("model")
                    }
                else:
                    return {
                        "verification": verification.to_dict(),
                        "phase": AgentPhase.VERIFYING.value
                    }

            except Exception as e:
                logger.error(f"Verification error: {e}")
                # On error, approve the response to avoid blocking
                verification.mark_verified(
                    result="approved",
                    feedback=f"Verification skipped due to error: {str(e)}",
                    confidence=0.7
                )
                return {
                    "verification": verification.to_dict(),
                    "final_response": draft_response,
                    "phase": AgentPhase.COMPLETE.value,
                    "model_used": self.llm_service.get_current_config().get("model")
                }

        return verify_node

    def _create_refinement_node(self, tool_map: Dict[str, Callable]):
        """Create the response refinement node"""
        async def refine_node(state: AgentState) -> Dict[str, Any]:
            """
            Refine the draft response based on verification feedback.
            This node is called when verification fails and revision is needed.
            """
            draft_response = state.get("draft_response", "")
            current_input = state.get("current_input", "")
            verification_dict = state.get("verification", {})
            verification = VerificationState(**verification_dict) if verification_dict else VerificationState()

            # Increment revision count
            verification.increment_revision()

            # Build refinement prompt
            feedback = verification.feedback or ""
            issues = verification.issues or []
            suggestions = verification.suggestions or []

            refinement_context = [
                "## REVISION REQUIRED",
                f"The previous response needs improvement.",
                f"Feedback: {feedback}" if feedback else "",
            ]

            if issues:
                refinement_context.append("Issues to address:")
                for issue in issues[:5]:
                    refinement_context.append(f"- {issue}")

            if suggestions:
                refinement_context.append("Suggestions:")
                for suggestion in suggestions[:3]:
                    refinement_context.append(f"- {suggestion}")

            refinement_context.append(f"\nPrevious response:\n{draft_response[:500]}...")
            refinement_context.append("\nPlease revise your response to address these issues.")

            # Add refinement instruction to messages
            messages = list(state.get("messages", []))
            messages.append({
                "role": "system",
                "content": "\n".join(refinement_context)
            })

            return {
                "messages": messages,
                "draft_response": None,  # Clear draft so agent generates new one
                "verification": verification.to_dict(),
                "phase": AgentPhase.REFINING.value
            }

        return refine_node

    async def invoke(
        self,
        session_id: str,
        message: str,
        db_session: Optional[AsyncSession] = None,
        user_id: int = 1
    ) -> Dict[str, Any]:
        """
        Process a message through the agent (non-streaming).

        Args:
            session_id: Conversation thread ID
            message: User's message
            db_session: Database session for tools
            user_id: User ID

        Returns:
            Dict with response and metadata
        """
        await self.initialize()

        # Build tools with dependencies including agentic components
        tools = build_tools(
            db_session=db_session,
            rag_service=self.rag_service,
            web_search_service=self.web_search_service,
            langgraph_service=self.langgraph_service,
            llm_service=self.llm_service,
            session_id=session_id,
            user_id=user_id,
            orchestrator=self._orchestrator,
            verifier=self._verifier
        )
        tool_map = {t.name: t.function for t in tools}

        # Get RAG context first
        rag_context = None
        if db_session and self.rag_service:
            try:
                rag_result = await self.rag_service.get_context_with_citations(
                    db_session, message, user_id
                )
                rag_context = {
                    "context_xml": rag_result.get("context_xml", ""),
                    "sources": rag_result.get("sources", []),
                    "chunk_mapping": rag_result.get("chunk_mapping", {})
                }
            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {e}")

        # Build initial state with agentic features
        initial_state = create_initial_state(
            session_id=session_id,
            user_id=user_id,
            enable_verification=self.enable_verification
        )
        initial_state["current_input"] = message
        initial_state["messages"] = [{"role": "user", "content": message}]
        if rag_context:
            initial_state["rag_context"] = rag_context

        # Use LangGraph if available
        if LANGGRAPH_AVAILABLE and self.checkpointer:
            graph = self._build_graph(tool_map)
            config = {"configurable": {"thread_id": session_id}}

            try:
                result = await graph.ainvoke(initial_state, config=config)
                return self._format_result(result, rag_context)
            except Exception as e:
                logger.error(f"Graph invocation failed: {e}")
                # Fall through to fallback

        # Fallback: Simple LLM call without graph
        return await self._fallback_invoke(
            message, rag_context, tools
        )

    async def stream(
        self,
        session_id: str,
        message: str,
        db_session: Optional[AsyncSession] = None,
        user_id: int = 1
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a response from the agent.

        Yields events:
        - {"type": "sources", "sources": [...]}
        - {"type": "tool_start", "tool": "name", "args": {...}}
        - {"type": "tool_end", "tool": "name", "result": {...}}
        - {"type": "token", "content": "..."}
        - {"type": "done", "response": "...", "metadata": {...}}
        """
        await self.initialize()

        # Build tools with agentic components
        tools = build_tools(
            db_session=db_session,
            rag_service=self.rag_service,
            web_search_service=self.web_search_service,
            langgraph_service=self.langgraph_service,
            llm_service=self.llm_service,
            session_id=session_id,
            user_id=user_id,
            orchestrator=self._orchestrator,
            verifier=self._verifier
        )
        tool_map = {t.name: t.function for t in tools}

        # Get RAG context
        rag_context = None
        if db_session and self.rag_service:
            try:
                rag_result = await self.rag_service.get_context_with_citations(
                    db_session, message, user_id
                )
                rag_context = {
                    "context_xml": rag_result.get("context_xml", ""),
                    "sources": rag_result.get("sources", []),
                    "chunk_mapping": rag_result.get("chunk_mapping", {})
                }

                # Yield sources first
                if rag_context.get("sources"):
                    yield {
                        "type": "sources",
                        "sources": [
                            {
                                "citation_number": s.get("citation_number"),
                                "document_title": s.get("document_title"),
                                "content_preview": s.get("content_preview", "")[:200],
                                "source_type": s.get("source_type"),
                            }
                            for s in rag_context["sources"][:10]
                        ]
                    }

            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {e}")

        # Build system prompt
        learning_state = {}
        if self.langgraph_service:
            try:
                learning_state = await self.langgraph_service.get_session_context(session_id)
            except:
                pass

        system_prompt = build_system_prompt(
            include_tools=bool(tool_map),
            include_citations=True,
            rag_context_xml=rag_context.get("context_xml", "") if rag_context else "",
            learning_state=learning_state
        )

        messages = [{"role": "user", "content": message}]
        full_response = ""
        tool_results = []
        # Populated if the agent itself calls generate_video during its own
        # reasoning (see tools.py's create_generate_video_tool) - this is
        # now the sole source of auto-video-generation for the agentic path,
        # replacing the old separate post-hoc video_analyzer_service call.
        auto_video = None

        # Agentic loop with streaming
        max_iterations = 5
        for iteration in range(max_iterations):
            # Check for tool use first (non-streaming call)
            tool_schemas = get_all_tool_schemas() if tool_map else []

            try:
                # First check if we need tools
                check_response = await self._check_for_tools(
                    messages, system_prompt, tool_schemas
                )

                if check_response.get("tool_calls"):
                    # Execute tools
                    for call in check_response["tool_calls"]:
                        tool_name = call.get("function", {}).get("name") or call.get("name")
                        tool_id = call.get("id", str(uuid.uuid4()))

                        # Parse arguments
                        args_str = call.get("function", {}).get("arguments") or call.get("arguments", "{}")
                        if isinstance(args_str, str):
                            args = json.loads(args_str)
                        else:
                            args = args_str

                        # Yield tool start
                        yield {
                            "type": "tool_start",
                            "tool": tool_name,
                            "args": args
                        }

                        # Execute
                        if tool_name in tool_map:
                            result = await tool_map[tool_name](**args)
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}

                        tool_results.append(result)

                        if tool_name == "generate_video" and isinstance(result, dict) and result.get("success"):
                            auto_video = {
                                "task_id": result.get("task_id"),
                                "topic": result.get("topic"),
                                "concepts": result.get("concepts", []),
                                "visualization_type": result.get("visualization_type"),
                                "estimated_duration": result.get("estimated_duration"),
                            }

                        # Yield tool end
                        yield {
                            "type": "tool_end",
                            "tool": tool_name,
                            "result": result
                        }

                        # Add to messages
                        messages.append({
                            "role": "assistant",
                            "content": check_response.get("content", ""),
                            "tool_calls": [call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": json.dumps(result)
                        })

                    continue  # Loop back for more reasoning

                else:
                    # No tools, stream final response
                    async for chunk in self.llm_service.generate_stream(
                        messages=messages,
                        system_prompt=system_prompt
                    ):
                        full_response += chunk
                        yield {"type": "token", "content": chunk}

                    break  # Done

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                error_msg = "I apologize, but I encountered an error. Please try again."
                yield {"type": "token", "content": error_msg}
                full_response = error_msg
                break

        # The loop can be exhausted by max_iterations while the model was
        # still requesting tools every round (never reaching the no-more-
        # tool-calls branch above that actually streams an answer) - a
        # multi-step query can easily use up all 5 rounds on tool calls
        # alone. Previously this fell straight through to the "done" event
        # with full_response still "", which the caller (chat.py) shows as
        # a generic "couldn't generate a complete response" with no logged
        # error at all. Force one final no-tools answer from everything
        # gathered so far instead of silently returning nothing.
        if not full_response.strip():
            try:
                # The system prompt still describes tools in detail (it's
                # unchanged from the tool-calling rounds above), but this
                # specific call has no tools parameter at all - without an
                # explicit steer, the model keeps narrating tool-seeking
                # intent ("Let me search for...") it now has no way to act
                # on, and trails off instead of answering. The forced
                # message overrides that as the most recent instruction.
                forced_messages = messages + [{
                    "role": "user",
                    "content": (
                        "No more tool calls are available for this turn. "
                        "Give your complete, direct final answer now using "
                        "everything gathered so far - do not say you will "
                        "search, check, or look anything up; just answer."
                    ),
                }]
                async for chunk in self.llm_service.generate_stream(
                    messages=forced_messages,
                    system_prompt=system_prompt
                ):
                    full_response += chunk
                    yield {"type": "token", "content": chunk}
            except Exception as e:
                logger.error(f"Forced final-answer generation failed: {e}")
                error_msg = "I apologize, but I encountered an error. Please try again."
                yield {"type": "token", "content": error_msg}
                full_response = error_msg

        # Final event
        yield {
            "type": "done",
            "response": full_response,
            "metadata": {
                "model": self.llm_service.get_current_config().get("model"),
                "sources": rag_context.get("sources", []) if rag_context else [],
                "tools_used": len(tool_results),
                "auto_video": auto_video,
            }
        }

    async def _check_for_tools(
        self,
        messages: List[Dict],
        system_prompt: str,
        tool_schemas: List[Dict]
    ) -> Dict[str, Any]:
        """Check if the LLM wants to use tools (non-streaming)"""
        try:
            # Ensure messages are plain dicts
            clean_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    cleaned = {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    }
                    # Preserve tool_calls/tool_call_id/name - dropping these
                    # (as this loop previously did) corrupts the tool-call
                    # round-trip the moment a second tool gets used: LiteLLM
                    # rejects a "tool" role message that isn't immediately
                    # preceded by an "assistant" message with matching
                    # tool_calls, which is exactly what stripping them here
                    # produces. Same fields litellm_service.py's
                    # _prepare_litellm_kwargs already preserves correctly.
                    if msg.get("role") == "assistant" and "tool_calls" in msg:
                        cleaned["tool_calls"] = msg["tool_calls"]
                        if not msg.get("content"):
                            cleaned["content"] = None
                    if msg.get("role") == "tool":
                        if "tool_call_id" in msg:
                            cleaned["tool_call_id"] = msg["tool_call_id"]
                        if "name" in msg:
                            cleaned["name"] = msg["name"]
                    clean_messages.append(cleaned)
                elif hasattr(msg, "content") and hasattr(msg, "type"):
                    # LangChain message object
                    role = "user" if msg.type == "human" else "assistant" if msg.type == "ai" else msg.type
                    clean_messages.append({
                        "role": role,
                        "content": msg.content
                    })
                else:
                    clean_messages.append({"role": "user", "content": str(msg)})

            # Use litellm with tools
            response = await self.llm_service.generate_with_tools(
                messages=clean_messages,
                system_prompt=system_prompt,
                tools=tool_schemas
            )
            return response
        except Exception as e:
            logger.warning(f"Tool checking failed: {e}, falling back to simple generation")
            # Fallback if generate_with_tools fails
            response = await self.llm_service.generate(
                messages=clean_messages if 'clean_messages' in dir() else messages,
                system_prompt=system_prompt
            )
            return {"content": response, "tool_calls": []}

    async def _fallback_invoke(
        self,
        message: str,
        rag_context: Optional[Dict],
        tools: List[BuiltTool]
    ) -> Dict[str, Any]:
        """Fallback processing without LangGraph"""
        system_prompt = build_system_prompt(
            include_tools=False,  # No tools in fallback
            include_citations=True,
            rag_context_xml=rag_context.get("context_xml", "") if rag_context else ""
        )

        try:
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt
            )

            return {
                "response": response,
                "sources": rag_context.get("sources", []) if rag_context else [],
                "model": self.llm_service.get_current_config().get("model"),
                "tools_used": [],
                "mode": "fallback"
            }

        except Exception as e:
            logger.error(f"Fallback invoke error: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your request. Please try again.",
                "error": str(e),
                "mode": "fallback"
            }

    def _format_result(
        self,
        state: Dict[str, Any],
        rag_context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Format the graph result for API response"""
        # Get search trail for transparency
        search_trail = state.get("search_trail", {})
        search_summary = search_trail.get("summary", "") if search_trail else ""

        return {
            "response": state.get("final_response", ""),
            "sources": rag_context.get("sources", []) if rag_context else [],
            "model": state.get("model_used"),
            "tools_used": state.get("tool_results", []),
            "learning_state": state.get("learning", {}),
            "search_trail": search_trail,
            "search_summary": search_summary,
            "query_classification": state.get("query_classification"),
            "mode": "langgraph"
        }


# =============================================================================
# Factory Function
# =============================================================================

_agent_instance: Optional[ScoratisAgent] = None


def create_agent(
    llm_service: Any,
    rag_service: Optional[Any] = None,
    web_search_service: Optional[Any] = None,
    langgraph_service: Optional[Any] = None,
    database_url: Optional[str] = None
) -> ScoratisAgent:
    """
    Create or get the Scoratis agent instance.

    Args:
        llm_service: LLM service for AI calls
        rag_service: RAG service for knowledge base
        web_search_service: Web search service
        langgraph_service: LangGraph service for state
        database_url: PostgreSQL URL for checkpointing

    Returns:
        ScoratisAgent instance
    """
    global _agent_instance

    if _agent_instance is None:
        _agent_instance = ScoratisAgent(
            llm_service=llm_service,
            rag_service=rag_service,
            web_search_service=web_search_service,
            langgraph_service=langgraph_service,
            database_url=database_url
        )

    return _agent_instance


def get_agent() -> Optional[ScoratisAgent]:
    """Get the current agent instance"""
    return _agent_instance
