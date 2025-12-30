"""
Agent Evaluation Tests

Runs the agent against the golden dataset and evaluates performance.
These tests are marked as 'evaluation' and require LLM access.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from .golden_dataset import (
    GOLDEN_DATASET,
    GoldenTestCase,
    ResponseFormat,
    get_test_cases_by_category,
    get_test_cases_by_difficulty,
)
from .evaluator import AgentEvaluator, EvaluationResult, generate_report

# Mark all tests as evaluation tests (require LLM)
pytestmark = [pytest.mark.evaluation, pytest.mark.slow]


class TestEvaluatorLogic:
    """Tests for the evaluator logic itself (no LLM required)."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return AgentEvaluator(min_passing_score=0.7)

    @pytest.fixture
    def sample_test_case(self):
        """Sample test case for unit testing evaluator."""
        return GoldenTestCase(
            id="test_001",
            query="What is machine learning?",
            category="definitions",
            expected_format=ResponseFormat.DEFINITION,
            expected_topics=["machine learning", "AI"],
            criteria=EvaluationCriteria(
                factual_accuracy=True,
                relevance=True
            ),
            min_length=50
        )

    def test_evaluate_good_response(self, evaluator):
        """Test evaluation of a good response."""
        test_case = GoldenTestCase(
            id="test_001",
            query="What is machine learning?",
            category="definitions",
            expected_format=ResponseFormat.DEFINITION,
            expected_topics=["machine learning", "AI", "algorithms"],
            criteria=EvaluationCriteria(),
            min_length=50
        )

        response = """
        Machine learning is a subset of artificial intelligence (AI) that enables
        systems to learn and improve from experience. It uses algorithms to analyze
        data and make predictions without being explicitly programmed.
        """

        result = evaluator.evaluate_response(test_case, response)

        assert result.score > 0.5
        assert result.test_case_id == "test_001"

    def test_evaluate_short_response(self, evaluator):
        """Test evaluation flags short responses."""
        test_case = GoldenTestCase(
            id="test_002",
            query="Explain neural networks",
            category="technical",
            expected_format=ResponseFormat.EXPLANATION,
            expected_topics=["neural network"],
            criteria=EvaluationCriteria(),
            min_length=100
        )

        response = "Neural networks are AI models."

        result = evaluator.evaluate_response(test_case, response)

        assert "too short" in str(result.issues).lower()
        assert result.criteria_scores["length"] < 1.0

    def test_evaluate_missing_topics(self, evaluator):
        """Test evaluation detects missing topics."""
        test_case = GoldenTestCase(
            id="test_003",
            query="Compare supervised and unsupervised learning",
            category="comparisons",
            expected_format=ResponseFormat.COMPARISON,
            expected_topics=["supervised", "unsupervised", "labeled data"],
            criteria=EvaluationCriteria(),
            min_length=50
        )

        response = """
        There are different types of machine learning approaches.
        Some use data to train models.
        """

        result = evaluator.evaluate_response(test_case, response)

        assert result.criteria_scores["topic_coverage"] < 1.0

    def test_evaluate_list_format(self, evaluator):
        """Test evaluation of list format."""
        test_case = GoldenTestCase(
            id="test_004",
            query="List NLP applications",
            category="applications",
            expected_format=ResponseFormat.LIST,
            expected_topics=["NLP"],
            criteria=EvaluationCriteria(),
            min_length=50
        )

        good_response = """
        NLP applications include:
        - Chatbots and virtual assistants
        - Machine translation
        - Sentiment analysis
        - Text summarization
        """

        bad_response = "NLP is used for many things in technology."

        good_result = evaluator.evaluate_response(test_case, good_response)
        bad_result = evaluator.evaluate_response(test_case, bad_response)

        assert good_result.criteria_scores["format"] > bad_result.criteria_scores["format"]

    def test_evaluate_comparison_format(self, evaluator):
        """Test evaluation of comparison format."""
        test_case = GoldenTestCase(
            id="test_005",
            query="Compare Python and JavaScript",
            category="comparisons",
            expected_format=ResponseFormat.COMPARISON,
            expected_topics=["Python", "JavaScript"],
            criteria=EvaluationCriteria(comparison_clarity=True),
            min_length=50
        )

        response = """
        Python and JavaScript are both programming languages. However,
        Python is often used for data science, whereas JavaScript is
        primarily used for web development. While Python uses indentation,
        JavaScript uses curly braces for code blocks.
        """

        result = evaluator.evaluate_response(test_case, response)

        assert result.criteria_scores["format"] >= 0.5
        assert result.criteria_scores["comparison"] >= 0.5

    def test_evaluate_citations(self, evaluator):
        """Test citation detection."""
        test_case = GoldenTestCase(
            id="test_006",
            query="What are my notes about?",
            category="personal",
            expected_format=ResponseFormat.SUMMARY,
            expected_topics=[],
            criteria=EvaluationCriteria(uses_citations=True),
            min_length=20
        )

        with_citations = "Based on your notes [1], you studied machine learning."
        without_citations = "You studied machine learning."

        result_with = evaluator.evaluate_response(test_case, with_citations)
        result_without = evaluator.evaluate_response(test_case, without_citations)

        assert result_with.criteria_scores["citations"] > result_without.criteria_scores["citations"]


class TestGoldenDataset:
    """Tests for the golden dataset structure."""

    def test_dataset_not_empty(self):
        """Test that golden dataset has test cases."""
        assert len(GOLDEN_DATASET) > 0

    def test_all_cases_have_required_fields(self):
        """Test that all cases have required fields."""
        for case in GOLDEN_DATASET:
            assert case.id
            assert case.category
            assert case.expected_format

    def test_get_by_category(self):
        """Test filtering by category."""
        definitions = get_test_cases_by_category("definitions")
        assert len(definitions) > 0
        assert all(c.category == "definitions" for c in definitions)

    def test_get_by_difficulty(self):
        """Test filtering by difficulty."""
        easy = get_test_cases_by_difficulty("easy")
        hard = get_test_cases_by_difficulty("hard")

        assert len(easy) > 0
        assert len(hard) > 0


class TestReportGeneration:
    """Tests for report generation."""

    def test_generate_report(self):
        """Test report generation."""
        from .evaluator import EvaluationSummary

        summary = EvaluationSummary(
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
            average_score=0.85,
            category_scores={"definitions": 0.9, "comparisons": 0.8},
            results=[
                EvaluationResult(
                    test_case_id="test_001",
                    query="Test query",
                    response="Test response",
                    passed=False,
                    score=0.5,
                    criteria_scores={},
                    issues=["Test issue"]
                )
            ]
        )

        report = generate_report(summary)

        assert "EVALUATION REPORT" in report
        assert "Passed: 8" in report
        assert "Failed: 2" in report
        assert "test_001" in report


# =============================================================================
# Live Agent Evaluation Tests (require LLM)
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.evaluation
class TestLiveAgentEvaluation:
    """
    Live evaluation tests against the actual agent.
    These tests require LLM access and are marked as 'evaluation'.

    Run with: pytest -m evaluation
    Skip with: pytest -m "not evaluation"
    """

    @pytest.fixture
    def mock_agent(self, mock_llm_service, mock_rag_service):
        """Create a mock agent for testing."""
        agent = MagicMock()

        async def mock_invoke(session_id, message, **kwargs):
            # Generate a response based on the query
            response = f"This is a test response about {message[:30]}. "
            response += "Machine learning is a type of AI. "
            response += "For example, neural networks can learn patterns."

            return {
                "response": response,
                "sources": [],
                "tools_used": [],
                "model": "test-model"
            }

        agent.invoke = mock_invoke
        return agent

    async def test_basic_evaluation(self, mock_agent):
        """Test basic evaluation flow."""
        evaluator = AgentEvaluator(min_passing_score=0.3)

        # Just test one case
        test_case = GOLDEN_DATASET[0]

        response_data = await mock_agent.invoke(
            session_id="test",
            message=test_case.query
        )

        result = evaluator.evaluate_response(
            test_case,
            response_data["response"],
            {"sources": response_data["sources"]}
        )

        assert isinstance(result, EvaluationResult)
        assert result.test_case_id == test_case.id

    async def test_evaluation_summary(self, mock_agent):
        """Test full evaluation run."""
        evaluator = AgentEvaluator(min_passing_score=0.3)

        # Run on subset of dataset
        subset = [tc for tc in GOLDEN_DATASET if tc.query.strip()][:3]

        summary = await evaluator.run_evaluation(
            agent=mock_agent,
            dataset=subset,
            session_id="eval-test"
        )

        assert summary.total_cases == len(subset)
        assert 0.0 <= summary.average_score <= 1.0

        # Generate report to make sure it works
        report = generate_report(summary)
        assert "EVALUATION REPORT" in report


# Import for fixture usage
from .evaluator import EvaluationCriteria
