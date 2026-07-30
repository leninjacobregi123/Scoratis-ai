from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class JournalCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []
    folder_id: Optional[int] = None

class JournalUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[int] = None

class FolderCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    color: Optional[str] = "

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    subject: Optional[str] = "general"
    attachment_ids: Optional[List[int]] = None
    use_web_search: Optional[bool] = True
    use_reasoning: Optional[bool] = False
    use_documents: Optional[bool] = True
    provider: Optional[str] = None
    model: Optional[str] = None

class DeleteConversation(BaseModel):
    permanent: Optional[bool] = False

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class LLMConfigUpdate(BaseModel):
    model: str
    provider: Optional[str] = "ollama"
    base_url: Optional[str] = None
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7
    context_length: Optional[int] = 4096
    validate: Optional[bool] = True
    skip_validation: Optional[bool] = False

class LLMProviderCreate(BaseModel):
    provider: str
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_default: Optional[bool] = False

class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

class SessionModelUpdate(BaseModel):
    session_id: str
    provider_id: Optional[int] = None
    model: str

class VideoGenerateRequest(BaseModel):
    topic: str
    quality: Optional[str] = "high"
    duration: Optional[int] = 90

class TTSRequest(BaseModel):
    text: str
