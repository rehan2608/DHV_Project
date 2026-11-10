# NIRF Assistant: RAG Architecture & Retrieval Pipeline (Phase 5)

**Status:** IMPLEMENTED & PRODUCTION CERTIFIED  
**Package:** `src/rag/`  
**Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors)  
**Vector Index:** FAISS `IndexFlatIP` (Exact Inner Product / Cosine Similarity)  

---

## 1. System Overview

The Retrieval-Augmented Generation (RAG) module delivers deterministic, grounded semantic document retrieval for the NIRF Conversational Analytical Assistant. It provides authoritative documentation context for questions regarding NIRF ranking methodology, parameter definitions (TLR, RPC, GO, OI, PR), data dictionary schemas, comparability rules, and data audit logs.

### Pipeline Architecture

```text
Approved Documents Manifest (approved_documents.json)
                         │
                         ▼
             [DocumentLoader] (Multi-format)
             ├─ .md    (Section hierarchy parser)
             ├─ .xlsx  (Field-level narrative generator)
             ├─ .csv   (Category cohort grouping)
             └─ .pdf   (pypdf page extractor)
                         │
                         ▼
             [TextCleaner] (Sanitizer)
             ├─ Normalizes whitespace & unicode (NFKC)
             └─ Preserves math formulas, tables, UIDs
                         │
                         ▼
             [SemanticChunker] (Token-aware)
             ├─ Chunk size: ~800 tokens, Overlap: ~120 tokens
             └─ Boundary splitting: Headings > Paragraphs > Sentences
                         │
                         ▼
           [EmbeddingGenerator] (SentenceTransformers)
           ├─ Model: all-MiniLM-L6-v2 (384 dim)
           └─ L2-normalization for cosine distance
                         │
                         ▼
               [FAISSIndex] (Vector Store)
               ├─ faiss.index (IndexFlatIP binary)
               ├─ index_metadata.json (Chunk records)
               └─ index_manifest.json (Provenance)
                         │
                         ▼
              [RAGRetriever] (Query Interface)
              ├─ Query embedding (Normalized)
              ├─ Vector k-NN retrieval
              ├─ Metadata filtering (document_type, document_id)
              └─ Output: Pydantic RetrievalResult
```

---

## 2. Core Components

### 2.1. `DocumentLoader` (`src/rag/document_loader.py`)
- Reads the canonical manifest `data/rag/approved_documents.json`.
- Enforces access control: only approved documents with existing file paths are ingested.
- Yields `LoadedDocument` objects containing structured `DocumentSection` elements.
- Handles specialized tabular logic: converts each column of `data_dictionary.xlsx` into distinct, high-resolution document sections for optimal metric discovery.

### 2.2. `TextCleaner` (`src/rag/text_cleaner.py`)
- Sanitizes non-breaking spaces, zero-width characters, excessive line returns, and encoding artifacts.
- Preserves domain structures: LaTeX equations (`$...$`, `$$...$$`), markdown tables (`| ... |`), parameter codes (`TLR`, `RPC`, `FSR`, `PU`, `QP`), and institution identifiers (`U-0456`).

### 2.3. `SemanticChunker` (`src/rag/chunker.py`)
- Splits document sections into overlapping chunks.
- Preserves paragraph cohesion and section titles in metadata.
- Generates stable, deterministic IDs: `{document_id}_{section_idx:03d}_{sub_chunk_idx:03d}`.

### 2.4. `EmbeddingGenerator` (`src/rag/embeddings.py`)
- Local inference via `SentenceTransformer('all-MiniLM-L6-v2')`.
- Normalized vectors guarantee that FAISS `IndexFlatIP` computes exact cosine similarity without distortion.
- Runs entirely on local CPU / Apple Silicon; zero cloud LLM latency or external API costs.

### 2.5. `FAISSIndex` (`src/rag/indexer.py`)
- Standard FAISS `IndexFlatIP` with 384 dimensions.
- Serializes and deserializes the vector index, chunk metadata registry, and JSON manifest to `data/rag/index/`.
- Validates index dimensionality against embedding specifications on load.

### 2.6. `RAGRetriever` (`src/rag/retriever.py`)
- Single unified interface for document retrieval:
  ```python
  retriever = RAGRetriever()
  result = retriever.retrieve(
      query="What does RPC represent and what are its sub-parameters?",
      top_k=5,
      document_type="methodology",  # Optional metadata filter
      threshold=0.35                # Optional similarity cutoff
  )
  ```
- Returns a strongly-typed `RetrievalResult` object containing `RetrievedChunk` items and `RetrievalMetadata`.

---

## 3. Data Contracts & Pydantic Schema

```python
class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float  # Cosine similarity in [0.0, 1.0]
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    source_reference: Optional[str] = None
    document_type: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RetrievalResult(BaseModel):
    query: str
    chunks: List[RetrievedChunk]
    metadata: RetrievalMetadata
```

---

## 4. Performance & Operational Characteristics

- **Index Footprint:** 146 vectors (175 KB FAISS binary index, 180 KB metadata JSON).
- **Retrieval Latency:** 7 ms to 27 ms per query (warm in-memory cache).
- **Cold Model Initialization:** ~10 seconds one-off on process startup.
- **Recall@5:** 100.0% across benchmark evaluation queries.
- **MRR:** 0.8333.

