"""
RAG (Retrieval-Augmented Generation) package for the NIRF Conversational Assistant.
Provides document loading, semantic chunking, dense vector embeddings, FAISS indexing,
and deterministic document retrieval with source attribution.
"""

from src.rag.exceptions import (
    RAGError,
    DocumentLoadingError,
    ChunkingError,
    EmbeddingError,
    VectorIndexError,
    RetrievalError,
)
from src.rag.result_schema import RetrievedChunk, RetrievalMetadata, RetrievalResult
from src.rag.document_loader import DocumentLoader, LoadedDocument, DocumentSection
from src.rag.chunker import SemanticChunker, DocumentChunk
from src.rag.embeddings import EmbeddingGenerator
from src.rag.indexer import FAISSIndex
from src.rag.retriever import RAGRetriever

__all__ = [
    "RAGError",
    "DocumentLoadingError",
    "ChunkingError",
    "EmbeddingError",
    "VectorIndexError",
    "RetrievalError",
    "RetrievedChunk",
    "RetrievalMetadata",
    "RetrievalResult",
    "DocumentLoader",
    "LoadedDocument",
    "DocumentSection",
    "SemanticChunker",
    "DocumentChunk",
    "EmbeddingGenerator",
    "FAISSIndex",
    "RAGRetriever",
]

