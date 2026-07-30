from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    is_visualizable: bool = False
    topic_for_video: Optional[str] = None
    visualization_type: Optional[str] = None
    key_concepts: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""

class LearningStateData(BaseModel):
    messages: List[Dict[str, str]]
    session_id: str
    subject: str
    learning_state: Dict[str, Any]
    video_analysis: Optional[Dict[str, Any]]
    video_eligible: bool
    current_user_message: str
    current_ai_response: str
    rag_context: Optional[str]
    model_used: Optional[str]
    search_used: bool
