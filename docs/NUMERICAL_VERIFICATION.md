# NIRF Assistant: Deterministic Numerical Verification (Phase 6)

**Engine:** `src/response/verifier.py` & `src/response/claim_extractor.py`  
**Tolerance:** Display Rounding $|\Delta| \le 0.05$  
**Status Categories:** `VERIFIED`, `CONFLICTING`, `UNVERIFIED`, `NOT_APPLICABLE`  

---

## 1. Principles of Deterministic Verification

In high-stakes academic analytics, language models frequently hallucinate subtle discrepancies (e.g., swapping ranks, transposing digits, inverting direction, or describing correlation as causation). 

The NIRF Assistant enforces a **deterministic post-generation audit**:
1. No numerical claim produced by the LLM is trusted by default.
2. Every number is extracted into a structured `NumericalClaim` object.
3. Every claim is checked against the Phase 4 analytical outputs before being returned.

---

## 2. Verification Rules & Audit Logic

### Rule A: Metric Scores & Display Rounding
- **Check:** Compare claimed value to actual dataset value for the matched institution and parameter.
- **Tolerance:** A display tolerance of $\pm 0.05$ is allowed for standard rounding (e.g., actual `91.2345` vs. displayed `91.23`).
- **Outcome:** `VERIFIED` if $|\text{Claimed} - \text{Actual}| \le 0.05$; `CONFLICTING` if beyond tolerance.

### Rule B: Rank Movements & Directional Integrity
- **Calculation:** $\Delta = \text{Rank}_{\text{start}} - \text{Rank}_{\text{end}}$.
- **Sign Convention:**
  - $\Delta > 0$: Rank improvement (e.g., moving from Rank 35 to Rank 20 is $+15$).
  - $\Delta < 0$: Rank decline (e.g., moving from Rank 10 to Rank 18 is $-8$).
- **Audit:** If an institution declined by 8 ranks but the LLM states "improved by 8 ranks", the verifier flags a directional reversal and marks the claim `CONFLICTING`.

### Rule C: Prohibition of Zero-Imputation
- **Context:** In NIRF, an institution in an unranked band (e.g., 101–150) or missing a specific parameter has a `null` / `NaN` value, not zero.
- **Audit:** If actual data is `null` and the LLM reports `0` or `0.0`, the verifier flags a missing-data violation and marks `CONFLICTING`.

### Rule D: Correlation vs. Causation
- **Check:** Correlation coefficient verified against actual Pearson / Spearman result ($|\Delta| \le 0.05$).
- **Causality Ban:** Scans for causal phrasing (`causes`, `caused by`, `leads to`, `drives`, `driven by`, `results in`).
- **Outcome:** If causal language is detected, the claim is marked `CONFLICTING` ("Unsupported causal leap").

### Rule E: Cohort and Entity Counts
- **Check:** Exact matching of claimed integers against dataset sample sizes, output lengths, and category totals.

---

## 3. Real Verification Examples

### Example 1: Verified Score & Rank
- **Sentence:** *"IIT Madras achieved an RPC score of 90.74 and ranked #1 in Engineering 2025."*
- **Extraction:**
  - `metric: rpc`, `claimed: 90.74`, `institution: IIT Madras`
  - `metric: rank`, `claimed: 1`, `institution: IIT Madras`
- **Audit:** Matches `U-456` record (`rpc: 90.74`, `rank: 1.0`).
- **Status:** **`VERIFIED`**

### Example 2: Conflicting Direction
- **Sentence:** *"Decline University improved by 8 ranks between 2020 and 2025."*
- **Extraction:** `metric: rank_diff`, `claimed: +8`
- **Audit:** Actual record shows `rank_start: 10`, `rank_end: 18`, `rank_diff: -8`.
- **Status:** **`CONFLICTING`** (*"Rank direction reversed: Claimed +8 ranks but actual movement was -8 ranks."*)

### Example 3: Unverified Institution
- **Sentence:** *"Nonexistent College scored 78.4 in TLR."*
- **Extraction:** `metric: tlr`, `claimed: 78.4`
- **Audit:** Institution not found in execution result.
- **Status:** **`UNVERIFIED`**

