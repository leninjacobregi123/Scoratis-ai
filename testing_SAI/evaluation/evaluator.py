"""
Agent Response Evaluator

Evaluates agent responses against golden dataset criteria.
Provides automated quality scoring for CI/CD pipelines.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .golden_dataset import (
    GoldenTestCase,
    EvaluationCriteria,
    ResponseFormat,
    ToolExpectation,
    GOLDEN_DATASET,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single response."""
    test_case_id: str
    query: str
    response: str
    passed: bool
    score: float  # 0.0 to 1.0
    criteria_scores: Dict[str, float]
    issues: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class EvaluationSummary:
    """Summary of evaluation run."""
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    category_scores: Dict[str, float]
    results: List[EvaluationResult]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentEvaluator:
    """
    Evaluates agent responses against golden dataset criteria.

    Usage:
        evaluator = AgentEvaluator()
        result = evaluator.evaluate_response(test_case, response, metadata)
        summary = evaluator.run_evaluation(agent, dataset)
    """

    def __init__(
        self,
        min_passing_score: float = 0.7,
        strict_mode: bool = False
    ):
        """
        Initialize evaluator.

        Args:
            min_passing_score: Minimum score to pass (0.0 to 1.0)
            strict_mode: If True, all criteria must pass
        """
        self.min_passing_score = min_passing_score
        self.strict_mode = strict_mode

    def evaluate_response(
        self,
        test_case: GoldenTestCase,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate a single response against test case criteria.

        Args:
            test_case: The golden test case
            response: Agent's response text
            metadata: Optional metadata (tools_used, sources, etc.)

        Returns:
            EvaluationResult with scores and issues
        """
        metadata = metadata or {}
        issues = []
        criteria_scores = {}

        # Check length requirements
        length_score = self._evaluate_length(
            response, test_case.min_length, test_case.max_length
        )
        criteria_scores["length"] = length_score
        if length_score < 1.0:
            if len(response) < test_case.min_length:
                issues.append(f"Response too short ({len(response)} < {test_case.min_length})")
            else:
                issues.append(f"Response too long ({len(response)} > {test_case.max_length})")

        # Check topic coverage
        topic_score = self._evaluate_topics(response, test_case.expected_topics)
        criteria_scores["topic_coverage"] = topic_score
        if topic_score < 0.5:
            missing = self._get_missing_topics(response, test_case.expected_topics)
            issues.append(f"Missing key topics: {', '.join(missing[:3])}")

        # Check format
        format_score = self._evaluate_format(response, test_case.expected_format)
        criteria_scores["format"] = format_score
        if format_score < 0.7:
            issues.append(f"Response format doesn't match expected: {test_case.expected_format.value}")

        # Check criteria-specific requirements
        criteria = test_case.criteria

        if criteria.uses_rag:
            rag_score = self._evaluate_rag_usage(response, metadata)
            criteria_scores["rag_usage"] = rag_score
            if rag_score < 0.5:
                issues.append("Expected RAG usage but not detected")

        if criteria.uses_citations:
            citation_score = self._evaluate_citations(response)
            criteria_scores["citations"] = citation_score
            if citation_score < 0.5:
                issues.append("Expected citations but none found")

        if criteria.examples_provided:
            example_score = self._evaluate_examples(response)
            criteria_scores["examples"] = example_score
            if example_score < 0.5:
                issues.append("Expected examples but none found")

        if criteria.comparison_clarity:
            comparison_score = self._evaluate_comparison(response)
            criteria_scores["comparison"] = comparison_score
            if comparison_score < 0.5:
                issues.append("Comparison lacks clarity")

        if criteria.technical_depth:
            depth_score = self._evaluate_technical_depth(response)
            criteria_scores["technical_depth"] = depth_score
            if depth_score < 0.5:
                issues.append("Lacks technical depth")

        # Check tool usage
        if test_case.expected_tools:
            tool_score = self._evaluate_tool_usage(
                test_case.expected_tools,
                metadata.get("tools_used", [])
            )
            criteria_scores["tool_usage"] = tool_score
            if tool_score < 0.5:
                issues.append("Expected tools were not used")

        # Calculate overall score
        if criteria_scores:
            overall_score = sum(criteria_scores.values()) / len(criteria_scores)
        else:
            overall_score = 1.0 if not issues else 0.5

        # Determine pass/fail
        if self.strict_mode:
            passed = all(s >= self.min_passing_score for s in criteria_scores.values())
        else:
            passed = overall_score >= self.min_passing_score

        return EvaluationResult(
            test_case_id=test_case.id,
            query=test_case.query,
            response=response[:500] + "..." if len(response) > 500 else response,
            passed=passed,
            score=overall_score,
            criteria_scores=criteria_scores,
            issues=issues,
            metadata=metadata
        )

    def _evaluate_length(
        self, response: str, min_len: int, max_len: int
    ) -> float:
        """Evaluate response length."""
        length = len(response)
        if length < min_len:
            return max(0.0, length / min_len)
        if length > max_len:
            return max(0.0, 1.0 - (length - max_len) / max_len)
        return 1.0

    def _evaluate_topics(
        self, response: str, expected_topics: List[str]
    ) -> float:
        """Evaluate topic coverage."""
        if not expected_topics:
            return 1.0

        response_lower = response.lower()
        covered = sum(1 for topic in expected_topics if topic.lower() in response_lower)
        return covered / len(expected_topics)

    def _get_missing_topics(
        self, response: str, expected_topics: List[str]
    ) -> List[str]:
        """Get list of missing topics."""
        response_lower = response.lower()
        return [t for t in expected_topics if t.lower() not in response_lower]

    def _evaluate_format(
        self, response: str, expected_format: ResponseFormat
    ) -> float:
        """Evaluate if response matches expected format."""
        if expected_format == ResponseFormat.LIST:
            # Check for bullet points or numbered list
            has_bullets = bool(re.search(r'[-*•]\s', response))
            has_numbers = bool(re.search(r'\d+[.)]\s', response))
            return 1.0 if (has_bullets or has_numbers) else 0.5

        elif expected_format == ResponseFormat.COMPARISON:
            # Check for comparison words
            comparison_words = ["however", "whereas", "while", "unlike", "similar", "different"]
            has_comparison = any(w in response.lower() for w in comparison_words)
            return 1.0 if has_comparison else 0.5

        elif expected_format == ResponseFormat.STEP_BY_STEP:
            # Check for step indicators
            has_steps = bool(re.search(r'(step\s*\d|first|second|then|next|finally)', response.lower()))
            return 1.0 if has_steps else 0.5

        elif expected_format == ResponseFormat.DEFINITION:
            # Check for definitional structure
            has_is_are = bool(re.search(r'\b(is|are|refers to|defined as)\b', response.lower()))
            return 1.0 if has_is_are else 0.7

        return 0.8  # Default for other formats

    def _evaluate_rag_usage(
        self, response: str, metadata: Dict[str, Any]
    ) -> float:
        """Evaluate if RAG was properly used."""
        sources = metadata.get("sources", [])
        tools_used = metadata.get("tools_used", [])

        if sources:
            return 1.0
        if any("search" in str(t).lower() for t in tools_used):
            return 0.7
        return 0.0

    def _evaluate_citations(self, response: str) -> float:
        """Evaluate citation usage."""
        # Check for citation patterns like [1], [citation:...], etc.
        has_brackets = bool(re.search(r'\[\d+\]', response))
        has_citation_tags = bool(re.search(r'\[citation:', response))
        has_source_refs = bool(re.search(r'(according to|based on|from|source)', response.lower()))

        if has_brackets or has_citation_tags:
            return 1.0
        if has_source_refs:
            return 0.5
        return 0.0

    def _evaluate_examples(self, response: str) -> float:
        """Evaluate if examples are provided."""
        example_indicators = [
            "for example", "for instance", "such as", "e.g.",
            "like", "including", "consider"
        ]
        has_examples = any(ind in response.lower() for ind in example_indicators)
        return 1.0 if has_examples else 0.3

    def _evaluate_comparison(self, response: str) -> float:
        """Evaluate comparison clarity."""
        comparison_patterns = [
            r'\b(both|neither|while|whereas|however|but|unlike|similar|different)\b',
            r'\b(on the other hand|in contrast|compared to)\b',
        ]
        matches = sum(1 for p in comparison_patterns if re.search(p, response.lower()))
        return min(1.0, matches * 0.5)

    def _evaluate_technical_depth(self, response: str) -> float:
        """Evaluate technical depth of response."""
        # Count technical indicators
        technical_patterns = [
            r'\b[A-Z][a-z]+[A-Z]\w*\b',  # CamelCase terms
            r'\b\w+_\w+\b',  # snake_case terms
            r'\b\d+(\.\d+)?\s*(ms|kb|mb|gb|hz)\b',  # measurements
            r'`[^`]+`',  # code snippets
        ]
        matches = sum(1 for p in technical_patterns if re.search(p, response, re.I))

        # Also check for technical vocabulary
        technical_words = ["algorithm", "function", "parameter", "variable", "process", "method"]
        word_matches = sum(1 for w in technical_words if w in response.lower())

        return min(1.0, (matches + word_matches) * 0.15)

    def _evaluate_tool_usage(
        self,
        expected: List[ToolExpectation],
        actual: List[Any]
    ) -> float:
        """Evaluate if expected tools were used."""
        if not expected:
            return 1.0

        actual_names = [str(t).lower() for t in actual]

        matched = 0
        for exp in expected:
            if exp == ToolExpectation.NONE:
                continue
            if any(exp.value.lower() in name for name in actual_names):
                matched += 1

        return matched / len([e for e in expected if e != ToolExpectation.NONE]) if expected else 1.0

    async def run_evaluation(
        self,
        agent: Any,
        dataset: List[GoldenTestCase] = None,
        session_id: str = "eval-session"
    ) -> EvaluationSummary:
        """
        Run evaluation on entire dataset.

        Args:
            agent: The agent to evaluate
            dataset: Test cases (defaults to GOLDEN_DATASET)
            session_id: Session ID for agent calls

        Returns:
            EvaluationSummary with all results
        """
        import time

        dataset = dataset or GOLDEN_DATASET
        results = []
        category_scores: Dict[str, List[float]] = {}

        for test_case in dataset:
            # Skip edge cases with empty queries
            if not test_case.query.strip():
                continue

            try:
                start = time.time()
                response_data = await agent.invoke(
                    session_id=session_id,
                    message=test_case.query
                )
                duration = (time.time() - start) * 1000

                response = response_data.get("response", "")
                metadata = {
                    "sources": response_data.get("sources", []),
                    "tools_used": response_data.get("tools_used", []),
                    "model": response_data.get("model")
                }

                result = self.evaluate_response(test_case, response, metadata)
                result.duration_ms = duration

            except Exception as e:
                logger.error(f"Evaluation error for {test_case.id}: {e}")
                result = EvaluationResult(
                    test_case_id=test_case.id,
                    query=test_case.query,
                    response="",
                    passed=False,
                    score=0.0,
                    criteria_scores={},
                    issues=[f"Agent error: {str(e)}"]
                )

            results.append(result)

            # Track category scores
            if test_case.category not in category_scores:
                category_scores[test_case.category] = []
            category_scores[test_case.category].append(result.score)

        # Calculate summary
        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        cat_avg = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }

        return EvaluationSummary(
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=len(results) - passed,
            average_score=avg_score,
            category_scores=cat_avg,
            results=results
        )


def generate_report(summary: EvaluationSummary) -> str:
    """Generate a human-readable evaluation report."""
    lines = [
        "=" * 60,
        "AGENT EVALUATION REPORT",
        "=" * 60,
        f"Timestamp: {summary.timestamp}",
        f"Total Test Cases: {summary.total_cases}",
        f"Passed: {summary.passed_cases} ({summary.passed_cases/summary.total_cases*100:.1f}%)",
        f"Failed: {summary.failed_cases}",
        f"Average Score: {summary.average_score:.2f}",
        "",
        "Category Scores:",
        "-" * 30,
    ]

    for cat, score in sorted(summary.category_scores.items()):
        lines.append(f"  {cat}: {score:.2f}")

    lines.extend([
        "",
        "Failed Cases:",
        "-" * 30,
    ])

    for result in summary.results:
        if not result.passed:
            lines.append(f"  [{result.test_case_id}] Score: {result.score:.2f}")
            lines.append(f"    Query: {result.query[:50]}...")
            for issue in result.issues[:3]:
                lines.append(f"    - {issue}")
            lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
