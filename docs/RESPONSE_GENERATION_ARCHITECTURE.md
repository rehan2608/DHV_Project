# NIRF Assistant: Response Generation Architecture (Phase 6)

**Package:** `src/response/`  
**Status:** IMPLEMENTED & PRODUCTION CERTIFIED  
**LLM Engine:** Gemma 4 31B Cloud (`gemma4:31b-cloud` via Ollama)  
**Verification Engine:** Deterministic Numerical Verifier & FAISS Citation Validator  
**Output Schema:** Pydantic `GeneratedResponse` (Strict JSON Serializable)

---

## 1. System Overview

The **Response Generation & Verification** subsystem transforms structured analytical execution results (Phase 4) and retrieved documentation chunks (Phase 5) into natural-language explanations.

It ensures that:
1. **The LLM never calculates numbers:** All metrics, scores, ranks, movements, sample sizes, and correlations originate from the Phase 2/4 execution output.
2. **Every numerical claim is verified:** Factual claims are parsed from the generated response and verified against the actual dataset.
3. **Every citation is audited:** Methodology claims are matched against the retrieved FAISS chunks.
4. **All data-quality caveats and comparability warnings survive:** Warnings from earlier phases are preserved in the structured output.

```text
User Question
     │
     ├─────────────────────────────────────────┐
     ▼                                         ▼
[Phase 4: ExecutionResult]         [Phase 5: RetrievalResult]
(Empirical analytical data)       (Retrieved documentation chunks)
     │                                         │
     └───────────────────┬─────────────────────┘
                         │
                         ▼
               [ContextBuilder]
               ├─ Distinguishes empirical vs. qualitative evidence
               ├─ Embeds anti-causality & missing data rules
               └─ Formats structured Markdown prompt context
                         │
                         ▼
            [Gemma LLM Text Generation]
            ├─ Model: gemma4:31b-cloud
            └─ System prompt enforces grounding & no causal claims
                         │
                         ▼
                 [Draft Response]
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
[ClaimExtractor]                [CitationValidator]
├─ Detects metric scores        ├─ Audits [CITE-XX] tags
├─ Detects rank movements       ├─ Verifies document IDs & pages
├─ Detects correlations         └─ Rejects fabricated sources
└─ Detects cohort counts
         │
         ▼
[NumericalClaimVerifier]
├─ Checks display rounding tolerance (±0.05)
├─ Validates rank direction (+ improvement vs - decline)
├─ Verifies correlation coefficients & bans causal words
├─ Enforces zero-imputation prohibition (null != 0)
└─ Output: VERIFIED / CONFLICTING / UNVERIFIED
         │
         ▼
[Regeneration & Failure Coordinator]
├─ If conflicting claims exist -> Retries with targeted feedback
├─ If persistent -> Adds cautionary limitation warning
└─ Sets ResponseStatus (SUCCESS / PARTIAL_SUCCESS / VERIFICATION_FAILED)
         │
         ▼
  [GeneratedResponse] (Strict JSON Serializable)
```

---

## 2. Core Components

### 2.1. `ContextBuilder` (`src/response/context_builder.py`)
- Compiles `ExecutionResult` and `RetrievalResult` into isolated sections.
- Classifies the interaction type into:
  - `ANALYTICAL_ONLY`
  - `DOCUMENTATION_ONLY`
  - `COMBINED`
  - `PARTIAL_EXECUTION`
  - `NO_EVIDENCE`
  - `CLARIFICATION_REQUIRED`
  - `FAILED`
- Formats tabular institution records with standard aliases (`institute_name_std`, `institution_uid`), parameters, and movement differentials.

### 2.2. `ClaimExtractor` (`src/response/claim_extractor.py`)
- Employs clause-level deterministic NLP parsing to isolate assertions.
- Prioritizes specific parameter metrics (`rpc`, `tlr`, `go`, `oi`, `perception`) over generic scoring verbs.
- Protects citation tags (`[CITE-XX]`) and calendar years (`2017–2025`) from being misinterpreted as entity counts.

### 2.3. `NumericalClaimVerifier` (`src/response/verifier.py`)
- Cross-checks extracted claims against indexed operation outputs.
- Enforces display-rounding tolerance ($|\Delta| \le 0.05$).
- Ensures mathematical sign consistency for rank changes (`rank_start - rank_end`).
- Enforces strict zero-imputation prohibitions: missing values in NIRF cannot be asserted as `0.0`.
- Audits correlation statements: flags any causal terms (`causes`, `drives`, `leads to`) as conflicting.

### 2.4. `CitationValidator` (`src/response/citation_validator.py`)
- Maps `[CITE-XX]` citation tags to retrieved documentation chunks.
- Validates canonical document IDs, section titles, page numbers, and verified URLs.
- Automatically attaches top grounded chunks if explicit tags are omitted.

### 2.5. `ResponseGenerator` (`src/response/generator.py`)
- Orchestrates the full generation and verification loop.
- Manages targeted single-retry regeneration when verifier uncovers discrepancies.
- Guarantees preservation of analytical warnings and comparability limitations.

