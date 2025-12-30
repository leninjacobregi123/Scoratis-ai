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
"""

import os
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

import litellm
from litellm import acompletion, completion

from config import settings
from services.encryption_service import get_encryption_service
from models import ProviderType, PROVIDER_INFO

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False  # Set to True for debugging


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


class LiteLLMService:
    """
    Universal LLM service using LiteLLM.
    Supports multiple providers with a consistent interface.
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
            ProviderType.LMSTUDIO: "openai/",  # LM Studio uses OpenAI-compatible API
            ProviderType.LOCALAI: "openai/",   # LocalAI uses OpenAI-compatible API
            ProviderType.TEXTGENWEBUI: "openai/",  # Text Gen WebUI uses OpenAI-compatible API
            # Cloud providers
            ProviderType.OPENAI: "",  # OpenAI is the default, no prefix needed
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
        # First try encrypted key from database
        if encrypted_key:
            try:
                return self.encryption.decrypt(encrypted_key)
            except Exception as e:
                logger.warning(f"Failed to decrypt key for {provider}: {e}")

        # Fall back to environment variable
        return self._env_keys.get(provider)

    def _prepare_litellm_kwargs(
        self,
        config: LiteLLMConfig,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare kwargs for LiteLLM completion call"""
        # Build message list
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        # Get model string
        model_string = self._get_model_string(config.provider, config.model)

        kwargs = {
            "model": model_string,
            "messages": api_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": config.stream,
        }

        # Add API key if required
        if config.api_key:
            kwargs["api_key"] = config.api_key

        # Add base URL for Ollama or custom endpoints
        if config.base_url:
            if config.provider == ProviderType.OLLAMA:
                kwargs["api_base"] = config.base_url
            elif config.provider == ProviderType.AZURE:
                kwargs["api_base"] = config.base_url

        # Provider-specific settings for local providers
        local_providers_with_openai_api = [
            ProviderType.LMSTUDIO,
            ProviderType.LOCALAI,
            ProviderType.TEXTGENWEBUI,
        ]

        if config.provider == ProviderType.OLLAMA:
            # Ollama-specific optimizations
            kwargs["api_base"] = config.base_url or settings.OLLAMA_BASE_URL
        elif config.provider in local_providers_with_openai_api:
            # Local providers using OpenAI-compatible API
            default_urls = {
                ProviderType.LMSTUDIO: "http://localhost:1234/v1",
                ProviderType.LOCALAI: "http://localhost:8080/v1",
                ProviderType.TEXTGENWEBUI: "http://localhost:5000/v1",
            }
            kwargs["api_base"] = config.base_url or default_urls.get(config.provider)
            # These local providers don't need real API keys
            kwargs["api_key"] = "not-needed"

        return kwargs

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
    ) -> str:
        """
        Generate a non-streaming response from any supported provider.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt for the model
            provider: LLM provider (defaults to Ollama)
            model: Model name (defaults to llama3.2)
            api_key_encrypted: Encrypted API key from database
            base_url: Custom base URL (for Ollama/Azure)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        # Use defaults if not specified
        provider = provider or ProviderType(settings.DEFAULT_LLM_PROVIDER)
        model = model or settings.DEFAULT_LLM_MODEL

        # Get API key
        api_key = self._get_api_key(provider, api_key_encrypted)

        # Check if API key is required but missing
        provider_info = PROVIDER_INFO.get(provider, {})
        if provider_info.get("requires_api_key") and not api_key:
            raise ValueError(f"API key required for {provider.value} but not configured")

        # For Ollama, prioritize settings.OLLAMA_BASE_URL (from env) over hardcoded default
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
        )

        kwargs = self._prepare_litellm_kwargs(config, messages, system_prompt)

        try:
            logger.info(f"LiteLLM generating with {provider.value}/{model}")
            response = await acompletion(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LiteLLM generation error ({provider.value}/{model}): {e}")
            raise Exception(f"LLM generation failed: {str(e)}")

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
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from any supported provider.

        Yields:
            Text chunks as they are generated
        """
        # Use defaults if not specified
        provider = provider or ProviderType(settings.DEFAULT_LLM_PROVIDER)
        model = model or settings.DEFAULT_LLM_MODEL

        # Get API key
        api_key = self._get_api_key(provider, api_key_encrypted)

        # Check if API key is required but missing
        provider_info = PROVIDER_INFO.get(provider, {})
        if provider_info.get("requires_api_key") and not api_key:
            raise ValueError(f"API key required for {provider.value} but not configured")

        # For Ollama, prioritize settings.OLLAMA_BASE_URL (from env) over hardcoded default
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
        )

        kwargs = self._prepare_litellm_kwargs(config, messages, system_prompt)

        try:
            logger.info(f"LiteLLM streaming with {provider.value}/{model}")
            response = await acompletion(**kwargs)

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LiteLLM streaming error ({provider.value}/{model}): {e}")
            raise Exception(f"LLM streaming failed: {str(e)}")

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
    ) -> Dict[str, Any]:
        """
        Generate a response with tool/function calling support.

        Args:
            messages: List of message dicts
            system_prompt: System prompt
            tools: List of OpenAI-format tool schemas
            provider: LLM provider
            model: Model name
            api_key_encrypted: Encrypted API key
            base_url: Custom base URL
            max_tokens: Max tokens
            temperature: Temperature

        Returns:
            Dict with 'content' and optionally 'tool_calls'
        """
        # Use defaults if not specified
        provider = provider or ProviderType(settings.DEFAULT_LLM_PROVIDER)
        model = model or settings.DEFAULT_LLM_MODEL

        # Get API key
        api_key = self._get_api_key(provider, api_key_encrypted)

        # Check if API key is required but missing
        provider_info = PROVIDER_INFO.get(provider, {})
        if provider_info.get("requires_api_key") and not api_key:
            raise ValueError(f"API key required for {provider.value} but not configured")

        # For Ollama, prioritize settings.OLLAMA_BASE_URL
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
        )

        kwargs = self._prepare_litellm_kwargs(config, messages, system_prompt)

        # Add tools if provided
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

            # Extract tool calls if present
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
            logger.error(f"LiteLLM tool generation error ({provider.value}/{model}): {e}")
            # Fallback: return empty tool calls, let agent handle gracefully
            return {
                "content": "",
                "tool_calls": [],
                "error": str(e)
            }

    async def test_provider(
        self,
        provider: ProviderType,
        model: str,
        api_key_encrypted: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test if a provider configuration works.

        Returns:
            Dict with 'success', 'message', and optionally 'response'
        """
        try:
            test_messages = [{"role": "user", "content": "Say 'Hello' in one word."}]

            response = await self.generate(
                messages=test_messages,
                system_prompt="You are a helpful assistant. Respond briefly.",
                provider=provider,
                model=model,
                api_key_encrypted=api_key_encrypted,
                base_url=base_url,
                max_tokens=50,
                temperature=0.5,
            )

            return {
                "success": True,
                "message": f"Successfully connected to {provider.value}",
                "response": response[:100] if response else "",
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
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


# Singleton instance
_litellm_service: Optional[LiteLLMService] = None


def get_litellm_service() -> LiteLLMService:
    """Get the global LiteLLM service instance."""
    global _litellm_service
    if _litellm_service is None:
        _litellm_service = LiteLLMService()
    return _litellm_service
