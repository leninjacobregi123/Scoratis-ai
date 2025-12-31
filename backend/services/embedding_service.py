"""
Embedding Service
Generates embeddings using sentence-transformers (local, no API calls)
"""

import logging
from typing import List, Optional
from functools import lru_cache
import numpy as np

logger = logging.getLogger(__name__)

# Lazy load to avoid slow startup
_model = None
_model_failed = False


def get_model():
    """Lazy load the embedding model"""
    global _model, _model_failed
    if _model_failed:
        return None
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            from config import settings

            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            # Use CPU for embeddings to avoid conflicts with Ollama using GPU
            _model = SentenceTransformer(settings.EMBEDDING_MODEL, device='cpu')
            logger.info("Embedding model loaded successfully on CPU")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}. Embeddings disabled.")
            _model_failed = True
            return None
    return _model


class EmbeddingService:
    """Service for generating text embeddings"""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy-load the model on first access"""
        if self._model is None:
            self._model = get_model()
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            return None

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        try:
            embeddings = self.model.encode(valid_texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return []

    def compute_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Cosine similarity
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
