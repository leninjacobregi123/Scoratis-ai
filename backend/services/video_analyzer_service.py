"""
Video Analyzer Service for Scoratis
Pure AI-based service for deciding if chat content warrants automatic video generation.
All decisions are made by the LLM - no hardcoded patterns or templates.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class VisualizationType(str, Enum):
    PROCESS = "process"          # Step-by-step processes
    STRUCTURE = "structure"      # Physical/spatial structures
    CONCEPT = "concept"          # Abstract concepts made visual
    COMPARISON = "comparison"    # Side-by-side comparisons
    TRANSFORMATION = "transformation"  # Changes over time
    DIAGRAM = "diagram"          # Charts, graphs, relationships
    SIMULATION = "simulation"    # Interactive/dynamic visualizations


@dataclass
class VisualizationDecision:
    """Result of AI visualization analysis"""
    should_generate: bool
    confidence: float = 0.0
    topic: str = ""
    duration_seconds: int = 20
    visualization_type: str = "concept"
    key_concepts: List[str] = field(default_factory=list)
    visual_elements: List[str] = field(default_factory=list)
    animation_suggestions: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_generate": self.should_generate,
            "confidence": self.confidence,
            "topic": self.topic,
            "duration_seconds": self.duration_seconds,
            "visualization_type": self.visualization_type,
            "key_concepts": self.key_concepts,
            "visual_elements": self.visual_elements,
            "animation_suggestions": self.animation_suggestions,
            "rejection_reason": self.rejection_reason
        }


class VideoAnalyzerService:
    """
    Pure AI-based service for deciding if chat content warrants automatic video generation.
    All decisions are made by the LLM - no hardcoded patterns or templates.
    """

    # Configuration thresholds
    MIN_RESPONSE_LENGTH = 150       # Skip very short responses
    MIN_CONFIDENCE = 0.70           # AI confidence threshold for auto-generation
    COOLDOWN_TURNS = 3              # Don't generate back-to-back

    def __init__(self, llm_service=None, langgraph_service=None):
        self.llm_service = llm_service
        self.langgraph_service = langgraph_service
        self._session_video_history: Dict[str, List[int]] = {}

    async def should_auto_generate(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        subject: str,
        turn_count: int = 0
    ) -> VisualizationDecision:
        """
        Main entry point: Use AI to decide if we should auto-generate a video.
        Completely AI-driven decision making with no hardcoded patterns.
        """
        logger.info(f"[VideoAnalyzer] AI analyzing: '{user_message[:50]}...' (response len: {len(ai_response)})")

        # Basic validation: response too short
        if len(ai_response) < self.MIN_RESPONSE_LENGTH:
            logger.info(f"[VideoAnalyzer] Skipped: Response too short ({len(ai_response)} chars)")
            return VisualizationDecision(
                should_generate=False,
                rejection_reason="Response too short for meaningful visualization"
            )

        # Cooldown check - don't generate if recent video exists
        recent_video_turns = self._session_video_history.get(session_id, [])
        if any(turn_count - turn < self.COOLDOWN_TURNS for turn in recent_video_turns):
            logger.info(f"[VideoAnalyzer] Skipped: Cooldown active (recent turns: {recent_video_turns})")
            return VisualizationDecision(
                should_generate=False,
                rejection_reason="Recent video cooldown active"
            )

        # Pure AI-based analysis
        if not self.llm_service:
            logger.warning("[VideoAnalyzer] No LLM service available for AI analysis")
            return VisualizationDecision(
                should_generate=False,
                rejection_reason="LLM service not available for analysis"
            )

        try:
            result = await self._ai_video_analysis(
                session_id, user_message, ai_response, subject, turn_count
            )

            if result.should_generate and result.confidence >= self.MIN_CONFIDENCE:
                logger.info(f"[VideoAnalyzer] AI APPROVED: '{result.topic}' (confidence: {result.confidence:.2f})")
                return result
            else:
                logger.info(f"[VideoAnalyzer] AI declined: {result.rejection_reason} (confidence: {result.confidence:.2f})")
                return result

        except Exception as e:
            logger.error(f"[VideoAnalyzer] AI analysis failed: {e}")
            return VisualizationDecision(
                should_generate=False,
                rejection_reason=f"AI analysis error: {str(e)}"
            )

    async def _ai_video_analysis(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        subject: str,
        turn_count: int
    ) -> VisualizationDecision:
        """
        Pure AI-based analysis for video generation decisions.
        The LLM determines everything: whether to generate, what to visualize, and how.
        """
        # Get conversation context if available
        context_info = ""
        recent_topics = []
        if self.langgraph_service:
            try:
                context = await self.langgraph_service.get_session_context(session_id)
                recent_topics = context.get("topics_discussed", [])
                if recent_topics:
                    context_info = f"\nPrevious topics in this session: {', '.join(recent_topics[-5:])}"
                if context.get("key_discoveries"):
                    context_info += f"\nStudent discoveries: {', '.join(context['key_discoveries'][-3:])}"
            except Exception:
                pass

        analysis_prompt = f"""You are an intelligent video generation advisor for an educational platform.
Analyze this conversation and decide if a short educational video (15-30 seconds) would enhance learning.

## CONTEXT
Subject Area: {subject}
Conversation Turn: {turn_count}{context_info}

## CURRENT EXCHANGE
Student asked: {user_message}

Tutor responded: {ai_response[:1500]}

## YOUR TASK
Analyze this content and determine:
1. Would a visual animation genuinely help the student understand this better?
2. What specific concept or process should be visualized?
3. What visual elements and animations would be most effective?

## DECISION CRITERIA

RECOMMEND VIDEO (high confidence 0.7-1.0) when the content involves:
- Physical processes that unfold over time (any scientific, mechanical, or natural process)
- Spatial relationships or 3D structures (molecules, anatomy, architecture, geometry)
- Mathematical concepts with visual representations (graphs, transformations, proofs)
- Cause-and-effect chains that benefit from animation
- Comparisons where side-by-side visuals help
- Abstract concepts that become clearer with visual metaphors
- Data flows, algorithms, or system behaviors
- Any topic where "showing" beats "telling"

DECLINE VIDEO (low confidence 0.0-0.4) when:
- The content is purely conversational (greetings, thanks, casual chat)
- The explanation is already complete and clear in text form
- The topic is inherently non-visual (pure philosophy, opinions, definitions)
- The student is asking for homework answers or simple factual lookups
- There's no specific concept to visualize

## RESPONSE FORMAT
Return ONLY a JSON object (no markdown, no explanation):

{{
    "generate": true,
    "confidence": 0.85,
    "topic": "Clear, Descriptive Video Title",
    "visualization_type": "process|structure|concept|comparison|transformation|diagram|simulation",
    "duration_seconds": 20,
    "key_concepts": ["concept1", "concept2", "concept3"],
    "visual_elements": ["element to show", "another element", "key visual"],
    "animation_suggestions": ["animate X moving to Y", "show Z transforming", "highlight the connection between A and B"],
    "reason": "Brief explanation of why this would benefit from visualization"
}}

OR if declining:

{{
    "generate": false,
    "confidence": 0.2,
    "topic": "",
    "visualization_type": "",
    "duration_seconds": 0,
    "key_concepts": [],
    "visual_elements": [],
    "animation_suggestions": [],
    "reason": "Why visualization wouldn't help here"
}}"""

        try:
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": analysis_prompt}],
                system_prompt="You are a video content decision AI. Analyze educational conversations and determine if visual explanations would help. Return ONLY valid JSON, no other text or markdown."
            )

            # Clean and parse JSON
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            should_gen = data.get("generate", False)
            confidence = float(data.get("confidence", 0))

            return VisualizationDecision(
                should_generate=should_gen,
                confidence=confidence,
                topic=data.get("topic", ""),
                duration_seconds=max(10, min(30, int(data.get("duration_seconds", 20)))),
                visualization_type=data.get("visualization_type", "concept"),
                key_concepts=data.get("key_concepts", [])[:5],
                visual_elements=data.get("visual_elements", [])[:5],
                animation_suggestions=data.get("animation_suggestions", [])[:5],
                rejection_reason=None if should_gen else data.get("reason", "AI determined video not beneficial")
            )

        except json.JSONDecodeError as e:
            logger.error(f"[VideoAnalyzer] JSON parsing failed: {e}")
            return VisualizationDecision(
                should_generate=False,
                confidence=0.0,
                rejection_reason=f"AI response parsing failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[VideoAnalyzer] Analysis error: {e}")
            return VisualizationDecision(
                should_generate=False,
                confidence=0.0,
                rejection_reason=f"AI analysis error: {str(e)}"
            )

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response that might contain extra text."""
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Find JSON object
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return text

    def record_video_generation(self, session_id: str, turn_number: int):
        """Record that a video was generated on this turn (for cooldown tracking)."""
        if session_id not in self._session_video_history:
            self._session_video_history[session_id] = []

        history = self._session_video_history[session_id]
        history.append(turn_number)
        # Keep only last 10 entries
        self._session_video_history[session_id] = history[-10:]

    def clear_session(self, session_id: str):
        """Clear video history for a session."""
        if session_id in self._session_video_history:
            del self._session_video_history[session_id]


# Global service instance (will be initialized with dependencies in main.py)
video_analyzer_service: Optional[VideoAnalyzerService] = None


def get_video_analyzer_service() -> Optional[VideoAnalyzerService]:
    """Get the global video analyzer service instance."""
    return video_analyzer_service


def init_video_analyzer_service(llm_service=None, langgraph_service=None) -> VideoAnalyzerService:
    """Initialize the global video analyzer service with dependencies."""
    global video_analyzer_service
    video_analyzer_service = VideoAnalyzerService(llm_service, langgraph_service)
    return video_analyzer_service
