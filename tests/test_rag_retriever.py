"""
Integration tests for the RAGRetriever module.
"""

import pytest
from src.rag.retriever import RAGRetriever
from src.rag.result_schema import RetrievalResult
from src.rag.exceptions import RetrievalError


@pytest.fixture(scope="module")
def shared_retriever():
    retriever = RAGRetriever()
    if not retriever.is_ready():
        retriever.build_or_refresh_index()
    return retriever


def test_retriever_query_basic(shared_retriever):
    result = shared_retriever.retrieve("What does TLR mean in NIRF?", top_k=3)
    assert isinstance(result, RetrievalResult)
    assert result.has_results()
    assert len(result.chunks) <= 3
    assert result.metadata.returned_count == len(result.chunks)
    assert result.metadata.execution_time_ms > 0
    # Top chunk should have positive similarity score
    assert result.chunks[0].score > 0.3


def test_retriever_filter_by_document_type(shared_retriever):
    result = shared_retriever.retrieve(
        "NIRF parameter definitions and weights",
        top_k=3,
        document_type="methodology",
    )
    assert result.has_results()
    for chunk in result.chunks:
        assert chunk.document_type == "methodology"


def test_retriever_filter_by_document_id(shared_retriever):
    result = shared_retriever.retrieve(
        "composite score and rank",
        top_k=3,
        document_id="data_dictionary",
    )
    assert result.has_results()
    for chunk in result.chunks:
        assert chunk.document_id == "data_dictionary"


def test_retriever_threshold_filter(shared_retriever):
    # Setting an impossible threshold should return 0 chunks without error
    result = shared_retriever.retrieve(
        "What is TLR?",
        top_k=5,
        threshold=0.999,
    )
    assert len(result.chunks) == 0
    assert not result.has_results()


def test_retriever_empty_query_raises(shared_retriever):
    with pytest.raises(RetrievalError):
        shared_retriever.retrieve("")


def test_retriever_combined_text(shared_retriever):
    result = shared_retriever.retrieve("TLR formula", top_k=2)
    text = result.get_combined_text()
    assert isinstance(text, str)
    assert len(text) > 0

