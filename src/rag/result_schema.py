"""
Result schema module for the NIRF RAG system.
Defines strongly-typed Pydantic models for chunks, retrieval metadata, and retrieval results.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """
    Represents a single retrieved document chunk with source attribution and relevance score.
    """
    chunk_id: str = Field(..., description="Unique deterministic identifier for the chunk")
    document_id: str = Field(..., description="ID of parent document from approved registry")
    text: str = Field(..., description="Actual text content of the chunk")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    section_title: Optional[str] = Field(None, description="Section heading or structural context")
    page_number: Optional[int] = Field(None, description="Page number if applicable, or None")
    source_reference: Optional[str] = Field(None, description="Document source authority or title")
    document_type: Optional[str] = Field(None, description="Category of document (e.g. methodology, audit)")
    file_path: Optional[str] = Field(None, description="Relative path of source file")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")


class RetrievalMetadata(BaseModel):
    """
    Metadata describing the execution of a retrieval query.
    """
    total_candidates: int = Field(..., description="Total number of chunks evaluated")
    returned_count: int = Field(..., description="Number of chunks returned after filtering")
    top_k: int = Field(..., description="Requested top-k parameter")
    threshold: Optional[float] = Field(None, description="Similarity threshold filter applied if any")
    execution_time_ms: float = Field(..., description="Retrieval latency in milliseconds")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Metadata filters applied")


class RetrievalResult(BaseModel):
    """
    Encapsulates the full result of a document retrieval query.
    """
    query: str = Field(..., description="The input query string")
    chunks: List[RetrievedChunk] = Field(default_factory=list, description="Ranked list of retrieved chunks")
    metadata: RetrievalMetadata = Field(..., description="Execution and performance metadata")

    def has_results(self) -> bool:
        """Return True if at least one chunk was retrieved."""
        return len(self.chunks) > 0

    def get_combined_text(self, separator: str = "\n\n---\n\n") -> str:
        """
        Return the combined text of all retrieved chunks, separated by a delimiter.
        Useful for passing context to downstream generation models.
        """
        return separator.join([c.text for c in self.chunks])

    def to_dict(self) -> Dict[str, Any]:
        """Convert the retrieval result to a standard dictionary."""
        return self.model_dump()

