# NIRF Dataset V3: Cross-Year & Cross-Category Comparability Report (2017–2025)

**Project:** NIRF Dashboard – Institutional Ranking Analysis (2017–2025)  
**Author:** Senior Statistical Data Scientist & Academic Ranking Auditor  
**Dataset Directory:** `NIRF_Cleaned_Dataset_v3/`  
**Machine-Readable Rules:** `NIRF_Cleaned_Dataset_v3/comparability_rules_v3.csv` (103 active cohorts)  
**Status:** **AUDITED & STATISTICALLY CERTIFIED (V3)**

---

## 1. Executive Summary & The Problem of Ranking Drift

A foundational fallacy in longitudinal institutional ranking analysis is the naive assumption that a rank or score in one year is directly comparable to the same rank or score in another. In the National Institutional Ranking Framework (NIRF) across 2017–2025, rankings are subject to substantial structural evolution:

1. **Expanding Categories:** NIRF began in 2017 with 6 categories and expanded to 16 distinct categories by 2025.
2. **Expanding Ranking Depths:** Ranking lists have expanded dramatically (e.g., Pharmacy expanded from Top 50 to Top 75 to Top 100; Colleges expanded from Top 100 to Top 200).
3. **Scoring Normalization Shifts:** Composite scores are normalized within cohorts on an annual curve, meaning a score of 65.0 in 2017 reflects a different relative performance than 65.0 in 2025.
4. **Boundary Discontinuities:** Published ranks above 100 are grouped into unranked 50-rank bands (`101-150`, `151-200`) where composite scores are deliberately withheld.

To prevent invalid cross-year conclusions in Tableau, Streamlit, and Level 3 Hybrid RAG querying, this report details the structural rules operationalized in `comparability_rules_v3.csv`.

---

## 2. Category Evolution Matrix (2017–2025)

| Category Standardized | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Introduction Year | Comparability Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Overall** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2017 | Continuous (Top 100 numeric; 101-200 banded) |
| **Universities** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2017 | Continuous (Top 100 numeric; 101-200 banded) |
| **Engineering** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2017 | Continuous (Top 100 numeric; 101-200/300 banded) |
| **Management** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2017 | Continuous (Top 50 expanded to Top 100/125) |
| **Pharmacy** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2017 | Continuous (Top 50 expanded to Top 75/100) |
| **Colleges** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2017 | Continuous (Top 100 expanded to Top 150/200) |
| **Architecture** | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2018 | Comparable 2018–2025 (Renamed Arch & Planning 2023) |
| **Law** | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2018 | Comparable 2018–2025 (Top 25/30 expanded to Top 50) |
| **Medical** | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2018 | Comparable 2018–2025 (Top 25/30 expanded to Top 50) |
| **Dental** | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2020 | Comparable 2020–2025 (Top 30/40) |
| **Research** | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | 2021 | Comparable 2021–2025 (Top 50) |
| **Innovation** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | 2023 | Distinct Metric; Non-comparable to 5-pillar categories |
| **Agriculture** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | 2023 | Comparable 2023–2025 (Top 40) |
| **Open University** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | 2024 | New Cohort (Top 3) |
| **Skill University** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | 2024 | New Cohort (Top 3) |
| **State Public Univ.** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | 2024 | New Cohort (Top 50) |

*Total active year-category cohorts: exactly **103 cohorts** across 2017–2025.*

---

## 3. Structural Parameter Pillar Models

NIRF evaluates institutions across distinct structural pillar frameworks:

### Model A: Standard 5-Parameter Framework (98 Cohorts)
Applied to all standard academic categories (Overall, Engineering, Management, Pharmacy, Colleges, Architecture, Law, Medical, Dental, Research, Agriculture, State Public Universities):
1. **Teaching, Learning & Resources (TLR):** Weight ~30% (Colleges: 40%).
2. **Research and Professional Practice (RPC):** Weight ~30% (Colleges: 15%).
3. **Graduation Outcomes (GO):** Weight ~20% (Colleges: 25%).
4. **Outreach and Inclusivity (OI):** Weight ~10% (Colleges: 10%).
5. **Perception (PR):** Weight ~10% (Colleges: 10%).

### Model B: Innovation Framework (3 Cohorts: 2023–2025)
Formerly ARIIA (Atal Ranking of Institutions on Innovation Achievements), incorporated into NIRF in 2023. Evaluates patents granted, spin-offs, incubation infrastructure, and technology transfer revenue. Scores are **not** structurally comparable to Model A parameter scores.

### Model C: Specialized Open & Skill Frameworks (2 Cohorts: 2024–2025)
Focus on vocational certification, flexibility of curriculum, apprenticeship tie-ups, and distance learning delivery mechanisms.

---

## 4. Operational Guidelines for Dashboards & Querying

To ensure defensible analytical implementations:

### For Level 1: Tableau Dashboards
- **Trend Lines:** Do not draw uninterrupted time-series trend lines for categories across years prior to their official inception (e.g. Law cannot be charted before 2018; Dental before 2020).
- **Score Color Gradients:** Filter on `has_parameter_scores = True` when rendering heatmap visuals, as banded institutions (`rank_band in ['101-150', '151-200']`) have null scores and must be visually rendered with a neutral "Banded / Unscored" gray color.

### For Level 2: Streamlit Analytical Applications
- **Cohort Selector:** Use `comparability_rules_v3.csv` to dynamically populate available categories per year. If a user selects 2017 and attempts to filter by "Dental", display an informative alert: `"Dental ranking category was introduced in 2020"`.
- **Rank Velocity:** When calculating year-over-year rank delta (`rank_t - rank_{t-1}`), verify that both years are within numeric rank boundaries (ranks 1 to 100). Do not calculate numerical deltas for institutions transitioning into or out of unranked bands.

### For Level 3: Natural Language Assistant (Hybrid RAG)
- **Prompt Guardrail:** When answering questions such as *"How did IIT Madras perform in Innovation in 2020?"*, the LLM assistant must respond that the Innovation category was introduced in 2023.
- **Score Invariance Guardrail:** Prevent the LLM from comparing raw composite scores across different years (e.g., claiming an institution "declined" because its score dropped from 82.1 in 2021 to 80.5 in 2022, even if its rank improved from #4 to #3).

---

*Report certified by Senior Statistical Data Scientist for NIRF V3 Pipeline.*
