"""
Exceptions module for the NIRF RAG system.
Defines strongly-typed exceptions for document loading, chunking, embedding, indexing, and retrieval.
"""

class RAGError(Exception):
    """Base exception for all RAG-related errors."""
    pass


class DocumentLoadingError(RAGError):
    """Raised when an approved document cannot be loaded or parsed."""
    pass


class ChunkingError(RAGError):
    """Raised when text splitting or semantic chunking fails."""
    pass


class EmbeddingError(RAGError):
    """Raised when embedding model fails to initialize, load, or generate vectors."""
    pass


class VectorIndexError(RAGError):
    """Raised when FAISS vector index creation, persistence, loading, or query fails."""
    pass


class RetrievalError(RAGError):
    """Raised when document retrieval fails or invalid retrieval parameters are supplied."""
    pass

