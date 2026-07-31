"""
Query Reformulation Service
Transforms raw user queries into optimized search queries using LLM and chat history.

Strategies implemented:
1. Context-Aware Reformulation: Uses chat history to resolve pronouns and ambiguity
2. Query Expansion: Adds synonyms and related terms
3. Query Decomposition: Breaks complex queries into sub-queries
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReformulatedQuery:
    """Result of query reformulation"""
    original_query: str
    reformulated_query: str
    sub_queries: List[str]  # For complex queries decomposed into parts
    keywords: List[str]  # Extracted key terms
    query_type: str  # "simple", "comparison", "temporal", "factual"
    confidence: float


QUERY_REFORMULATION_PROMPT = """You are a search query optimization expert. Your task is to transform a user's conversational query into an optimized search query that will retrieve the most relevant documents from a knowledge base.

## Your Goals:
1. **Resolve Ambiguity**: If the query contains pronouns like "it", "that", "this", use the chat history to determine what they refer to.
2. **Enhance Specificity**: Add relevant keywords, synonyms, and related terms that would help find relevant documents.
3. **Expand Key Concepts**: If the user mentions a concept briefly, expand it with related terminology.
4. **Preserve Intent**: Keep the core intent of the query while making it more searchable.
5. **Handle Temporal References**: Convert "yesterday", "last week" etc. to be understood in search context.

## Chat History (for context):
{chat_history}

## User's Original Query:
{query}

## Instructions:
Analyze the query and chat history, then respond with a JSON object containing:
{{
    "reformulated_query": "The optimized search query (single string, comprehensive)",
    "sub_queries": ["list", "of", "sub-queries", "if the question is complex"],
    "keywords": ["key", "search", "terms", "extracted"],
    "query_type": "simple|comparison|temporal|factual|exploratory",
    "reasoning": "Brief explanation of changes made"
}}

Only respond with the JSON object, no other text."""


SIMPLE_EXPANSION_PROMPT = """Expand this search query with related terms and synonyms to improve retrieval.

Query: {query}

Return only the expanded query as a single line, adding 2-3 related terms in parentheses.
Example: "photosynthesis" -> "photosynthesis (light reactions, chloroplast, carbon fixation)"
"""


class QueryReformulationService:
    """
    Service for transforming user queries into optimized search queries.

    Uses LLM to:
    - Resolve pronouns and ambiguous references using chat history
    - Expand queries with synonyms and related terms
    - Decompose complex queries into searchable sub-queries
    """

    def __init__(self, llm_service: Any = None):
        self.llm_service = llm_service
        self._initialized = False

    def set_llm_service(self, llm_service: Any):
        """Set the LLM service (allows lazy initialization)"""
        self.llm_service = llm_service
        self._initialized = True

    async def reformulate_query(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        use_llm: bool = True
    ) -> ReformulatedQuery:
        """
        Reformulate a user query for better search results.

        Args:
            query: The user's raw query
            chat_history: Recent conversation messages [{"role": "user/assistant", "content": "..."}]
            use_llm: Whether to use LLM for reformulation (False = simple expansion only)

        Returns:
            ReformulatedQuery with optimized query and metadata
        """
        if not query or not query.strip():
            return ReformulatedQuery(
                original_query=query,
                reformulated_query=query,
                sub_queries=[],
                keywords=[],
                query_type="simple",
                confidence=0.0
            )

        query = query.strip()

        # If no LLM or LLM disabled, use simple expansion
        if not use_llm or not self.llm_service:
            return await self._simple_expansion(query)

        try:
            return await self._llm_reformulation(query, chat_history)
        except Exception as e:
            logger.warning(f"LLM reformulation failed, using simple expansion: {e}")
            return await self._simple_expansion(query)

    async def _llm_reformulation(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]],
    ) -> ReformulatedQuery:
        """Use LLM for intelligent query reformulation"""

        # Format chat history for prompt
        history_text = ""
        if chat_history:
            history_parts = []
            # Only use last 5 exchanges for context
            recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
            for msg in recent_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:500]  # Truncate long messages
                history_parts.append(f"{role.upper()}: {content}")
            history_text = "\n".join(history_parts)
        else:
            history_text = "(No previous conversation)"

        # Build prompt
        prompt = QUERY_REFORMULATION_PROMPT.format(
            chat_history=history_text,
            query=query
        )

        # Call LLM
        response = await self.llm_service.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a search query optimization assistant. Respond only with valid JSON."
        )

        # Parse response
        import json
        try:
            # Clean response (remove markdown code blocks if present)
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            result = json.loads(response_text)

            return ReformulatedQuery(
                original_query=query,
                reformulated_query=result.get("reformulated_query", query),
                sub_queries=result.get("sub_queries", []),
                keywords=result.get("keywords", []),
                query_type=result.get("query_type", "simple"),
                confidence=0.9
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Fall back to using the raw response as the reformulated query
            return ReformulatedQuery(
                original_query=query,
                reformulated_query=response.strip()[:500] if response else query,
                sub_queries=[],
                keywords=self._extract_keywords(query),
                query_type="simple",
                confidence=0.6
            )

    async def _simple_expansion(
        self,
        query: str,
    ) -> ReformulatedQuery:
        """Simple rule-based query expansion without LLM"""

        keywords = self._extract_keywords(query)

        return ReformulatedQuery(
            original_query=query,
            reformulated_query=query,
            sub_queries=[],
            keywords=keywords,
            query_type=self._detect_query_type(query),
            confidence=0.5
        )

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from query using simple heuristics"""
        # Remove common stop words
        stop_words = {
            "what", "is", "are", "the", "a", "an", "how", "why", "when",
            "where", "which", "who", "does", "do", "can", "could", "would",
            "should", "will", "about", "from", "to", "in", "on", "at",
            "for", "with", "by", "of", "and", "or", "but", "this", "that",
            "these", "those", "it", "its", "my", "your", "our", "their",
            "me", "you", "us", "them", "i", "we", "they", "he", "she"
        }

        words = query.lower().split()
        keywords = [w.strip("?.,!") for w in words if w.lower() not in stop_words and len(w) > 2]

        return keywords[:10]  # Limit to top 10 keywords

    def _detect_query_type(self, query: str) -> str:
        """Detect the type of query for better handling"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["compare", "difference", "vs", "versus", "between"]):
            return "comparison"
        elif any(word in query_lower for word in ["when", "yesterday", "today", "last week", "recent"]):
            return "temporal"
        elif any(word in query_lower for word in ["what is", "define", "explain", "meaning"]):
            return "factual"
        elif any(word in query_lower for word in ["how to", "steps", "process", "guide"]):
            return "procedural"
        elif any(word in query_lower for word in ["why", "reason", "cause"]):
            return "explanatory"
        else:
            return "simple"

    async def decompose_complex_query(
        self,
        query: str,
    ) -> List[str]:
        """
        Decompose a complex query into multiple simpler sub-queries.
        Useful for comparison questions or multi-part queries.

        Args:
            query: Complex user query

        Returns:
            List of simpler sub-queries
        """
        query_type = self._detect_query_type(query)

        if query_type == "comparison":
            # Extract entities being compared
            # e.g., "Compare mitosis and meiosis" -> ["mitosis", "meiosis", "mitosis vs meiosis"]
            keywords = self._extract_keywords(query)
            if len(keywords) >= 2:
                return [
                    keywords[0],
                    keywords[1],
                    f"{keywords[0]} vs {keywords[1]}",
                    f"comparison {keywords[0]} {keywords[1]}"
                ]

        # For other types, return original query
        return [query]


# Singleton instance
_query_service: Optional[QueryReformulationService] = None


def get_query_service() -> QueryReformulationService:
    """Get or create the query reformulation service singleton"""
    global _query_service
    if _query_service is None:
        _query_service = QueryReformulationService()
    return _query_service
