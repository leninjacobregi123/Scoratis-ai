import logging
from typing import Dict, Any, List
from .state import ConversationState, LearningStateData
from .video_analyzer import VideoAnalyzerNode

logger = logging.getLogger(__name__)

class LangGraphNodes:
        session_id = state.get("session_id", "")
        user_message = state.get("current_user_message", "")
        
        messages = list(state.get("messages", []))
        messages.append({"role": "user", "content": user_message})
        
        learning_state = state.get("learning_state", {})
        if not learning_state:
            learning_state = LearningStateData().model_dump()
        learning_state["turn_count"] = learning_state.get("turn_count", 0) + 1
        
        return {"messages": messages, "learning_state": learning_state}

    async def generate_response_node(self, state: ConversationState) -> Dict[str, Any]:
        analysis = await self.video_analyzer.analyze(
            state.get("current_user_message"),
            state.get("current_ai_response"),
            state.get("subject"),
            state.get("learning_state")
        )
        return {
            "video_analysis": analysis.model_dump(),
            "video_eligible": analysis.is_visualizable and analysis.confidence > 0.6
        }

    async def format_output_node(self, state: ConversationState) -> Dict[str, Any]:
