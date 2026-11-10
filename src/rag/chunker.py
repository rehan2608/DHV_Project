"""
Semantic chunker module for the NIRF RAG system.
Splits loaded documents and sections into structured, overlapping chunks
while preserving paragraph boundaries, section context, and source traceability.
"""

import hashlib
import re
from typing import List, Dict, Any, Optional

from src.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from src.rag.document_loader import LoadedDocument, DocumentSection
from src.rag.exceptions import ChunkingError
from src.rag.text_cleaner import clean_text


class DocumentChunk:
    """
    Internal representation of a generated document chunk before vector indexing.
    """
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        section_title: Optional[str] = None,
        page_number: Optional[int] = None,
        source_reference: Optional[str] = None,
        document_type: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.section_title = section_title
        self.page_number = page_number
        self.source_reference = source_reference
        self.document_type = document_type
        self.file_path = file_path
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "source_reference": self.source_reference,
            "document_type": self.document_type,
            "file_path": self.file_path,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            text=data["text"],
            section_title=data.get("section_title"),
            page_number=data.get("page_number"),
            source_reference=data.get("source_reference"),
            document_type=data.get("document_type"),
            file_path=data.get("file_path"),
            metadata=data.get("metadata", {}),
        )


class SemanticChunker:
    """
    Token-aware and section-preserving chunker.
    Splits document sections along natural paragraph and sentence boundaries.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        chars_per_token: float = 4.0,
    ):
        if chunk_overlap >= chunk_size:
            raise ChunkingError("chunk_overlap must be strictly less than chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chars_per_token = chars_per_token
        self.max_chars = int(chunk_size * chars_per_token)
        self.overlap_chars = int(chunk_overlap * chars_per_token)

    def chunk_document(self, document: LoadedDocument) -> List[DocumentChunk]:
        """
        Chunks an entire LoadedDocument into a list of DocumentChunks.
        """
        chunks: List[DocumentChunk] = []
        chunk_counter = 0

        for sec_idx, section in enumerate(document.sections):
            section_chunks = self._chunk_section(
                section=section,
                document=document,
                sec_idx=sec_idx,
                start_counter=chunk_counter,
            )
            chunks.extend(section_chunks)
            chunk_counter += len(section_chunks)

        return chunks

    def chunk_all(self, documents: List[LoadedDocument]) -> List[DocumentChunk]:
        """
        Chunks multiple LoadedDocuments into a unified flat list of DocumentChunks.
        """
        all_chunks: List[DocumentChunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks

    def _chunk_section(
        self,
        section: DocumentSection,
        document: LoadedDocument,
        sec_idx: int,
        start_counter: int,
    ) -> List[DocumentChunk]:
        """
        Splits a single DocumentSection into one or more DocumentChunks.
        """
        content = clean_text(section.content)
        if not content:
            return []

        # If section is small enough, keep as single chunk
        if len(content) <= self.max_chars:
            chunk_id = f"{document.document_id}_{sec_idx:03d}_000"
            return [
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    text=content,
                    section_title=section.title,
                    page_number=section.page_number,
                    source_reference=document.source_reference,
                    document_type=document.document_type,
                    file_path=document.file_path,
                    metadata={
                        **section.metadata,
                        "section_index": sec_idx,
                        "char_length": len(content),
                    },
                )
            ]

        # Break larger section by paragraphs
        paragraphs = re.split(r"\n\s*\n", content)
        pieces: List[str] = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if len(p) <= self.max_chars:
                pieces.append(p)
            else:
                # Break huge paragraph by sentences
                sentences = re.split(r"(?<=[.!?])\s+", p)
                current_sent_piece = ""
                for s in sentences:
                    if len(current_sent_piece) + len(s) + 1 <= self.max_chars:
                        current_sent_piece = f"{current_sent_piece} {s}".strip()
                    else:
                        if current_sent_piece:
                            pieces.append(current_sent_piece)
                        current_sent_piece = s
                if current_sent_piece:
                    pieces.append(current_sent_piece)

        # Assemble pieces into overlapping chunks
        result_chunks: List[DocumentChunk] = []
        current_chunk_pieces: List[str] = []
        current_length = 0
        sub_idx = 0

        for piece in pieces:
            piece_len = len(piece)
            if current_length + piece_len + 2 <= self.max_chars:
                current_chunk_pieces.append(piece)
                current_length += piece_len + 2
            else:
                if current_chunk_pieces:
                    chunk_text = "\n\n".join(current_chunk_pieces).strip()
                    chunk_id = f"{document.document_id}_{sec_idx:03d}_{sub_idx:03d}"
                    result_chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=document.document_id,
                            text=chunk_text,
                            section_title=section.title,
                            page_number=section.page_number,
                            source_reference=document.source_reference,
                            document_type=document.document_type,
                            file_path=document.file_path,
                            metadata={
                                **section.metadata,
                                "section_index": sec_idx,
                                "sub_chunk_index": sub_idx,
                                "char_length": len(chunk_text),
                            },
                        )
                    )
                    sub_idx += 1

                    # Retain overlap pieces
                    overlap_pieces: List[str] = []
                    overlap_len = 0
                    for p in reversed(current_chunk_pieces):
                        if overlap_len + len(p) <= self.overlap_chars:
                            overlap_pieces.insert(0, p)
                            overlap_len += len(p)
                        else:
                            break
                    current_chunk_pieces = overlap_pieces + [piece]
                    current_length = sum(len(p) + 2 for p in current_chunk_pieces)
                else:
                    current_chunk_pieces = [piece]
                    current_length = piece_len

        # Flush final piece
        if current_chunk_pieces:
            chunk_text = "\n\n".join(current_chunk_pieces).strip()
            chunk_id = f"{document.document_id}_{sec_idx:03d}_{sub_idx:03d}"
            result_chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    text=chunk_text,
                    section_title=section.title,
                    page_number=section.page_number,
                    source_reference=document.source_reference,
                    document_type=document.document_type,
                    file_path=document.file_path,
                    metadata={
                        **section.metadata,
                        "section_index": sec_idx,
                        "sub_chunk_index": sub_idx,
                        "char_length": len(chunk_text),
                    },
                )
            )

        return result_chunks

