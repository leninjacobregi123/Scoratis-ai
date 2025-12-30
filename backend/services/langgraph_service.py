"""
LangGraph Service for Scoratis
Manages conversation state with PostgreSQL checkpointing and LLM-based video analysis.
"""

import json
import logging
import os
from typing import TypedDict, List, Optional, Annotated, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# LangGraph imports - will be available after pip install
try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not installed. Using fallback mode.")


# ============================================================================
# State Models
# ============================================================================

class Message(BaseModel):
    """Standard message structure for LangGraph"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


class VideoAnalysisResult(BaseModel):
    """Result of LLM-based video analysis"""
    is_visualizable: bool = False
    topic_for_video: Optional[str] = None
    visualization_type: Optional[str] = None  # 'process', 'structure', 'concept', 'comparison', 'transformation'
    key_concepts: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""


class LearningStateData(BaseModel):
    """Learning progression tracking"""
    current_state: str = "initial"  # initial, engaged, confused, struggling, progressing, understanding, mastery
    topic: Optional[str] = None
    turn_count: int = 0
    confusion_count: int = 0
    understanding_signals: int = 0
    topics_discussed: List[str] = Field(default_factory=list)
    key_discoveries: List[str] = Field(default_factory=list)


class ConversationState(TypedDict):
    """
    LangGraph State Schema for Scoratis Chat

    This replaces:
    - conversation_memory dict in main.py
    - memory_service in-memory storage
    - conversation_analyzer.ConversationState
    """
    # Core message history
    messages: List[Dict[str, str]]

    # Session identification
    session_id: str
    subject: str  # physics, chemistry, etc.

    # Learning state tracking
    learning_state: Dict[str, Any]

    # Video analysis result (updated after each turn)
    video_analysis: Optional[Dict[str, Any]]
    video_eligible: bool

    # Current turn context
    current_user_message: str
    current_ai_response: str

    # RAG context (retrieved from database)
    rag_context: Optional[str]

    # Metadata
    model_used: Optional[str]
    search_used: bool


# ============================================================================
# Video Analysis Prompt - Pure AI-Based (No Hardcoded Patterns)
# ============================================================================

VIDEO_ANALYSIS_PROMPT = """You are an intelligent video generation advisor analyzing educational conversations.
Your task is to determine if a short animated video (15-30 seconds) would enhance the student's understanding.

## CONTEXT
Subject Area: {subject}
Previous Topics Discussed: {topics_discussed}
Student's Learning State: {learning_state}

## CURRENT EXCHANGE
Student Question: {user_message}

Tutor Response: {ai_response}

## YOUR ANALYSIS TASK

Carefully analyze this educational exchange and determine:

1. **Would visualization genuinely help?**
   - Does this content involve something that can be SHOWN rather than just told?
   - Would seeing this in motion or as a diagram clarify the concept?
   - Is there a spatial, temporal, or process-based element?

2. **What exactly should be visualized?**
   - Identify the core concept that needs visual representation
   - Think about what visual elements would make this clearer
   - Consider what animations or transformations would help

3. **Video Value Assessment:**
   - Would a 15-30 second animation add significant value?
   - Or is the text explanation already sufficient?

## DECISION GUIDELINES

**RECOMMEND VIDEO (confidence 0.6-1.0) when content involves:**
- Physical or natural processes (how things work, cycles, transformations)
- Spatial structures or relationships (anatomy, architecture, geometry, molecules)
- Mathematical concepts with graphical representations
- Cause-and-effect chains or sequences
- Algorithms, data flows, or system behaviors
- Comparisons that benefit from side-by-side visualization
- Abstract concepts that become clearer with visual metaphors
- Motion, change, or dynamics of any kind

**DECLINE VIDEO (confidence 0.0-0.5) when:**
- Content is purely conversational or casual
- Topic is inherently non-visual (pure definitions, opinions)
- Text explanation is already complete and clear
- Student is seeking factual lookups or quick answers
- No specific concept exists to animate

## RESPONSE FORMAT

Return ONLY a JSON object:

{{
    "is_visualizable": true,
    "topic_for_video": "Clear, Engaging Video Title",
    "visualization_type": "process|structure|concept|comparison|transformation|diagram|simulation",
    "key_concepts": ["main concept", "supporting concept 1", "supporting concept 2"],
    "confidence": 0.85,
    "reason": "Brief explanation of why visualization would help"
}}

OR if not visualizable:

{{
    "is_visualizable": false,
    "topic_for_video": null,
    "visualization_type": null,
    "key_concepts": [],
    "confidence": 0.3,
    "reason": "Why visualization wouldn't add value here"
}}"""

VIDEO_ANALYSIS_SYSTEM_PROMPT = """You are an AI video content advisor for an educational platform.
Your job is to intelligently determine when visual animations would genuinely enhance learning.
Make decisions based on the actual content - there are no predefined topics that should or shouldn't have videos.
Every decision should be based on whether visualization would truly help understanding.
Return ONLY valid JSON, no other text or markdown."""


# ============================================================================
# LangGraph Service Class
# ============================================================================

class LangGraphService:
    """
    Service for managing conversation state using LangGraph.
    Provides PostgreSQL-backed checkpointing and LLM-based video analysis.
    """

    def __init__(self, database_url: str, llm_service=None, rag_service=None):
        self.database_url = database_url
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.graph = None
        self.checkpointer = None
        self._initialized = False

        # Fallback in-memory state when LangGraph not available
        self._fallback_states: Dict[str, ConversationState] = {}

    async def initialize(self):
        """Initialize the LangGraph service."""
        if self._initialized:
            return

        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, using fallback mode")
            self._initialized = True
            return

        # Use fallback mode with in-memory state management
        # This provides full video analysis functionality without PostgreSQL checkpointing
        # The LLM-based video analysis and pattern-based fallback work identically
        logger.info("LangGraph service initialized with in-memory state management")
        self._initialized = True

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(ConversationState)

        # Add nodes
        graph.add_node("process_input", self._process_input_node)
        graph.add_node("generate_response", self._generate_response_node)
        graph.add_node("analyze_video", self._analyze_video_node)
        graph.add_node("format_output", self._format_output_node)

        # Define edges
        graph.set_entry_point("process_input")
        graph.add_edge("process_input", "generate_response")
        graph.add_edge("generate_response", "analyze_video")
        graph.add_edge("analyze_video", "format_output")
        graph.add_edge("format_output", END)

        return graph.compile(checkpointer=self.checkpointer)

    async def _process_input_node(self, state: ConversationState) -> Dict[str, Any]:
        """Process input and retrieve RAG context."""
        session_id = state.get("session_id", "")
        user_message = state.get("current_user_message", "")

        # RAG context is handled by the main endpoint if needed
        rag_context = None

        # Add user message to history
        messages = list(state.get("messages", []))
        messages.append({"role": "user", "content": user_message})

        # Update learning state
        learning_state = state.get("learning_state", {})
        if not learning_state:
            learning_state = LearningStateData().model_dump()
        learning_state["turn_count"] = learning_state.get("turn_count", 0) + 1

        return {
            "messages": messages,
            "rag_context": rag_context,
            "learning_state": learning_state
        }

    async def _generate_response_node(self, state: ConversationState) -> Dict[str, Any]:
        """Generate LLM response."""
        if not self.llm_service:
            return {"current_ai_response": "LLM service not available"}

        messages = state.get("messages", [])
        subject = state.get("subject", "general")
        rag_context = state.get("rag_context")

        try:
            # Import here to avoid circular imports
            from prompts import get_subject_prompt

            # Build system prompt with RAG context
            system_prompt = get_subject_prompt(subject)
            if rag_context:
                system_prompt = f"{system_prompt}\n\n## RELEVANT CONTEXT\n{rag_context}"

            # Generate response
            response = await self.llm_service.generate(
                messages=messages,
                system_prompt=system_prompt
            )

            # Add to messages
            new_messages = list(messages)
            new_messages.append({"role": "assistant", "content": response})

            return {
                "messages": new_messages,
                "current_ai_response": response,
                "model_used": self.llm_service.current_config.get("model", "unknown")
            }
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            fallback = "I apologize, but I'm having trouble generating a response right now. Could you please try again?"
            return {
                "current_ai_response": fallback,
                "model_used": "fallback"
            }

    async def _analyze_video_node(self, state: ConversationState) -> Dict[str, Any]:
        """Analyze if content is suitable for video visualization using pure AI analysis."""
        user_message = state.get("current_user_message", "")
        ai_response = state.get("current_ai_response", "")
        subject = state.get("subject", "general")
        learning_state = state.get("learning_state", {})

        # Skip analysis for very short responses
        if len(ai_response) < 100:
            return {
                "video_analysis": VideoAnalysisResult(
                    is_visualizable=False,
                    reason="Response too short for visualization"
                ).model_dump(),
                "video_eligible": False
            }

        # Pure AI-based analysis (no pattern fallback)
        if self.llm_service:
            try:
                analysis = await self._llm_video_analysis(
                    user_message=user_message,
                    ai_response=ai_response,
                    subject=subject,
                    learning_state=learning_state
                )
                return {
                    "video_analysis": analysis.model_dump(),
                    "video_eligible": analysis.is_visualizable and analysis.confidence > 0.6
                }
            except Exception as e:
                logger.error(f"AI video analysis failed: {e}")
                return {
                    "video_analysis": VideoAnalysisResult(
                        is_visualizable=False,
                        reason=f"AI analysis failed: {str(e)}"
                    ).model_dump(),
                    "video_eligible": False
                }

        # No LLM service available
        return {
            "video_analysis": VideoAnalysisResult(
                is_visualizable=False,
                reason="LLM service not available for video analysis"
            ).model_dump(),
            "video_eligible": False
        }

    async def _llm_video_analysis(
        self,
        user_message: str,
        ai_response: str,
        subject: str,
        learning_state: Dict
    ) -> VideoAnalysisResult:
        """Pure AI-based video analysis - no hardcoded patterns."""
        topics_discussed = learning_state.get("topics_discussed", [])
        current_state = learning_state.get("current_state", "initial")

        prompt = VIDEO_ANALYSIS_PROMPT.format(
            subject=subject,
            topics_discussed=", ".join(topics_discussed[-5:]) if topics_discussed else "none",
            learning_state=current_state,
            user_message=user_message[:500],
            ai_response=ai_response[:2000]
        )

        response = await self.llm_service.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=VIDEO_ANALYSIS_SYSTEM_PROMPT
        )

        # Parse JSON response
        try:
            clean_response = self._extract_json_from_response(response)
            data = json.loads(clean_response)
            return VideoAnalysisResult(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse video analysis JSON: {e}")
            return VideoAnalysisResult(
                is_visualizable=False,
                reason=f"AI analysis parsing failed: {str(e)}"
            )

    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response that might contain markdown or extra text."""
        clean_response = response.strip()

        # Remove markdown code blocks if present
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            lines = lines[1:]  # Remove first line (```json or ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_response = "\n".join(lines)

        # Find JSON object
        start = clean_response.find('{')
        end = clean_response.rfind('}')
        if start != -1 and end != -1 and end > start:
            return clean_response[start:end+1]

        return clean_response.strip()

    async def _format_output_node(self, state: ConversationState) -> Dict[str, Any]:
        """Format the final output state."""
        # Update topic in learning state if video is eligible
        learning_state = state.get("learning_state", {})
        video_analysis = state.get("video_analysis", {})

        if video_analysis and video_analysis.get("is_visualizable"):
            topic = video_analysis.get("topic_for_video")
            if topic:
                topics = learning_state.get("topics_discussed", [])
                if topic not in topics:
                    topics.append(topic)
                    learning_state["topics_discussed"] = topics[-10:]  # Keep last 10
                learning_state["topic"] = topic

        return {"learning_state": learning_state}

    # ========================================================================
    # Public API
    # ========================================================================

    async def analyze_for_video(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        subject: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze a conversation turn for video potential.
        This method only does video analysis, not response generation.

        Returns:
            Dict with: video_available, video_topic, video_concepts, video_type,
                      learning_state, turn_count
        """
        await self.initialize()

        # Get or create state for tracking
        if session_id not in self._fallback_states:
            self._fallback_states[session_id] = self._create_initial_state(session_id, subject)

        state = self._fallback_states[session_id]
        state["current_user_message"] = user_message
        state["current_ai_response"] = ai_response
        state["subject"] = subject

        # Update message history
        messages = list(state.get("messages", []))
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": ai_response})
        state["messages"] = messages[-20:]  # Keep last 20

        # Update learning state
        learning_state = state.get("learning_state", {})
        if not learning_state:
            learning_state = LearningStateData().model_dump()
        learning_state["turn_count"] = learning_state.get("turn_count", 0) + 1
        state["learning_state"] = learning_state

        # Run video analysis only
        video_result = await self._analyze_video_node(state)
        state.update(video_result)

        # Update topics if visualizable
        format_result = await self._format_output_node(state)
        state.update(format_result)

        self._fallback_states[session_id] = state

        video_analysis = state.get("video_analysis", {})
        return {
            "video_available": state.get("video_eligible", False),
            "video_topic": video_analysis.get("topic_for_video") if video_analysis else None,
            "video_concepts": video_analysis.get("key_concepts", []) if video_analysis else [],
            "video_type": video_analysis.get("visualization_type") if video_analysis else None,
            "learning_state": learning_state.get("current_state", "initial"),
            "turn_count": learning_state.get("turn_count", 0)
        }

    async def process_message(
        self,
        session_id: str,
        message: str,
        subject: str = "general"
    ) -> Dict[str, Any]:
        """
        Process a user message through the LangGraph pipeline.

        Returns:
            Dict with: reply, video_available, video_topic, video_concepts,
                      video_type, learning_state, turn_count, model
        """
        await self.initialize()

        # Get or create initial state
        config = {"configurable": {"thread_id": session_id}}

        if self.graph:
            # Use LangGraph
            try:
                # Get existing state or create new
                existing = await self.graph.aget_state(config)
                if existing and existing.values:
                    initial_state = existing.values
                else:
                    initial_state = self._create_initial_state(session_id, subject)

                # Update with new message
                initial_state["current_user_message"] = message
                initial_state["subject"] = subject

                # Run the graph
                result = await self.graph.ainvoke(initial_state, config=config)

                return self._format_response(result)
            except Exception as e:
                logger.error(f"LangGraph processing failed: {e}")
                # Fall through to fallback

        # Fallback processing
        return await self._fallback_process(session_id, message, subject)

    def _create_initial_state(self, session_id: str, subject: str) -> ConversationState:
        """Create initial conversation state."""
        return {
            "messages": [],
            "session_id": session_id,
            "subject": subject,
            "learning_state": LearningStateData().model_dump(),
            "video_analysis": None,
            "video_eligible": False,
            "current_user_message": "",
            "current_ai_response": "",
            "rag_context": None,
            "model_used": None,
            "search_used": False
        }

    def _format_response(self, state: Dict) -> Dict[str, Any]:
        """Format state into API response."""
        video_analysis = state.get("video_analysis", {})
        learning_state = state.get("learning_state", {})

        return {
            "reply": state.get("current_ai_response", ""),
            "video_available": state.get("video_eligible", False),
            "video_topic": video_analysis.get("topic_for_video") if video_analysis else None,
            "video_concepts": video_analysis.get("key_concepts", []) if video_analysis else [],
            "video_type": video_analysis.get("visualization_type") if video_analysis else None,
            "learning_state": learning_state.get("current_state", "initial"),
            "turn_count": learning_state.get("turn_count", 0),
            "model": state.get("model_used", "unknown"),
            "source": "llm"
        }

    async def _fallback_process(
        self,
        session_id: str,
        message: str,
        subject: str
    ) -> Dict[str, Any]:
        """Fallback processing when LangGraph is not available."""
        # Get or create state
        if session_id not in self._fallback_states:
            self._fallback_states[session_id] = self._create_initial_state(session_id, subject)

        state = self._fallback_states[session_id]
        state["current_user_message"] = message
        state["subject"] = subject

        # Process through nodes manually
        state.update(await self._process_input_node(state))
        state.update(await self._generate_response_node(state))
        state.update(await self._analyze_video_node(state))
        state.update(await self._format_output_node(state))

        # Keep only last 20 messages
        if len(state["messages"]) > 20:
            state["messages"] = state["messages"][-20:]

        self._fallback_states[session_id] = state

        return self._format_response(state)

    async def get_video_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get video generation context for a session."""
        await self.initialize()

        config = {"configurable": {"thread_id": session_id}}

        if self.graph:
            try:
                state_snapshot = await self.graph.aget_state(config)
                if state_snapshot and state_snapshot.values:
                    state = state_snapshot.values
                    video_analysis = state.get("video_analysis", {})

                    if not state.get("video_eligible"):
                        return None

                    return {
                        "topic_title": video_analysis.get("topic_for_video"),
                        "key_concepts": video_analysis.get("key_concepts", []),
                        "visualization_hints": [
                            f"Visualize {c}" for c in video_analysis.get("key_concepts", [])
                        ],
                        "visualization_type": video_analysis.get("visualization_type"),
                        "conversation_summary": self._build_summary(state),
                        "learning_state": state.get("learning_state", {}).get("current_state"),
                        "duration_suggestion": 20  # 15-30 seconds target
                    }
            except Exception as e:
                logger.error(f"Failed to get video context: {e}")

        # Fallback
        if session_id in self._fallback_states:
            state = self._fallback_states[session_id]
            video_analysis = state.get("video_analysis", {})

            if not state.get("video_eligible"):
                return None

            return {
                "topic_title": video_analysis.get("topic_for_video"),
                "key_concepts": video_analysis.get("key_concepts", []),
                "visualization_hints": [
                    f"Visualize {c}" for c in video_analysis.get("key_concepts", [])
                ],
                "visualization_type": video_analysis.get("visualization_type"),
                "conversation_summary": self._build_summary(state),
                "learning_state": state.get("learning_state", {}).get("current_state"),
                "duration_suggestion": 20
            }

        return None

    def _build_summary(self, state: Dict) -> str:
        """Build conversation summary for video context."""
        messages = state.get("messages", [])[-4:]  # Last 2 exchanges
        summary_parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")[:200]
            summary_parts.append(f"{role.capitalize()}: {content}")

        return "\n".join(summary_parts)

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session context for video analysis.
        Provides conversation history summary for intelligent decisions.

        Returns:
            Dict with topics_discussed, turn_count, current_topic, learning_state, etc.
        """
        await self.initialize()

        if session_id not in self._fallback_states:
            return {
                "topics_discussed": [],
                "turn_count": 0,
                "current_topic": None,
                "learning_state": "initial",
                "key_discoveries": [],
                "recent_video_turns": []
            }

        state = self._fallback_states[session_id]
        learning_state = state.get("learning_state", {})

        return {
            "topics_discussed": learning_state.get("topics_discussed", []),
            "turn_count": learning_state.get("turn_count", 0),
            "current_topic": learning_state.get("topic"),
            "learning_state": learning_state.get("current_state", "initial"),
            "key_discoveries": learning_state.get("key_discoveries", []),
            "recent_video_turns": state.get("recent_video_turns", [])
        }

    async def get_summary(self, session_id: str) -> str:
        """
        Build a concise summary of conversation for video context.
        Used by video generation to understand what to visualize.
        """
        if session_id not in self._fallback_states:
            return ""

        state = self._fallback_states[session_id]
        return self._build_summary(state)

    def record_video_generation(self, session_id: str, turn_number: int):
        """Record that a video was generated on this turn (for cooldown tracking)."""
        if session_id in self._fallback_states:
            state = self._fallback_states[session_id]
            recent = state.get("recent_video_turns", [])
            recent.append(turn_number)
            state["recent_video_turns"] = recent[-5:]  # Keep last 5

    async def clear_session(self, session_id: str):
        """Clear a session's state."""
        if session_id in self._fallback_states:
            del self._fallback_states[session_id]

        # Note: LangGraph checkpoints are immutable, so we create a new thread
        # by using a different session_id or letting it expire


# ============================================================================
# Global Service Instance
# ============================================================================

_langgraph_service: Optional[LangGraphService] = None


def get_langgraph_service() -> Optional[LangGraphService]:
    """Get the global LangGraph service instance."""
    return _langgraph_service


def initialize_langgraph_service(database_url: str, llm_service=None, rag_service=None) -> LangGraphService:
    """Initialize the global LangGraph service."""
    global _langgraph_service
    _langgraph_service = LangGraphService(
        database_url=database_url,
        llm_service=llm_service,
        rag_service=rag_service
    )
    return _langgraph_service
