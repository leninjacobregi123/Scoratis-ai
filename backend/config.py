"""
Configuration Management for Scoratis
Centralized settings with environment variable support
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Database
    DATABASE_URL: str = "postgresql://scoratis:scoratis_password@localhost:5433/scoratis"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://scoratis:scoratis_password@localhost:5433/scoratis"

    # Legacy SQLite (for rollback)
    USE_LEGACY_DB: bool = False
    SQLITE_PATH: str = "../scoratis.db"

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Legacy RAG Settings (for backward compatibility)
    RAG_SIMILARITY_THRESHOLD: float = 0.5
    RAG_MAX_JOURNAL_RESULTS: int = 3
    RAG_MAX_CONVERSATION_RESULTS: int = 5

    # === NEW: Professional RAG System Settings ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # Chunking settings
    CHUNK_SIZE: int = 800  # Characters per chunk
    CHUNK_OVERLAP: int = 100  # Overlap between chunks

    # RRF (Reciprocal Rank Fusion) settings
    RRF_K: int = 60  # RRF constant

    # Search limits
    SEARCH_CHUNK_LIMIT: int = 20  # Max chunks to retrieve
    SEARCH_DOCUMENT_LIMIT: int = 10  # Max documents for document-level search

    # Upload settings
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: list = ["pdf", "docx", "txt", "html", "md"]

    # Web Search
    WEB_SEARCH_ENABLED: bool = True
    WEB_SEARCH_MAX_RESULTS: int = 3

    # Memory
    SHORT_TERM_MEMORY_LIMIT: int = 20

    # Ollama LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # API Keys (legacy - now stored encrypted in database)
    GEMINI_API_KEY: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None

    # LLM Provider API Keys (optional - can also be stored encrypted in DB)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    TOGETHER_API_KEY: Optional[str] = None
    AZURE_API_KEY: Optional[str] = None
    AZURE_API_BASE: Optional[str] = None

    # Default LLM Settings
    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_LLM_MODEL: str = "gpt-oss:20b"

    # Encryption (REQUIRED for production - generate secure values!)
    SCORATIS_ENCRYPTION_KEY: str = "scoratis-default-dev-key-change-in-production-32chars"
    SCORATIS_ENCRYPTION_SALT: str = "scoratis-salt-value"

    # LangSmith Observability
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "scoratis-production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function for quick access
settings = get_settings()
