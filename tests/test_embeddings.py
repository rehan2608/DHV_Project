"""
Unit tests for the EmbeddingGenerator module.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock

from src.rag.embeddings import EmbeddingGenerator
from src.rag.exceptions import EmbeddingError


def test_embedding_generator_dimension():
    gen = EmbeddingGenerator(expected_dimension=384)
    assert gen.dimension == 384


def test_embedding_generator_empty_text():
    gen = EmbeddingGenerator(expected_dimension=384)
    vec = gen.embed_text("")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    assert np.all(vec == 0.0)


def test_embedding_generator_empty_list():
    gen = EmbeddingGenerator(expected_dimension=384)
    matrix = gen.embed_texts([])
    assert isinstance(matrix, np.ndarray)
    assert matrix.shape == (0, 384)


def test_embedding_generator_mocked_model():
    gen = EmbeddingGenerator(expected_dimension=4)
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.5, 0.5, 0.5, 0.5]], dtype=np.float32)
    gen._model = mock_model

    vec = gen.embed_text("test query")
    assert vec.shape == (4,)
    assert np.isclose(vec[0], 0.5)
    mock_model.encode.assert_called_once()


def test_embedding_generator_dimension_mismatch_raises():
    gen = EmbeddingGenerator(expected_dimension=384)
    mock_model = MagicMock()
    # Returns dimension 128 instead of 384
    mock_model.encode.return_value = np.zeros((1, 128), dtype=np.float32)
    gen._model = mock_model

    with pytest.raises(EmbeddingError):
        gen.embed_text("test")


def test_real_embedding_generation():
    # Test with real model
    gen = EmbeddingGenerator()
    vec = gen.embed_text("National Institutional Ranking Framework")
    assert vec.shape == (384,)
    assert vec.dtype == np.float32
    # Ensure vector is L2 normalized
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0, atol=1e-3)

