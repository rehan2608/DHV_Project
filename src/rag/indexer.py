"""
FAISS Vector Index module for the NIRF RAG system.
Builds, persists, loads, and queries a FAISS IndexFlatIP vector index with chunk metadata.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import faiss
import numpy as np

from src.config import RAG_INDEX_DIR, EMBEDDING_DIMENSION, DEFAULT_EMBEDDING_MODEL
from src.rag.chunker import DocumentChunk
from src.rag.exceptions import VectorIndexError


class FAISSIndex:
    """
    Encapsulates FAISS IndexFlatIP management, serialization, and similarity search.
    Maintains a 1-to-1 correspondence between vector rows and DocumentChunk instances.
    """

    def __init__(
        self,
        dimension: int = EMBEDDING_DIMENSION,
        index_dir: Optional[Path] = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.dimension = dimension
        self.index_dir = index_dir or RAG_INDEX_DIR
        self.model_name = model_name
        self.index: Optional[faiss.Index] = None
        self.chunks: List[DocumentChunk] = []

    @property
    def is_built(self) -> bool:
        """Returns True if index is loaded/built and contains chunks."""
        return self.index is not None and self.index.ntotal > 0

    @property
    def total_vectors(self) -> int:
        """Returns the number of vectors in the active index."""
        return self.index.ntotal if self.index is not None else 0

    def build(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> None:
        """
        Builds a new FAISS IndexFlatIP index from chunks and their normalized embeddings.
        """
        if len(chunks) != len(embeddings):
            raise VectorIndexError(
                f"Mismatch between chunks count ({len(chunks)}) and embeddings count ({len(embeddings)})"
            )

        if len(chunks) == 0:
            raise VectorIndexError("Cannot build an empty FAISS index: 0 chunks provided.")

        if embeddings.shape[1] != self.dimension:
            raise VectorIndexError(
                f"Embedding dimension {embeddings.shape[1]} does not match index dimension {self.dimension}"
            )

        # Ensure float32 contiguous array
        vectors = np.ascontiguousarray(embeddings, dtype=np.float32)

        # IndexFlatIP computes exact inner products (cosine similarity for normalized vectors)
        index = faiss.IndexFlatIP(self.dimension)
        index.add(vectors)

        self.index = index
        self.chunks = list(chunks)

    def save(self, index_dir: Optional[Path] = None) -> None:
        """
        Persists the FAISS index, metadata registry, and manifest to disk.
        """
        if self.index is None or not self.chunks:
            raise VectorIndexError("Cannot save an unbuilt or empty index.")

        target_dir = index_dir or self.index_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        index_file = target_dir / "faiss.index"
        metadata_file = target_dir / "index_metadata.json"
        manifest_file = target_dir / "index_manifest.json"

        try:
            # 1. Write FAISS binary index
            faiss.write_index(self.index, str(index_file))

            # 2. Write Chunks metadata
            chunks_data = [c.to_dict() for c in self.chunks]
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(chunks_data, f, indent=2, ensure_ascii=False)

            # 3. Write Manifest
            doc_ids = sorted(list(set(c.document_id for c in self.chunks)))
            manifest = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model_name": self.model_name,
                "dimension": self.dimension,
                "total_chunks": len(self.chunks),
                "index_type": "IndexFlatIP",
                "document_ids": doc_ids,
            }
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

        except Exception as e:
            raise VectorIndexError(f"Failed to persist FAISS index to {target_dir}: {e}")

    def load(self, index_dir: Optional[Path] = None) -> None:
        """
        Loads the FAISS index, metadata registry, and manifest from disk.
        """
        target_dir = index_dir or self.index_dir
        index_file = target_dir / "faiss.index"
        metadata_file = target_dir / "index_metadata.json"
        manifest_file = target_dir / "index_manifest.json"

        if not index_file.exists():
            raise VectorIndexError(f"FAISS index file not found at {index_file}")
        if not metadata_file.exists():
            raise VectorIndexError(f"Index metadata file not found at {metadata_file}")

        try:
            # 1. Read FAISS index
            index = faiss.read_index(str(index_file))
            if index.d != self.dimension:
                raise VectorIndexError(
                    f"Loaded index dimension {index.d} does not match expected {self.dimension}"
                )

            # 2. Read Chunks metadata
            with open(metadata_file, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)
            chunks = [DocumentChunk.from_dict(d) for d in chunks_data]

            if index.ntotal != len(chunks):
                raise VectorIndexError(
                    f"Index size ({index.ntotal}) differs from metadata chunks count ({len(chunks)})"
                )

            # 3. Read Manifest if present
            if manifest_file.exists():
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    self.model_name = manifest.get("model_name", self.model_name)

            self.index = index
            self.chunks = chunks

        except Exception as e:
            if isinstance(e, VectorIndexError):
                raise
            raise VectorIndexError(f"Failed to load FAISS index from {target_dir}: {e}")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Searches the index with a normalized query vector.
        Returns a list of (DocumentChunk, similarity_score) tuples sorted descending by score.
        """
        if self.index is None or not self.chunks:
            raise VectorIndexError("Search failed: FAISS index is not loaded or is empty.")

        query_vec = np.ascontiguousarray(query_vector, dtype=np.float32)
        if query_vec.ndim == 1:
            query_vec = np.expand_dims(query_vec, axis=0)

        if query_vec.shape[1] != self.dimension:
            raise VectorIndexError(
                f"Query vector dimension {query_vec.shape[1]} does not match index dimension {self.dimension}"
            )

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_vec, k)

        results: List[Tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))

        return results

