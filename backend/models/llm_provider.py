"""
LLM Provider Configuration Model
Stores encrypted API keys and provider settings for LiteLLM integration.
"""

from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, TYPE_CHECKING
import enum

from .base import Base

if TYPE_CHECKING:
    from .user import User


class ProviderType(str, enum.Enum):
    """Supported LLM providers"""
    # Local providers (no API key required)
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    LOCALAI = "localai"
    TEXTGENWEBUI = "textgenwebui"
    # Cloud providers (API key required)
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    TOGETHER = "together"
    AZURE = "azure"
    DEEPSEEK = "deepseek"


class LLMProviderConfig(Base):
    """
    Configuration for LLM providers with encrypted API keys.
    Each user can have multiple provider configurations.
    """
    __tablename__ = "llm_provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )

    # Provider identification
    provider: Mapped[str] = mapped_column(
        SQLEnum(ProviderType, name="provider_type", create_type=True),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Credentials (encrypted)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Provider-specific settings
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    extra_settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="llm_providers")

    def __repr__(self) -> str:
        return f"<LLMProviderConfig(id={self.id}, provider={self.provider}, name={self.name})>"

    def to_dict(self, include_key: bool = False) -> dict:
        """Convert to dictionary for API responses."""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider.value if isinstance(self.provider, ProviderType) else self.provider,
            "name": self.name,
            "base_url": self.base_url,
            "extra_settings": self.extra_settings,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
        if include_key:
            result["api_key_encrypted"] = self.api_key_encrypted
        return result


# Provider metadata for frontend display
PROVIDER_INFO = {
    # Local providers (no API key required)
    ProviderType.OLLAMA: {
        "display_name": "Ollama",
        "icon": "🦙",
        "requires_api_key": False,
        "is_local": True,
        "default_base_url": "http://localhost:11434",
        "models": ["llama3.2", "llama3.1", "mistral", "qwen2.5", "codellama", "phi3", "gemma2"],
    },
    ProviderType.LMSTUDIO: {
        "display_name": "LM Studio",
        "icon": "💻",
        "requires_api_key": False,
        "is_local": True,
        "default_base_url": "http://localhost:1234/v1",
        "models": ["local-model"],
    },
    ProviderType.LOCALAI: {
        "display_name": "LocalAI",
        "icon": "🏠",
        "requires_api_key": False,
        "is_local": True,
        "default_base_url": "http://localhost:8080/v1",
        "models": ["gpt4all-j", "wizardlm", "orca-mini"],
    },
    ProviderType.TEXTGENWEBUI: {
        "display_name": "Text Gen WebUI",
        "icon": "🌐",
        "requires_api_key": False,
        "is_local": True,
        "default_base_url": "http://localhost:5000/v1",
        "models": ["loaded-model"],
    },
    # Cloud providers (API key required)
    ProviderType.OPENAI: {
        "display_name": "OpenAI",
        "icon": "🤖",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
    },
    ProviderType.ANTHROPIC: {
        "display_name": "Anthropic",
        "icon": "🧠",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    },
    ProviderType.GOOGLE: {
        "display_name": "Google AI",
        "icon": "✨",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    ProviderType.GROQ: {
        "display_name": "Groq",
        "icon": "⚡",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant", "gemma2-9b-it"],
    },
    ProviderType.TOGETHER: {
        "display_name": "Together AI",
        "icon": "🤝",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"],
    },
    ProviderType.AZURE: {
        "display_name": "Azure OpenAI",
        "icon": "☁️",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-35-turbo"],
    },
    ProviderType.DEEPSEEK: {
        "display_name": "DeepSeek",
        "icon": "🔍",
        "requires_api_key": True,
        "is_local": False,
        "default_base_url": None,
        "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
    },
}
