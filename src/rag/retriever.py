"""
Retriever module for the NIRF RAG system.
Coordinates query embedding, vector search, metadata filtering, thresholding,
and standardized RetrievalResult generation.
"""

from pathlib import Path
import time
from typing import List, Dict, Any, Optional

from src.config import RAG_INDEX_DIR, DEFAULT_RETRIEVAL_TOP_K
from src.rag.chunker import SemanticChunker
from src.rag.document_loader import DocumentLoader
from src.rag.embeddings import EmbeddingGenerator
from src.rag.exceptions import RetrievalError
from src.rag.indexer import FAISSIndex
from src.rag.result_schema import RetrievedChunk, RetrievalMetadata, RetrievalResult


class RAGRetriever:
    """
    Primary interface for semantic document retrieval against approved NIRF documentation.
    """

    def __init__(
        self,
        index: Optional[FAISSIndex] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        index_dir: Optional[Path] = None,
        auto_load: bool = True,
    ):
        self.index_dir = index_dir or RAG_INDEX_DIR
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.index = index or FAISSIndex(
            dimension=self.embedding_generator.dimension,
            index_dir=self.index_dir,
            model_name=self.embedding_generator.model_name,
        )

        if auto_load and not self.index.is_built:
            if (self.index_dir / "faiss.index").exists():
                self.index.load(self.index_dir)

    def is_ready(self) -> bool:
        """Returns True if the index is loaded and ready for queries."""
        return self.index.is_built

    def build_or_refresh_index(
        self,
        approved_docs_path: Optional[Path] = None,
        force_rebuild: bool = False,
    ) -> int:
        """
        Loads all approved documents, chunks them, computes embeddings,
        builds the FAISS index, and persists everything to disk.
        """
        if self.index.is_built and not force_rebuild:
            return self.index.total_vectors

        loader = DocumentLoader(approved_documents_path=approved_docs_path)
        documents = loader.load_all_approved_documents()

        chunker = SemanticChunker()
        chunks = chunker.chunk_all(documents)

        texts = [c.text for c in chunks]
        embeddings = self.embedding_generator.embed_texts(texts, show_progress_bar=False)

        self.index.build(chunks=chunks, embeddings=embeddings)
        self.index.save(self.index_dir)

        return self.index.total_vectors

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_RETRIEVAL_TOP_K,
        document_type: Optional[str] = None,
        document_id: Optional[str] = None,
        threshold: Optional[float] = None,
        **custom_filters: Any,
    ) -> RetrievalResult:
        """
        Performs semantic retrieval for a natural-language query.
        Applies optional metadata filters and similarity score thresholds.
        """
        start_time = time.perf_counter()

        if not isinstance(query, str) or not query.strip():
            raise RetrievalError("Query must be a non-empty string.")

        if not self.index.is_built:
            # Try to build/load if index files exist, else raise
            if (self.index_dir / "faiss.index").exists():
                self.index.load(self.index_dir)
            else:
                raise RetrievalError(
                    "FAISS index is not built. Call build_or_refresh_index() before retrieving."
                )

        if top_k <= 0:
            raise RetrievalError("top_k must be a positive integer.")

        # Embed user query
        query_vec = self.embedding_generator.embed_text(query)

        # Retrieve candidates with oversampling if filters are specified
        search_k = min(self.index.total_vectors, max(top_k * 4, 20)) if (document_type or document_id or custom_filters) else min(top_k, self.index.total_vectors)
        candidate_results = self.index.search(query_vec, top_k=search_k)

        # Filter candidates
        filtered_chunks: List[RetrievedChunk] = []
        filters_applied = {}
        if document_type:
            filters_applied["document_type"] = document_type
        if document_id:
            filters_applied["document_id"] = document_id
        if custom_filters:
            filters_applied.update(custom_filters)

        for chunk, score in candidate_results:
            # Threshold check
            if threshold is not None and score < threshold:
                continue

            # Document type check
            if document_type and chunk.document_type != document_type:
                continue

            # Document ID check
            if document_id and chunk.document_id != document_id:
                continue

            # Custom filters check
            match = True
            for k, v in custom_filters.items():
                if chunk.metadata.get(k) != v:
                    match = False
                    break
            if not match:
                continue

            retrieved = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                score=round(score, 4),
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                source_reference=chunk.source_reference,
                document_type=chunk.document_type,
                file_path=chunk.file_path,
                metadata=chunk.metadata,
            )
            filtered_chunks.append(retrieved)

            if len(filtered_chunks) >= top_k:
                break

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = RetrievalMetadata(
            total_candidates=self.index.total_vectors,
            returned_count=len(filtered_chunks),
            top_k=top_k,
            threshold=threshold,
            execution_time_ms=round(elapsed_ms, 2),
            filters_applied=filters_applied,
        )

        return RetrievalResult(
            query=query,
            chunks=filtered_chunks,
            metadata=metadata,
        )

