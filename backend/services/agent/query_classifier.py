"""
Query Classifier - Detect trivial vs substantive queries

This module classifies user queries to determine whether they need
tool usage (knowledge base search, web search) or can be answered directly.

Types of queries:
- trivial: Greetings, small talk, yes/no responses - skip tools entirely
- general_knowledge: Simple factual questions - can use LLM knowledge
- substantive: Complex questions requiring research - use tools

This helps optimize the agentic workflow by avoiding unnecessary
tool calls for simple interactions.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class QueryClassification:
    """Result of classifying a user query."""
    is_trivial: bool
    query_type: str  # "trivial", "general_knowledge", "substantive"
    skip_tools: bool
    reason: str
    confidence: float = 0.8


class QueryClassifier:
    """
    Classify queries to determine if tools are needed.

    The goal is to identify queries that don't require searching
    the knowledge base or web, saving unnecessary API calls and latency.
    """

    # Patterns for trivial queries (greetings, small talk)
    TRIVIAL_PATTERNS = [
        # Greetings
        r"^(hi|hello|hey|hiya|greetings|good morning|good afternoon|good evening|good night)[\s!.,?]*$",
        r"^(what'?s up|wassup|sup|howdy)[\s!.,?]*$",

        # Pleasantries
        r"^(thank you|thanks|thx|ty|thank u|much appreciated)[\s!.,?]*$",
        r"^(bye|goodbye|see you|see ya|later|cya|farewell)[\s!.,?]*$",
        r"^(please|pls|plz)[\s!.,?]*$",

        # Small talk
        r"^(how are you|how're you|how r u|how you doing|how do you do)[\s!.,?]*$",
        r"^(i'?m (good|fine|great|okay|ok|doing well))[\s!.,?]*$",
        r"^(nice to meet you|nice meeting you)[\s!.,?]*$",

        # Single word responses
        r"^(yes|no|ok|okay|sure|maybe|nope|yep|yup|nah)[\s!.,?]*$",
        r"^(cool|awesome|great|nice|perfect|excellent|wonderful)[\s!.,?]*$",
        r"^(hmm|hm|um|uh|ah|oh|wow)[\s!.,?]*$",

        # Simple acknowledgments
        r"^(got it|understood|i see|i understand|makes sense)[\s!.,?]*$",
        r"^(alright|all right|sounds good)[\s!.,?]*$",

        # Simple math that LLM can handle
        r"^(what is|what's|calculate|compute)\s+\d+\s*[+\-*/]\s*\d+[\s!.,?]*$",
    ]

    # Patterns for general knowledge (can use LLM without tools)
    GENERAL_KNOWLEDGE_PATTERNS = [
        # Basic factual questions
        r"(what|which) is the capital of",
        r"who (is|was) the (first|current|last) (president|prime minister|king|queen)",
        r"what year (did|was|were)",
        r"how many (days|months|weeks|hours|minutes|seconds) (in|are in)",
        r"what (is|are) the (days|months) of",
        r"how do you (spell|say|pronounce)",
        r"what does .{1,20} mean$",
        r"define (the word |word )?[a-zA-Z]+$",
        r"(what|which) (color|colour) is",
        r"is .{1,30} (true|false|correct|right|wrong)",
    ]

    # Patterns that indicate substantive query (definitely need tools)
    SUBSTANTIVE_INDICATORS = [
        # Personal context references
        r"(my|our) (notes|documents|journal|files|uploads|papers)",
        r"(i|we) (wrote|uploaded|saved|noted|recorded)",
        r"(in|from) my (notes|documents|files|uploads)",
        r"what (did|have) (i|we) (learn|write|note|save)",

        # Research/exploration requests
        r"(search|find|look for|research|explore|investigate)",
        r"(tell me|explain|describe) (about|how|why|what)",
        r"(can you|could you|please) (help|assist|explain)",

        # Complex topics
        r"(compare|contrast|difference|similar)",
        r"(analyze|analysis|evaluate|assess)",
        r"(explain|describe|elaborate) (the|how|why|what)",
        r"(summarize|summary|overview)",

        # Questions with context
        r"(based on|according to|referring to)",
        r"(in the context of|regarding|about the)",
    ]

    def __init__(self):
        # Pre-compile patterns for efficiency
        self._trivial_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.TRIVIAL_PATTERNS
        ]
        self._general_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.GENERAL_KNOWLEDGE_PATTERNS
        ]
        self._substantive_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.SUBSTANTIVE_INDICATORS
        ]

    def classify(self, query: str) -> QueryClassification:
        """
        Classify a user query to determine if tools are needed.

        Args:
            query: The user's query text

        Returns:
            QueryClassification with type and whether to skip tools
        """
        query_lower = query.lower().strip()

        # Check for trivial patterns first
        for pattern in self._trivial_compiled:
            if pattern.match(query_lower):
                return QueryClassification(
                    is_trivial=True,
                    query_type="trivial",
                    skip_tools=True,
                    reason="Simple greeting, acknowledgment, or small talk",
                    confidence=0.95
                )

        # Check if it clearly indicates substantive query (needs tools)
        for pattern in self._substantive_compiled:
            if pattern.search(query_lower):
                return QueryClassification(
                    is_trivial=False,
                    query_type="substantive",
                    skip_tools=False,
                    reason="Query indicates research or personal content lookup",
                    confidence=0.9
                )

        # Check for general knowledge patterns
        for pattern in self._general_compiled:
            if pattern.search(query_lower):
                return QueryClassification(
                    is_trivial=True,
                    query_type="general_knowledge",
                    skip_tools=True,
                    reason="General knowledge question - LLM can answer directly",
                    confidence=0.75
                )

        # Short queries (under 5 words) without keywords - might be trivial
        word_count = len(query.split())
        if word_count < 3:
            # Very short query - likely trivial unless it's a keyword
            if not any(kw in query_lower for kw in ["explain", "what", "how", "why", "tell", "help"]):
                return QueryClassification(
                    is_trivial=True,
                    query_type="trivial",
                    skip_tools=True,
                    reason="Very short query without research keywords",
                    confidence=0.6
                )

        # Default: Treat as substantive (err on the side of searching)
        return QueryClassification(
            is_trivial=False,
            query_type="substantive",
            skip_tools=False,
            reason="Defaulting to substantive query - may require research",
            confidence=0.5
        )

    def is_trivial(self, query: str) -> bool:
        """Quick check if query is trivial."""
        return self.classify(query).is_trivial

    def should_skip_tools(self, query: str) -> bool:
        """Quick check if tools should be skipped."""
        return self.classify(query).skip_tools


# Singleton instance
_classifier: Optional[QueryClassifier] = None


def get_query_classifier() -> QueryClassifier:
    """Get or create the query classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = QueryClassifier()
    return _classifier
