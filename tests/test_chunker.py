"""
Unit tests for the SemanticChunker module.
"""

import pytest
from src.rag.chunker import SemanticChunker, DocumentChunk
from src.rag.document_loader import LoadedDocument, DocumentSection
from src.rag.exceptions import ChunkingError


def test_chunker_initialization():
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=100)
    assert chunker.chunk_size == 500
    assert chunker.chunk_overlap == 100

    # Overlap >= chunk_size should raise
    with pytest.raises(ChunkingError):
        SemanticChunker(chunk_size=100, chunk_overlap=100)


def test_chunk_small_section():
    chunker = SemanticChunker(chunk_size=500, chunk_overlap=100)
    section = DocumentSection(title="Short Intro", content="This is a short section about NIRF.")
    doc = LoadedDocument(
        document_id="test_doc",
        title="Test Doc",
        document_type="test",
        file_path="test.md",
        format="md",
        source_reference="Test Authority",
        description="A test document",
        sections=[section],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.document_id == "test_doc"
    assert chunk.chunk_id == "test_doc_000_000"
    assert chunk.section_title == "Short Intro"
    assert chunk.text == "This is a short section about NIRF."


def test_chunk_large_section_with_overlap():
    # Use very small chunk_size to force splitting
    chunker = SemanticChunker(chunk_size=50, chunk_overlap=10, chars_per_token=1.0)
    
    paras = [
        "Paragraph 1 contains thirty characters.",
        "Paragraph 2 contains thirty characters.",
        "Paragraph 3 contains thirty characters.",
        "Paragraph 4 contains thirty characters.",
    ]
    content = "\n\n".join(paras)
    section = DocumentSection(title="Multi Para", content=content)
    doc = LoadedDocument(
        document_id="large_doc",
        title="Large Doc",
        document_type="test",
        file_path="large.md",
        format="md",
        source_reference="Author",
        description="Large document",
        sections=[section],
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) > 1
    # Check that IDs increment properly
    assert chunks[0].chunk_id == "large_doc_000_000"
    assert chunks[1].chunk_id == "large_doc_000_001"
    # Metadata contains character length
    for c in chunks:
        assert "char_length" in c.metadata


def test_chunk_empty_section():
    chunker = SemanticChunker()
    section = DocumentSection(title="Empty", content="   \n  \n  ")
    doc = LoadedDocument(
        document_id="empty_doc",
        title="Empty Doc",
        document_type="test",
        file_path="empty.md",
        format="md",
        source_reference=None,
        description="",
        sections=[section],
    )
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 0


def test_chunk_serialization():
    chunk = DocumentChunk(
        chunk_id="c_001",
        document_id="doc_001",
        text="Sample text content",
        section_title="Title",
        page_number=1,
        source_reference="Source",
        document_type="audit",
        file_path="path/to/doc.md",
        metadata={"k": "v"},
    )
    d = chunk.to_dict()
    assert d["chunk_id"] == "c_001"
    assert d["page_number"] == 1

    restored = DocumentChunk.from_dict(d)
    assert restored.chunk_id == chunk.chunk_id
    assert restored.text == chunk.text
    assert restored.metadata == chunk.metadata

