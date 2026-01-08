"""
Unit Tests for Response Verifier

Tests the verification system that checks response quality:
- QuickVerifier: Fast heuristic checks
- ResponseVerifier: Full LLM-based verification
- Verification criteria and scoring

Location: testing_SAI/unit/test_verifier.py
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from services.agent.verifier import (
    QuickVerifier,
    ResponseVerifier,
    VerificationConfig,
    VerificationCriterion,
    DEFAULT_VERIFICATION_CONFIG,
    EDUCATIONAL_VERIFICATION_CONFIG,
)
from services.agent.state import VerificationResult

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# QuickVerifier Tests
# =============================================================================

class TestQuickVerifierInit:
    """Tests for QuickVerifier initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        verifier = QuickVerifier()
        assert verifier.min_length == 50
        assert verifier.max_length == 5000

    def test_custom_lengths(self):
        """Test custom length parameters."""
        verifier = QuickVerifier(min_length=100, max_length=3000)
        assert verifier.min_length == 100
        assert verifier.max_length == 3000


class TestQuickVerifierLengthChecks:
    """Tests for length-based verification."""

    @pytest.fixture
    def verifier(self):
        return QuickVerifier(min_length=50, max_length=500)

    def test_empty_response_fails(self, verifier):
        """Empty responses should fail verification."""
        result = verifier.quick_check("What is AI?", "")

        assert result.result == VerificationResult.NEEDS_REVISION.value
        assert result.confidence_score == 0.0
        assert any("empty" in issue.lower() for issue in result.issues)

    def test_whitespace_only_fails(self, verifier):
        """Whitespace-only responses should fail."""
        result = verifier.quick_check("What is AI?", "   \n\t  ")

        assert result.confidence_score == 0.0  # Empty after strip

    def test_too_short_response_penalized(self, verifier):
        """Short responses should be penalized."""
        short_response = "AI is cool."  # 11 characters, < min_length of 50

        result = verifier.quick_check("What is AI?", short_response)

        # Score should be 0.8 (1.0 - 0.2 for being short)
        assert result.confidence_score < 1.0
        assert any("short" in issue.lower() for issue in result.issues)

    def test_too_long_response_penalized(self, verifier):
        """Very long responses should be penalized."""
        long_response = "A" * 600  # Exceeds max_length of 500

        result = verifier.quick_check("Question?", long_response)

        assert result.confidence_score < 1.0
        assert any("long" in issue.lower() for issue in result.issues)

    def test_optimal_length_approved(self, verifier):
        """Optimal length responses should score well."""
        good_response = """
        Artificial Intelligence (AI) is a field of computer science focused on
        creating systems that can perform tasks typically requiring human
        intelligence. This includes learning, reasoning, and problem-solving.
        """

        result = verifier.quick_check("What is AI?", good_response)

        assert result.confidence_score >= 0.8
        assert result.result == VerificationResult.APPROVED.value


class TestQuickVerifierContentChecks:
    """Tests for content-based verification."""

    @pytest.fixture
    def verifier(self):
        return QuickVerifier(min_length=20, max_length=2000)

    def test_socratic_question_not_penalized(self, verifier):
        """Socratic responses (questions) should not be penalized."""
        # Response is a guiding question (Socratic method)
        response = "What do you think happens when force is applied to an object at rest?"

        result = verifier.quick_check("Explain Newton's laws", response)

        # Should not be heavily penalized for being a question
        assert result.confidence_score >= 0.5

    def test_citations_detected(self, verifier):
        """Responses with citations should be recognized."""
        response_with_citations = """
        According to the sources, machine learning [1] is a subset of AI [2].
        It involves training algorithms on data to make predictions.
        """

        result = verifier.quick_check(
            "What is ML?",
            response_with_citations,
            sources=[{"chunk_id": 1}, {"chunk_id": 2}]
        )

        # Should not penalize for missing citations since they're present
        assert result.confidence_score >= 0.8


class TestQuickVerifierResults:
    """Tests for verification result structure."""

    @pytest.fixture
    def verifier(self):
        return QuickVerifier()

    def test_result_has_required_fields(self, verifier):
        """Result should have all required fields."""
        result = verifier.quick_check("Question", "Answer with enough content to pass the minimum length check")

        assert hasattr(result, 'verified')
        assert hasattr(result, 'result')
        assert hasattr(result, 'feedback')
        assert hasattr(result, 'issues')
        assert hasattr(result, 'suggestions')
        assert hasattr(result, 'confidence_score')

    def test_result_types_correct(self, verifier):
        """Result field types should be correct."""
        result = verifier.quick_check("Q", "A" * 100)

        assert isinstance(result.verified, bool)
        assert isinstance(result.result, str)
        assert isinstance(result.issues, list)
        assert isinstance(result.suggestions, list)
        assert isinstance(result.confidence_score, (int, float))

    def test_approved_result(self, verifier):
        """Test approved result structure."""
        good_response = """
        Machine learning is a branch of artificial intelligence that enables
        computers to learn from data and improve their performance over time
        without being explicitly programmed for every scenario.
        """

        result = verifier.quick_check("What is machine learning?", good_response)

        # Good response should be approved
        assert result.confidence_score >= 0.8
        assert result.result == VerificationResult.APPROVED.value

    def test_score_thresholds(self, verifier):
        """Test score thresholds for different verdicts."""
        # Score >= 0.8 = APPROVED
        # Score >= 0.6 = NEEDS_REVISION
        # Score < 0.6 = NEEDS_MORE_INFO

        # Short response (score = 0.8) is still approved
        short_but_ok = "A" * 40  # Less than 50 but not empty
        short_result = verifier.quick_check("Q?", short_but_ok)

        # Empty response should need revision
        empty_result = verifier.quick_check("Q?", "")
        assert empty_result.result == VerificationResult.NEEDS_REVISION.value


# =============================================================================
# VerificationConfig Tests
# =============================================================================

class TestVerificationConfig:
    """Tests for VerificationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = DEFAULT_VERIFICATION_CONFIG

        assert config.min_passing_score == 0.7
        assert config.max_revision_attempts == 2
        assert VerificationCriterion.FACTUAL_ACCURACY in config.criteria
        assert VerificationCriterion.RELEVANCE in config.criteria

    def test_educational_config(self):
        """Test educational configuration."""
        config = EDUCATIONAL_VERIFICATION_CONFIG

        assert config.min_passing_score == 0.75
        assert VerificationCriterion.EDUCATIONAL_QUALITY in config.criteria

    def test_custom_config(self):
        """Test custom configuration."""
        config = VerificationConfig(
            criteria=[VerificationCriterion.FACTUAL_ACCURACY],
            min_passing_score=0.9,
            require_all_criteria=True,
            max_revision_attempts=3
        )

        assert config.min_passing_score == 0.9
        assert config.require_all_criteria is True
        assert config.max_revision_attempts == 3
        assert len(config.criteria) == 1


# =============================================================================
# VerificationCriterion Tests
# =============================================================================

class TestVerificationCriterion:
    """Tests for VerificationCriterion enum."""

    def test_all_criteria_exist(self):
        """Test all criteria exist."""
        criteria = [
            VerificationCriterion.FACTUAL_ACCURACY,
            VerificationCriterion.COMPLETENESS,
            VerificationCriterion.RELEVANCE,
            VerificationCriterion.EDUCATIONAL_QUALITY,
            VerificationCriterion.CITATION_ACCURACY,
            VerificationCriterion.TONE_AND_CLARITY,
        ]

        for criterion in criteria:
            assert criterion is not None
            assert isinstance(criterion.value, str)


# =============================================================================
# ResponseVerifier Tests (with mocked LLM)
# =============================================================================

class TestResponseVerifierInit:
    """Tests for ResponseVerifier initialization."""

    def test_initialization_with_llm(self, mock_llm_service):
        """Test initialization with LLM service."""
        verifier = ResponseVerifier(mock_llm_service)

        assert verifier.llm_service == mock_llm_service
        assert verifier.config is not None

    def test_initialization_with_custom_config(self, mock_llm_service):
        """Test initialization with custom config."""
        config = VerificationConfig(
            criteria=[VerificationCriterion.FACTUAL_ACCURACY],
            min_passing_score=0.9
        )
        verifier = ResponseVerifier(mock_llm_service, config=config)

        assert verifier.config.min_passing_score == 0.9


class TestResponseVerifierVerify:
    """Tests for ResponseVerifier.verify method."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM that returns verification JSON."""
        llm = MagicMock()
        llm.generate = AsyncMock(return_value="""
        {
            "overall_verdict": "approved",
            "overall_score": 0.85,
            "criteria_results": {
                "factual_accuracy": {"score": 0.9, "issues": [], "suggestions": []},
                "completeness": {"score": 0.8, "issues": [], "suggestions": []},
                "relevance": {"score": 0.85, "issues": [], "suggestions": []}
            },
            "summary_feedback": "Response is accurate and relevant.",
            "revision_instructions": ""
        }
        """)
        return llm

    @pytest.mark.asyncio
    async def test_verify_calls_llm(self, mock_llm):
        """Test that verify calls LLM."""
        verifier = ResponseVerifier(mock_llm)

        result = await verifier.verify(
            user_query="What is photosynthesis?",
            response="Photosynthesis is the process by which plants convert sunlight..."
        )

        mock_llm.generate.assert_called_once()
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_verify_parses_approved(self, mock_llm):
        """Test parsing approved response."""
        verifier = ResponseVerifier(mock_llm)

        result = await verifier.verify("Q", "A" * 100)

        assert result.result == "approved"
        assert result.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_verify_with_sources(self, mock_llm):
        """Test verification with sources."""
        verifier = ResponseVerifier(mock_llm)

        sources = [
            {"chunk_id": 1, "content": "Source 1 content"},
            {"chunk_id": 2, "content": "Source 2 content"}
        ]

        result = await verifier.verify(
            user_query="What is AI?",
            response="AI is artificial intelligence [1]...",
            sources=sources
        )

        assert result.verified is True

    @pytest.mark.asyncio
    async def test_verify_with_context(self, mock_llm):
        """Test verification with context."""
        verifier = ResponseVerifier(mock_llm)

        context = {
            "subject": "physics",
            "learning_state": {"state": "engaged"}
        }

        result = await verifier.verify(
            user_query="Explain gravity",
            response="Gravity is the force of attraction...",
            context=context
        )

        assert result.verified is True

    @pytest.mark.asyncio
    async def test_verify_handles_llm_error(self, mock_llm):
        """Test graceful handling of LLM errors."""
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM Error"))
        verifier = ResponseVerifier(mock_llm)

        result = await verifier.verify("Q", "A" * 100)

        # Should not crash, should return default approved
        assert result.verified is True
        assert result.result == VerificationResult.APPROVED.value

    @pytest.mark.asyncio
    async def test_verify_handles_invalid_json(self):
        """Test handling of invalid JSON response."""
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="This is not valid JSON")

        verifier = ResponseVerifier(mock_llm)
        result = await verifier.verify("Q", "A" * 100)

        # Should handle gracefully
        assert result.verified is True


class TestResponseVerifierNeedsRevision:
    """Tests for needs_revision scenarios."""

    @pytest.fixture
    def mock_llm_revision(self):
        """Mock LLM that returns needs_revision."""
        llm = MagicMock()
        llm.generate = AsyncMock(return_value="""
        {
            "overall_verdict": "needs_revision",
            "overall_score": 0.55,
            "criteria_results": {
                "factual_accuracy": {"score": 0.6, "issues": ["Inaccurate claim about X"], "suggestions": ["Verify source"]},
                "completeness": {"score": 0.5, "issues": ["Missing key concept"], "suggestions": ["Add more detail"]}
            },
            "summary_feedback": "Response needs improvement.",
            "revision_instructions": "Please add more accurate information."
        }
        """)
        return llm

    @pytest.mark.asyncio
    async def test_verify_needs_revision(self, mock_llm_revision):
        """Test parsing needs_revision response."""
        verifier = ResponseVerifier(mock_llm_revision)

        result = await verifier.verify("Q", "Incomplete answer")

        assert result.result == "needs_revision"
        assert result.confidence_score < 0.7
        assert len(result.issues) > 0
        assert len(result.suggestions) > 0


class TestResponseVerifierRefinement:
    """Tests for verify_with_refinement method."""

    @pytest.fixture
    def mock_llm_improving(self):
        """Mock LLM that initially rejects, then approves."""
        llm = MagicMock()
        call_count = [0]

        async def generate_response(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return """
                {
                    "overall_verdict": "needs_revision",
                    "overall_score": 0.5,
                    "criteria_results": {},
                    "summary_feedback": "Needs more detail",
                    "revision_instructions": "Add examples"
                }
                """
            else:
                return """
                {
                    "overall_verdict": "approved",
                    "overall_score": 0.85,
                    "criteria_results": {},
                    "summary_feedback": "Good response",
                    "revision_instructions": ""
                }
                """

        llm.generate = AsyncMock(side_effect=generate_response)
        return llm

    @pytest.mark.asyncio
    async def test_refinement_loop(self, mock_llm_improving):
        """Test the refinement loop."""
        verifier = ResponseVerifier(mock_llm_improving)

        # Check if verify_with_refinement exists
        if hasattr(verifier, 'verify_with_refinement'):
            async def refine_callback(response, feedback):
                return response + "\n\nAdditional detail based on feedback."

            result = await verifier.verify_with_refinement(
                user_query="Explain AI",
                initial_response="AI is artificial intelligence.",
                refine_callback=refine_callback
            )

            assert result["verified"] is True
        else:
            # If method doesn't exist, just verify basic functionality works
            result = await verifier.verify("Q", "A" * 100)
            assert result.verified is True


# =============================================================================
# Integration-style Tests
# =============================================================================

class TestVerifierIntegration:
    """Integration-style tests for verifier components."""

    def test_quick_verifier_consistency(self):
        """Test QuickVerifier produces consistent results."""
        verifier = QuickVerifier()
        response = "A" * 100

        result1 = verifier.quick_check("Q", response)
        result2 = verifier.quick_check("Q", response)

        assert result1.confidence_score == result2.confidence_score
        assert result1.result == result2.result

    def test_different_responses_different_scores(self):
        """Different quality responses should get different scores."""
        verifier = QuickVerifier(min_length=30)

        poor = "Bad."  # Very short
        good = "This is a comprehensive and detailed response that covers the topic well with multiple points and examples to illustrate the concept."

        poor_result = verifier.quick_check("Q", poor)
        good_result = verifier.quick_check("Q", good)

        # Good response should score higher than poor response
        assert good_result.confidence_score > poor_result.confidence_score

    def test_empty_vs_short_vs_good(self):
        """Test score progression from empty to good responses."""
        verifier = QuickVerifier(min_length=50)

        empty_result = verifier.quick_check("Q", "")
        short_result = verifier.quick_check("Q", "Short response")
        good_result = verifier.quick_check("Q", "A" * 100)

        assert empty_result.confidence_score < short_result.confidence_score
        assert short_result.confidence_score <= good_result.confidence_score
