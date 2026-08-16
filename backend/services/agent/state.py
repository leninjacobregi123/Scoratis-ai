"""
Agent State Module
Defines the stateful brain of the Scoratis agentic workflow.

The AgentState is passed through every node in the graph and holds:
- Message history (conversation memory)
- Tool execution results
- Learning state tracking
- RAG context and citations
- Scratchpad for reasoning persistence (agentic loop)
- Sub-agent delegation tracking
- Verification state
"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated, Sequence, Literal
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

# LangGraph message handling
try:
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Fallback: simple list append
    def add_messages(left: list, right: list) -> list:
        return left + right


class MessageRole(str, Enum):
    """Message roles in the conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class LearningState(str, Enum):
    """Student's learning progression states"""
    INITIAL = "initial"
    ENGAGED = "engaged"
    CONFUSED = "confused"
    STRUGGLING = "struggling"
    PROGRESSING = "progressing"
    UNDERSTANDING = "understanding"
    MASTERY = "mastery"


class AgentPhase(str, Enum):
    """Current phase in the agentic loop"""
    THINKING = "thinking"       # Initial reasoning
    RESEARCHING = "researching"  # Using tools to gather info
    DELEGATING = "delegating"   # Delegating to sub-agent
    DRAFTING = "drafting"       # Creating response
    VERIFYING = "verifying"     # Quality check
    REFINING = "refining"       # Improving based on verification
    COMPLETE = "complete"       # Final response ready


class SubAgentType(str, Enum):
    """Types of specialized sub-agents"""
    RESEARCH = "research"       # Deep knowledge retrieval
    ANALYSIS = "analysis"       # Complex reasoning/analysis
    SUMMARY = "summary"         # Summarization and synthesis
    EXPERT = "expert"           # Subject matter expertise
    FACT_CHECK = "fact_check"   # Verify accuracy


class VerificationResult(str, Enum):
    """Result of response verification"""
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    NEEDS_MORE_INFO = "needs_more_info"
    FACTUALLY_INCORRECT = "factually_incorrect"


@dataclass
class ToolCall:
    """Represents a tool call from the agent"""
    id: str
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments
        }


@dataclass
class ToolResult:
    """Result from executing a tool"""
    tool_call_id: str
    name: str
    result: Any
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "result": self.result,
            "error": self.error
        }


class Message(BaseModel):
    """Standard message structure for the agent"""
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # For tool messages
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "role": self.role if isinstance(self.role, str) else self.role.value,
            "content": self.content
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


class LearningContext(BaseModel):
    """Tracks the student's learning progression"""
    state: LearningState = LearningState.INITIAL
    topic: Optional[str] = None
    turn_count: int = 0
    confusion_count: int = 0
    understanding_signals: int = 0
    topics_discussed: List[str] = Field(default_factory=list)
    key_discoveries: List[str] = Field(default_factory=list)
    video_turns: List[int] = Field(default_factory=list)  # Turns where video was generated

    def increment_turn(self):
        self.turn_count += 1

    def add_topic(self, topic: str):
        if topic and topic not in self.topics_discussed:
            self.topics_discussed.append(topic)
            self.topics_discussed = self.topics_discussed[-10:]  # Keep last 10
            self.topic = topic

    def record_video(self, turn: int):
        self.video_turns.append(turn)
        self.video_turns = self.video_turns[-5:]  # Keep last 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value if isinstance(self.state, LearningState) else self.state,
            "topic": self.topic,
            "turn_count": self.turn_count,
            "confusion_count": self.confusion_count,
            "understanding_signals": self.understanding_signals,
            "topics_discussed": self.topics_discussed,
            "key_discoveries": self.key_discoveries,
            "video_turns": self.video_turns
        }


class RAGContext(BaseModel):
    """RAG retrieval context for the agent"""
    context_xml: str = ""
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    chunk_mapping: Dict[str, int] = Field(default_factory=dict)

    def has_context(self) -> bool:
        return bool(self.sources)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_xml": self.context_xml,
            "sources": self.sources,
            "chunk_mapping": self.chunk_mapping
        }


# =============================================================================
# Agentic Loop Components
# =============================================================================

class Scratchpad(BaseModel):
    """
    Reasoning scratchpad for the agentic loop.
    Persists agent's thinking across iterations.
    """
    thoughts: List[str] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)
    plan: List[str] = Field(default_factory=list)
    current_goal: Optional[str] = None
    iteration: int = 0
    confidence: float = 0.0
    needs_more_info: bool = False
    should_delegate: bool = False
    delegation_reason: Optional[str] = None

    def add_thought(self, thought: str):
        """Add a reasoning thought"""
        self.thoughts.append(f"[{self.iteration}] {thought}")
        self.thoughts = self.thoughts[-10:]  # Keep last 10

    def add_observation(self, observation: str):
        """Add an observation from tool use"""
        self.observations.append(f"[{self.iteration}] {observation}")
        self.observations = self.observations[-10:]

    def set_plan(self, steps: List[str]):
        """Set the execution plan"""
        self.plan = steps

    def increment_iteration(self):
        self.iteration += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thoughts": self.thoughts,
            "observations": self.observations,
            "plan": self.plan,
            "current_goal": self.current_goal,
            "iteration": self.iteration,
            "confidence": self.confidence,
            "needs_more_info": self.needs_more_info,
            "should_delegate": self.should_delegate,
            "delegation_reason": self.delegation_reason
        }

    def to_context_string(self) -> str:
        """Convert to string for LLM context"""
        parts = []
        if self.current_goal:
            parts.append(f"Current Goal: {self.current_goal}")
        if self.plan:
            parts.append(f"Plan: {' → '.join(self.plan)}")
        if self.thoughts:
            parts.append(f"Recent Thoughts: {'; '.join(self.thoughts[-3:])}")
        if self.observations:
            parts.append(f"Recent Observations: {'; '.join(self.observations[-3:])}")
        return "\n".join(parts)


class SubAgentResult(BaseModel):
    """Result from a sub-agent delegation"""
    agent_type: str
    task: str
    result: str
    confidence: float = 0.0
    sources_used: List[str] = Field(default_factory=list)
    iteration_count: int = 0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "task": self.task,
            "result": self.result,
            "confidence": self.confidence,
            "sources_used": self.sources_used,
            "iteration_count": self.iteration_count,
            "success": self.success,
            "error": self.error
        }


class VerificationState(BaseModel):
    """State of response verification"""
    verified: bool = False
    result: Optional[str] = None  # approved, needs_revision, etc.
    feedback: Optional[str] = None
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    revision_count: int = 0
    max_revisions: int = 2

    def needs_revision(self) -> bool:
        return self.result == VerificationResult.NEEDS_REVISION.value and \
               self.revision_count < self.max_revisions

    def mark_verified(self, result: str, feedback: str = "", confidence: float = 1.0):
        self.verified = True
        self.result = result
        self.feedback = feedback
        self.confidence_score = confidence

    def add_issue(self, issue: str):
        self.issues.append(issue)

    def add_suggestion(self, suggestion: str):
        self.suggestions.append(suggestion)

    def increment_revision(self):
        self.revision_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "result": self.result,
            "feedback": self.feedback,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "confidence_score": self.confidence_score,
            "revision_count": self.revision_count,
            "max_revisions": self.max_revisions
        }


class SearchAttempt(BaseModel):
    """
    Records a search attempt for transparency (search trail).

    Used to track which sources were searched and their results,
    enabling the agent to show the user what was searched.
    """
    source: str  # "knowledge_base", "web_search", "conversations"
    query: str
    results_count: int = 0
    success: bool = True
    had_results: bool = False
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "query": self.query,
            "results_count": self.results_count,
            "success": self.success,
            "had_results": self.had_results,
            "timestamp": self.timestamp,
            "error": self.error
        }

    @staticmethod
    def from_tool_result(tool_name: str, result: Dict[str, Any]) -> "SearchAttempt":
        """Create SearchAttempt from a tool result."""
        return SearchAttempt(
            source=tool_name,
            query=result.get("query", ""),
            results_count=result.get("results_count", 0),
            success=result.get("success", True),
            had_results=result.get("results_count", 0) > 0,
            error=result.get("error")
        )


class SearchTrail(BaseModel):
    """
    Tracks all search attempts for transparency.

    This allows the agent to inform the user about what sources were searched:
    - "I checked your notes but didn't find anything on this topic."
    - "Based on your saved documents [citations]..."
    - "I found this information on the web..."
    """
    attempts: List[SearchAttempt] = Field(default_factory=list)

    def add_attempt(self, attempt: SearchAttempt):
        """Add a search attempt to the trail."""
        self.attempts.append(attempt)

    def add_from_tool_result(self, tool_name: str, result: Dict[str, Any]):
        """Add a search attempt from a tool result."""
        attempt = SearchAttempt.from_tool_result(tool_name, result)
        self.attempts.append(attempt)

    def get_summary(self) -> str:
        """Get a human-readable summary of the search trail."""
        if not self.attempts:
            return ""

        lines = ["**Sources searched:**"]
        for attempt in self.attempts:
            source_name = attempt.source.replace("_", " ").title()
            if attempt.had_results:
                lines.append(f"- {source_name}: {attempt.results_count} results found")
            else:
                lines.append(f"- {source_name}: No results found")

        return "\n".join(lines)

    def has_any_results(self) -> bool:
        """Check if any search returned results."""
        return any(a.had_results for a in self.attempts)

    def all_failed(self) -> bool:
        """Check if all searches returned no results."""
        return len(self.attempts) > 0 and not self.has_any_results()

    def kb_searched(self) -> bool:
        """Check if knowledge base was searched."""
        return any(a.source in ["search_knowledge_base", "knowledge_base"]
                   for a in self.attempts)

    def web_searched(self) -> bool:
        """Check if web was searched."""
        return any(a.source in ["web_search"] for a in self.attempts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempts": [a.to_dict() for a in self.attempts],
            "has_any_results": self.has_any_results(),
            "all_failed": self.all_failed(),
            "summary": self.get_summary()
        }


class StopCondition(BaseModel):
    """Conditions for stopping the agentic loop"""
    max_iterations: int = 7
    current_iteration: int = 0
    confidence_threshold: float = 0.8
    current_confidence: float = 0.0
    verification_required: bool = True
    verified: bool = False
    explicit_stop: bool = False
    stop_reason: Optional[str] = None

    def should_stop(self) -> bool:
        """Check if the loop should stop"""
        # Explicit stop
        if self.explicit_stop:
            return True

        # Max iterations reached
        if self.current_iteration >= self.max_iterations:
            self.stop_reason = "max_iterations"
            return True

        # High confidence achieved
        if self.current_confidence >= self.confidence_threshold:
            if not self.verification_required or self.verified:
                self.stop_reason = "confidence_achieved"
                return True

        return False

    def increment(self):
        self.current_iteration += 1

    def set_confidence(self, confidence: float):
        self.current_confidence = confidence

    def mark_verified(self):
        self.verified = True

    def force_stop(self, reason: str):
        self.explicit_stop = True
        self.stop_reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "confidence_threshold": self.confidence_threshold,
            "current_confidence": self.current_confidence,
            "verification_required": self.verification_required,
            "verified": self.verified,
            "explicit_stop": self.explicit_stop,
            "stop_reason": self.stop_reason,
            "should_stop": self.should_stop()
        }


class AgentState(TypedDict):
    """
    The central state object for the Scoratis Agent.

    This is the "brain" of the agent - passed to every node in the graph
    and persisted via the checkpointer for long-term memory.

    Key Fields:
    - messages: Full conversation history (managed by add_messages reducer)
    - session_id: Unique conversation identifier (thread_id for checkpointing)
    - learning: Learning progression tracking
    - rag_context: Retrieved context from knowledge base
    - pending_tool_calls: Tools the agent wants to execute
    - tool_results: Results from executed tools
    - final_response: The agent's final response (after reasoning)

    Agentic Loop Fields:
    - scratchpad: Reasoning persistence across iterations
    - phase: Current phase in the agentic loop
    - stop_condition: Conditions for stopping the loop
    - verification: Response verification state
    - sub_agent_results: Results from delegated sub-agents
    - draft_response: In-progress response (before verification)
    """

    # === Core Message History ===
    # Uses add_messages reducer for proper history management
    messages: Annotated[Sequence[Dict[str, Any]], add_messages]

    # === Session Context ===
    session_id: str
    user_id: int

    # === Current Turn State ===
    current_input: str  # Latest user message
    final_response: Optional[str]  # Agent's final response
    draft_response: Optional[str]  # In-progress response (before verification)

    # === Learning State ===
    learning: Dict[str, Any]  # LearningContext serialized

    # === RAG Context ===
    rag_context: Optional[Dict[str, Any]]  # RAGContext serialized
    web_search_used: bool

    # === Tool Execution ===
    pending_tool_calls: List[Dict[str, Any]]  # Tools to execute
    tool_results: List[Dict[str, Any]]  # Results from tools

    # === Agentic Loop Components ===
    scratchpad: Optional[Dict[str, Any]]  # Scratchpad serialized
    phase: str  # Current AgentPhase
    stop_condition: Optional[Dict[str, Any]]  # StopCondition serialized

    # === Sub-Agent Delegation ===
    sub_agent_results: List[Dict[str, Any]]  # SubAgentResult list
    pending_delegation: Optional[Dict[str, Any]]  # Pending delegation request

    # === Verification ===
    verification: Optional[Dict[str, Any]]  # VerificationState serialized

    # === Search Trail (Transparency) ===
    search_trail: Optional[Dict[str, Any]]  # SearchTrail serialized
    query_classification: Optional[Dict[str, Any]]  # QueryClassification result

    # === Metadata ===
    model_used: Optional[str]
    error: Optional[str]


def create_initial_state(
    session_id: str,
    user_id: int = 1,
    enable_verification: bool = True
) -> AgentState:
    """Create a fresh agent state for a new conversation"""
    return AgentState(
        messages=[],
        session_id=session_id,
        user_id=user_id,
        current_input="",
        final_response=None,
        draft_response=None,
        learning=LearningContext().to_dict(),
        rag_context=None,
        web_search_used=False,
        pending_tool_calls=[],
        tool_results=[],
        # Agentic loop components
        scratchpad=Scratchpad().to_dict(),
        phase=AgentPhase.THINKING.value,
        stop_condition=StopCondition(
            verification_required=enable_verification
        ).to_dict(),
        # Sub-agent delegation
        sub_agent_results=[],
        pending_delegation=None,
        # Verification
        verification=VerificationState().to_dict(),
        # Search trail (transparency)
        search_trail=SearchTrail().to_dict(),
        query_classification=None,
        model_used=None,
        error=None
    )


def merge_state_update(state: AgentState, update: Dict[str, Any]) -> AgentState:
    """
    Merge an update into the current state.
    Handles special cases like message appending.
    """
    new_state = dict(state)

    for key, value in update.items():
        if key == "messages" and key in new_state:
            # Messages use the add_messages reducer
            # Already handled by LangGraph, but fallback for manual mode
            if isinstance(value, list):
                new_state[key] = add_messages(new_state[key], value)
        else:
            new_state[key] = value

    return AgentState(**new_state)
