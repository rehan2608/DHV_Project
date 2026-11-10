"""
Unit tests for the FAISSIndex module.
"""

import pytest
import numpy as np
from pathlib import Path

from src.rag.chunker import DocumentChunk
from src.rag.indexer import FAISSIndex
from src.rag.exceptions import VectorIndexError


def _create_sample_chunks(n: int = 5) -> list[DocumentChunk]:
    chunks = []
    for i in range(n):
        chunks.append(
            DocumentChunk(
                chunk_id=f"doc_test_{i:03d}",
                document_id="doc_test",
                text=f"Text for chunk number {i}",
                section_title=f"Section {i}",
                metadata={"index": i},
            )
        )
    return chunks


def _create_normalized_vectors(n: int = 5, dim: int = 4) -> np.ndarray:
    raw = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    return raw / norms


def test_index_build_and_search():
    dim = 4
    index = FAISSIndex(dimension=dim)
    chunks = _create_sample_chunks(3)
    vectors = _create_normalized_vectors(3, dim)

    index.build(chunks=chunks, embeddings=vectors)
    assert index.is_built
    assert index.total_vectors == 3

    # Search with first vector
    results = index.search(vectors[0], top_k=2)
    assert len(results) == 2
    # The first result should be chunks[0] with similarity score ~ 1.0
    top_chunk, top_score = results[0]
    assert top_chunk.chunk_id == chunks[0].chunk_id
    assert np.isclose(top_score, 1.0, atol=1e-4)


def test_index_save_and_load(tmp_path):
    dim = 4
    index = FAISSIndex(dimension=dim, index_dir=tmp_path)
    chunks = _create_sample_chunks(4)
    vectors = _create_normalized_vectors(4, dim)

    index.build(chunks=chunks, embeddings=vectors)
    index.save(tmp_path)

    assert (tmp_path / "faiss.index").exists()
    assert (tmp_path / "index_metadata.json").exists()
    assert (tmp_path / "index_manifest.json").exists()

    # Load in new instance
    loaded_index = FAISSIndex(dimension=dim, index_dir=tmp_path)
    loaded_index.load(tmp_path)
    assert loaded_index.is_built
    assert loaded_index.total_vectors == 4

    # Verify search on loaded index
    results = loaded_index.search(vectors[1], top_k=1)
    assert results[0][0].chunk_id == chunks[1].chunk_id


def test_index_build_dimension_mismatch_raises():
    index = FAISSIndex(dimension=4)
    chunks = _create_sample_chunks(2)
    vectors = _create_normalized_vectors(2, dim=8)  # 8 != 4

    with pytest.raises(VectorIndexError):
        index.build(chunks=chunks, embeddings=vectors)


def test_index_search_before_build_raises():
    index = FAISSIndex(dimension=4)
    with pytest.raises(VectorIndexError):
        index.search(np.zeros((1, 4), dtype=np.float32))

