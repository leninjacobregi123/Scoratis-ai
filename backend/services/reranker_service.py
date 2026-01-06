"""
Re-ranker Service
Uses cross-encoder models to re-rank initial retrieval results for better relevance.

The re-ranker takes the top-N results from hybrid search and applies a more
accurate (but slower) cross-encoder model to re-score and re-order them.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Cross-encoder is disabled to avoid TensorFlow/PyTorch conflicts
# The fallback scoring (using RRF scores) is used instead
# Re-enable by setting ENABLE_CROSS_ENCODER=true in environment
import os

_cross_encoder = None
_cross_encoder_failed = True  # Disabled by default due to segfault issues


def get_cross_encoder():
    """
    Get cross-encoder model (disabled by default).

    The cross-encoder causes segmentation faults due to TensorFlow/PyTorch
    conflicts in the current environment. Using RRF-based fallback scoring instead.
    To re-enable, set ENABLE_CROSS_ENCODER=true in environment.
    """
    global _cross_encoder, _cross_encoder_failed

    # Check if explicitly enabled
    if not os.environ.get("ENABLE_CROSS_ENCODER", "").lower() == "true":
        return None

    if _cross_encoder_failed:
        return None

    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder

            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            logger.info(f"Loading cross-encoder model: {model_name}")

            _cross_encoder = CrossEncoder(model_name, max_length=512, device='cpu')
            logger.info("Cross-encoder model loaded successfully")

        except ImportError:
            logger.warning(
                "sentence-transformers not available for cross-encoder. "
                "Re-ranking will use fallback scoring."
            )
            _cross_encoder_failed = True
            return None
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            _cross_encoder_failed = True
            return None

    return _cross_encoder


@dataclass
class RerankedResult:
    """A re-ranked search result"""
    id: int
    content: str
    original_score: float
    reranked_score: float
    rank_change: int  # Positive = moved up, Negative = moved down
    metadata: Dict[str, Any]


class RerankerService:
    """
    Service for re-ranking search results using cross-encoder models.

    Cross-encoders are more accurate than bi-encoders (used in initial retrieval)
    because they process the query and document together, allowing for better
    understanding of relevance. However, they are slower, so we only apply them
    to the top-N candidates from initial retrieval.

    Strategies:
    1. Cross-Encoder Scoring: Use MS-MARCO trained model for relevance
    2. Score Calibration: Normalize scores across different retrieval methods
    3. Confidence Filtering: Remove results below a confidence threshold
    """

    def __init__(self):
        self._model = None
        self.default_top_k = 20  # Re-rank top 20 results
        self.confidence_threshold = 0.1  # Minimum score to keep result

    @property
    def model(self):
        """Lazy load the cross-encoder model"""
        if self._model is None:
            self._model = get_cross_encoder()
        return self._model

    @property
    def is_available(self) -> bool:
        """Check if cross-encoder is available"""
        return self.model is not None

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        content_key: str = "content",
        score_key: str = "rrf_score",
        apply_threshold: bool = True
    ) -> List[RerankedResult]:
        """
        Re-rank search results using cross-encoder.

        Args:
            query: The search query
            results: List of search results with content and scores
            top_k: Number of top results to return (default: 20)
            content_key: Key for content in result dict
            score_key: Key for original score in result dict
            apply_threshold: Whether to filter low-confidence results

        Returns:
            List of RerankedResult sorted by reranked_score descending
        """
        if not results:
            return []

        top_k = top_k or self.default_top_k

        # If model not available, return results with original scores
        if not self.is_available:
            logger.debug("Cross-encoder not available, returning original ranking")
            return self._fallback_rerank(results, content_key, score_key, top_k)

        try:
            # Prepare query-document pairs for cross-encoder
            pairs = []
            valid_indices = []

            for i, result in enumerate(results[:top_k * 2]):  # Consider more candidates
                content = result.get(content_key, "")
                if content and isinstance(content, str):
                    # Truncate long content
                    content = content[:1000]
                    pairs.append([query, content])
                    valid_indices.append(i)

            if not pairs:
                return self._fallback_rerank(results, content_key, score_key, top_k)

            # Get cross-encoder scores
            scores = self.model.predict(pairs)

            # Combine with original results
            reranked = []
            for idx, (pair_idx, score) in enumerate(zip(valid_indices, scores)):
                result = results[pair_idx]
                original_score = float(result.get(score_key, 0))

                # Normalize cross-encoder score (sigmoid-like, 0-1 range)
                normalized_score = float(score)

                # Apply threshold filtering
                if apply_threshold and normalized_score < self.confidence_threshold:
                    continue

                reranked.append(RerankedResult(
                    id=result.get("id", result.get("chunk_id", pair_idx)),
                    content=result.get(content_key, ""),
                    original_score=original_score,
                    reranked_score=normalized_score,
                    rank_change=0,  # Will calculate after sorting
                    metadata={
                        k: v for k, v in result.items()
                        if k not in [content_key, score_key]
                    }
                ))

            # Sort by reranked score
            reranked.sort(key=lambda x: x.reranked_score, reverse=True)

            # Calculate rank changes
            original_order = {r.id: i for i, r in enumerate(reranked)}
            for new_rank, result in enumerate(reranked):
                old_rank = original_order.get(result.id, new_rank)
                result.rank_change = old_rank - new_rank

            # Return top_k results
            return reranked[:top_k]

        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            return self._fallback_rerank(results, content_key, score_key, top_k)

    def _fallback_rerank(
        self,
        results: List[Dict[str, Any]],
        content_key: str,
        score_key: str,
        top_k: int
    ) -> List[RerankedResult]:
        """Fallback when cross-encoder is not available"""
        reranked = []

        for i, result in enumerate(results[:top_k]):
            original_score = float(result.get(score_key, 0))

            reranked.append(RerankedResult(
                id=result.get("id", result.get("chunk_id", i)),
                content=result.get(content_key, ""),
                original_score=original_score,
                reranked_score=original_score,  # Same as original
                rank_change=0,
                metadata={
                    k: v for k, v in result.items()
                    if k not in [content_key, score_key]
                }
            ))

        return reranked

    def rerank_chunks(
        self,
        query: str,
        chunks: List[Any],
        top_k: Optional[int] = None
    ) -> List[Tuple[Any, float]]:
        """
        Re-rank ChunkResult objects.

        Args:
            query: Search query
            chunks: List of ChunkResult objects
            top_k: Number of results to return

        Returns:
            List of (ChunkResult, reranked_score) tuples
        """
        if not chunks:
            return []

        top_k = top_k or self.default_top_k

        # Convert to dict format for reranking
        results = []
        for chunk in chunks:
            if hasattr(chunk, 'content'):
                results.append({
                    "id": getattr(chunk, 'chunk_id', 0),
                    "content": chunk.content,
                    "rrf_score": getattr(chunk, 'rrf_score', 0),
                    "chunk_obj": chunk
                })
            elif isinstance(chunk, dict):
                results.append(chunk)

        if not results:
            return [(c, 0.0) for c in chunks[:top_k]]

        # Rerank
        reranked = self.rerank(query, results, top_k=top_k)

        # Map back to original objects
        id_to_chunk = {r.get("id"): r.get("chunk_obj") for r in results if "chunk_obj" in r}

        output = []
        for rr in reranked:
            chunk_obj = id_to_chunk.get(rr.id)
            if chunk_obj:
                output.append((chunk_obj, rr.reranked_score))

        return output

    def batch_rerank(
        self,
        queries: List[str],
        results_per_query: List[List[Dict[str, Any]]],
        top_k: Optional[int] = None
    ) -> List[List[RerankedResult]]:
        """
        Re-rank results for multiple queries efficiently.

        Args:
            queries: List of queries
            results_per_query: List of result lists, one per query
            top_k: Results per query

        Returns:
            List of reranked result lists
        """
        return [
            self.rerank(query, results, top_k=top_k)
            for query, results in zip(queries, results_per_query)
        ]


# Singleton instance
_reranker_service: Optional[RerankerService] = None


def get_reranker_service() -> RerankerService:
    """Get or create the reranker service singleton"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
