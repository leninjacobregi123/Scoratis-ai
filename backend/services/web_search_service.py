"""
Web Search Service
Tavily integration for knowledge augmentation
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


@dataclass
class SearchResult:
    """A single web search result"""

    title: str
    url: str
    snippet: str


class WebSearchService:
    """Service for web search using DuckDuckGo"""

    # Patterns that indicate the LLM lacks knowledge
    KNOWLEDGE_GAP_PATTERNS = [
        r"i don'?t have (access to|information about|knowledge of)",
        r"i'?m not (sure|certain|aware)",
        r"i cannot (provide|give|find)",
        r"my (knowledge|training|information) (cutoff|ends|is limited)",
        r"i don'?t know",
        r"i'?m unable to",
        r"beyond my (knowledge|capabilities)",
        r"i (can'?t|cannot) (access|browse|search)",
        r"as of my (last|knowledge) (update|cutoff)",
        r"i (don'?t|do not) have (real-?time|current|up-?to-?date)",
    ]

    def __init__(self, max_results: int = 3):
        from config import settings

        self.max_results = settings.WEB_SEARCH_MAX_RESULTS
        self.api_key = settings.TAVILY_API_KEY
        # Disabled if there's no key, regardless of WEB_SEARCH_ENABLED -
        # Tavily requires one, unlike the old unauthenticated DDGS scraping.
        self.enabled = settings.WEB_SEARCH_ENABLED and bool(self.api_key)
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.KNOWLEDGE_GAP_PATTERNS
        ]

    def detect_knowledge_gap(self, response: str) -> bool:
        """
        Detect if an LLM response indicates a knowledge gap.

        Args:
            response: The LLM's response text

        Returns:
            True if knowledge gap detected
        """
        if not response:
            return False

        for pattern in self._compiled_patterns:
            if pattern.search(response):
                logger.info(f"Knowledge gap detected: {pattern.pattern}")
                return True

        return False

    def extract_search_query(self, user_message: str, llm_response: str) -> str:
        """
        Extract a search query from the context.

        Args:
            user_message: The user's original message
            llm_response: The LLM's response (may contain what it doesn't know)

        Returns:
            A search query string
        """
        # For now, use the user's message as the search query
        # Could be enhanced to extract key terms
        query = user_message.strip()

        # Limit query length
        if len(query) > 150:
            query = query[:150]

        return query

    async def search(self, query: str) -> List[SearchResult]:
        """
        Perform a web search using the Tavily API.

        Args:
            query: Search query string

        Returns:
            List of SearchResult objects
        """
        if not self.enabled:
            logger.info("Web search is disabled (no TAVILY_API_KEY configured)")
            return []

        if not query or not query.strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    TAVILY_SEARCH_URL,
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": self.max_results,
                        "search_depth": "basic",
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                )
                for r in data.get("results", [])
            ]

            logger.info(f"Web search found {len(results)} results for: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """
        Format search results for LLM context injection.

        Args:
            results: List of SearchResult objects

        Returns:
            Formatted string for LLM prompt
        """
        if not results:
            return ""

        parts = ["**Web Search Results:**"]

        for i, result in enumerate(results, 1):
            parts.append(f"\n[{i}] {result.title}")
            parts.append(f"    URL: {result.url}")
            parts.append(f"    {result.snippet}")

        parts.append(
            "\nPlease use the above web search results to provide an accurate, "
            "up-to-date response. Cite sources where appropriate."
        )

        return "\n".join(parts)

    async def augment_response(
        self, user_message: str, initial_response: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if response needs augmentation and provide search results if so.

        Args:
            user_message: User's original message
            initial_response: LLM's first response

        Returns:
            Dict with search_results and formatted_context, or None if not needed
        """
        if not self.detect_knowledge_gap(initial_response):
            return None

        query = self.extract_search_query(user_message, initial_response)
        results = await self.search(query)

        if not results:
            return None

        return {
            "search_results": results,
            "formatted_context": self.format_results_for_llm(results),
            "query": query,
        }


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create the web search service singleton"""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
