"""
Scoratis LLM Service - Cloud Provider Support

This is a facade service that delegates to the centralized LiteLLMService.
It maintains backwards compatibility with the existing API while leveraging
the centralized error handling and validation from LiteLLMService.
"""

from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
import logging

from models import ProviderType, PROVIDER_INFO
from services.litellm_service import (
    get_litellm_service,
    LLMGenerationError,
    LLMError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: ProviderType
    model: str
    base_url: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.6
    top_p: float = 0.9
    context_length: int = 4096
    frequency_penalty: float = 0.2


class LLMService:
    """
    Universal LLM service supporting multiple cloud providers via LiteLLM.

    This is a facade that delegates to the centralized LiteLLMService
    while maintaining backwards compatibility with the existing API.
    """

    def __init__(self):
        # No default config: accounts must configure their own provider
        # (Settings page) - the deployment's env-configured GROQ_API_KEY/
        # DEFAULT_LLM_PROVIDER is no longer auto-seeded here. Every caller
        # must resolve a real per-user config before calling set_provider();
        # generate()/generate_stream()/etc. all raise if current_config is
        # still None.
        self.current_config: Optional[LLMConfig] = None
        self.litellm = get_litellm_service()

    def set_provider(
        self,
        model: str,
        provider: str,
        base_url: Optional[str] = None,
        api_key_encrypted: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        context_length: int = 4096
    ):
        """Set the LLM configuration"""
        provider_enum = ProviderType(provider.lower())

        self.current_config = LLMConfig(
            provider=provider_enum,
            model=model,
            base_url=base_url,
            api_key_encrypted=api_key_encrypted,
            max_tokens=max_tokens,
            temperature=temperature,
            context_length=context_length
        )

        logger.info(f"LLM configured: {model} via {provider}")

    def _get_provider_type(self) -> ProviderType:
        """Convert current config provider to ProviderType"""
        if self.current_config:
            return self.current_config.provider
        raise Exception("LLM provider not configured")

    def has_api_key(self) -> bool:
        """Whether the currently configured provider has a usable key (DB or env)."""
        if not self.current_config:
            return False
        return self.litellm.has_api_key(self.current_config.provider, self.current_config.api_key_encrypted)

    # ==================== GENERATION METHODS ====================
    # These delegate to LiteLLMService and let exceptions propagate

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a response using LiteLLM.

        Args:
            max_tokens: Override the configured provider's default token budget
                for this call.

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
            max_tokens=max_tokens or self.current_config.max_tokens,
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
        provider = self.current_config.provider if self.current_config else None

        if provider is None:
            return {
                "available": False,
                "message": "No LLM provider configured",
                "error_type": "not_configured",
            }

        return {
            "available": True,
            "message": f"Cloud provider '{provider.value}' configured",
            "error_type": None,
        }

    # ==================== PROVIDER MANAGEMENT ====================

    async def check_availability(self) -> Dict[str, Any]:
        """Check provider availability"""
        return {
            "providers": self.litellm.get_available_providers(),
        }

    def get_available_models(self) -> Dict[str, List[Dict]]:
        """Get all available models grouped by provider"""
        result = {}

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

    def get_current_config(self) -> Optional[Dict]:
        """Get current configuration"""
        if not self.current_config:
            return None

        return {
            "provider": self.current_config.provider.value,
            "model": self.current_config.model,
            "base_url": self.current_config.base_url,
            "max_tokens": self.current_config.max_tokens,
            "temperature": self.current_config.temperature,
            "context_length": self.current_config.context_length
        }

    async def health_check(self) -> Dict[str, Any]:
        """Full health check"""
        if not self.current_config:
            return {
                "status": "unconfigured",
                "provider": None,
                "message": "No LLM provider configured",
            }

        result = await self.litellm.test_provider(
            provider=self.current_config.provider,
            model=self.current_config.model,
            api_key_encrypted=self.current_config.api_key_encrypted,
            base_url=self.current_config.base_url,
        )

        return {
            "status": "healthy" if result["success"] else "unhealthy",
            "provider": self.current_config.provider.value,
            "message": result["message"],
        }

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
        pass


# Global service instance
llm_service = LLMService()
