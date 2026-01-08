"""
Unit Tests for Agent State Management

Tests the state classes used in the agentic workflow:
- AgentState: Main state container
- Scratchpad: Reasoning persistence
- StopCondition: Loop termination logic
- SearchTrail: Transparency tracking

Location: testing_SAI/unit/test_agent_state.py
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from services.agent.state import (
    Scratchpad,
    StopCondition,
    SearchTrail,
    SearchAttempt,
    AgentPhase,
    VerificationResult,
    VerificationState,
    SubAgentResult,
    SubAgentType,
)

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# Scratchpad Tests
# =============================================================================

class TestScratchpad:
    """Tests for Scratchpad reasoning persistence."""

    def test_scratchpad_initializes_empty(self):
        """Scratchpad should initialize with empty lists."""
        scratchpad = Scratchpad()

        assert scratchpad.thoughts == []
        assert scratchpad.observations == []
        assert scratchpad.plan == []
        assert scratchpad.current_goal is None
        assert scratchpad.iteration == 0
        assert scratchpad.confidence == 0.0

    def test_add_thought(self):
        """Test adding thoughts to scratchpad."""
        scratchpad = Scratchpad()

        scratchpad.add_thought("First thought about the query")
        scratchpad.add_thought("Second thought after research")

        assert len(scratchpad.thoughts) == 2
        # Note: add_thought prepends iteration number
        assert "[0] First thought about the query" in scratchpad.thoughts[0]
        assert "[0] Second thought after research" in scratchpad.thoughts[1]

    def test_add_observation(self):
        """Test adding observations from tool results."""
        scratchpad = Scratchpad()

        scratchpad.add_observation("Found 3 relevant documents")
        scratchpad.add_observation("Web search returned 5 results")

        assert len(scratchpad.observations) == 2
        # Observations also get iteration prefix
        assert "[0]" in scratchpad.observations[0]

    def test_confidence_direct_set(self):
        """Test confidence level can be set directly."""
        scratchpad = Scratchpad()

        scratchpad.confidence = 0.5
        assert scratchpad.confidence == 0.5

        scratchpad.confidence = 0.8
        assert scratchpad.confidence == 0.8

    def test_set_plan(self):
        """Test setting execution plan."""
        scratchpad = Scratchpad()

        plan_steps = [
            "Search knowledge base",
            "Analyze results",
            "Formulate response"
        ]
        scratchpad.set_plan(plan_steps)

        assert len(scratchpad.plan) == 3
        assert scratchpad.plan[0] == "Search knowledge base"

    def test_increment_iteration(self):
        """Test iteration counter."""
        scratchpad = Scratchpad()

        assert scratchpad.iteration == 0

        scratchpad.increment_iteration()
        assert scratchpad.iteration == 1

        scratchpad.increment_iteration()
        assert scratchpad.iteration == 2

    def test_delegation_flags(self):
        """Test delegation-related flags."""
        scratchpad = Scratchpad()

        assert scratchpad.should_delegate is False
        assert scratchpad.delegation_reason is None

        scratchpad.should_delegate = True
        scratchpad.delegation_reason = "Complex research task"

        assert scratchpad.should_delegate is True
        assert scratchpad.delegation_reason == "Complex research task"

    def test_needs_more_info_flag(self):
        """Test needs_more_info flag."""
        scratchpad = Scratchpad()

        assert scratchpad.needs_more_info is False

        scratchpad.needs_more_info = True
        assert scratchpad.needs_more_info is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        scratchpad = Scratchpad()
        scratchpad.add_thought("Test thought")
        scratchpad.confidence = 0.7

        data = scratchpad.to_dict()

        assert isinstance(data, dict)
        assert "thoughts" in data
        assert "confidence" in data
        assert data["confidence"] == 0.7

    def test_to_context_string(self):
        """Test conversion to context string for LLM."""
        scratchpad = Scratchpad()
        scratchpad.current_goal = "Answer the question about physics"
        scratchpad.set_plan(["Research", "Respond"])
        scratchpad.add_thought("Need to find sources")

        context = scratchpad.to_context_string()

        assert isinstance(context, str)
        assert "physics" in context.lower() or "goal" in context.lower()


# =============================================================================
# StopCondition Tests
# =============================================================================

class TestStopCondition:
    """Tests for agent stop conditions."""

    def test_stop_condition_defaults(self):
        """Test default stop condition values."""
        stop = StopCondition()

        assert stop.max_iterations == 7
        assert stop.confidence_threshold == 0.8
        assert stop.verification_required is True
        assert stop.explicit_stop is False

    def test_max_iterations_stop(self):
        """Test stopping at max iterations."""
        stop = StopCondition(max_iterations=5)

        stop.current_iteration = 4
        assert stop.should_stop() is False

        stop.current_iteration = 5
        assert stop.should_stop() is True

        stop.current_iteration = 6
        assert stop.should_stop() is True

    def test_confidence_threshold_without_verification(self):
        """Test confidence threshold when verification not required."""
        stop = StopCondition(
            confidence_threshold=0.8,
            verification_required=False
        )

        stop.current_confidence = 0.7
        assert stop.should_stop() is False

        stop.current_confidence = 0.85
        assert stop.should_stop() is True

    def test_confidence_with_verification(self):
        """Test confidence threshold when verification is required."""
        stop = StopCondition(
            confidence_threshold=0.8,
            verification_required=True
        )

        # High confidence but not verified
        stop.current_confidence = 0.9
        stop.verified = False
        assert stop.should_stop() is False

        # High confidence and verified
        stop.verified = True
        assert stop.should_stop() is True

    def test_explicit_stop(self):
        """Test explicit stop signal."""
        stop = StopCondition()

        assert stop.should_stop() is False

        stop.explicit_stop = True
        assert stop.should_stop() is True

    def test_explicit_stop_overrides_all(self):
        """Explicit stop should override other conditions."""
        stop = StopCondition(max_iterations=10)
        stop.current_iteration = 1
        stop.current_confidence = 0.3
        stop.verified = False

        stop.explicit_stop = True
        assert stop.should_stop() is True

    def test_stop_reason_on_max_iterations(self):
        """Test stop_reason is set when max iterations reached."""
        stop = StopCondition(max_iterations=3)

        stop.current_iteration = 3
        stop.should_stop()  # This sets the stop_reason

        assert stop.stop_reason == "max_iterations"

    def test_increment_method(self):
        """Test iteration increment method."""
        stop = StopCondition()

        stop.increment()
        assert stop.current_iteration == 1

        stop.increment()
        assert stop.current_iteration == 2

    def test_set_confidence(self):
        """Test set_confidence method."""
        stop = StopCondition()

        stop.set_confidence(0.75)
        assert stop.current_confidence == 0.75

    def test_mark_verified(self):
        """Test mark_verified method."""
        stop = StopCondition()

        assert stop.verified is False
        stop.mark_verified()
        assert stop.verified is True

    def test_force_stop(self):
        """Test force_stop method."""
        stop = StopCondition()

        stop.force_stop("User requested stop")
        assert stop.explicit_stop is True
        assert stop.stop_reason == "User requested stop"

    def test_to_dict(self):
        """Test serialization to dict."""
        stop = StopCondition(max_iterations=5)
        stop.current_iteration = 2

        data = stop.to_dict()

        assert isinstance(data, dict)
        assert data["max_iterations"] == 5
        assert data["current_iteration"] == 2


# =============================================================================
# SearchTrail Tests
# =============================================================================

class TestSearchAttempt:
    """Tests for SearchAttempt dataclass."""

    def test_search_attempt_creation(self):
        """Test creating a search attempt record."""
        attempt = SearchAttempt(
            source="knowledge_base",
            query="photosynthesis",
            results_count=5,
            success=True,
            had_results=True
        )

        assert attempt.source == "knowledge_base"
        assert attempt.query == "photosynthesis"
        assert attempt.results_count == 5
        assert attempt.success is True

    def test_search_attempt_with_error(self):
        """Test search attempt with error."""
        attempt = SearchAttempt(
            source="web_search",
            query="test query",
            results_count=0,
            success=False,
            had_results=False,
            error="Connection timeout"
        )

        assert attempt.success is False
        assert attempt.error == "Connection timeout"

    def test_search_attempt_from_tool_result(self):
        """Test creating SearchAttempt from tool result dict."""
        tool_result = {
            "query": "physics notes",
            "results_count": 3,
            "success": True
        }

        attempt = SearchAttempt.from_tool_result("search_knowledge_base", tool_result)

        assert attempt.source == "search_knowledge_base"
        assert attempt.query == "physics notes"
        assert attempt.results_count == 3

    def test_search_attempt_to_dict(self):
        """Test serialization to dict."""
        attempt = SearchAttempt(
            source="knowledge_base",
            query="test",
            results_count=2,
            success=True,
            had_results=True
        )

        data = attempt.to_dict()

        assert isinstance(data, dict)
        assert data["source"] == "knowledge_base"


class TestSearchTrail:
    """Tests for SearchTrail transparency tracking."""

    def test_search_trail_initializes_empty(self):
        """Search trail should start empty."""
        trail = SearchTrail()
        assert trail.attempts == []

    def test_add_search_attempt(self):
        """Test recording search attempts using SearchAttempt object."""
        trail = SearchTrail()

        attempt = SearchAttempt(
            source="knowledge_base",
            query="Newton's laws",
            results_count=3,
            success=True,
            had_results=True
        )
        trail.add_attempt(attempt)

        assert len(trail.attempts) == 1
        assert trail.attempts[0].source == "knowledge_base"
        assert trail.attempts[0].results_count == 3

    def test_add_from_tool_result(self):
        """Test adding attempt from tool result dict."""
        trail = SearchTrail()

        tool_result = {
            "query": "physics",
            "results_count": 5,
            "success": True
        }
        trail.add_from_tool_result("search_knowledge_base", tool_result)

        assert len(trail.attempts) == 1
        assert trail.attempts[0].source == "search_knowledge_base"

    def test_add_multiple_attempts(self):
        """Test recording multiple search attempts."""
        trail = SearchTrail()

        trail.add_attempt(SearchAttempt(source="knowledge_base", query="physics", results_count=2, had_results=True))
        trail.add_attempt(SearchAttempt(source="web_search", query="physics", results_count=5, had_results=True))
        trail.add_attempt(SearchAttempt(source="journals", query="physics notes", results_count=0, had_results=False))

        assert len(trail.attempts) == 3

    def test_get_summary(self):
        """Test summary generation for transparency."""
        trail = SearchTrail()

        trail.add_attempt(SearchAttempt(source="knowledge_base", query="test", results_count=3, had_results=True))
        trail.add_attempt(SearchAttempt(source="web_search", query="test", results_count=0, had_results=False))

        summary = trail.get_summary()

        assert isinstance(summary, str)
        assert len(summary) > 0
        # Should mention sources searched
        assert "Knowledge Base" in summary or "knowledge" in summary.lower()

    def test_get_summary_empty(self):
        """Test summary when no searches made."""
        trail = SearchTrail()
        summary = trail.get_summary()

        assert summary == ""  # Empty trail returns empty string

    def test_has_any_results(self):
        """Test checking if any search had results."""
        trail = SearchTrail()

        trail.add_attempt(SearchAttempt(source="knowledge_base", query="test", results_count=0, had_results=False))
        assert trail.has_any_results() is False

        trail.add_attempt(SearchAttempt(source="web_search", query="test", results_count=5, had_results=True))
        assert trail.has_any_results() is True

    def test_all_failed(self):
        """Test checking if all searches failed."""
        trail = SearchTrail()

        trail.add_attempt(SearchAttempt(source="knowledge_base", query="test", results_count=0, had_results=False))
        trail.add_attempt(SearchAttempt(source="web_search", query="test", results_count=0, had_results=False))

        assert trail.all_failed() is True

        trail.add_attempt(SearchAttempt(source="journals", query="test", results_count=1, had_results=True))
        assert trail.all_failed() is False

    def test_kb_searched(self):
        """Test checking if KB was searched."""
        trail = SearchTrail()

        assert trail.kb_searched() is False

        trail.add_attempt(SearchAttempt(source="search_knowledge_base", query="test", results_count=0, had_results=False))
        assert trail.kb_searched() is True

    def test_web_searched(self):
        """Test checking if web was searched."""
        trail = SearchTrail()

        assert trail.web_searched() is False

        trail.add_attempt(SearchAttempt(source="web_search", query="test", results_count=0, had_results=False))
        assert trail.web_searched() is True

    def test_to_dict(self):
        """Test serialization to dict."""
        trail = SearchTrail()
        trail.add_attempt(SearchAttempt(source="knowledge_base", query="test", results_count=2, had_results=True))

        data = trail.to_dict()

        assert isinstance(data, dict)
        assert "attempts" in data
        assert "has_any_results" in data
        assert data["has_any_results"] is True


# =============================================================================
# AgentPhase Tests
# =============================================================================

class TestAgentPhase:
    """Tests for AgentPhase enum."""

    def test_all_phases_exist(self):
        """Test all expected phases exist."""
        phases = [
            AgentPhase.THINKING,
            AgentPhase.RESEARCHING,
            AgentPhase.DELEGATING,
            AgentPhase.DRAFTING,
            AgentPhase.VERIFYING,
            AgentPhase.REFINING,
            AgentPhase.COMPLETE,
        ]

        for phase in phases:
            assert phase is not None
            assert isinstance(phase.value, str)

    def test_phase_values_are_lowercase(self):
        """Phase values should be lowercase strings."""
        for phase in AgentPhase:
            assert phase.value == phase.value.lower()


# =============================================================================
# VerificationResult Tests
# =============================================================================

class TestVerificationResult:
    """Tests for VerificationResult enum."""

    def test_verification_results_exist(self):
        """Test all verification results exist."""
        results = [
            VerificationResult.APPROVED,
            VerificationResult.NEEDS_REVISION,
            VerificationResult.NEEDS_MORE_INFO,
            VerificationResult.FACTUALLY_INCORRECT,
        ]

        for result in results:
            assert result is not None


class TestVerificationState:
    """Tests for VerificationState dataclass."""

    def test_verification_state_defaults(self):
        """Test default verification state."""
        state = VerificationState()

        assert state.verified is False
        assert state.result is None
        assert state.feedback is None
        assert state.issues == []
        assert state.suggestions == []

    def test_verification_state_approved(self):
        """Test approved verification state."""
        state = VerificationState(
            verified=True,
            result=VerificationResult.APPROVED.value,
            confidence_score=0.9,
            feedback="Response is accurate and complete"
        )

        assert state.verified is True
        assert state.result == "approved"
        assert state.confidence_score == 0.9

    def test_verification_state_needs_revision(self):
        """Test needs revision state."""
        state = VerificationState(
            verified=True,
            result=VerificationResult.NEEDS_REVISION.value,
            issues=["Missing citation", "Too brief"],
            suggestions=["Add source references", "Expand explanation"]
        )

        assert state.result == "needs_revision"
        assert len(state.issues) == 2
        assert len(state.suggestions) == 2

    def test_needs_revision_method(self):
        """Test needs_revision() method."""
        state = VerificationState(
            result=VerificationResult.NEEDS_REVISION.value,
            revision_count=0,
            max_revisions=2
        )

        assert state.needs_revision() is True

        state.revision_count = 2
        assert state.needs_revision() is False

    def test_mark_verified_method(self):
        """Test mark_verified method."""
        state = VerificationState()

        state.mark_verified("approved", "All good", 0.95)

        assert state.verified is True
        assert state.result == "approved"
        assert state.feedback == "All good"
        assert state.confidence_score == 0.95

    def test_add_issue(self):
        """Test add_issue method."""
        state = VerificationState()

        state.add_issue("Missing citation")
        state.add_issue("Too brief")

        assert len(state.issues) == 2
        assert "Missing citation" in state.issues

    def test_add_suggestion(self):
        """Test add_suggestion method."""
        state = VerificationState()

        state.add_suggestion("Add more detail")

        assert len(state.suggestions) == 1

    def test_increment_revision(self):
        """Test revision counter increment."""
        state = VerificationState()

        assert state.revision_count == 0

        state.increment_revision()
        assert state.revision_count == 1

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = VerificationState(
            verified=True,
            result="approved",
            confidence_score=0.85
        )

        data = state.to_dict()

        assert isinstance(data, dict)
        assert data["verified"] is True
        assert data["result"] == "approved"


# =============================================================================
# SubAgentType Tests
# =============================================================================

class TestSubAgentType:
    """Tests for SubAgentType enum."""

    def test_subagent_types_exist(self):
        """Test all sub-agent types exist."""
        types = [
            SubAgentType.RESEARCH,
            SubAgentType.ANALYSIS,
            SubAgentType.SUMMARY,
            SubAgentType.EXPERT,
            SubAgentType.FACT_CHECK,
        ]

        for agent_type in types:
            assert agent_type is not None


class TestSubAgentResult:
    """Tests for SubAgentResult dataclass."""

    def test_subagent_result_creation(self):
        """Test creating a sub-agent result."""
        result = SubAgentResult(
            agent_type="research",
            task="Find information about quantum physics",
            result="Found 5 relevant sources...",
            success=True,
            confidence=0.85
        )

        assert result.agent_type == "research"
        assert result.success is True
        assert result.confidence == 0.85

    def test_subagent_result_with_error(self):
        """Test sub-agent result with error."""
        result = SubAgentResult(
            agent_type="analysis",
            task="Analyze data",
            result="",
            success=False,
            error="Analysis failed: insufficient data"
        )

        assert result.success is False
        assert "insufficient data" in result.error

    def test_subagent_result_sources(self):
        """Test sub-agent result with sources used."""
        result = SubAgentResult(
            agent_type="research",
            task="Research topic",
            result="Found information...",
            success=True,
            sources_used=["knowledge_base", "web_search"],
            iteration_count=2
        )

        assert len(result.sources_used) == 2
        assert result.iteration_count == 2

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = SubAgentResult(
            agent_type="summary",
            task="Summarize document",
            result="Summary: ...",
            success=True
        )

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["agent_type"] == "summary"
        assert data["success"] is True
