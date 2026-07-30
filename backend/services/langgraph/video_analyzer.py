import json
import logging
from typing import Dict, Any, Optional
from .state import VideoAnalysisResult

logger = logging.getLogger(__name__)

    
    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def analyze(self, user_message: str, ai_response: str, subject: str, learning_state: Dict) -> VideoAnalysisResult:
        if not self.llm_service or len(ai_response) < 100:
            return VideoAnalysisResult(is_visualizable=False, reason="Too short or no LLM")
            
        prompt = VIDEO_ANALYSIS_PROMPT.format(
            subject=subject,
            topics_discussed=", ".join(learning_state.get("topics_discussed", [])[-5:]),
            learning_state=learning_state.get("current_state", "initial"),
            user_message=user_message[:500],
            ai_response=ai_response[:2000]
        )
        
        try:
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="AI video advisor. Return ONLY JSON."
            )
            data = self._extract_json(response)
            return VideoAnalysisResult(**json.loads(data))
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return VideoAnalysisResult(is_visualizable=False, reason=str(e))

    def _extract_json(self, text: str) -> str:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text.strip()
