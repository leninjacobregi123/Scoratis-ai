"""
Scoratis LLM Service - Universal Provider Support
Powered by LiteLLM for 100+ model support including local Ollama
All data stays on your machine with Ollama - fully open source
"""

import os
import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging

from config import settings
from models import ProviderType, PROVIDER_INFO
from services.litellm_service import get_litellm_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Legacy enum for backwards compatibility
class LLMProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    TOGETHER = "together"
    AZURE = "azure"


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    base_url: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.6
    top_p: float = 0.9
    context_length: int = 4096
    frequency_penalty: float = 0.2
    num_batch: int = 512
    num_gpu: int = 99


# Models optimized for different VRAM sizes (Ollama)
RECOMMENDED_MODELS = {
    "4GB": [
        {"id": "llama3.2", "name": "Llama 3.2 3B", "description": "Best balance of speed & quality", "size": "3B", "vram": "~2.5GB", "recommended": True},
        {"id": "llama3.2:1b", "name": "Llama 3.2 1B", "description": "Ultra fast, lightweight", "size": "1B", "vram": "~1GB"},
        {"id": "phi3", "name": "Phi-3 Mini", "description": "Microsoft's efficient model", "size": "3.8B", "vram": "~3GB"},
        {"id": "qwen2.5:3b", "name": "Qwen 2.5 3B", "description": "Good for reasoning", "size": "3B", "vram": "~2.5GB"},
    ],
    "8GB": [
        {"id": "llama3.1", "name": "Llama 3.1 8B", "description": "Excellent all-around", "size": "8B", "vram": "~6GB", "recommended": True},
        {"id": "mistral", "name": "Mistral 7B", "description": "Fast and capable", "size": "7B", "vram": "~5GB"},
        {"id": "qwen2.5", "name": "Qwen 2.5 7B", "description": "Strong reasoning", "size": "7B", "vram": "~5GB"},
    ],
    "16GB": [
        {"id": "llama3.1:13b", "name": "Llama 3.1 13B", "description": "High quality responses", "size": "13B", "vram": "~10GB"},
        {"id": "qwen2.5:14b", "name": "Qwen 2.5 14B", "description": "Excellent reasoning", "size": "14B", "vram": "~11GB", "recommended": True},
    ],
    "24GB+": [
        {"id": "qwen2.5:32b", "name": "Qwen 2.5 32B", "description": "Excellent all-around", "size": "32B", "vram": "~20GB", "recommended": True},
        {"id": "deepseek-coder:33b", "name": "DeepSeek Coder 33B", "description": "Best open coder", "size": "33B", "vram": "~22GB"},
    ]
}

# All available Ollama models
AVAILABLE_MODELS = {
    LLMProvider.OLLAMA: [
        {"id": "llama3.2", "name": "Llama 3.2 3B", "description": "Latest Llama, fast & efficient", "size": "3B", "category": "general"},
        {"id": "llama3.2:1b", "name": "Llama 3.2 1B", "description": "Ultra lightweight", "size": "1B", "category": "general"},
        {"id": "llama3.1", "name": "Llama 3.1 8B", "description": "Excellent all-around", "size": "8B", "category": "general"},
        {"id": "mistral", "name": "Mistral 7B", "description": "Fast and efficient", "size": "7B", "category": "general"},
        {"id": "qwen2.5", "name": "Qwen 2.5 7B", "description": "Strong reasoning", "size": "7B", "category": "general"},
        {"id": "phi3", "name": "Phi-3 Mini", "description": "Small but powerful", "size": "3.8B", "category": "general"},
        {"id": "deepseek-coder", "name": "DeepSeek Coder", "description": "Excellent for code", "size": "6.7B", "category": "coding"},
        {"id": "codellama", "name": "CodeLlama 7B", "description": "Meta's coding model", "size": "7B", "category": "coding"},
    ],
}


class OllamaProvider:
    """Direct Ollama provider for backwards compatibility and pull operations"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(180.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def is_available(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "id": m["name"],
                        "name": m["name"].split(":")[0],
                        "size": self._format_size(m.get("size", 0)),
                        "modified": m.get("modified_at", ""),
                        "details": m.get("details", {})
                    }
                    for m in data.get("models", [])
                ]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []

    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict, None]:
        try:
            client = await self._get_client()
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=None
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        yield json.loads(line)
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            yield {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        try:
            is_available = await self.is_available()
            if not is_available:
                return {
                    "status": "unhealthy",
                    "message": "Ollama server not responding",
                    "base_url": self.base_url
                }

            models = await self.list_models()
            current_model_available = any(
                m["id"].startswith(self.config.model.split(":")[0])
                for m in models
            )

            return {
                "status": "healthy",
                "base_url": self.base_url,
                "current_model": self.config.model,
                "model_available": current_model_available,
                "installed_models": len(models),
                "models": [m["id"] for m in models[:10]]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "base_url": self.base_url
            }


class LLMService:
    """
    Universal LLM service supporting multiple providers via LiteLLM.
    Maintains backwards compatibility with existing Ollama-only interface.
    """

    def __init__(self):
        self.current_config: Optional[LLMConfig] = None
        self.ollama_provider: Optional[OllamaProvider] = None
        self.litellm = get_litellm_service()
        self._load_default_config()

    def _load_default_config(self):
        """Load default configuration"""
        self.set_provider(
            model=settings.DEFAULT_LLM_MODEL,
            provider=settings.DEFAULT_LLM_PROVIDER
        )

    def set_provider(
        self,
        model: str,
        provider: str = "ollama",
        base_url: Optional[str] = None,
        api_key_encrypted: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        context_length: int = 4096
    ):
        """Set the LLM configuration"""
        # Map string to enum
        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            provider_enum = LLMProvider.OLLAMA

        self.current_config = LLMConfig(
            provider=provider_enum,
            model=model,
            base_url=base_url,
            api_key_encrypted=api_key_encrypted,
            max_tokens=max_tokens,
            temperature=temperature,
            context_length=context_length
        )

        # Initialize Ollama provider for direct operations
        if provider_enum == LLMProvider.OLLAMA:
            self.ollama_provider = OllamaProvider(self.current_config)

        logger.info(f"LLM configured: {model} via {provider}")

    def _get_provider_type(self) -> ProviderType:
        """Convert current config provider to ProviderType"""
        if self.current_config:
            return ProviderType(self.current_config.provider.value)
        return ProviderType.OLLAMA

    async def generate(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """Generate a response using LiteLLM"""
        if not self.current_config:
            raise Exception("LLM provider not configured")

        return await self.litellm.generate(
            messages=messages,
            system_prompt=system_prompt,
            provider=self._get_provider_type(),
            model=self.current_config.model,
            api_key_encrypted=self.current_config.api_key_encrypted,
            base_url=self.current_config.base_url,
            max_tokens=self.current_config.max_tokens,
            temperature=self.current_config.temperature,
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using LiteLLM"""
        if not self.current_config:
            raise Exception("LLM provider not configured")

        async for chunk in self.litellm.generate_stream(
            messages=messages,
            system_prompt=system_prompt,
            provider=self._get_provider_type(),
            model=self.current_config.model,
            api_key_encrypted=self.current_config.api_key_encrypted,
            base_url=self.current_config.base_url,
            max_tokens=self.current_config.max_tokens,
            temperature=self.current_config.temperature,
        ):
            yield chunk

    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a response with tool/function calling support"""
        if not self.current_config:
            raise Exception("LLM provider not configured")

        return await self.litellm.generate_with_tools(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            provider=self._get_provider_type(),
            model=self.current_config.model,
            api_key_encrypted=self.current_config.api_key_encrypted,
            base_url=self.current_config.base_url,
            max_tokens=self.current_config.max_tokens,
            temperature=self.current_config.temperature,
        )

    async def check_availability(self) -> Dict[str, Any]:
        """Check provider availability"""
        result = {}

        # Check Ollama
        ollama_health = await self.litellm.check_ollama_health()
        result["ollama"] = {
            "available": ollama_health["available"],
            "installed_models": ollama_health.get("installed_models", []),
        }

        # Get all available providers
        result["providers"] = self.litellm.get_available_providers()

        return result

    def get_available_models(self) -> Dict[str, List[Dict]]:
        """Get all available models grouped by provider"""
        result = {
            "ollama": AVAILABLE_MODELS.get(LLMProvider.OLLAMA, []),
        }

        # Add models from all providers
        for provider in PROVIDER_INFO:
            provider_models = PROVIDER_INFO[provider].get("models", [])
            result[provider.value] = [
                {"id": m, "name": m, "category": "general"}
                for m in provider_models
            ]

        return result

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of all supported providers"""
        return self.litellm.get_available_providers()

    def get_recommended_models(self, vram_gb: int = 4) -> List[Dict]:
        """Get models recommended for specific VRAM size"""
        if vram_gb <= 4:
            return RECOMMENDED_MODELS["4GB"]
        elif vram_gb <= 8:
            return RECOMMENDED_MODELS["8GB"]
        elif vram_gb <= 16:
            return RECOMMENDED_MODELS["16GB"]
        else:
            return RECOMMENDED_MODELS["24GB+"]

    def get_current_config(self) -> Optional[Dict]:
        """Get current configuration"""
        if not self.current_config:
            return None

        return {
            "provider": self.current_config.provider.value,
            "model": self.current_config.model,
            "base_url": self.current_config.base_url or settings.OLLAMA_BASE_URL,
            "max_tokens": self.current_config.max_tokens,
            "temperature": self.current_config.temperature,
            "context_length": self.current_config.context_length
        }

    async def health_check(self) -> Dict[str, Any]:
        """Full health check"""
        if self.current_config and self.current_config.provider == LLMProvider.OLLAMA:
            if self.ollama_provider:
                return await self.ollama_provider.health_check()

        # For other providers, do a test call
        provider_type = self._get_provider_type()
        result = await self.litellm.test_provider(
            provider=provider_type,
            model=self.current_config.model if self.current_config else settings.DEFAULT_LLM_MODEL,
            api_key_encrypted=self.current_config.api_key_encrypted if self.current_config else None,
            base_url=self.current_config.base_url if self.current_config else None,
        )

        return {
            "status": "healthy" if result["success"] else "unhealthy",
            "provider": provider_type.value,
            "message": result["message"],
        }

    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict, None]:
        """Pull a model from Ollama"""
        if not self.ollama_provider:
            self.ollama_provider = OllamaProvider(
                LLMConfig(
                    provider=LLMProvider.OLLAMA,
                    model=model_name,
                    base_url=settings.OLLAMA_BASE_URL
                )
            )

        async for progress in self.ollama_provider.pull_model(model_name):
            yield progress

    async def test_provider(
        self,
        provider: str,
        model: str,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Test a provider configuration"""
        try:
            provider_type = ProviderType(provider.lower())
        except ValueError:
            return {"success": False, "message": f"Unknown provider: {provider}"}

        return await self.litellm.test_provider(
            provider=provider_type,
            model=model,
            api_key_encrypted=api_key_encrypted,
            base_url=base_url,
        )

    async def close(self):
        """Cleanup resources"""
        if self.ollama_provider:
            await self.ollama_provider.close()


# Global service instance
llm_service = LLMService()
