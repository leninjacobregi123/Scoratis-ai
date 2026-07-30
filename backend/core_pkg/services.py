import logging
from typing import Optional, Any
from database import DatabaseManager
from services.rag_service import RAGService
from services.web_search_service import WebSearchService
from services.memory_service import MemoryService
from services.langgraph_service import LangGraphService
from services.video_analyzer_service import VideoAnalyzerService
from services.agent import ScoratisAgent
from services.guardrail_service import GuardrailService

db: Optional[DatabaseManager] = None
rag_service: Optional[RAGService] = None
web_search_service: Optional[WebSearchService] = None
memory_service: Optional[MemoryService] = None
langgraph_service: Optional[LangGraphService] = None
video_analyzer_service: Optional[VideoAnalyzerService] = None
scoratis_agent: Optional[ScoratisAgent] = None
guardrail_service: Optional[GuardrailService] = None

youtube_client = None

def get_youtube_client():
    global youtube_client
    if youtube_client is None:
        try:
            from googleapiclient.discovery import build
            import os
            api_key = os.getenv("YOUTUBE_API_KEY")
            if api_key:
                youtube_client = build('youtube', 'v3', developerKey=api_key)
        except ImportError:
            pass
    return youtube_client
