# NIRF Assistant: Citation & Grounding Integrity (Phase 6)

**Validator:** `src/response/citation_validator.py`  
**Registry Authority:** `data/rag/approved_documents.json`  
**Retrieval Grounding:** Phase 5 FAISS Vector Index (`data/rag/index/`)  

---

## 1. Grounding Principles & Citation Policy

To prevent hallucinations, the NIRF Assistant enforces strict grounding standards for qualitative and methodological explanations:

1. **No Unretrieved Citations:** The LLM is only permitted to cite documents that were actually retrieved in the current query's `RetrievalResult`.
2. **Deterministic Citation Tags:** Passages are presented in the prompt context labeled with indexed tags (e.g., `[CITE-01]`, `[CITE-02]`). The validator maps these tags back to exact chunk metadata.
3. **No Hallucinated URLs:** URLs are only displayed if they exist in the physical metadata registry (`comparability_rules.csv` or `approved_documents.json`).
4. **Authority Separation:** Project-internal audit documentation (`institution_identity_audit.md`, `cleaning_log.md`) is distinguished from official statutory NIRF publications (`nirf_methodology_reference.md`).

---

## 2. Citation Schema & Audit Lifecycle

```python
class Citation(BaseModel):
    citation_id: str             # e.g., "CITE-01"
    document_id: str             # e.g., "nirf_methodology_reference"
    document_name: Optional[str] # Section or document title
    document_type: Optional[str] # "methodology", "dictionary", "rules", "audit"
    source_reference: Optional[str] # "Ministry of Education (MoE), Government of India"
    section_title: Optional[str] # Section heading
    page_number: Optional[int]   # Validated page number, or None
    url: Optional[str]           # Verified external URL, or None
    chunk_id: Optional[str]      # FAISS chunk index ID
    status: CitationStatus       # "VALID", "INVALID", "UNRETRIEVED"
    validation_notes: Optional[str]
```

---

## 3. Real Retrieval & Validation Outcomes

### Benchmark 2 Example (*"What does RPC mean in NIRF, and what are its sub-parameters?"*)
- **Retrieved Chunk:**
  - `chunk_id: nirf_methodology_reference_004_000`
  - `section_title: 3.2. Research and Professional Practice (RPC) — 100 Marks`
  - `source_reference: Ministry of Education (MoE), Government of India`
- **Generated Answer Reference:**
  - *"Based on the official NIRF documentation, **RPC** stands for **Research and Professional Practice** [CITE-01]."*
- **Validation Outcome:**
  - `status: VALID`
  - `notes: "Verified match for retrieved chunk nirf_methodology_reference_004_000 (nirf_methodology_reference)."`

### Benchmark 3 Example (*"Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025 and explain what RPC measures."*)
- **Retrieved Chunk:**
  - `chunk_id: nirf_methodology_reference_004_000`
  - `document_id: nirf_methodology_reference`
- **Generated Answer Reference:**
  - *"As defined in [CITE-01], RPC evaluates publication volume (PU), citation quality (QP), patents (IPR), and sponsored projects (FPPP)."*
- **Validation Outcome:**
  - `status: VALID`
  - Fully distinguishes empirical comparison (`IIT Madras RPC: 90.74` vs. `IIT Bombay RPC: 86.81`) from official parameter methodology.

