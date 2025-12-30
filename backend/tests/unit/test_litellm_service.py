"""
Unit Tests for LiteLLM Service

Tests the universal LLM service:
- Provider configuration
- Model string generation
- API key management
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


class TestLiteLLMConfig:
    """Tests for LiteLLM configuration."""

    def test_config_dataclass(self):
        """Test LiteLLMConfig dataclass creation."""
        from services.litellm_service import LiteLLMConfig
        from models import ProviderType

        config = LiteLLMConfig(
            provider=ProviderType.OLLAMA,
            model="llama3.2",
            max_tokens=2048,
            temperature=0.7
        )

        assert config.provider == ProviderType.OLLAMA
        assert config.model == "llama3.2"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7
        assert config.stream is True  # default


class TestLiteLLMServiceModelStrings:
    """Tests for model string generation."""

    @pytest.fixture
    def litellm_service(self):
        """Create a LiteLLM service instance."""
        with patch("services.litellm_service.get_encryption_service"):
            from services.litellm_service import LiteLLMService
            return LiteLLMService()

    def test_ollama_model_string(self, litellm_service):
        """Test Ollama model string generation."""
        from models import ProviderType

        result = litellm_service._get_model_string(ProviderType.OLLAMA, "llama3.2")
        assert result == "ollama/llama3.2"

    def test_openai_model_string(self, litellm_service):
        """Test OpenAI model string (no prefix)."""
        from models import ProviderType

        result = litellm_service._get_model_string(ProviderType.OPENAI, "gpt-4")
        assert result == "gpt-4"

    def test_anthropic_model_string(self, litellm_service):
        """Test Anthropic model string."""
        from models import ProviderType

        result = litellm_service._get_model_string(ProviderType.ANTHROPIC, "claude-3-opus")
        assert result == "anthropic/claude-3-opus"

    def test_google_model_string(self, litellm_service):
        """Test Google/Gemini model string."""
        from models import ProviderType

        result = litellm_service._get_model_string(ProviderType.GOOGLE, "gemini-pro")
        assert result == "gemini/gemini-pro"

    def test_groq_model_string(self, litellm_service):
        """Test Groq model string."""
        from models import ProviderType

        result = litellm_service._get_model_string(ProviderType.GROQ, "mixtral-8x7b")
        assert result == "groq/mixtral-8x7b"


class TestLiteLLMServiceProviders:
    """Tests for provider management."""

    @pytest.fixture
    def litellm_service(self):
        """Create a LiteLLM service instance."""
        with patch("services.litellm_service.get_encryption_service"):
            from services.litellm_service import LiteLLMService
            return LiteLLMService()

    def test_get_available_providers(self, litellm_service):
        """Test getting list of available providers."""
        providers = litellm_service.get_available_providers()

        assert isinstance(providers, list)
        assert len(providers) > 0

        # Check structure
        provider = providers[0]
        assert "id" in provider
        assert "name" in provider
        assert "models" in provider

    def test_get_provider_models(self, litellm_service):
        """Test getting models for a provider."""
        from models import ProviderType

        models = litellm_service.get_provider_models(ProviderType.OLLAMA)

        assert isinstance(models, list)
        assert len(models) > 0


class TestLiteLLMServiceGeneration:
    """Tests for LLM generation methods."""

    @pytest.fixture
    def mock_litellm(self):
        """Mock litellm module."""
        with patch("services.litellm_service.acompletion") as mock:
            mock.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Test response"))]
            )
            yield mock

    @pytest.fixture
    def litellm_service(self):
        """Create a LiteLLM service instance with mocks."""
        with patch("services.litellm_service.get_encryption_service"):
            from services.litellm_service import LiteLLMService
            return LiteLLMService()

    @pytest.mark.asyncio
    async def test_generate_returns_string(self, litellm_service, mock_litellm):
        """Test that generate returns a string response."""
        result = await litellm_service.generate(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are helpful."
        )

        assert isinstance(result, str)
        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_tools_structure(self, litellm_service):
        """Test generate_with_tools returns proper structure."""
        with patch("services.litellm_service.acompletion") as mock:
            mock.return_value = MagicMock(
                choices=[MagicMock(
                    message=MagicMock(
                        content="I'll search for that.",
                        tool_calls=[
                            MagicMock(
                                id="call_1",
                                function=MagicMock(
                                    name="search_knowledge_base",
                                    arguments='{"query": "test"}'
                                )
                            )
                        ]
                    )
                )]
            )

            result = await litellm_service.generate_with_tools(
                messages=[{"role": "user", "content": "Search my notes"}],
                system_prompt="You are helpful.",
                tools=[{"type": "function", "function": {"name": "search"}}]
            )

            assert "content" in result
            assert "tool_calls" in result
            assert len(result["tool_calls"]) > 0

    @pytest.mark.asyncio
    async def test_generate_handles_error_gracefully(self, litellm_service):
        """Test that errors are handled gracefully."""
        with patch("services.litellm_service.acompletion") as mock:
            mock.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await litellm_service.generate(
                    messages=[{"role": "user", "content": "Hello"}],
                    system_prompt="You are helpful."
                )

            assert "LLM generation failed" in str(exc_info.value)


class TestLiteLLMServiceTestProvider:
    """Tests for provider testing functionality."""

    @pytest.fixture
    def litellm_service(self):
        """Create a LiteLLM service instance."""
        with patch("services.litellm_service.get_encryption_service"):
            from services.litellm_service import LiteLLMService
            return LiteLLMService()

    @pytest.mark.asyncio
    async def test_test_provider_success(self, litellm_service):
        """Test successful provider test."""
        from models import ProviderType

        with patch.object(litellm_service, "generate", return_value="Hello"):
            result = await litellm_service.test_provider(
                provider=ProviderType.OLLAMA,
                model="llama3.2"
            )

            assert result["success"] is True
            assert "Successfully connected" in result["message"]

    @pytest.mark.asyncio
    async def test_test_provider_failure(self, litellm_service):
        """Test failed provider test."""
        from models import ProviderType

        with patch.object(litellm_service, "generate", side_effect=Exception("Connection failed")):
            result = await litellm_service.test_provider(
                provider=ProviderType.OPENAI,
                model="gpt-4"
            )

            assert result["success"] is False
            assert "Connection failed" in result["message"]
