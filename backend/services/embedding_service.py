"""
Embedding Service (Async)
Generates embeddings using Ollama's all-minilm model (384 dimensions)
Fully async implementation with parallel batch processing for better performance.
"""

import logging
import asyncio
import aiohttp
from typing import List, Optional
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

# Ollama embedding endpoint
OLLAMA_EMBED_URL = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
OLLAMA_EMBED_MODEL = "all-minilm"  # 384 dimensions, compatible with our DB schema

# Connection pool settings for better performance
CONCURRENT_EMBEDDINGS = 10  # Max parallel embedding requests


class EmbeddingService:
    """Async service for generating text embeddings using Ollama"""

    def __init__(self):
        self._ollama_available = None
        self._semaphore = asyncio.Semaphore(CONCURRENT_EMBEDDINGS)

    async def _check_ollama_async(self) -> bool:
        """Async check if Ollama is available"""
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{settings.OLLAMA_BASE_URL}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m['name'] for m in data.get('models', [])]
                        if any(OLLAMA_EMBED_MODEL in m for m in models):
                            self._ollama_available = True
                            logger.info(f"Ollama embedding model '{OLLAMA_EMBED_MODEL}' available")
                        else:
                            logger.warning(f"Ollama model '{OLLAMA_EMBED_MODEL}' not found. Available: {models}")
                            self._ollama_available = False
                    else:
                        self._ollama_available = False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            self._ollama_available = False

        return self._ollama_available

    async def _get_ollama_embedding_async(self, text: str) -> Optional[List[float]]:
        """Async get embedding from Ollama with semaphore for rate limiting"""
        async with self._semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=30, connect=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        OLLAMA_EMBED_URL,
                        json={"model": OLLAMA_EMBED_MODEL, "prompt": text}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get("embedding")
                        else:
                            text_preview = text[:50] + "..." if len(text) > 50 else text
                            logger.error(f"Ollama embedding failed: {resp.status} for '{text_preview}'")
                            return None
            except asyncio.TimeoutError:
                logger.error(f"Ollama embedding timeout for text: {text[:50]}...")
                return None
            except Exception as e:
                logger.error(f"Ollama embedding request failed: {e}")
                return None

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

        if not await self._check_ollama_async():
            logger.error("Embedding service unavailable - Ollama not running")
            return None

        return await self._get_ollama_embedding_async(text.strip())

    async def embed_texts_async(self, texts: List[str]) -> List[List[float]]:
        """
        Async generate embeddings for multiple texts with PARALLEL processing.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        if not await self._check_ollama_async():
            logger.error("Embedding service unavailable - Ollama not running")
            return []

        # Process all texts in PARALLEL using asyncio.gather
        logger.info(f"Generating {len(valid_texts)} embeddings in parallel...")

        tasks = [self._get_ollama_embedding_async(text) for text in valid_texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful embeddings
        embeddings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Embedding failed for text {i}: {result}")
                # Continue with other embeddings instead of failing completely
                embeddings.append(None)
            elif result is None:
                embeddings.append(None)
            else:
                embeddings.append(result)

        # Filter out None values but maintain order
        successful = [e for e in embeddings if e is not None]

        if len(successful) < len(valid_texts):
            logger.warning(f"Only {len(successful)}/{len(valid_texts)} embeddings succeeded")

        return successful

    async def embed_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Async alias for embed_texts_async"""
        return await self.embed_texts_async(texts)

    # ===== SYNC METHODS (Backward Compatibility) =====

    def _check_ollama(self) -> bool:
        """Sync check if Ollama is available (for backward compatibility)"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create new loop in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._check_ollama_async())
                    return future.result()
            else:
                return loop.run_until_complete(self._check_ollama_async())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._check_ollama_async())

    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Sync generate embedding for a single text string.
        For backward compatibility - prefer embed_text_async.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context - use thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.embed_text_async(text))
                    return future.result()
            else:
                return loop.run_until_complete(self.embed_text_async(text))
        except RuntimeError:
            return asyncio.run(self.embed_text_async(text))

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Sync generate embeddings for multiple texts.
        For backward compatibility - prefer embed_texts_async.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.embed_texts_async(texts))
                    return future.result()
            else:
                return loop.run_until_complete(self.embed_texts_async(texts))
        except RuntimeError:
            return asyncio.run(self.embed_texts_async(texts))

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


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
