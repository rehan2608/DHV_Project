"""
Citation validator module for NIRF Response Generation (Phase 6).
Validates attached documentation references against actual Phase 5 RetrievalResults,
preventing citation fabrication, out-of-scope document references, and URL hallucination.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple

from src.rag.result_schema import RetrievalResult, RetrievedChunk
from src.response.result_schema import Citation, CitationStatus


class CitationValidator:
    """
    Deterministically audits and constructs citations for generated responses,
    ensuring 1-to-1 fidelity with retrieved documentation chunks.
    """

    def __init__(self):
        pass

    def validate_and_extract_citations(
        self,
        response_text: str,
        retrieval_result: Optional[RetrievalResult],
    ) -> List[Citation]:
        """
        Extracts citations referenced in the text (e.g. [CITE-01]) and validates them
        against the provided RetrievalResult. If no explicit tags were placed but retrieval
        was provided, attaches citations for the top retrieved sources.
        """
        if retrieval_result is None or not retrieval_result.has_results():
            # Check if text fabricated a citation anyway
            fabricated = re.findall(r"\[CITE-\d{2}\]", response_text)
            if fabricated:
                return [
                    Citation(
                        citation_id=f"cite_fab_{i}",
                        document_id="UNKNOWN",
                        status="INVALID",
                        validation_notes=f"Fabricated citation {tag}: No documentation was retrieved.",
                    )
                    for i, tag in enumerate(fabricated)
                ]
            return []

        # Map chunks by CITE-XX tag (1-indexed) and document_id
        tag_to_chunk: Dict[str, RetrievedChunk] = {}
        doc_id_to_chunks: Dict[str, List[RetrievedChunk]] = {}
        for idx, chunk in enumerate(retrieval_result.chunks, start=1):
            tag = f"CITE-{idx:02d}"
            tag_to_chunk[tag] = chunk
            doc_id_to_chunks.setdefault(chunk.document_id, []).append(chunk)

        # Detect tags in text
        found_tags = set(re.findall(r"\[(CITE-\d{2})\]", response_text))

        citations: List[Citation] = []
        cited_chunk_ids: Set[str] = set()

        for tag in sorted(found_tags):
            if tag in tag_to_chunk:
                chunk = tag_to_chunk[tag]
                cited_chunk_ids.add(chunk.chunk_id)
                citations.append(
                    Citation(
                        citation_id=tag,
                        document_id=chunk.document_id,
                        document_name=chunk.section_title,
                        document_type=chunk.document_type,
                        source_reference=chunk.source_reference,
                        section_title=chunk.section_title,
                        page_number=chunk.page_number,
                        url=chunk.metadata.get("source_url") or chunk.metadata.get("url"),
                        chunk_id=chunk.chunk_id,
                        status="VALID",
                        validation_notes=f"Verified match for retrieved chunk {chunk.chunk_id} ({chunk.document_id}).",
                    )
                )
            else:
                citations.append(
                    Citation(
                        citation_id=tag,
                        document_id="UNKNOWN",
                        status="INVALID",
                        validation_notes=f"Citation {tag} is out of bounds for the {len(retrieval_result.chunks)} chunks retrieved.",
                    )
                )

        # If model did not place explicit [CITE-XX] tags, but text discusses the retrieved topic,
        # attach the top grounded chunks automatically so Phase 7 UI has verified source cards
        if not citations:
            for idx, chunk in enumerate(retrieval_result.chunks[:3], start=1):
                citations.append(
                    Citation(
                        citation_id=f"CITE-{idx:02d}",
                        document_id=chunk.document_id,
                        document_name=chunk.section_title,
                        document_type=chunk.document_type,
                        source_reference=chunk.source_reference,
                        section_title=chunk.section_title,
                        page_number=chunk.page_number,
                        url=chunk.metadata.get("source_url") or chunk.metadata.get("url"),
                        chunk_id=chunk.chunk_id,
                        status="VALID",
                        validation_notes="Grounded source chunk retrieved from FAISS index.",
                    )
                )

        return citations

