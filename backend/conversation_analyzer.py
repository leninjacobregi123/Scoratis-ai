"""
Conversation Analyzer for Scoratis
Tracks learning state and determines optimal video trigger points
Based on context-aware video suggestions from meaningful chat content

Enhanced Features:
- Content richness scoring - only suggest videos when substantial content exists
- Concept extraction - identify specific concepts for video generation
- Chat context building - gather history for LLM-based Manim code generation
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class LearningState(Enum):
    """Current learning state of the student"""
    INITIAL = "initial"           # Just started, exploring
    ENGAGED = "engaged"           # Actively participating
    CONFUSED = "confused"         # Showing signs of confusion
    STRUGGLING = "struggling"     # Multiple confusion signals
    PROGRESSING = "progressing"   # Making progress, partial understanding
    UNDERSTANDING = "understanding"  # Demonstrating comprehension
    MASTERY = "mastery"           # Clear mastery, ready for reinforcement


class VideoTrigger(Enum):
    """Video trigger types based on learning state"""
    NONE = "none"                           # No video recommended
    HINT = "hint"                           # Subtle suggestion on every response
    SCAFFOLD = "scaffold"                   # Forced: Help when stuck (confusion >= 2)
    REINFORCEMENT = "reinforcement"         # Post-discovery celebration
    SUMMARY = "summary"                     # Lesson recap


class ContentRichness(Enum):
    """Level of educational content in conversation"""
    EMPTY = "empty"               # No meaningful content
    CASUAL = "casual"             # Greetings, casual chat
    EXPLORING = "exploring"       # User asking basic questions
    LEARNING = "learning"         # Active learning with explanations
    DEEP = "deep"                 # Deep conceptual discussion


@dataclass
class ConversationState:
    """Tracks the state of a learning conversation"""
    session_id: str
    topic: Optional[str] = None
    turn_count: int = 0
    confusion_count: int = 0
    understanding_signals: int = 0
    last_state: LearningState = LearningState.INITIAL
    topics_discussed: List[str] = field(default_factory=list)
    key_discoveries: List[str] = field(default_factory=list)
    video_offered: bool = False
    video_generated: bool = False
    # New fields for content richness tracking
    content_richness: ContentRichness = ContentRichness.EMPTY
    content_score: float = 0.0
    extracted_concepts: List[Dict] = field(default_factory=list)
    conversation_context: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "turn_count": self.turn_count,
            "confusion_count": self.confusion_count,
            "understanding_signals": self.understanding_signals,
            "learning_state": self.last_state.value,
            "topics_discussed": self.topics_discussed,
            "key_discoveries": self.key_discoveries,
            "video_offered": self.video_offered,
            "video_generated": self.video_generated,
            "content_richness": self.content_richness.value,
            "content_score": self.content_score,
            "extracted_concepts": self.extracted_concepts
        }


# Pattern detection for student responses
CONFUSION_PATTERNS = [
    r"\bi don'?t know\b",
    r"\bi'?m confused\b",
    r"\bi'?m lost\b",
    r"\bi'?m not sure\b",
    r"\bno idea\b",
    r"\bwhat do you mean\b",
    r"\bcan you explain\b",
    r"\bi need help\b",
    r"\bthis is hard\b",
    r"\bi give up\b",
    r"\bjust tell me\b",
    r"\bgive me the answer\b",
    r"\bi'?m stuck\b",
    r"\b\?\?\?+\b",  # Multiple question marks
]

UNDERSTANDING_PATTERNS = [
    r"\boh,? i see\b",
    r"\bah,? i get it\b",
    r"\bthat makes sense\b",
    r"\bi understand\b",
    r"\bso basically\b",
    r"\bin other words\b",
    r"\bso it'?s like\b",
    r"\bthat'?s because\b",
    r"\bwhich means\b",
    r"\btherefore\b",
    r"\bso the answer is\b",
    r"\bi think it'?s\b",
    r"\bthe reason is\b",
    r"\bif .+ then\b",  # Conditional reasoning
    r"\bbecause .+ so\b",  # Causal reasoning
]

SUMMARY_REQUEST_PATTERNS = [
    r"\bsummarize\b",
    r"\bsummary\b",
    r"\bwrap up\b",
    r"\bwhat did we learn\b",
    r"\bwhat have we discussed\b",
    r"\brecap\b",
    r"\breview\b",
    r"\bconclusion\b",
    r"\bfinish\b",
    r"\bend lesson\b",
]

VISUAL_REQUEST_PATTERNS = [
    r"\bshow me\b",
    r"\bvisualize\b",
    r"\bvideo\b",
    r"\banimation\b",
    r"\bdiagram\b",
    r"\billustrate\b",
    r"\bpicture\b",
    r"\bimage\b",
    r"\bsee it\b",
    r"\bvisual\b",
]

# Note: VISUAL_TOPICS removed - video decisions are now made by AI
# The AI analyzes content dynamically instead of matching against predefined topics

# Patterns indicating casual/non-educational chat
CASUAL_PATTERNS = [
    r"^(hi|hello|hey|greetings)[\s\!\.\?]*$",
    r"^how are you",
    r"^what'?s up",
    r"^thanks?|thank you",
    r"^ok(ay)?[\s\!\.\?]*$",
    r"^bye|goodbye|see you",
    r"^yes|no|maybe[\s\!\.\?]*$",
]

# Patterns indicating educational content in AI response
EDUCATIONAL_CONTENT_PATTERNS = [
    r"\bfor example\b",
    r"\bthis means\b",
    r"\bin other words\b",
    r"\bthe reason\b",
    r"\bbecause\b",
    r"\btherefore\b",
    r"\bfirst\b.*\bthen\b",
    r"\bstep \d",
    r"\bthe process\b",
    r"\bthis works by\b",
    r"\bimagine\b",
    r"\bthink of\b",
    r"\blike when\b",
    r"\bequation|formula|calculation\b",
    r"\bdiagram|visual|illustration\b",
    r"\bstructure|mechanism|function\b",
]

# Patterns for concepts that could be visualized
VISUALIZABLE_CONCEPT_PATTERNS = [
    (r"how (?:does|do) (.+) work", "process"),
    (r"what (?:is|are) (.+)", "concept"),
    (r"explain (.+)", "explanation"),
    (r"why (?:does|do) (.+)", "causation"),
    (r"the (.+) (?:process|cycle|mechanism)", "process"),
    (r"(.+) (?:structure|anatomy|composition)", "structure"),
    (r"(.+) (?:reaction|transformation|change)", "transformation"),
    (r"relationship between (.+)", "relationship"),
]


class ConversationAnalyzer:
    """Analyzes conversations to determine learning state and video triggers"""

    def __init__(self):
        self.states: Dict[str, ConversationState] = {}

    def get_or_create_state(self, session_id: str) -> ConversationState:
        """Get existing state or create new one"""
        if session_id not in self.states:
            self.states[session_id] = ConversationState(session_id=session_id)
        return self.states[session_id]

    def _is_casual_message(self, message: str) -> bool:
        """Check if message is casual/non-educational"""
        message_lower = message.lower().strip()
        for pattern in CASUAL_PATTERNS:
            if re.match(pattern, message_lower, re.IGNORECASE):
                return True
        return len(message_lower) < 10  # Very short messages are likely casual

    def _calculate_content_richness(self, state: ConversationState, user_message: str, ai_response: str) -> Tuple[ContentRichness, float]:
        """
        Calculate how rich the educational content is in the conversation.
        Returns (richness_level, score 0-1)
        """
        score = 0.0

        # Check if just casual chat
        if self._is_casual_message(user_message):
            return ContentRichness.CASUAL, 0.1

        user_lower = user_message.lower()
        ai_lower = ai_response.lower() if ai_response else ""

        # Score based on conversation length (more turns = more context)
        if state.turn_count >= 3:
            score += 0.15
        if state.turn_count >= 5:
            score += 0.1

        # Score based on topics discussed
        if len(state.topics_discussed) >= 1:
            score += 0.2
        if len(state.topics_discussed) >= 2:
            score += 0.1

        # Score based on educational patterns in AI response
        edu_pattern_count = 0
        for pattern in EDUCATIONAL_CONTENT_PATTERNS:
            if re.search(pattern, ai_lower, re.IGNORECASE):
                edu_pattern_count += 1
        score += min(edu_pattern_count * 0.05, 0.25)

        # Score based on response length (longer = more explanation)
        if len(ai_response or "") > 200:
            score += 0.1
        if len(ai_response or "") > 500:
            score += 0.1

        # Score based on educational indicators in response
        # (Visual topic detection is now handled by AI - no hardcoded list)
        educational_indicators = [
            "because", "therefore", "this means", "for example",
            "imagine", "think of", "picture", "visualize",
            "step by step", "first", "then", "finally",
            "process", "structure", "mechanism", "function"
        ]
        indicator_count = sum(1 for ind in educational_indicators if ind in ai_lower)
        if indicator_count >= 2:
            score += 0.15

        # Score based on key discoveries
        if len(state.key_discoveries) >= 1:
            score += 0.15

        # Cap score at 1.0
        score = min(score, 1.0)

        # Determine richness level
        if score < 0.2:
            return ContentRichness.CASUAL, score
        elif score < 0.4:
            return ContentRichness.EXPLORING, score
        elif score < 0.7:
            return ContentRichness.LEARNING, score
        else:
            return ContentRichness.DEEP, score

    def _extract_visualizable_concepts(self, user_message: str, ai_response: str, state: ConversationState) -> List[Dict]:
        """
        Extract concepts from the conversation that could benefit from video visualization.
        Returns a list of concepts with their types and descriptions.
        """
        concepts = []
        combined_text = f"{user_message} {ai_response or ''}"
        combined_lower = combined_text.lower()

        # Check for visualizable concept patterns
        for pattern, concept_type in VISUALIZABLE_CONCEPT_PATTERNS:
            matches = re.finditer(pattern, combined_lower, re.IGNORECASE)
            for match in matches:
                concept_text = match.group(1).strip()
                # Filter out very short or generic matches
                if len(concept_text) > 3 and concept_text not in ['it', 'this', 'that', 'they']:
                    concepts.append({
                        "text": concept_text,
                        "type": concept_type,
                        "source": "pattern_match"
                    })

        # Extract visual concepts from sentences (AI will determine if truly visual)
        # Look for sentences that describe processes, structures, or mechanisms
        process_indicators = ["works by", "happens when", "process of", "cycle of", "transforms", "converts"]
        structure_indicators = ["structure of", "made of", "consists of", "composed of", "parts of"]

        sentences = re.split(r'[.!?]', combined_text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for indicator in process_indicators + structure_indicators:
                if indicator in sentence_lower:
                    # Extract the subject of this sentence
                    concept_type = "process" if indicator in process_indicators else "structure"
                    concepts.append({
                        "text": sentence.strip()[:100],
                        "type": concept_type,
                        "context": sentence.strip()[:200],
                        "source": "content_analysis"
                    })
                    break

        # Use topic from state if available
        if state.topic and state.topic not in [c.get("text") for c in concepts]:
            concepts.append({
                "text": state.topic,
                "type": "main_topic",
                "source": "state"
            })

        # Remove duplicates while preserving order
        seen = set()
        unique_concepts = []
        for c in concepts:
            key = c.get("text", "").lower()
            if key not in seen:
                seen.add(key)
                unique_concepts.append(c)

        return unique_concepts[:5]  # Limit to top 5 concepts

    def _build_video_context(self, state: ConversationState, user_message: str, ai_response: str) -> Dict:
        """
        Build context for LLM-based Manim code generation.
        Extracts the key information needed to generate a relevant video.
        """
        # Store this turn in conversation context
        state.conversation_context.append({
            "user": user_message,
            "ai": ai_response[:1000] if ai_response else ""  # Limit AI response length
        })

        # Keep only last 5 turns for context
        if len(state.conversation_context) > 5:
            state.conversation_context = state.conversation_context[-5:]

        # Build the context object for video generation
        context = {
            "main_topic": state.topic,
            "topics_discussed": state.topics_discussed,
            "key_discoveries": state.key_discoveries,
            "extracted_concepts": state.extracted_concepts,
            "recent_exchanges": state.conversation_context[-3:],  # Last 3 turns
            "learning_state": state.last_state.value,
            "content_richness": state.content_richness.value,
            "content_score": state.content_score
        }

        return context

    def analyze_message(self, session_id: str, user_message: str, ai_response: str) -> Dict:
        """
        Analyze a conversation turn and update state.
        Uses content richness scoring to only suggest videos when meaningful content exists.
        Returns video recommendation and learning state.
        """
        state = self.get_or_create_state(session_id)
        state.turn_count += 1

        user_lower = user_message.lower()
        ai_lower = ai_response.lower() if ai_response else ""

        # Detect topic from conversation
        detected_topic = self._detect_topic(user_message + " " + (ai_response or ""))
        if detected_topic and detected_topic not in state.topics_discussed:
            state.topics_discussed.append(detected_topic)
            state.topic = detected_topic

        # Calculate content richness BEFORE making video decisions
        content_richness, content_score = self._calculate_content_richness(state, user_message, ai_response)
        state.content_richness = content_richness
        state.content_score = content_score

        # Extract visualizable concepts for context-aware video generation
        concepts = self._extract_visualizable_concepts(user_message, ai_response, state)
        state.extracted_concepts = concepts

        # Build video context for LLM-based generation
        video_context = self._build_video_context(state, user_message, ai_response)

        # Check for explicit requests first
        if self._matches_patterns(user_lower, SUMMARY_REQUEST_PATTERNS):
            # Only allow summary if there's meaningful content
            if content_richness in [ContentRichness.LEARNING, ContentRichness.DEEP]:
                return self._create_recommendation(state, VideoTrigger.SUMMARY,
                    "User requested lesson summary", video_context)
            else:
                return self._create_recommendation(state, VideoTrigger.NONE,
                    "Not enough content for summary video", video_context)

        if self._matches_patterns(user_lower, VISUAL_REQUEST_PATTERNS):
            # Only allow visual request if there's a topic to visualize
            if content_richness != ContentRichness.CASUAL and state.topic:
                return self._create_recommendation(state, VideoTrigger.REINFORCEMENT,
                    "User explicitly requested visual content", video_context)

        # Analyze confusion signals
        confusion_detected = self._matches_patterns(user_lower, CONFUSION_PATTERNS)
        if confusion_detected:
            state.confusion_count += 1

        # Analyze understanding signals
        understanding_detected = self._matches_patterns(user_lower, UNDERSTANDING_PATTERNS)
        if understanding_detected:
            state.understanding_signals += 1
            # Reset confusion when understanding improves
            state.confusion_count = max(0, state.confusion_count - 1)

        # Detect key discoveries (when AI celebrates understanding)
        if self._detect_discovery_moment(ai_response):
            discovery = self._extract_discovery(user_message)
            if discovery:
                state.key_discoveries.append(discovery)

        # Update learning state
        state.last_state = self._determine_learning_state(state)

        # CRITICAL: Only suggest videos when content is meaningful
        # This prevents false suggestions for casual/empty conversations
        if content_richness in [ContentRichness.EMPTY, ContentRichness.CASUAL]:
            return self._create_recommendation(state, VideoTrigger.NONE,
                "No meaningful educational content yet", video_context)

        if content_richness == ContentRichness.EXPLORING and state.turn_count < 3:
            return self._create_recommendation(state, VideoTrigger.NONE,
                "Still exploring topic, waiting for more context", video_context)

        # Determine video trigger based on state
        trigger, reason = self._determine_video_trigger(state)

        return self._create_recommendation(state, trigger, reason, video_context)

    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_topic(self, text: str) -> Optional[str]:
        """Detect the main topic being discussed using content analysis."""
        text_lower = text.lower()

        # Extract topic from question patterns
        question_patterns = [
            (r"what is (?:a |an |the )?(.+?)[\?\.]", "definition"),
            (r"how does (?:a |an |the )?(.+?) work", "mechanism"),
            (r"explain (?:the )?(.+)", "explanation"),
            (r"why does (?:a |an |the )?(.+)", "causation"),
            (r"tell me about (?:the )?(.+)", "general"),
            (r"describe (?:the )?(.+)", "description"),
        ]

        for pattern, _ in question_patterns:
            match = re.search(pattern, text_lower)
            if match:
                topic = match.group(1).strip()
                # Clean up the topic
                topic = re.sub(r'\?$', '', topic).strip()
                if len(topic) > 2 and len(topic) < 50:
                    return topic

        # Look for noun phrases that might be topics
        # Simple heuristic: find capitalized words or common topic indicators
        topic_indicators = ["about", "regarding", "concerning", "on the topic of"]
        for indicator in topic_indicators:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                remaining = text[idx + len(indicator):].strip()
                # Take first few words as topic
                words = remaining.split()[:5]
                if words:
                    topic = " ".join(words).strip(".,?!")
                    if len(topic) > 2:
                        return topic

        return None

    def _detect_discovery_moment(self, ai_response: str) -> bool:
        """Detect if AI is celebrating a discovery moment"""
        if not ai_response:
            return False

        celebration_patterns = [
            r"excellent!",
            r"exactly!",
            r"you.+got it",
            r"you.+discovered",
            r"you.+figured",
            r"that'?s right",
            r"well done",
            r"you reasoned",
            r"brilliant",
            r"now you understand",
        ]

        ai_lower = ai_response.lower()
        for pattern in celebration_patterns:
            if re.search(pattern, ai_lower):
                return True
        return False

    def _extract_discovery(self, user_message: str) -> Optional[str]:
        """Extract the key discovery from user's message"""
        # Simplified extraction - just capture the core insight
        if len(user_message) > 20:
            return user_message[:100] + "..." if len(user_message) > 100 else user_message
        return None

    def _determine_learning_state(self, state: ConversationState) -> LearningState:
        """Determine current learning state based on signals"""

        # Multiple confusion signals - struggling (lowered to 2)
        if state.confusion_count >= 2:
            return LearningState.STRUGGLING

        # Single confusion signal
        if state.confusion_count >= 1 and state.understanding_signals == 0:
            return LearningState.CONFUSED

        # Strong understanding signals
        if state.understanding_signals >= 2 and len(state.key_discoveries) >= 1:
            return LearningState.MASTERY

        if state.understanding_signals >= 1:
            return LearningState.UNDERSTANDING

        # Early conversation
        if state.turn_count <= 1:
            return LearningState.INITIAL

        # Making progress
        if state.turn_count >= 2 and state.confusion_count == 0:
            return LearningState.PROGRESSING

        return LearningState.ENGAGED

    def _determine_video_trigger(self, state: ConversationState) -> Tuple[VideoTrigger, str]:
        """
        Determine if and what type of video should be triggered.
        Note: Actual video decision is made by AI - this provides hints for the AI system.
        """
        # Check if we have substantial content to potentially visualize
        has_topic = state.topic is not None and len(state.topic) > 2
        has_rich_content = state.content_richness in [ContentRichness.LEARNING, ContentRichness.DEEP]
        has_concepts = len(state.extracted_concepts) > 0

        # FORCED: Scaffold for confused students (confusion >= 2)
        if state.confusion_count >= 2 and (has_topic or has_concepts):
            state.video_offered = True
            return VideoTrigger.SCAFFOLD, f"Student struggling - video may help clarify: {state.topic or 'current topic'}"

        # FORCED: Reinforcement after understanding
        if state.last_state in [LearningState.UNDERSTANDING, LearningState.MASTERY]:
            if has_rich_content and len(state.key_discoveries) >= 1:
                state.video_offered = True
                return VideoTrigger.REINFORCEMENT, f"Student demonstrated understanding - reinforce with video"

        # SUBTLE HINT: Suggest video when content is rich enough
        if has_rich_content and state.turn_count >= 2:
            return VideoTrigger.HINT, f"Rich educational content detected - video may enhance understanding"

        # Also hint when we have extracted concepts that could be visualized
        if has_concepts and state.turn_count >= 1:
            return VideoTrigger.HINT, f"Visualizable concepts detected: {[c.get('text', '')[:30] for c in state.extracted_concepts[:2]]}"

        return VideoTrigger.NONE, "No video trigger conditions met - AI will make final decision"

    def _create_recommendation(self, state: ConversationState, trigger: VideoTrigger, reason: str, video_context: Dict = None) -> Dict:
        """Create a video recommendation response with context for LLM-based Manim generation"""
        return {
            "video_trigger": trigger.value,
            "should_offer_video": trigger != VideoTrigger.NONE,
            "trigger_reason": reason,
            "learning_state": state.last_state.value,
            "topic": state.topic,
            "turn_count": state.turn_count,
            "confusion_level": state.confusion_count,
            "understanding_level": state.understanding_signals,
            "key_discoveries": state.key_discoveries[-3:] if state.key_discoveries else [],
            "suggested_video_topic": self._generate_video_topic(state, trigger),
            "video_message": self._generate_video_message(state, trigger),
            # New fields for content-aware video generation
            "content_richness": state.content_richness.value,
            "content_score": state.content_score,
            "extracted_concepts": state.extracted_concepts,
            "video_context": video_context  # Context for LLM-based Manim generation
        }

    def _generate_video_topic(self, state: ConversationState, trigger: VideoTrigger) -> Optional[str]:
        """Generate appropriate video topic based on content analysis - no hardcoded titles."""
        if not state.topic:
            # Try to get topic from extracted concepts
            if state.extracted_concepts:
                first_concept = state.extracted_concepts[0]
                topic_text = first_concept.get("text", "")
                if topic_text:
                    return self._format_topic_title(topic_text, first_concept.get("type", ""), trigger)
            return None

        # Format the topic title based on trigger type
        return self._format_topic_title(state.topic, "general", trigger)

    def _format_topic_title(self, topic: str, concept_type: str, trigger: VideoTrigger) -> str:
        """Format a topic into a video title based on concept type and trigger."""
        # Capitalize the topic properly
        base_title = topic.title() if len(topic) > 3 else topic.upper()

        # Add prefix based on concept type
        if concept_type == "process":
            base_title = f"How {base_title} Works"
        elif concept_type == "structure":
            base_title = f"{base_title} Structure"
        elif concept_type == "mechanism":
            base_title = f"Understanding {base_title}"
        elif concept_type == "causation":
            base_title = f"Why {base_title} Happens"
        elif concept_type == "explanation":
            base_title = f"{base_title} Explained"

        # Add trigger-based prefix
        if trigger == VideoTrigger.SCAFFOLD:
            return f"Visual Guide: {base_title}"
        elif trigger == VideoTrigger.REINFORCEMENT:
            return f"Visualizing: {base_title}"
        elif trigger == VideoTrigger.SUMMARY:
            return f"Summary: {base_title}"

        return base_title

    def _generate_video_message(self, state: ConversationState, trigger: VideoTrigger) -> Optional[str]:
        """Generate contextual message for video offer"""
        if trigger == VideoTrigger.NONE:
            return None

        if trigger == VideoTrigger.HINT:
            return "A visual explanation is available for this topic."

        if trigger == VideoTrigger.SCAFFOLD:
            return "This concept is easier to understand with visuals. Let me create a video demonstration to help you see it clearly!"

        elif trigger == VideoTrigger.REINFORCEMENT:
            return "Excellent work discovering that! Would you like to see a visual animation that brings your understanding to life? It can help cement what you've learned."

        elif trigger == VideoTrigger.SUMMARY:
            return "Let me create a visual summary of our learning journey together. This will help reinforce the key concepts you've discovered."

        return None

    def reset_session(self, session_id: str):
        """Reset a session's state"""
        if session_id in self.states:
            del self.states[session_id]

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get a summary of the session for lesson recap"""
        if session_id not in self.states:
            return None

        state = self.states[session_id]
        return {
            "topics_covered": state.topics_discussed,
            "key_discoveries": state.key_discoveries,
            "total_turns": state.turn_count,
            "final_state": state.last_state.value,
            "understanding_achieved": state.understanding_signals > 0
        }

    def get_video_generation_context(self, session_id: str) -> Optional[Dict]:
        """
        Get the full context needed for LLM-based Manim code generation.
        This provides all the information the LLM needs to generate relevant video code.
        """
        if session_id not in self.states:
            return None

        state = self.states[session_id]

        # Only return context if there's meaningful content
        if state.content_richness in [ContentRichness.EMPTY, ContentRichness.CASUAL]:
            return None

        # Build comprehensive context for video generation
        context = {
            "main_topic": state.topic,
            "topic_title": self._generate_topic_title_for_context(state),
            "topics_discussed": state.topics_discussed,
            "key_concepts": [c.get("text") for c in state.extracted_concepts],
            "concept_details": state.extracted_concepts,
            "key_discoveries": state.key_discoveries,
            "learning_state": state.last_state.value,
            "content_richness": state.content_richness.value,
            "content_score": state.content_score,
            "conversation_history": state.conversation_context,
            "turn_count": state.turn_count,
            # Specific guidance for Manim code generation
            "visualization_hints": self._generate_visualization_hints(state),
            "duration_suggestion": self._suggest_video_duration(state)
        }

        return context

    def _generate_topic_title_for_context(self, state: ConversationState) -> str:
        """Generate a clear title for the video based on context"""
        if not state.topic:
            return "Educational Explanation"

        # Check extracted concepts for more specific title
        for concept in state.extracted_concepts:
            if concept.get("type") == "process":
                return f"How {state.topic.title()} Works"
            elif concept.get("type") == "structure":
                return f"{state.topic.title()} Structure"
            elif concept.get("type") == "causation":
                return f"Understanding {state.topic.title()}"

        return f"{state.topic.title()} Explained"

    def _generate_visualization_hints(self, state: ConversationState) -> List[str]:
        """Generate hints for what should be visualized in the video"""
        hints = []

        for concept in state.extracted_concepts:
            concept_text = concept.get("text", "")
            concept_type = concept.get("type", "")

            if concept_type == "process":
                hints.append(f"Show step-by-step process of {concept_text}")
            elif concept_type == "structure":
                hints.append(f"Display the structure/anatomy of {concept_text}")
            elif concept_type == "causation":
                hints.append(f"Illustrate cause and effect relationship in {concept_text}")
            elif concept_type == "transformation":
                hints.append(f"Animate the transformation/change in {concept_text}")
            elif concept_type == "relationship":
                hints.append(f"Show how components relate in {concept_text}")
            elif concept_type == "visual_topic":
                context = concept.get("context", "")
                if context:
                    hints.append(f"Visualize: {context[:100]}")

        # Add hints based on key discoveries
        for discovery in state.key_discoveries[-2:]:
            if discovery:
                hints.append(f"Reinforce discovery: {discovery[:80]}")

        return hints[:5]  # Limit to 5 hints

    def _suggest_video_duration(self, state: ConversationState) -> int:
        """Suggest appropriate video duration based on content complexity"""
        base_duration = 60  # 1 minute base

        # Add time for more concepts
        concept_count = len(state.extracted_concepts)
        base_duration += concept_count * 15

        # Add time for deeper content
        if state.content_richness == ContentRichness.DEEP:
            base_duration += 30
        elif state.content_richness == ContentRichness.LEARNING:
            base_duration += 15

        # Cap at 2 minutes
        return min(base_duration, 120)


# Global analyzer instance
conversation_analyzer = ConversationAnalyzer()
