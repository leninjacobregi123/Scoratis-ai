"""
Evaluation Tests for Agent Quality

Tests agent response quality using golden datasets:
- Tool selection accuracy
- Socratic teaching method
- Response quality scoring
- RAG relevance

Location: testing_SAI/evaluation/test_agent_evaluation.py
"""

import pytest
import sys
import os
import re
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from evaluation.evaluator import AgentEvaluator, EvaluationResult
from evaluation.golden_dataset import (
    GOLDEN_DATASET,
    GoldenTestCase,
    ResponseFormat,
    ToolExpectation,
    EvaluationCriteria,
)

# Mark all tests as evaluation tests
pytestmark = [pytest.mark.evaluation]


# =============================================================================
# Evaluator Tests
# =============================================================================

class TestAgentEvaluator:
    """Tests for the AgentEvaluator class."""

    @pytest.fixture
    def evaluator(self):
        return AgentEvaluator(min_passing_score=0.7)

    def test_evaluator_initialization(self, evaluator):
        """Test evaluator initializes correctly."""
        assert evaluator.min_passing_score == 0.7
        assert evaluator.strict_mode is False

    def test_evaluate_response_returns_result(self, evaluator):
        """Test evaluate_response returns EvaluationResult."""
        test_case = GoldenTestCase(
            id="test_001",
            query="What is AI?",
            category="definitions",
            expected_format=ResponseFormat.DEFINITION,
            expected_topics=["AI", "artificial intelligence"],
            criteria=EvaluationCriteria()
        )

        result = evaluator.evaluate_response(
            test_case,
            response="AI stands for Artificial Intelligence. It is a branch of computer science."
        )

        assert isinstance(result, EvaluationResult)
        assert result.test_case_id == "test_001"

    def test_length_evaluation(self, evaluator):
        """Test length-based evaluation."""
        test_case = GoldenTestCase(
            id="length_test",
            query="Explain something",
            category="explanations",
            expected_format=ResponseFormat.EXPLANATION,
            expected_topics=[],
            criteria=EvaluationCriteria(),
            min_length=100,
            max_length=500
        )

        # Too short
        short_result = evaluator.evaluate_response(
            test_case,
            response="Short."
        )
        assert short_result.criteria_scores.get("length", 1.0) < 1.0

        # Good length
        good_response = "A" * 200
        good_result = evaluator.evaluate_response(
            test_case,
            response=good_response
        )
        assert good_result.criteria_scores.get("length", 0.0) >= 0.8

    def test_topic_coverage_evaluation(self, evaluator):
        """Test topic coverage evaluation."""
        test_case = GoldenTestCase(
            id="topic_test",
            query="Explain machine learning",
            category="explanations",
            expected_format=ResponseFormat.EXPLANATION,
            expected_topics=["machine learning", "AI", "algorithms", "data"],
            criteria=EvaluationCriteria()
        )

        # Good coverage
        good_response = """
        Machine learning is a subset of AI that uses algorithms to learn from data.
        These algorithms can improve their performance over time without explicit programming.
        """
        good_result = evaluator.evaluate_response(test_case, response=good_response)
        assert good_result.criteria_scores.get("topic_coverage", 0.0) >= 0.5

        # Poor coverage
        poor_response = "It's a computer thing."
        poor_result = evaluator.evaluate_response(test_case, response=poor_response)
        assert poor_result.criteria_scores.get("topic_coverage", 1.0) < 0.5

    def test_format_evaluation_list(self, evaluator):
        """Test list format evaluation."""
        test_case = GoldenTestCase(
            id="format_list",
            query="List the planets",
            category="lists",
            expected_format=ResponseFormat.LIST,
            expected_topics=["planets"],
            criteria=EvaluationCriteria()
        )

        # With bullets
        bulleted = """
        The planets are:
        - Mercury
        - Venus
        - Earth
        - Mars
        """
        result = evaluator.evaluate_response(test_case, response=bulleted)
        assert result.criteria_scores.get("format", 0.0) >= 0.8

    def test_format_evaluation_comparison(self, evaluator):
        """Test comparison format evaluation."""
        test_case = GoldenTestCase(
            id="format_compare",
            query="Compare X and Y",
            category="comparisons",
            expected_format=ResponseFormat.COMPARISON,
            expected_topics=["X", "Y"],
            criteria=EvaluationCriteria()
        )

        comparison = """
        X and Y are similar in some ways, however they differ in key aspects.
        While X focuses on one thing, Y takes a different approach.
        Unlike X, Y prioritizes different outcomes.
        """
        result = evaluator.evaluate_response(test_case, response=comparison)
        assert result.criteria_scores.get("format", 0.0) >= 0.5


# =============================================================================
# Tool Selection Evaluation Tests
# =============================================================================

class TestToolSelectionEvaluation:
    """Tests for tool selection accuracy."""

    @pytest.fixture
    def evaluator(self):
        return AgentEvaluator(min_passing_score=0.7)

    def test_rag_tool_expected(self, evaluator):
        """Test that RAG tool usage is detected."""
        test_case = GoldenTestCase(
            id="rag_tool",
            query="What's in my notes?",
            category="personal_knowledge",
            expected_format=ResponseFormat.SUMMARY,
            expected_topics=["notes"],
            expected_tools=[ToolExpectation.SEARCH_KNOWLEDGE],
            criteria=EvaluationCriteria(uses_rag=True)
        )

        # With RAG used
        metadata = {
            "tools_used": ["search_knowledge_base"],
            "sources": [{"chunk_id": 1, "content": "Note content"}]
        }
        result = evaluator.evaluate_response(
            test_case,
            response="Based on your notes, here is what I found...",
            metadata=metadata
        )
        assert result.criteria_scores.get("rag_usage", 0.0) >= 0.5

        # Without RAG
        no_rag_metadata = {"tools_used": [], "sources": []}
        no_rag_result = evaluator.evaluate_response(
            test_case,
            response="I don't have that information.",
            metadata=no_rag_metadata
        )
        assert no_rag_result.criteria_scores.get("rag_usage", 1.0) < 0.5

    def test_web_search_tool_expected(self, evaluator):
        """Test that web search tool usage is detected."""
        test_case = GoldenTestCase(
            id="web_tool",
            query="Latest AI news",
            category="current_events",
            expected_format=ResponseFormat.LIST,
            expected_topics=["AI", "news"],
            expected_tools=[ToolExpectation.WEB_SEARCH],
            criteria=EvaluationCriteria()
        )

        # With web search
        metadata = {"tools_used": ["web_search"]}
        result = evaluator.evaluate_response(
            test_case,
            response="Recent AI developments include...",
            metadata=metadata
        )
        assert result.criteria_scores.get("tool_usage", 0.0) >= 0.5

    def test_no_tools_expected(self, evaluator):
        """Test when no tools should be used."""
        test_case = GoldenTestCase(
            id="no_tools",
            query="Hello!",
            category="greetings",
            expected_format=ResponseFormat.CONVERSATIONAL,
            expected_topics=[],
            expected_tools=[],  # Empty list instead of NONE
            criteria=EvaluationCriteria()
        )

        # Should pass without tools
        metadata = {"tools_used": []}
        result = evaluator.evaluate_response(
            test_case,
            response="Hello! How can I help you today?",
            metadata=metadata
        )
        # No tools expected, should pass
        assert result.passed or result.score >= 0.5


# =============================================================================
# Socratic Method Evaluation Tests
# =============================================================================

class TestSocraticMethodEvaluation:
    """Tests for Socratic teaching method quality."""

    def test_response_contains_questions(self):
        """Test detecting guiding questions in response."""
        response_with_questions = """
        That's interesting! What do you think causes this phenomenon?
        Have you considered how this relates to what we discussed earlier?
        """

        has_questions = "?" in response_with_questions
        assert has_questions

    def test_response_builds_understanding(self):
        """Test responses that build understanding."""
        response = """
        Great observation! You mentioned that force affects motion.
        Building on that idea, what happens when two objects of different
        masses experience the same force? Think about pushing a shopping cart
        versus pushing a car.
        """

        # Check for building phrases
        building_phrases = ["building on", "mentioned", "think about"]
        has_building = any(p in response.lower() for p in building_phrases)
        assert has_building

    def test_socratic_scaffolding(self):
        """Test Socratic scaffolding in response."""
        scaffolded_response = """
        Let's start with what you know. You said plants need sunlight.
        Now, what do you think happens to that sunlight inside the leaf?
        Consider the green color of leaves - what might that tell us?
        """

        # Check for scaffolding indicators
        scaffolding_indicators = ["let's start", "what do you think", "consider"]
        matches = sum(1 for i in scaffolding_indicators if i in scaffolded_response.lower())
        assert matches >= 2


# =============================================================================
# Citation Evaluation Tests
# =============================================================================

class TestCitationEvaluation:
    """Tests for citation usage evaluation."""

    @pytest.fixture
    def evaluator(self):
        return AgentEvaluator()

    def test_bracket_citations_detected(self, evaluator):
        """Test that bracket citations are detected."""
        test_case = GoldenTestCase(
            id="citation_test",
            query="Tell me about physics",
            category="explanations",
            expected_format=ResponseFormat.EXPLANATION,
            expected_topics=["physics"],
            criteria=EvaluationCriteria(uses_citations=True)
        )

        response = "According to the sources [1], physics is the study of matter [2]."
        result = evaluator.evaluate_response(test_case, response=response)

        assert result.criteria_scores.get("citations", 0.0) >= 0.5

    def test_source_references_detected(self, evaluator):
        """Test that source references are detected."""
        test_case = GoldenTestCase(
            id="source_ref_test",
            query="Explain this",
            category="explanations",
            expected_format=ResponseFormat.EXPLANATION,
            expected_topics=[],
            criteria=EvaluationCriteria(uses_citations=True)
        )

        response = "Based on the source material, the concept works as follows..."
        result = evaluator.evaluate_response(test_case, response=response)

        # Should get partial credit for "based on"
        citation_score = result.criteria_scores.get("citations", 0.0)
        assert citation_score >= 0.3


# =============================================================================
# Golden Dataset Tests
# =============================================================================

class TestGoldenDataset:
    """Tests for the golden dataset."""

    def test_dataset_not_empty(self):
        """Test that golden dataset has entries."""
        assert len(GOLDEN_DATASET) > 0

    def test_dataset_has_variety(self):
        """Test that dataset covers various categories."""
        categories = set(tc.category for tc in GOLDEN_DATASET)
        assert len(categories) >= 3  # At least 3 different categories

    def test_dataset_has_required_fields(self):
        """Test that all test cases have required fields."""
        for tc in GOLDEN_DATASET:
            assert tc.id is not None
            assert tc.query is not None
            assert tc.category is not None
            assert tc.expected_format is not None

    def test_dataset_formats_valid(self):
        """Test that all formats are valid ResponseFormat values."""
        valid_formats = set(ResponseFormat)
        for tc in GOLDEN_DATASET:
            assert tc.expected_format in valid_formats


# =============================================================================
# Full Evaluation Run Tests
# =============================================================================

class TestFullEvaluationRun:
    """Tests for running full evaluation."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent for evaluation."""
        agent = MagicMock()

        async def mock_invoke(session_id, message, **kwargs):
            return {
                "response": f"This is a detailed response about {message[:20]}. "
                           f"It covers the main topics and provides examples.",
                "sources": [],
                "tools_used": [],
                "model": "test-model"
            }

        agent.invoke = AsyncMock(side_effect=mock_invoke)
        return agent

    @pytest.mark.asyncio
    async def test_run_evaluation(self, mock_agent):
        """Test running evaluation on dataset."""
        evaluator = AgentEvaluator(min_passing_score=0.5)

        # Use subset of dataset
        subset = GOLDEN_DATASET[:3]

        summary = await evaluator.run_evaluation(
            agent=mock_agent,
            dataset=subset,
            session_id="eval-test"
        )

        assert summary.total_cases == len(subset)
        assert summary.passed_cases >= 0
        assert 0.0 <= summary.average_score <= 1.0

    @pytest.mark.asyncio
    async def test_evaluation_handles_errors(self, mock_agent):
        """Test that evaluation handles agent errors."""
        # Make agent fail for some cases
        call_count = [0]

        async def sometimes_fails(session_id, message, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                raise Exception("Agent error")
            return {
                "response": "Response text here.",
                "sources": [],
                "tools_used": []
            }

        mock_agent.invoke = AsyncMock(side_effect=sometimes_fails)
        evaluator = AgentEvaluator()

        subset = GOLDEN_DATASET[:4]
        summary = await evaluator.run_evaluation(
            agent=mock_agent,
            dataset=subset
        )

        # Should complete despite errors
        assert summary is not None
        assert summary.total_cases == len(subset)


# =============================================================================
# Report Generation Tests
# =============================================================================

class TestReportGeneration:
    """Tests for evaluation report generation."""

    def test_generate_report(self):
        """Test report generation."""
        from evaluation.evaluator import generate_report, EvaluationSummary

        summary = EvaluationSummary(
            total_cases=10,
            passed_cases=7,
            failed_cases=3,
            average_score=0.72,
            category_scores={"definitions": 0.8, "comparisons": 0.65},
            results=[]
        )

        report = generate_report(summary)

        assert isinstance(report, str)
        assert "10" in report  # Total cases
        assert "7" in report   # Passed
        assert "0.72" in report  # Average score

    def test_report_includes_failures(self):
        """Test that report includes failed cases."""
        from evaluation.evaluator import generate_report, EvaluationSummary, EvaluationResult

        failed_result = EvaluationResult(
            test_case_id="fail_001",
            query="Test query",
            response="Bad response",
            passed=False,
            score=0.3,
            criteria_scores={},
            issues=["Too short", "Missing topics"]
        )

        summary = EvaluationSummary(
            total_cases=1,
            passed_cases=0,
            failed_cases=1,
            average_score=0.3,
            category_scores={},
            results=[failed_result]
        )

        report = generate_report(summary)

        assert "fail_001" in report
        assert "Too short" in report or "Missing" in report
