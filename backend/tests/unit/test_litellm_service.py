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
            provider=ProviderType.GROQ,
            model="llama-3.3-70b-versatile",
            max_tokens=2048,
            temperature=0.7
        )

        assert config.provider == ProviderType.GROQ
        assert config.model == "llama-3.3-70b-versatile"
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

        models = litellm_service.get_provider_models(ProviderType.GROQ)

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
        from models import ProviderType

        # api_key_encrypted is a dummy value decrypted by the mocked
        # encryption service (from the litellm_service fixture's
        # get_encryption_service patch) into a truthy MagicMock, satisfying
        # Groq's "API key required" guard without needing a real key -
        # isolates this test to the acompletion-response-parsing logic.
        result = await litellm_service.generate(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are helpful.",
            provider=ProviderType.GROQ,
            api_key_encrypted="fake_encrypted_key",
        )

        assert isinstance(result, str)
        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_tools_structure(self, litellm_service):
        """Test generate_with_tools returns proper structure."""
        from models import ProviderType

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
                tools=[{"type": "function", "function": {"name": "search"}}],
                provider=ProviderType.GROQ,
                api_key_encrypted="fake_encrypted_key",
            )

            assert "content" in result
            assert "tool_calls" in result
            assert len(result["tool_calls"]) > 0

    @pytest.mark.asyncio
    async def test_generate_handles_error_gracefully(self, litellm_service):
        """Test that errors are handled gracefully."""
        from models import ProviderType

        with patch("services.litellm_service.acompletion") as mock:
            mock.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await litellm_service.generate(
                    messages=[{"role": "user", "content": "Hello"}],
                    system_prompt="You are helpful.",
                    provider=ProviderType.GROQ,
                    api_key_encrypted="fake_encrypted_key",
                )

            # _categorize_error's fallback branch for an unrecognized
            # exception produces "Unexpected error: ..." - "LLM generation
            # failed" never appears anywhere in the source, this was
            # asserting on text that was never actually produced.
            assert "Unexpected error" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)


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

        # test_provider() calls validate_config(), not generate() - mock
        # validate_config() directly instead of mocking generate(), which
        # would be a no-op.
        with patch.object(
            litellm_service, "validate_config",
            return_value=(True, "Successfully validated model", None)
        ):
            result = await litellm_service.test_provider(
                provider=ProviderType.GROQ,
                model="llama-3.3-70b-versatile"
            )

            assert result["success"] is True
            assert "Successfully connected" in result["message"]

    @pytest.mark.asyncio
    async def test_test_provider_failure(self, litellm_service):
        """Test failed provider test."""
        from models import ProviderType

        # test_provider() calls self.validate_config(), not self.generate() -
        # mocking generate() here was a no-op, this test was only "passing"
        # because OPENAI's real validate_config() independently hit its own
        # "API key required" branch, not because of anything this mock did.
        with patch.object(
            litellm_service, "validate_config",
            return_value=(False, "Connection failed", None)
        ):
            result = await litellm_service.test_provider(
                provider=ProviderType.OPENAI,
                model="gpt-4"
            )

            assert result["success"] is False
            assert "Connection failed" in result["message"]
