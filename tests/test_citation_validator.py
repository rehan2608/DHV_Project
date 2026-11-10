"""
Unit tests for CitationValidator module (Phase 6).
"""

from src.rag.result_schema import RetrievalResult, RetrievedChunk, RetrievalMetadata
from src.response.citation_validator import CitationValidator


def _get_mock_retrieval_result() -> RetrievalResult:
    chunk1 = RetrievedChunk(
        chunk_id="chunk_tlr",
        document_id="nirf_methodology_reference",
        text="Teaching, Learning and Resources (TLR) measures student strength and faculty.",
        score=0.88,
        section_title="TLR Definition",
        source_reference="Ministry of Education",
        page_number=3,
        metadata={"url": "https://www.nirfindia.org"},
    )
    chunk2 = RetrievedChunk(
        chunk_id="chunk_dict",
        document_id="data_dictionary",
        text="score is the composite ranking score.",
        score=0.75,
        section_title="Field: score",
        source_reference="NIRF Project Specification",
    )
    return RetrievalResult(
        query="What is TLR?",
        chunks=[chunk1, chunk2],
        metadata=RetrievalMetadata(total_candidates=100, returned_count=2, top_k=5, execution_time_ms=12.0),
    )


def test_validate_matching_citations():
    validator = CitationValidator()
    rag_res = _get_mock_retrieval_result()
    text = "According to official guidelines [CITE-01], TLR measures teaching capacity."
    citations = validator.validate_and_extract_citations(text, rag_res)

    assert len(citations) == 1
    c = citations[0]
    assert c.citation_id == "CITE-01"
    assert c.status == "VALID"
    assert c.document_id == "nirf_methodology_reference"
    assert c.page_number == 3
    assert c.url == "https://www.nirfindia.org"


def test_validate_out_of_bounds_citation():
    validator = CitationValidator()
    rag_res = _get_mock_retrieval_result()
    # Tag [CITE-99] does not exist (only 2 chunks retrieved)
    text = "As stated in [CITE-99], rankings are annual."
    citations = validator.validate_and_extract_citations(text, rag_res)

    assert len(citations) == 1
    c = citations[0]
    assert c.citation_id == "CITE-99"
    assert c.status == "INVALID"
    assert "out of bounds" in c.validation_notes


def test_validate_fabricated_citation_without_retrieval():
    validator = CitationValidator()
    text = "As demonstrated in [CITE-01], RPC measures citations."
    # No retrieval result provided
    citations = validator.validate_and_extract_citations(text, None)

    assert len(citations) == 1
    assert citations[0].status == "INVALID"
    assert "Fabricated" in citations[0].validation_notes


def test_automatic_source_attachment_when_no_explicit_tags():
    validator = CitationValidator()
    rag_res = _get_mock_retrieval_result()
    text = "TLR evaluates student strength without explicit cite tag."
    citations = validator.validate_and_extract_citations(text, rag_res)

    # Should automatically attach the retrieved chunks as valid citations
    assert len(citations) == 2
    assert citations[0].status == "VALID"
    assert citations[0].document_id == "nirf_methodology_reference"

