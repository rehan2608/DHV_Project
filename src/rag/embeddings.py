"""
Embedding generator module for the NIRF RAG system.
Generates normalized dense vector embeddings using local Sentence Transformers models.
"""

from typing import List, Optional, Union
import numpy as np

from src.config import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSION
from src.rag.exceptions import EmbeddingError


class EmbeddingGenerator:
    """
    Manages embedding model initialization, batch inference, and vector normalization.
    Uses local Sentence Transformers with lazy model loading.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        expected_dimension: int = EMBEDDING_DIMENSION,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.expected_dimension = expected_dimension
        self.device = device
        self._model = None

    def _get_model(self):
        """Lazy loads the SentenceTransformer model on first usage."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as e:
                raise EmbeddingError(f"Failed to load embedding model '{self.model_name}': {e}")
        return self._model

    @property
    def dimension(self) -> int:
        """Returns the embedding vector dimensionality."""
        return self.expected_dimension

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embeds a single text string into a normalized 1D float32 NumPy array.
        """
        if not isinstance(text, str):
            raise EmbeddingError("Input text must be a string.")
        
        cleaned = text.strip()
        if not cleaned:
            # Return zero vector for empty strings
            return np.zeros(self.dimension, dtype=np.float32)

        try:
            model = self._get_model()
            vec = model.encode(cleaned, normalize_embeddings=True, show_progress_bar=False)
            vec = np.asarray(vec, dtype=np.float32)
            if vec.ndim == 2 and vec.shape[0] == 1:
                vec = vec[0]
            if vec.shape[0] != self.expected_dimension:
                raise EmbeddingError(
                    f"Generated embedding dimension {vec.shape[0]} does not match expected {self.expected_dimension}"
                )
            return vec
        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(f"Error generating embedding for text: {e}")

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        """
        Embeds a list of texts into a normalized 2D float32 NumPy array of shape (N, dimension).
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        sanitized_texts = [t.strip() if isinstance(t, str) else "" for t in texts]

        try:
            model = self._get_model()
            embeddings = model.encode(
                sanitized_texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=show_progress_bar,
            )
            embeddings = np.asarray(embeddings, dtype=np.float32)
            if embeddings.shape[1] != self.expected_dimension:
                raise EmbeddingError(
                    f"Generated embeddings dimension {embeddings.shape[1]} does not match expected {self.expected_dimension}"
                )
            return embeddings
        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(f"Error generating batch embeddings: {e}")

