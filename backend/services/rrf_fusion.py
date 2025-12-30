"""
Reciprocal Rank Fusion (RRF) Utilities
Combines multiple ranked lists into a single fused ranking
"""

from typing import List, Dict, Any, Optional, Tuple, TypeVar
from dataclasses import dataclass
from collections import defaultdict

from config import settings


T = TypeVar('T')


@dataclass
class RankedItem:
    """A single item with ranking information"""
    id: Any
    rank: int
    score: float
    source: str  # 'semantic' or 'keyword'
    data: Optional[Dict[str, Any]] = None


@dataclass
class FusedResult:
    """Result after RRF fusion"""
    id: Any
    rrf_score: float
    semantic_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


def reciprocal_rank_fusion(
    ranked_lists: List[List[RankedItem]],
    k: int = None
) -> List[FusedResult]:
    """
    Perform Reciprocal Rank Fusion on multiple ranked lists.

    RRF Score = sum(1 / (k + rank)) for each list where item appears

    Args:
        ranked_lists: List of ranked lists, each containing RankedItem objects
        k: RRF constant (default from settings.RRF_K = 60)

    Returns:
        List of FusedResult objects sorted by RRF score descending
    """
    if k is None:
        k = settings.RRF_K

    # Accumulate scores by ID
    scores: Dict[Any, float] = defaultdict(float)
    ranks: Dict[Any, Dict[str, int]] = defaultdict(dict)
    data: Dict[Any, Dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        for item in ranked_list:
            # RRF formula: 1 / (k + rank)
            # Rank is 1-indexed for RRF
            rrf_contribution = 1.0 / (k + item.rank)
            scores[item.id] += rrf_contribution
            ranks[item.id][item.source] = item.rank

            # Store data from first occurrence
            if item.id not in data and item.data:
                data[item.id] = item.data

    # Create fused results
    results = []
    for item_id, score in scores.items():
        result = FusedResult(
            id=item_id,
            rrf_score=score,
            semantic_rank=ranks[item_id].get('semantic'),
            keyword_rank=ranks[item_id].get('keyword'),
            data=data.get(item_id),
        )
        results.append(result)

    # Sort by RRF score descending
    results.sort(key=lambda x: x.rrf_score, reverse=True)

    return results


def boost_chunk_scores(
    chunks: List[FusedResult],
    doc_scores: Dict[int, float],
    boost_factor: float = 0.3
) -> List[FusedResult]:
    """
    Boost chunk scores based on their parent document scores.

    This implements the second-pass fusion for multi-level retrieval:
    chunks from higher-ranked documents get a score boost.

    Args:
        chunks: List of chunk results from chunk-level search
        doc_scores: Mapping of document_id -> document RRF score
        boost_factor: How much to weight document score (0.0-1.0)

    Returns:
        List of chunks with boosted scores
    """
    if not chunks or not doc_scores:
        return chunks

    # Normalize document scores to 0-1 range
    max_doc_score = max(doc_scores.values()) if doc_scores else 1.0
    if max_doc_score == 0:
        max_doc_score = 1.0

    boosted_results = []
    for chunk in chunks:
        # Get document ID from chunk data
        doc_id = chunk.data.get('document_id') if chunk.data else None

        # Calculate boost
        if doc_id and doc_id in doc_scores:
            normalized_doc_score = doc_scores[doc_id] / max_doc_score
            boost = boost_factor * normalized_doc_score
        else:
            boost = 0.0

        # Apply boost
        boosted_chunk = FusedResult(
            id=chunk.id,
            rrf_score=chunk.rrf_score + boost,
            semantic_rank=chunk.semantic_rank,
            keyword_rank=chunk.keyword_rank,
            data=chunk.data,
        )
        boosted_results.append(boosted_chunk)

    # Re-sort by boosted score
    boosted_results.sort(key=lambda x: x.rrf_score, reverse=True)

    return boosted_results


def merge_with_reranking(
    primary_results: List[FusedResult],
    secondary_results: List[FusedResult],
    primary_weight: float = 0.7
) -> List[FusedResult]:
    """
    Merge two result lists with weighted reranking.

    Useful for combining chunk-level and document-level results.

    Args:
        primary_results: Primary result list (usually chunk-level)
        secondary_results: Secondary result list (usually document-level)
        primary_weight: Weight for primary results (0.0-1.0)

    Returns:
        Merged and reranked results
    """
    secondary_weight = 1.0 - primary_weight

    # Index by ID
    merged_scores: Dict[Any, float] = {}
    merged_data: Dict[Any, Dict[str, Any]] = {}

    for result in primary_results:
        merged_scores[result.id] = result.rrf_score * primary_weight
        if result.data:
            merged_data[result.id] = result.data

    for result in secondary_results:
        if result.id in merged_scores:
            merged_scores[result.id] += result.rrf_score * secondary_weight
        else:
            merged_scores[result.id] = result.rrf_score * secondary_weight
            if result.data:
                merged_data[result.id] = result.data

    # Create merged results
    results = [
        FusedResult(
            id=item_id,
            rrf_score=score,
            data=merged_data.get(item_id),
        )
        for item_id, score in merged_scores.items()
    ]

    # Sort by score
    results.sort(key=lambda x: x.rrf_score, reverse=True)

    return results


def deduplicate_by_content(
    results: List[FusedResult],
    similarity_threshold: float = 0.95
) -> List[FusedResult]:
    """
    Remove near-duplicate results based on content similarity.

    Uses simple character-level overlap for efficiency.

    Args:
        results: List of results with content in data
        similarity_threshold: Minimum similarity to consider duplicate

    Returns:
        Deduplicated results
    """
    if not results:
        return results

    deduped = []
    seen_content: List[str] = []

    for result in results:
        content = result.data.get('content', '') if result.data else ''
        content_lower = content.lower().strip()

        # Check for duplicates
        is_duplicate = False
        for seen in seen_content:
            # Simple overlap check
            if len(content_lower) > 0 and len(seen) > 0:
                shorter = min(content_lower, seen, key=len)
                longer = max(content_lower, seen, key=len)
                if shorter in longer:
                    is_duplicate = True
                    break

                # Character overlap
                overlap = len(set(content_lower) & set(seen)) / len(set(content_lower) | set(seen))
                if overlap >= similarity_threshold:
                    is_duplicate = True
                    break

        if not is_duplicate:
            deduped.append(result)
            seen_content.append(content_lower)

    return deduped


def format_context_xml(
    results: List[Dict[str, Any]],
    include_metadata: bool = True
) -> str:
    """
    Format search results as XML for LLM context.

    Args:
        results: List of result dictionaries with chunk_id, content, etc.
        include_metadata: Whether to include metadata attributes

    Returns:
        XML-formatted context string
    """
    if not results:
        return "<context>\n  <no_results>No relevant information found.</no_results>\n</context>"

    xml_parts = ["<context>"]

    for result in results:
        chunk_id = result.get('chunk_id', result.get('id'))
        content = result.get('content', '')
        doc_title = result.get('document_title', '')
        page = result.get('page')

        # Build chunk element
        attrs = [f"id='{chunk_id}'"]
        if include_metadata:
            if doc_title:
                attrs.append(f"document='{doc_title}'")
            if page:
                attrs.append(f"page='{page}'")

        attr_str = ' '.join(attrs)
        xml_parts.append(f"  <chunk {attr_str}>")
        xml_parts.append(f"    {content}")
        xml_parts.append("  </chunk>")

    xml_parts.append("</context>")

    return '\n'.join(xml_parts)


def extract_citation_ids(text: str) -> List[str]:
    """
    Extract citation IDs from text.

    Looks for patterns like [citation:chunk_123]

    Args:
        text: Text containing citations

    Returns:
        List of chunk IDs
    """
    import re
    pattern = r'\[citation:(chunk_\d+)\]'
    return re.findall(pattern, text)


def replace_citations_with_numbers(
    text: str,
    chunk_id_to_number: Dict[str, int]
) -> Tuple[str, Dict[int, str]]:
    """
    Replace citation tags with numbered references.

    Converts [citation:chunk_123] to [1] and builds a mapping.

    Args:
        text: Text with citation tags
        chunk_id_to_number: Mapping of chunk_id -> citation number

    Returns:
        Tuple of (processed text, number to chunk_id mapping)
    """
    import re

    number_to_chunk: Dict[int, str] = {}
    processed_text = text

    for chunk_id, number in chunk_id_to_number.items():
        pattern = f'\\[citation:{chunk_id}\\]'
        processed_text = re.sub(pattern, f'[{number}]', processed_text)
        number_to_chunk[number] = chunk_id

    return processed_text, number_to_chunk
