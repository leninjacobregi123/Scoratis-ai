"""
Scoratis LLM Service - Universal Provider Support

This is a facade service that delegates to the centralized LiteLLMService.
It maintains backwards compatibility with the existing API while leveraging
the centralized error handling and validation from LiteLLMService.
"""

import os
import httpx
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging

from config import settings
from models import ProviderType, PROVIDER_INFO
from services.litellm_service import (
    get_litellm_service,
    LLMGenerationError,
    LLMError,
)

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

    This is a facade that delegates to the centralized LiteLLMService
    while maintaining backwards compatibility with the existing API.
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

        if provider_enum == LLMProvider.OLLAMA:
            self.ollama_provider = OllamaProvider(self.current_config)

        logger.info(f"LLM configured: {model} via {provider}")

    def _get_provider_type(self) -> ProviderType:
        """Convert current config provider to ProviderType"""
        if self.current_config:
            return ProviderType(self.current_config.provider.value)
        return ProviderType.OLLAMA

    # ==================== GENERATION METHODS ====================
    # These delegate to LiteLLMService and let exceptions propagate

    async def generate(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        """
        Generate a response using LiteLLM.

        Raises:
            LLMGenerationError: On any LLM failure with structured error info
        """
        if not self.current_config:
            raise Exception("LLM provider not configured")

        # Delegate to centralized service - let LLMGenerationError propagate
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
        system_prompt: str,
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        api_key_encrypted: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using LiteLLM.

        Args:
            messages: Conversation messages
            system_prompt: System prompt to use
            provider: Optional provider override (uses current_config if not specified)
            model: Optional model override (uses current_config if not specified)
            api_key_encrypted: Optional API key for cloud providers

        Raises:
            LLMGenerationError: On any LLM failure with structured error info
        """
        if not self.current_config:
            raise Exception("LLM provider not configured")

        # Use provided provider/model or fall back to current_config
        use_provider = provider if provider else self._get_provider_type()
        use_model = model if model else self.current_config.model

        # Get API key - use provided one, or fall back to current_config
        api_key = api_key_encrypted or self.current_config.api_key_encrypted
        base_url = self.current_config.base_url

        # If using a different provider, log it
        if provider and provider != self._get_provider_type():
            logger.info(f"Using override provider: {use_provider.value}/{use_model}")

        logger.info(f"Streaming with {use_provider.value}/{use_model}")

        async for chunk in self.litellm.generate_stream(
            messages=messages,
            system_prompt=system_prompt,
            provider=use_provider,
            model=use_model,
            api_key_encrypted=api_key,
            base_url=base_url,
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

    # ==================== VALIDATION METHODS ====================
    # These delegate to the centralized LiteLLMService validation

    async def validate_model_config(
        self,
        provider: str,
        model: str,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Validate an LLM configuration by attempting a test API call with timeout.

        Delegates to the centralized LiteLLMService.validate_config method.

        Returns:
            Dict with 'success', 'message', 'error_type', and optionally 'suggestion'
        """
        try:
            provider_type = ProviderType(provider.lower())
        except ValueError:
            return {
                "success": False,
                "message": f"Unknown provider: {provider}",
                "error_type": "invalid_provider",
            }

        # For Ollama, first check if model is installed (quick check)
        if provider_type == ProviderType.OLLAMA:
            is_installed, installed_models = await self.litellm.check_model_installed(model)

            # Check server availability
            ollama_health = await self.litellm.check_ollama_health()
            if not ollama_health.get("available"):
                return {
                    "success": False,
                    "message": "Ollama server is not running",
                    "error_type": "server_unavailable",
                    "suggestion": "Start Ollama with: ollama serve",
                }

            if not is_installed:
                return {
                    "success": False,
                    "message": f"Model '{model}' is not installed locally",
                    "error_type": "model_not_installed",
                    "suggestion": f"Download the model with: ollama pull {model}",
                    "installed_models": installed_models[:10],
                }

        # Use centralized validation with timeout
        is_valid, message, error = await self.litellm.validate_config(
            provider=provider_type,
            model=model,
            api_key_encrypted=api_key_encrypted,
            base_url=base_url,
            timeout=timeout_seconds,
        )

        if is_valid:
            return {
                "success": True,
                "message": message,
                "error_type": None,
            }
        else:
            return {
                "success": False,
                "message": message,
                "error_type": error.error_type if error else "unknown_error",
                "suggestion": error.suggestion if error else None,
            }

    async def check_model_availability(self, model: str = None) -> Dict[str, Any]:
        """
        Quick check if current/specified model is available and ready.

        Returns:
            Dict with 'available', 'message', 'error_type', and 'suggestion'
        """
        model = model or (self.current_config.model if self.current_config else settings.DEFAULT_LLM_MODEL)
        provider = self.current_config.provider if self.current_config else LLMProvider.OLLAMA

        if provider == LLMProvider.OLLAMA:
            ollama_health = await self.litellm.check_ollama_health()

            if not ollama_health.get("available"):
                return {
                    "available": False,
                    "message": "Ollama server is not running",
                    "error_type": "server_unavailable",
                    "suggestion": "Start Ollama with: ollama serve",
                }

            is_installed, installed_models = await self.litellm.check_model_installed(model)

            if not is_installed:
                return {
                    "available": False,
                    "message": f"Model '{model}' is not installed",
                    "error_type": "model_not_installed",
                    "suggestion": f"ollama pull {model}",
                    "installed_models": installed_models[:5],
                }

            return {
                "available": True,
                "message": f"Model '{model}' is ready",
                "error_type": None,
            }
        else:
            # For cloud providers, assume available if API key is set
            return {
                "available": True,
                "message": f"Cloud provider '{provider.value}' configured",
                "error_type": None,
            }

    # ==================== PROVIDER MANAGEMENT ====================

    async def check_availability(self) -> Dict[str, Any]:
        """Check provider availability"""
        result = {}

        ollama_health = await self.litellm.check_ollama_health()
        result["ollama"] = {
            "available": ollama_health["available"],
            "installed_models": ollama_health.get("installed_models", []),
        }

        result["providers"] = self.litellm.get_available_providers()

        return result

    def get_available_models(self) -> Dict[str, List[Dict]]:
        """Get all available models grouped by provider"""
        result = {
            "ollama": AVAILABLE_MODELS.get(LLMProvider.OLLAMA, []),
        }

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
