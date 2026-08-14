from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any


def _strip_or_none(value: Optional[str]) -> Optional[str]:
    """Trim surrounding whitespace, collapsing an all-whitespace value to None.

    Credentials and endpoint identifiers get pasted into the Settings form,
    and a stray leading/trailing space is invisible in the UI but is sent
    verbatim to the provider - e.g. a model saved as "sofie-code " fails
    with an opaque "model not found" that looks like a wrong model name
    rather than a whitespace bug.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    attachment_ids: Optional[List[int]] = None
    use_web_search: Optional[bool] = True
    use_reasoning: Optional[bool] = False
    provider: Optional[str] = None
    model: Optional[str] = None
    # Set when the question was asked from inside the lesson player. The
    # backend resolves these to the scene the learner is actually looking at
    # and puts its content in the tutor's context, so "why is that 4?"
    # resolves against what is on screen rather than being answered blind.
    lesson_id: Optional[int] = None
    scene_id: Optional[str] = None

class DeleteConversation(BaseModel):
    permanent: Optional[bool] = False

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class LLMConfigUpdate(BaseModel):
    model: str
    provider: Optional[str] = None
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
    default_model: Optional[str] = None
    is_default: Optional[bool] = False

    _strip = field_validator("api_key", "base_url", "default_model", mode="before")(
        lambda v: _strip_or_none(v) if isinstance(v, str) or v is None else v
    )

class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    _strip = field_validator("api_key", "base_url", "default_model", mode="before")(
        lambda v: _strip_or_none(v) if isinstance(v, str) or v is None else v
    )

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
