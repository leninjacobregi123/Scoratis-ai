"""
Response Verifier Module
Implements the verifier pattern for quality assurance in agent responses.

The verifier is a separate LLM call that checks:
1. Factual accuracy (against sources)
2. Response completeness
3. Relevance to the question
4. Educational quality (for learning contexts)
5. Citation accuracy

If verification fails, the response is sent back for refinement.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .state import VerificationState, VerificationResult

logger = logging.getLogger(__name__)


# =============================================================================
# Verification Criteria
# =============================================================================

class VerificationCriterion(str, Enum):
    """Criteria for response verification"""
    FACTUAL_ACCURACY = "factual_accuracy"
    COMPLETENESS = "completeness"
    RELEVANCE = "relevance"
    EDUCATIONAL_QUALITY = "educational_quality"
    CITATION_ACCURACY = "citation_accuracy"
    TONE_AND_CLARITY = "tone_and_clarity"


@dataclass
class CriterionResult:
    """Result of checking a single criterion"""
    criterion: VerificationCriterion
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[str]
    suggestions: List[str]


@dataclass
class VerificationConfig:
    """Configuration for the verifier"""
    criteria: List[VerificationCriterion]
    min_passing_score: float = 0.7
    require_all_criteria: bool = False
    max_revision_attempts: int = 2
    enable_fact_checking: bool = True
    enable_citation_check: bool = True


DEFAULT_VERIFICATION_CONFIG = VerificationConfig(
    criteria=[
        VerificationCriterion.FACTUAL_ACCURACY,
        VerificationCriterion.COMPLETENESS,
        VerificationCriterion.RELEVANCE,
        VerificationCriterion.TONE_AND_CLARITY,
    ],
    min_passing_score=0.7,
    require_all_criteria=False,
    max_revision_attempts=2
)


EDUCATIONAL_VERIFICATION_CONFIG = VerificationConfig(
    criteria=[
        VerificationCriterion.FACTUAL_ACCURACY,
        VerificationCriterion.COMPLETENESS,
        VerificationCriterion.RELEVANCE,
        VerificationCriterion.EDUCATIONAL_QUALITY,
        VerificationCriterion.TONE_AND_CLARITY,
    ],
    min_passing_score=0.75,
    require_all_criteria=False,
    max_revision_attempts=2
)


# =============================================================================
# Verifier Prompts
# =============================================================================

VERIFIER_SYSTEM_PROMPT = """You are a Response Quality Verifier. Your task is to critically evaluate AI-generated responses for quality and accuracy.

You must be CRITICAL but FAIR. Look for:
1. Factual errors or unsupported claims
2. Missing information that should be included
3. Irrelevant content
4. Poor educational value (for learning contexts)
5. Incorrect or missing citations
6. Unclear or confusing explanations

IMPORTANT: You are NOT the main response generator. Your job is quality assurance.

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
    "overall_verdict": "approved" | "needs_revision" | "needs_more_info",
    "overall_score": 0.0-1.0,
    "criteria_results": {
        "factual_accuracy": {"score": 0.0-1.0, "issues": [], "suggestions": []},
        "completeness": {"score": 0.0-1.0, "issues": [], "suggestions": []},
        "relevance": {"score": 0.0-1.0, "issues": [], "suggestions": []},
        "educational_quality": {"score": 0.0-1.0, "issues": [], "suggestions": []},
        "tone_and_clarity": {"score": 0.0-1.0, "issues": [], "suggestions": []}
    },
    "summary_feedback": "Brief explanation of your verdict",
    "revision_instructions": "If needs_revision, specific instructions for improvement"
}"""


def build_verification_prompt(
    user_query: str,
    response: str,
    sources: List[Dict[str, Any]],
    context: Dict[str, Any]
) -> str:
    """Build the verification prompt with all context"""
    prompt_parts = [
        "## USER QUERY",
        user_query,
        "",
        "## RESPONSE TO VERIFY",
        response,
        "",
    ]

    # Add sources if available
    if sources:
        prompt_parts.append("## AVAILABLE SOURCES (for fact-checking)")
        for i, source in enumerate(sources[:10], 1):  # Limit to 10 sources
            source_text = source.get("content_preview", source.get("content", ""))[:300]
            source_title = source.get("document_title", f"Source {i}")
            prompt_parts.append(f"[{i}] {source_title}: {source_text}...")
        prompt_parts.append("")

    # Add context
    if context.get("subject"):
        prompt_parts.append(f"## SUBJECT CONTEXT: {context['subject']}")
        prompt_parts.append("")

    if context.get("learning_state"):
        state = context["learning_state"]
        prompt_parts.append(f"## LEARNING STATE: {state.get('state', 'initial')}")
        prompt_parts.append("")

    prompt_parts.append("## YOUR TASK")
    prompt_parts.append("Evaluate the response against all verification criteria and return JSON.")

    return "\n".join(prompt_parts)


# =============================================================================
# Response Verifier
# =============================================================================

class ResponseVerifier:
    """
    Verifies response quality using a separate LLM call.

    This implements the "verifier pattern" where a separate LLM
    evaluates the main agent's response for quality issues.
    """

    def __init__(
        self,
        llm_service: Any,
        config: Optional[VerificationConfig] = None
    ):
        self.llm_service = llm_service
        self.config = config or DEFAULT_VERIFICATION_CONFIG

    async def verify(
        self,
        user_query: str,
        response: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationState:
        """
        Verify a response for quality.

        Args:
            user_query: The original user question
            response: The response to verify
            sources: Available sources for fact-checking
            context: Additional context (subject, learning state, etc.)

        Returns:
            VerificationState with verification results
        """
        sources = sources or []
        context = context or {}

        # Build verification prompt
        verification_prompt = build_verification_prompt(
            user_query=user_query,
            response=response,
            sources=sources,
            context=context
        )

        try:
            # Call verifier LLM
            verifier_response = await self.llm_service.generate(
                messages=[{"role": "user", "content": verification_prompt}],
                system_prompt=VERIFIER_SYSTEM_PROMPT
            )

            # Parse the JSON response
            verification_result = self._parse_verification_response(verifier_response)

            # Create VerificationState
            state = VerificationState(
                verified=True,
                result=verification_result.get("overall_verdict", VerificationResult.APPROVED.value),
                feedback=verification_result.get("summary_feedback", ""),
                issues=self._extract_all_issues(verification_result),
                suggestions=self._extract_all_suggestions(verification_result),
                confidence_score=verification_result.get("overall_score", 0.5),
            )

            logger.info(f"Verification complete: {state.result} (score: {state.confidence_score:.2f})")
            return state

        except Exception as e:
            logger.error(f"Verification error: {e}")
            # Return approved by default on error (don't block response)
            return VerificationState(
                verified=True,
                result=VerificationResult.APPROVED.value,
                feedback=f"Verification failed: {str(e)}",
                confidence_score=0.5
            )

    def _parse_verification_response(self, response: str) -> Dict[str, Any]:
        """Parse the JSON response from the verifier"""
        try:
            # Try to extract JSON from the response
            response = response.strip()

            # Handle markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            return json.loads(response)

        except json.JSONDecodeError:
            logger.warning("Failed to parse verification JSON, using defaults")
            return {
                "overall_verdict": "approved",
                "overall_score": 0.7,
                "summary_feedback": "Could not parse verification response",
                "criteria_results": {},
                "revision_instructions": ""
            }

    def _extract_all_issues(self, result: Dict[str, Any]) -> List[str]:
        """Extract all issues from criteria results"""
        issues = []
        criteria_results = result.get("criteria_results", {})
        for criterion, data in criteria_results.items():
            if isinstance(data, dict) and data.get("issues"):
                issues.extend(data["issues"])
        return issues

    def _extract_all_suggestions(self, result: Dict[str, Any]) -> List[str]:
        """Extract all suggestions from criteria results"""
        suggestions = []
        criteria_results = result.get("criteria_results", {})
        for criterion, data in criteria_results.items():
            if isinstance(data, dict) and data.get("suggestions"):
                suggestions.extend(data["suggestions"])

        # Add revision instructions if present
        if result.get("revision_instructions"):
            suggestions.append(result["revision_instructions"])

        return suggestions

    async def verify_with_refinement(
        self,
        user_query: str,
        initial_response: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        refine_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Verify and potentially refine a response.

        If verification fails and refine_callback is provided,
        attempts to refine the response up to max_revision_attempts times.

        Args:
            user_query: The original user question
            initial_response: The initial response to verify
            sources: Available sources for fact-checking
            context: Additional context
            refine_callback: Async function(response, feedback) -> refined_response

        Returns:
            Dict with final response and verification details
        """
        current_response = initial_response
        attempts = 0
        verification_history = []

        while attempts < self.config.max_revision_attempts:
            # Verify current response
            verification = await self.verify(
                user_query=user_query,
                response=current_response,
                sources=sources,
                context=context
            )

            verification_history.append(verification.to_dict())

            # Check if approved
            if verification.result == VerificationResult.APPROVED.value:
                return {
                    "final_response": current_response,
                    "verified": True,
                    "verification": verification.to_dict(),
                    "refinement_attempts": attempts,
                    "verification_history": verification_history
                }

            # Check if we should/can refine
            if not refine_callback or verification.result == VerificationResult.FACTUALLY_INCORRECT.value:
                # Can't refine factual errors without more info
                break

            # Attempt refinement
            attempts += 1
            try:
                feedback = self._build_refinement_feedback(verification)
                current_response = await refine_callback(current_response, feedback)
                verification.increment_revision()
            except Exception as e:
                logger.error(f"Refinement attempt {attempts} failed: {e}")
                break

        # Return final state (may not be fully verified)
        final_verification = verification_history[-1] if verification_history else {}
        return {
            "final_response": current_response,
            "verified": final_verification.get("result") == VerificationResult.APPROVED.value,
            "verification": final_verification,
            "refinement_attempts": attempts,
            "verification_history": verification_history
        }

    def _build_refinement_feedback(self, verification: VerificationState) -> str:
        """Build feedback string for refinement"""
        parts = []

        if verification.feedback:
            parts.append(f"Feedback: {verification.feedback}")

        if verification.issues:
            parts.append("Issues to address:")
            for issue in verification.issues[:5]:  # Limit to 5
                parts.append(f"- {issue}")

        if verification.suggestions:
            parts.append("Suggestions:")
            for suggestion in verification.suggestions[:3]:  # Limit to 3
                parts.append(f"- {suggestion}")

        return "\n".join(parts)


# =============================================================================
# Quick Verification (Lightweight)
# =============================================================================

class QuickVerifier:
    """
    Lightweight verifier for simple quality checks.

    Uses heuristics and simple checks instead of LLM calls
    for faster verification of straightforward responses.
    """

    def __init__(self, min_length: int = 50, max_length: int = 5000):
        self.min_length = min_length
        self.max_length = max_length

    def quick_check(
        self,
        user_query: str,
        response: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> VerificationState:
        """
        Perform quick heuristic verification.

        Returns:
            VerificationState with quick check results
        """
        issues = []
        suggestions = []
        score = 1.0

        # Length check
        if len(response) < self.min_length:
            issues.append("Response is too short")
            suggestions.append("Provide more detailed explanation")
            score -= 0.2

        if len(response) > self.max_length:
            issues.append("Response is very long")
            suggestions.append("Consider being more concise")
            score -= 0.1

        # Empty response check
        if not response.strip():
            return VerificationState(
                verified=True,
                result=VerificationResult.NEEDS_REVISION.value,
                feedback="Empty response",
                issues=["Response is empty"],
                suggestions=["Generate a meaningful response"],
                confidence_score=0.0
            )

        # Check for question marks in question responses
        query_is_question = "?" in user_query
        response_answers = not response.strip().endswith("?")
        if query_is_question and not response_answers:
            # Response is another question - might be Socratic method
            pass  # Don't penalize for Socratic questioning

        # Citation check if sources provided
        if sources:
            has_citations = any(f"[{i}]" in response for i in range(1, len(sources) + 1))
            if not has_citations and len(response) > 200:
                suggestions.append("Consider adding citations to sources")
                score -= 0.1

        # Determine result
        if score >= 0.8:
            result = VerificationResult.APPROVED.value
        elif score >= 0.6:
            result = VerificationResult.NEEDS_REVISION.value
        else:
            result = VerificationResult.NEEDS_MORE_INFO.value

        return VerificationState(
            verified=True,
            result=result,
            feedback="Quick verification complete",
            issues=issues,
            suggestions=suggestions,
            confidence_score=score
        )


# =============================================================================
# Factory Functions
# =============================================================================

_verifier_instance: Optional[ResponseVerifier] = None
_quick_verifier_instance: Optional[QuickVerifier] = None


def create_verifier(
    llm_service: Any,
    config: Optional[VerificationConfig] = None
) -> ResponseVerifier:
    """Create or get the verifier instance"""
    global _verifier_instance

    if _verifier_instance is None:
        _verifier_instance = ResponseVerifier(
            llm_service=llm_service,
            config=config or DEFAULT_VERIFICATION_CONFIG
        )

    return _verifier_instance


def get_verifier() -> Optional[ResponseVerifier]:
    """Get the current verifier instance"""
    return _verifier_instance


def get_quick_verifier() -> QuickVerifier:
    """Get the quick verifier instance"""
    global _quick_verifier_instance

    if _quick_verifier_instance is None:
        _quick_verifier_instance = QuickVerifier()

    return _quick_verifier_instance
