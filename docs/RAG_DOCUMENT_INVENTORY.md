# NIRF Assistant: Approved Document Inventory & Ingestion Registry (Phase 5)

**Status:** AUDITED & OPERATIONAL  
**Embedding Engine:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors)  
**Vector Store:** FAISS `IndexFlatIP` (Cosine Similarity)  
**Catalog Manifest:** `data/rag/approved_documents.json`  
**Index Artifacts:** `data/rag/index/faiss.index`, `data/rag/index/index_metadata.json`, `data/rag/index/index_manifest.json`

---

## 1. Document Inventory & Approved Registry

The NIRF RAG system operates strictly under an **Approved Document Policy**. Unregistered or unverified sources cannot be ingested or retrieved. The table below catalogs all 9 approved documents currently indexed:

| Document ID | Title | Format | Document Type | Source Reference / Authority | Chunks Indexed | Primary Content / Scope |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| `nirf_methodology_reference` | NIRF Official Methodology & Parameter Reference | `.md` | `methodology` | Ministry of Education (MoE), Government of India | 21 | Core ranking parameters (TLR, RPC, GO, OI, PR), sub-parameters, formulas, weightage matrices, Research category schemas. |
| `data_dictionary` | NIRF Dataset Data Dictionary | `.xlsx` | `dictionary` | NIRF Dashboard Project V3 Dataset Specification | 41 | Detailed field definitions for all 40 columns in the cleaned master dataset, Tableau aliases, roles, valid ranges, and null interpretations. |
| `comparability_report` | NIRF Cross-Year & Cross-Category Comparability Report | `.md` | `methodology` | Senior Statistical Data Scientist & Academic Ranking Auditor | 11 | Longitudinal analysis of ranking drift, expanding categories, cohort depth expansions, and cross-year comparability rules. |
| `comparability_rules` | NIRF Longitudinal Comparability Cohort Rules | `.csv` | `rules` | NIRF Cleaned Dataset V3 Comparability Registry | 18 | Tabular registry of 103 active cohorts specifying metric schemas (Standard 5 vs Research Specific vs Rank Only), rank cohorts, and status. |
| `institution_identity_audit` | NIRF Institution Identity & UID Resolution Audit | `.md` | `audit` | Data Engineering & Institutional Audit Team | 11 | Statutory acts, AISHE codes, DCS IDs, and resolution of historical UID mapping anomalies across 23 higher education institutions. |
| `final_validation_report` | NIRF Dataset Final Independent Validation Audit | `.md` | `audit` | Independent Data Quality Auditor | 13 | 16-point comprehensive data audit certifying dataset integrity, row count (6,980 rows × 40 columns), primary keys, and data hygiene. |
| `geography_audit` | NIRF Geographic Harmonization & Location Audit | `.md` | `audit` | Geographic Data Cleaning Audit | 9 | Audit of 36 Indian States and Union Territories, city spellings, municipal boundaries, and campus location imputation standards. |
| `documentation_correction_log` | NIRF Documentation Discrepancy & Correction Log | `.md` | `audit` | Documentation Audit Team | 9 | Log of discrepancies identified between published NIRF summary narratives and underlying dataset tables, with audited resolutions. |
| `cleaning_log` | NIRF Data Cleaning Pipeline & Transformation Log | `.md` | `audit` | Data Pipeline Engineering Team | 13 | Step-by-step transformation and imputation record documenting the exact cleaning pipeline applied from raw data to V3 master dataset. |
| **TOTAL** | **9 Approved Documents** | — | — | — | **146** | **Full Grounding Coverage** |

---

## 2. Ingestion & Preprocessing Policies

1. **Deterministic Indexing:**
   - Every document chunk receives a deterministic, repeatable ID: `{document_id}_{section_idx:03d}_{sub_chunk_idx:03d}`.
   - Vector indexing produces bitwise identical embeddings and rankings across multiple index rebuilds.
2. **Structure Preservation:**
   - Markdown documents are segmented along heading hierarchies (`#`, `##`, `###`), preserving section titles and parent context.
   - Tabular documents (`data_dictionary.xlsx`) are rendered into structured key-value narratives with field-level resolution, allowing fine-grained semantic retrieval for individual columns and metrics.
   - Longitudinal CSV registries (`comparability_rules.csv`) are grouped by academic category to retain cross-year temporal continuity.
3. **Traceability & Attribution:**
   - Every chunk stores source references, relative file paths, document types, and section titles.
   - No citation, page number, or source authority is ever hallucinated or synthesized.

