import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.core.config import settings

logger = logging.getLogger("documind.embedding")

class BaseEmbeddingService(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Encodes a single text into a normalized 1D float32 numpy array."""
        pass

    @abstractmethod
    def embed_chunks(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encodes a batch of texts into a normalized 2D float32 numpy array."""
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Returns the vector dimensionality produced by the embedding model."""
        pass

class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """
    Local embedding service using HuggingFace sentence-transformers.
    Loads the model lazily and caches it in memory.
    All embeddings are L2 normalized to support cosine similarity via dot product (IndexFlatIP).
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._dimension: Optional[int] = None

    def _get_model(self):
        if self._model is None:
            logger.info(f"[EmbeddingService] Initializing local embedding model: '{self.model_name}'...")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                # Compute and cache dimension
                test_vec = self._model.encode("test", normalize_embeddings=True)
                self._dimension = int(test_vec.shape[0])
                logger.info(f"[EmbeddingService] Model '{self.model_name}' loaded successfully (dimension={self._dimension}).")
            except Exception as e:
                logger.error(f"[EmbeddingService] Failed to load embedding model '{self.model_name}': {e}", exc_info=True)
                raise RuntimeError(f"Failed to load local embedding model '{self.model_name}': {e}") from e
        return self._model

    def get_embedding_dimension(self) -> int:
        if self._dimension is None:
            self._get_model()
        return self._dimension or 384

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single string query or chunk.
        Returns a 1D float32 array normalized to unit length.
        """
        if not text or not text.strip():
            dim = self.get_embedding_dimension()
            return np.zeros(dim, dtype=np.float32)

        model = self._get_model()
        vec = model.encode(text.strip(), normalize_embeddings=True, show_progress_bar=False)
        vec = np.asarray(vec, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_chunks(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embeds a list of texts in batches.
        Returns a 2D float32 array with shape (len(texts), embedding_dim), normalized.
        """
        if not texts:
            dim = self.get_embedding_dimension()
            return np.empty((0, dim), dtype=np.float32)

        model = self._get_model()
        sanitized = [t.strip() if t and t.strip() else " " for t in texts]
        vectors = model.encode(
            sanitized,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        vectors = np.asarray(vectors, dtype=np.float32)

        # Ensure unit normalization for every row
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms
        return vectors

embedding_service = SentenceTransformerEmbeddingService()
