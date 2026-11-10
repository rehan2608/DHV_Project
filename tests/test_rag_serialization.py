"""
Unit tests for RAG result schema validation and JSON serialization.
"""

import json
from src.rag.result_schema import RetrievedChunk, RetrievalMetadata, RetrievalResult


def test_retrieved_chunk_serialization():
    chunk = RetrievedChunk(
        chunk_id="chunk_01",
        document_id="doc_01",
        text="Sample retrieved text about NIRF RPC score.",
        score=0.8521,
        section_title="RPC Section",
        page_number=3,
        source_reference="NIRF 2024 Guidelines",
        document_type="methodology",
        file_path="docs/sample.md",
        metadata={"category": "Overall"},
    )

    data = chunk.model_dump()
    assert data["chunk_id"] == "chunk_01"
    assert data["score"] == 0.8521
    assert data["page_number"] == 3

    # Round trip
    reconstructed = RetrievedChunk.model_validate(data)
    assert reconstructed.chunk_id == chunk.chunk_id
    assert reconstructed.text == chunk.text
    assert reconstructed.score == chunk.score


def test_retrieval_result_json_roundtrip():
    chunk = RetrievedChunk(
        chunk_id="chunk_02",
        document_id="data_dict",
        text="TLR represents Teaching, Learning and Resources.",
        score=0.7654,
        section_title=None,
        page_number=None,
        source_reference=None,
        document_type="dictionary",
        file_path="data/dict.xlsx",
        metadata={},
    )
    metadata = RetrievalMetadata(
        total_candidates=150,
        returned_count=1,
        top_k=5,
        threshold=0.5,
        execution_time_ms=12.45,
        filters_applied={"document_type": "dictionary"},
    )
    result = RetrievalResult(
        query="What is TLR?",
        chunks=[chunk],
        metadata=metadata,
    )

    # Convert to JSON string
    json_str = json.dumps(result.to_dict())
    assert "What is TLR?" in json_str

    # Parse back
    loaded_dict = json.loads(json_str)
    reconstructed_result = RetrievalResult.model_validate(loaded_dict)
    assert reconstructed_result.query == "What is TLR?"
    assert len(reconstructed_result.chunks) == 1
    assert reconstructed_result.chunks[0].chunk_id == "chunk_02"
    assert reconstructed_result.metadata.total_candidates == 150

