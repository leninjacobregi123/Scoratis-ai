"""
Embedding Service
Generates embeddings locally using sentence-transformers' all-MiniLM-L6-v2
(384 dimensions, same output size as the previous Ollama all-minilm model, so
no DB/schema migration is needed). Runs on CPU, no network call, no API key -
removes the Ollama dependency from the RAG/ingestion path entirely and avoids
adding per-call latency or cost from a cloud embedding API.
"""

import asyncio
import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dimensions, compatible with our DB schema

# Concurrent CPU-bound encode calls are pointless (they'd contend for the same
# cores), but batching multiple texts per encode() call is efficient, so batch
# embedding still goes through a single call rather than N parallel ones.
_model = None
_model_lock = asyncio.Lock()


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model


class EmbeddingService:
    """Service for generating text embeddings locally via sentence-transformers."""

    async def _get_model(self):
        if _model is None:
            async with _model_lock:
                if _model is None:
                    await asyncio.to_thread(_load_model)
        return _model

    # ===== ASYNC METHODS (Primary) =====

    async def embed_text_async(self, text: str) -> Optional[List[float]]:
        """
        Async generate embedding for a single text string.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector (384 dimensions)
        """
        if not text or not text.strip():
            return None

        results = await self.embed_texts_async([text])
        return results[0] if results else None

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        """
        Async generate embeddings for multiple texts in one batched encode() call.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        try:
            model = await self._get_model()
            embeddings = await asyncio.to_thread(
                model.encode, valid_texts, convert_to_numpy=True, show_progress_bar=False
            )
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"Local embedding failed for {len(valid_texts)} text(s): {e}")
            return []

    async def embed_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Async alias for embed_texts_async"""
        return await self.embed_texts_async(texts)

    # ===== SYNC METHODS (Backward Compatibility) =====

    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Sync generate embedding for a single text string.
        For backward compatibility - prefer embed_text_async.
        """
        return _run_sync(self.embed_text_async(text))

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Sync generate embeddings for multiple texts.
        For backward compatibility - prefer embed_texts_async.
        """
        return _run_sync(self.embed_texts_async(texts))

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Sync alias for embed_texts"""
        return self.embed_texts(texts)

    def compute_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        This is CPU-bound so remains synchronous.
        """
        if not embedding1 or not embedding2:
            return 0.0

        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0


def _run_sync(coro):
    """Run an async embedding call from sync code, whether or not a loop is already running."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
