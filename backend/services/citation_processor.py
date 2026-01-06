"""
Citation Processor Service
Converts LLM citation tags to user-friendly footnote format.

Transforms:
  [citation:chunk_123] -> superscript numbers (e.g., ¹)

And builds a footnotes section with source details.
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional

logger = logging.getLogger(__name__)

# Unicode superscript digits
SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
}

# Citation pattern: [citation:chunk_123] or [citation:chunk_45]
CITATION_PATTERN = re.compile(r'\[citation:(chunk_\d+)\]')


class CitationProcessor:
    """
    Processes LLM responses to format citations as inline footnotes.

    Input: "Energy is conserved [citation:chunk_45] in closed systems."
    Output: "Energy is conserved¹ in closed systems."

    Plus footnotes section:
    ---
    **Sources:**
    ¹ Physics Notes, p.5 — "The law of conservation..."
    """

    @staticmethod
    def to_superscript(num: int) -> str:
        """
        Convert a number to its superscript Unicode representation.

        Args:
            num: Integer to convert (e.g., 12)

        Returns:
            Superscript string (e.g., '¹²')
        """
        return ''.join(SUPERSCRIPT_MAP.get(d, d) for d in str(num))

    @staticmethod
    def extract_citations(text: str) -> Set[str]:
        """
        Extract all chunk IDs from citation tags in text.

        Args:
            text: Text containing [citation:chunk_id] tags

        Returns:
            Set of chunk IDs found (e.g., {'chunk_45', 'chunk_123'})
        """
        return set(CITATION_PATTERN.findall(text))

    def format_response_with_footnotes(
        self,
        response: str,
        sources: List[Dict],
        chunk_mapping: Dict[str, int]
    ) -> Tuple[str, str, List[Dict]]:
        """
        Convert citation tags to superscript numbers and build footnotes section.

        Args:
            response: LLM response text with [citation:chunk_id] tags
            sources: List of source metadata dicts with chunk_id, document_title, etc.
            chunk_mapping: Maps chunk_id to citation number (1-indexed)

        Returns:
            Tuple of:
            - formatted_response: Text with superscript citations
            - footnotes_section: Formatted footnotes markdown
            - used_sources: List of sources that were actually cited
        """
        # Extract which citations were actually used
        used_citations = self.extract_citations(response)

        if not used_citations:
            # No citations in response - return as-is
            return response, "", []

        # Replace [citation:chunk_id] with superscript numbers
        def replace_citation(match):
            chunk_id = match.group(1)
            if chunk_id in chunk_mapping:
                num = chunk_mapping[chunk_id]
                return self.to_superscript(num)
            # Unknown chunk ID - remove the tag
            logger.warning(f"Unknown chunk_id in citation: {chunk_id}")
            return ""

        formatted_response = CITATION_PATTERN.sub(replace_citation, response)

        # Build footnotes section
        used_sources = []
        footnote_lines = []

        for src in sources:
            chunk_id = src.get("chunk_id", "")
            if chunk_id in used_citations:
                citation_num = chunk_mapping.get(chunk_id, 0)
                title = src.get("document_title", "Unknown Source")
                page = src.get("page")
                preview = src.get("content_preview", src.get("content", ""))[:100]

                # Clean up preview
                preview = preview.replace("\n", " ").strip()
                if len(preview) > 80:
                    preview = preview[:80] + "..."

                # Format footnote line
                page_str = f", p.{page}" if page else ""
                superscript = self.to_superscript(citation_num)
                footnote = f"{superscript} **{title}**{page_str} — \"{preview}\""
                footnote_lines.append((citation_num, footnote))

                used_sources.append({
                    **src,
                    "was_cited": True
                })

        # Sort footnotes by citation number
        footnote_lines.sort(key=lambda x: x[0])

        # Build footnotes markdown section
        if footnote_lines:
            footnotes_section = "\n\n---\n**Sources:**\n" + "\n".join(
                line for _, line in footnote_lines
            )
        else:
            footnotes_section = ""

        return formatted_response, footnotes_section, used_sources

    def combine_response_with_footnotes(
        self,
        response: str,
        sources: List[Dict],
        chunk_mapping: Dict[str, int]
    ) -> str:
        """
        Convenience method that returns the complete formatted response with footnotes.

        Args:
            response: LLM response with citation tags
            sources: Source metadata list
            chunk_mapping: chunk_id to citation number mapping

        Returns:
            Complete formatted response with inline superscripts and footnotes section
        """
        formatted, footnotes, _ = self.format_response_with_footnotes(
            response, sources, chunk_mapping
        )
        return formatted + footnotes

    def validate_citations(
        self,
        response: str,
        sources: List[Dict],
        chunk_mapping: Dict[str, int]
    ) -> Dict:
        """
        Validate that citations in the response match available sources.

        Returns:
            Dict with validation results:
            - valid: bool
            - used_citations: set of used chunk_ids
            - available_citations: set of available chunk_ids
            - missing_citations: set of referenced but unavailable chunk_ids
            - unused_sources: count of sources not cited
        """
        used = self.extract_citations(response)
        available = set(chunk_mapping.keys())

        missing = used - available
        unused_count = len(available) - len(used & available)

        return {
            "valid": len(missing) == 0,
            "used_citations": used,
            "available_citations": available,
            "missing_citations": missing,
            "unused_sources": unused_count,
            "citation_count": len(used),
        }


# Singleton instance
_citation_processor: Optional[CitationProcessor] = None


def get_citation_processor() -> CitationProcessor:
    """Get or create the citation processor singleton."""
    global _citation_processor
    if _citation_processor is None:
        _citation_processor = CitationProcessor()
    return _citation_processor
