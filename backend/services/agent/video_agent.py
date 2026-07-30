import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .state import VideoAnalysis

logger = logging.getLogger(__name__)

class VideoAnalysisAgent:
    

    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def analyze(self, subject: str, history: List[Dict], latest_response: str) -> VideoAnalysis:
        history_str = "\n".join([f"{m['role'].upper()}: {m['content'][:200]}..." for m in history[-5:]])
        
        prompt = self.ANALYSIS_PROMPT.format(
            subject=subject,
            history=history_str,
            latest_response=latest_response
        )
        
        try:
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a Video Strategy Agent. Output ONLY JSON."
            )
            
            clean_json = self._extract_json(response)
            data = json.loads(clean_json)
            
            if "reasoning" in data and "reason" not in data:
                data["reason"] = data.pop("reasoning")
                
            return VideoAnalysis(**data)
            
        except Exception as e:
            logger.error(f"Video analysis agent failed: {e}")
            return VideoAnalysis(is_visualizable=False, reason=f"Error: {str(e)}")

    def _extract_json(self, text: str) -> str:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text
