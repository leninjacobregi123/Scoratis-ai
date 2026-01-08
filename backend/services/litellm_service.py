"""
LiteLLM Universal LLM Service
Provides a unified interface to 100+ LLM providers including:
- Ollama (local)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Groq
- Together AI
- Azure OpenAI

This service is the SINGLE SOURCE OF TRUTH for all LLM interactions.
All error handling, validation, and configuration is centralized here.
"""

import os
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from dataclasses import dataclass
from enum import Enum

import litellm
from litellm import acompletion, completion
from litellm.exceptions import (
    Timeout as LiteLLMTimeout,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    APIError,
)

from config import settings
from services.encryption_service import get_encryption_service
from models import ProviderType, PROVIDER_INFO

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging

# Default timeout for LLM calls (in seconds)
# Increased for Ollama tool calling which can be slow
DEFAULT_TIMEOUT = 180
VALIDATION_TIMEOUT = 60


@dataclass
class LLMError:
    """Structured error information for LLM failures"""
    error_type: str
    message: str
    suggestion: str
    provider: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "suggestion": self.suggestion,
            "provider": self.provider,
            "model": self.model,
        }


@dataclass
class LiteLLMConfig:
    """Configuration for LiteLLM calls"""
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = True
    timeout: int = DEFAULT_TIMEOUT  # Timeout in seconds


class LiteLLMService:
    """
    Centralized Universal LLM service using LiteLLM.

    This is the SINGLE SOURCE OF TRUTH for:
    - LLM configuration validation
    - Model availability checking
    - Response generation
    - Error handling and recovery

    All other parts of the application should use this service
    instead of calling LiteLLM directly.
    """

    def __init__(self):
        self.encryption = get_encryption_service()
        self._provider_configs: Dict[str, Dict] = {}
        self._current_provider: Optional[ProviderType] = None
        self._current_model: Optional[str] = None
        self._load_env_keys()

    def _load_env_keys(self):
        """Load API keys from environment variables"""
        self._env_keys = {
            ProviderType.OPENAI: settings.OPENAI_API_KEY,
            ProviderType.ANTHROPIC: settings.ANTHROPIC_API_KEY,
            ProviderType.GOOGLE: settings.GEMINI_API_KEY,
            ProviderType.GROQ: settings.GROQ_API_KEY,
            ProviderType.TOGETHER: settings.TOGETHER_API_KEY,
            ProviderType.AZURE: settings.AZURE_API_KEY,
        }

    def _get_model_string(self, provider: ProviderType, model: str) -> str:
        """
        Convert provider + model to LiteLLM model string.
        LiteLLM uses prefixes to identify providers.
        """
        prefix_map = {
            # Local providers
            ProviderType.OLLAMA: "ollama/",
            ProviderType.LMSTUDIO: "openai/",
            ProviderType.LOCALAI: "openai/",
            ProviderType.TEXTGENWEBUI: "openai/",
            # Cloud providers
            ProviderType.OPENAI: "",
            ProviderType.ANTHROPIC: "anthropic/",
            ProviderType.GOOGLE: "gemini/",
            ProviderType.GROQ: "groq/",
            ProviderType.TOGETHER: "together_ai/",
            ProviderType.AZURE: "azure/",
            ProviderType.DEEPSEEK: "deepseek/",
        }
        prefix = prefix_map.get(provider, "")
        return f"{prefix}{model}"

    def _get_api_key(
        self,
        provider: ProviderType,
        encrypted_key: Optional[str] = None
    ) -> Optional[str]:
        """Get API key from encrypted storage or environment"""
        if encrypted_key:
            try:
                return self.encryption.decrypt(encrypted_key)
            except Exception as e:
                logger.warning(f"Failed to decrypt key for {provider}: {e}")

        return self._env_keys.get(provider)

    def _categorize_error(
        self,
        error: Exception,
        provider: ProviderType,
        model: str
    ) -> LLMError:
        """
        Categorize an exception into a user-friendly error with suggestions.
        This is the centralized error categorization logic.
        """
        error_str = str(error).lower()
        provider_name = provider.value

        # Timeout errors - model may be downloading or too slow
        if isinstance(error, LiteLLMTimeout) or "timeout" in error_str:
            return LLMError(
                error_type="timeout",
                message=f"Connection to model '{model}' timed out",
                suggestion="The model may be downloading or the server is slow. Wait a few minutes and try again.",
                provider=provider_name,
                model=model,
            )

        # Connection errors - server not running or network issues
        if isinstance(error, APIConnectionError) or "connection" in error_str or "refused" in error_str:
            if provider == ProviderType.OLLAMA:
                return LLMError(
                    error_type="server_unavailable",
                    message="Cannot connect to Ollama server",
                    suggestion="Start Ollama with: ollama serve",
                    provider=provider_name,
                    model=model,
                )
            return LLMError(
                error_type="connection_error",
                message=f"Cannot connect to {provider_name} server",
                suggestion="Check your network connection and server URL",
                provider=provider_name,
                model=model,
            )

        # Authentication errors
        if isinstance(error, AuthenticationError) or "unauthorized" in error_str or "api_key" in error_str or "authentication" in error_str:
            return LLMError(
                error_type="authentication_error",
                message=f"Authentication failed for {provider_name}",
                suggestion="Check your API key in Settings",
                provider=provider_name,
                model=model,
            )

        # Rate limit errors
        if isinstance(error, RateLimitError) or "rate limit" in error_str:
            return LLMError(
                error_type="rate_limit",
                message=f"Rate limit exceeded for {provider_name}",
                suggestion="Wait a moment before trying again, or upgrade your API plan",
                provider=provider_name,
                model=model,
            )

        # Model not found errors
        if "not found" in error_str or "does not exist" in error_str:
            if provider == ProviderType.OLLAMA:
                return LLMError(
                    error_type="model_not_installed",
                    message=f"Model '{model}' is not installed locally",
                    suggestion=f"Download with: ollama pull {model}",
                    provider=provider_name,
                    model=model,
                )
            return LLMError(
                error_type="model_not_found",
                message=f"Model '{model}' not found",
                suggestion="Check the model name and try again",
                provider=provider_name,
                model=model,
            )

        # Out of memory errors
        if "out of memory" in error_str or "oom" in error_str or "cuda" in error_str or "memory" in error_str:
            return LLMError(
                error_type="insufficient_memory",
                message=f"Model '{model}' requires more memory than available",
                suggestion="Try a smaller model: llama3.2:1b for 4GB, llama3.2 for 8GB",
                provider=provider_name,
                model=model,
            )

        # Service unavailable
        if isinstance(error, ServiceUnavailableError) or "service unavailable" in error_str:
            return LLMError(
                error_type="service_unavailable",
                message=f"{provider_name} service is currently unavailable",
                suggestion="The service may be overloaded. Try again in a few minutes.",
                provider=provider_name,
                model=model,
            )

        # Generic API error
        if isinstance(error, APIError):
            return LLMError(
                error_type="api_error",
                message=f"API error from {provider_name}: {str(error)[:100]}",
                suggestion="Check the error message and try again",
                provider=provider_name,
                model=model,
            )

        # Unknown error - fallback
        return LLMError(
            error_type="unknown_error",
            message=f"Unexpected error: {str(error)[:150]}",
            suggestion="Check logs for details or try a different model",
            provider=provider_name,
            model=model,
        )

    def _prepare_litellm_kwargs(
        self,
        config: LiteLLMConfig,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare kwargs for LiteLLM completion call.

        IMPORTANT: Preserves tool_calls and tool_call_id fields for Groq/OpenAI compatibility.
        """
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        # Process messages, preserving tool-related fields
        for msg in messages:
            processed_msg = {"role": msg.get("role", "user")}

            # Always include content (can be empty string for tool-calling assistant messages)
            if "content" in msg:
                processed_msg["content"] = msg["content"]

            # Preserve tool_calls for assistant messages (required by Groq/OpenAI)
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                processed_msg["tool_calls"] = msg["tool_calls"]
                # Groq requires content to be null or omitted when tool_calls present
                if not msg.get("content"):
                    processed_msg["content"] = None

            # Preserve tool_call_id and name for tool response messages (required by Groq)
            if msg.get("role") == "tool":
                if "tool_call_id" in msg:
                    processed_msg["tool_call_id"] = msg["tool_call_id"]
                if "name" in msg:
                    processed_msg["name"] = msg["name"]

            api_messages.append(processed_msg)

        model_string = self._get_model_string(config.provider, config.model)

        kwargs = {
            "model": model_string,
            "messages": api_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": config.stream,
            "timeout": config.timeout,  # Add timeout to all calls
        }

        if config.api_key:
            kwargs["api_key"] = config.api_key

        if config.base_url:
            if config.provider == ProviderType.OLLAMA:
                kwargs["api_base"] = config.base_url
            elif config.provider == ProviderType.AZURE:
                kwargs["api_base"] = config.base_url

        local_providers_with_openai_api = [
            ProviderType.LMSTUDIO,
            ProviderType.LOCALAI,
            ProviderType.TEXTGENWEBUI,
        ]

        if config.provider == ProviderType.OLLAMA:
            kwargs["api_base"] = config.base_url or settings.OLLAMA_BASE_URL
        elif config.provider in local_providers_with_openai_api:
            default_urls = {
                ProviderType.LMSTUDIO: "http://localhost:1234/v1",
                ProviderType.LOCALAI: "http://localhost:8080/v1",
                ProviderType.TEXTGENWEBUI: "http://localhost:5000/v1",
            }
            kwargs["api_base"] = config.base_url or default_urls.get(config.provider)
            kwargs["api_key"] = "not-needed"

        return kwargs

    # ==================== VALIDATION METHODS ====================

    async def validate_config(
        self,
        provider: ProviderType,
        model: str,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = VALIDATION_TIMEOUT,
    ) -> Tuple[bool, str, Optional[LLMError]]:
        """
        Validate an LLM configuration by making a test API call.

        This is the centralized validation method that handles:
        1. Timeout for slow model downloads
        2. Connection errors for server unavailable
        3. Authentication errors for invalid API keys
        4. Model not found errors
        5. Memory errors for models too large

        Args:
            provider: LLM provider type
            model: Model name to validate
            api_key_encrypted: Encrypted API key (for cloud providers)
            base_url: Custom base URL (for local providers)
            timeout: Timeout in seconds (default: 30)

        Returns:
            Tuple of (is_valid: bool, message: str, error: Optional[LLMError])
        """
        try:
            # Get API key
            api_key = self._get_api_key(provider, api_key_encrypted)

            # Check if API key is required but missing
            provider_info = PROVIDER_INFO.get(provider, {})
            if provider_info.get("requires_api_key") and not api_key:
                return (
                    False,
                    f"API key required for {provider.value} but not configured",
                    LLMError(
                        error_type="authentication_error",
                        message=f"API key required for {provider.value}",
                        suggestion="Add your API key in Settings",
                        provider=provider.value,
                        model=model,
                    )
                )

            # Determine base URL
            if provider == ProviderType.OLLAMA:
                effective_base_url = base_url or settings.OLLAMA_BASE_URL
            else:
                effective_base_url = base_url or provider_info.get("default_base_url")

            # Build config with validation timeout
            config = LiteLLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=effective_base_url,
                max_tokens=50,  # Small for validation
                temperature=0.5,
                stream=False,
                timeout=timeout,
            )

            # Prepare and execute test call
            test_messages = [{"role": "user", "content": "Hello"}]
            kwargs = self._prepare_litellm_kwargs(config, test_messages, "Respond briefly.")

            logger.info(f"Validating LLM config: {provider.value}/{model}")
            response = await acompletion(**kwargs)

            # Check if we got a valid response
            if response and response.choices and response.choices[0].message.content:
                logger.info(f"Successfully validated LLM config for model: {model}")
                return (True, f"Model '{model}' validated successfully", None)
            else:
                logger.warning(f"Validation returned empty response for model: {model}")
                return (
                    False,
                    "LLM returned an empty response",
                    LLMError(
                        error_type="empty_response",
                        message="Model returned an empty response",
                        suggestion="The model may not be working correctly. Try another model.",
                        provider=provider.value,
                        model=model,
                    )
                )

        except LiteLLMTimeout as e:
            # Specific timeout handling - model may be downloading
            logger.error(f"Validation timeout for {provider.value}/{model}: {e}")
            error = LLMError(
                error_type="timeout",
                message=f"Connection to model '{model}' timed out after {timeout} seconds",
                suggestion="The model may be downloading. Wait a few minutes and try again, or check 'ollama ps'.",
                provider=provider.value,
                model=model,
            )
            return (False, error.message, error)

        except Exception as e:
            # Catch all other errors and categorize them
            logger.error(f"Validation error for {provider.value}/{model}: {e}")
            error = self._categorize_error(e, provider, model)
            return (False, error.message, error)

    async def check_model_installed(self, model: str) -> Tuple[bool, List[str]]:
        """
        Check if an Ollama model is installed locally.

        Returns:
            Tuple of (is_installed: bool, installed_models: List[str])
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    installed_models = [m["name"] for m in data.get("models", [])]

                    # Check if model is installed (handle tags like llama3.2:latest)
                    model_base = model.split(":")[0]
                    is_installed = any(
                        m.split(":")[0] == model_base or m.startswith(model_base)
                        for m in installed_models
                    )
                    return (is_installed, installed_models)
        except Exception as e:
            logger.warning(f"Failed to check installed models: {e}")

        return (False, [])

    # ==================== GENERATION METHODS ====================

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Generate a non-streaming response from any supported provider.

        This method includes centralized error handling. All errors are
        categorized and re-raised with structured information.

        Raises:
            LLMGenerationError: On any LLM failure with structured error info
        """
        provider = provider or ProviderType(settings.DEFAULT_LLM_PROVIDER)
        model = model or settings.DEFAULT_LLM_MODEL
        api_key = self._get_api_key(provider, api_key_encrypted)

        provider_info = PROVIDER_INFO.get(provider, {})
        if provider_info.get("requires_api_key") and not api_key:
            raise ValueError(f"API key required for {provider.value} but not configured")

        if provider == ProviderType.OLLAMA:
            effective_base_url = base_url or settings.OLLAMA_BASE_URL
        else:
            effective_base_url = base_url or provider_info.get("default_base_url")

        config = LiteLLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=effective_base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            timeout=timeout,
        )

        kwargs = self._prepare_litellm_kwargs(config, messages, system_prompt)

        try:
            logger.info(f"LiteLLM generating with {provider.value}/{model}")
            response = await acompletion(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            # Categorize the error and re-raise with structured info
            error = self._categorize_error(e, provider, model)
            logger.error(f"LiteLLM generation error ({provider.value}/{model}): {error.message}")
            # Re-raise with error info attached
            raise LLMGenerationError(error) from e

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from any supported provider.
        """
        provider = provider or ProviderType(settings.DEFAULT_LLM_PROVIDER)
        model = model or settings.DEFAULT_LLM_MODEL
        api_key = self._get_api_key(provider, api_key_encrypted)

        provider_info = PROVIDER_INFO.get(provider, {})
        if provider_info.get("requires_api_key") and not api_key:
            raise ValueError(f"API key required for {provider.value} but not configured")

        if provider == ProviderType.OLLAMA:
            effective_base_url = base_url or settings.OLLAMA_BASE_URL
        else:
            effective_base_url = base_url or provider_info.get("default_base_url")

        config = LiteLLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=effective_base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            timeout=timeout,
        )

        kwargs = self._prepare_litellm_kwargs(config, messages, system_prompt)

        try:
            logger.info(f"LiteLLM streaming with {provider.value}/{model}")
            response = await acompletion(**kwargs)

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error = self._categorize_error(e, provider, model)
            logger.error(f"LiteLLM streaming error ({provider.value}/{model}): {error.message}")
            raise LLMGenerationError(error) from e

    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        tools: List[Dict[str, Any]],
        provider: Optional[ProviderType] = None,
        model: Optional[str] = None,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Generate a response with tool/function calling support.
        """
        provider = provider or ProviderType(settings.DEFAULT_LLM_PROVIDER)
        model = model or settings.DEFAULT_LLM_MODEL
        api_key = self._get_api_key(provider, api_key_encrypted)

        provider_info = PROVIDER_INFO.get(provider, {})
        if provider_info.get("requires_api_key") and not api_key:
            raise ValueError(f"API key required for {provider.value} but not configured")

        if provider == ProviderType.OLLAMA:
            effective_base_url = base_url or settings.OLLAMA_BASE_URL
        else:
            effective_base_url = base_url or provider_info.get("default_base_url")

        config = LiteLLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=effective_base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            timeout=timeout,
        )

        kwargs = self._prepare_litellm_kwargs(config, messages, system_prompt)

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            logger.info(f"LiteLLM generating with tools via {provider.value}/{model}")
            response = await acompletion(**kwargs)

            message = response.choices[0].message

            result = {
                "content": message.content or "",
                "tool_calls": []
            }

            if hasattr(message, "tool_calls") and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]

            return result

        except Exception as e:
            error = self._categorize_error(e, provider, model)
            logger.error(f"LiteLLM tool generation error ({provider.value}/{model}): {error.message}")
            # Return error info instead of raising for tool calls
            return {
                "content": "",
                "tool_calls": [],
                "error": error.to_dict()
            }

    # ==================== TESTING & HEALTH METHODS ====================

    async def test_provider(
        self,
        provider: ProviderType,
        model: str,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test if a provider configuration works.
        Uses the centralized validate_config method.
        """
        is_valid, message, error = await self.validate_config(
            provider=provider,
            model=model,
            api_key_encrypted=api_key_encrypted,
            base_url=base_url,
        )

        if is_valid:
            return {
                "success": True,
                "message": f"Successfully connected to {provider.value}",
            }
        else:
            return {
                "success": False,
                "message": message,
                "error": error.to_dict() if error else None,
            }

    async def check_ollama_health(self) -> Dict[str, Any]:
        """Check if Ollama is running and list installed models"""
        import httpx

        base_url = settings.OLLAMA_BASE_URL
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {
                        "available": True,
                        "base_url": base_url,
                        "installed_models": models,
                    }
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")

        return {
            "available": False,
            "base_url": base_url,
            "installed_models": [],
            "error": "Ollama not running. Start with: ollama serve",
        }

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of all supported providers with their info"""
        providers = []
        for provider_type, info in PROVIDER_INFO.items():
            providers.append({
                "id": provider_type.value,
                "name": info["display_name"],
                "icon": info["icon"],
                "requires_api_key": info["requires_api_key"],
                "default_base_url": info["default_base_url"],
                "models": info["models"],
            })
        return providers

    def get_provider_models(self, provider: ProviderType) -> List[str]:
        """Get available models for a specific provider"""
        info = PROVIDER_INFO.get(provider)
        if info:
            return info["models"]
        return []


class LLMGenerationError(Exception):
    """
    Custom exception for LLM generation failures.
    Contains structured error information for user feedback.
    """
    def __init__(self, error: LLMError):
        self.error = error
        super().__init__(error.message)

    def get_user_message(self) -> str:
        """Get a user-friendly error message"""
        if self.error.suggestion:
            return f"{self.error.message}. {self.error.suggestion}"
        return self.error.message


# Singleton instance
_litellm_service: Optional[LiteLLMService] = None


def get_litellm_service() -> LiteLLMService:
    """Get the global LiteLLM service instance."""
    global _litellm_service
    if _litellm_service is None:
        _litellm_service = LiteLLMService()
    return _litellm_service
