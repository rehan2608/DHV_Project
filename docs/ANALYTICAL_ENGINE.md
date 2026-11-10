# NIRF Analytical Engine Documentation (Level 3)

This document provides the reference specification, function signatures, input arguments, calculation methodologies, missing-value behaviors, comparability guardrails, and return schemas for the ten core analytical functions in `src/analytics/`.

The analytical engine is **deterministic, grounded in the canonical dataset, and strictly independent of the LLM**. The LLM / query router formulates query arguments, and this engine computes mathematical truth using Pandas, NumPy, and SciPy.

---

## Central Facade

All functions are available via the singleton facade:
```python
from src.analytics.engine import get_analytics_engine
engine = get_analytics_engine()
```
or by direct import from `src.analytics`:
```python
from src.analytics import (
    get_institution_trend,
    get_rank_movement,
    get_category_performance,
    get_geographic_analysis,
    get_parameter_correlation,
    get_parameter_relationship,
    get_multidimensional_performance,
    get_score_distribution,
    get_rank_transitions,
    get_outlier_analysis,
)
```

---

## Function 1: Institution Trend Analysis (`get_institution_trend`)

- **Module**: `src.analytics.trends`
- **Purpose**: Tracks an institution's historical trajectory over time, capturing rank, score, and individual parameter movements without imputing missing years.
- **Arguments**:
  - `institution_id_or_name` (`str`): Standardized `institution_uid`, raw ID (`institute_id`), or institution name / acronym (e.g. "U-456", "IIT Madras").
  - `category` (`str`): Target discipline (e.g. "Engineering", "Overall").
  - `start_year` (`int`, default `2017`): Baseline edition.
  - `end_year` (`int`, default `2025`): Ending edition.
  - `parameters` (`Optional[List[str]]`): Specific parameter columns to track (e.g. `["tlr", "rpc"]`). Defaults to available cohort parameters.
- **Calculation Methodology**:
  - Longitudinal chronological slice across editions.
  - `overall_rank_improvement = start_year_rank - end_year_rank` (Positive = gain, Negative = decline).
  - Validates endpoints: if either start or end year rank is missing, rank improvement returns `None` with an informative warning.
- **Missing-Value Behavior**:
  - Missing years within the selected span are retained as explicit gaps with `is_observed=False`, `rank=None`, `score=None`. Missing values are never filled with zero or interpolated.
- **Comparability Guardrails**:
  - Validates `valid_comparison_start_year` (e.g. Research Institutions only started in 2021).
  - Warns if cohort depth expanded over the selected period.
- **Example Return**:
```json
{
  "success": true,
  "institution_uid": "U-456",
  "institute_name_std": "Indian Institute of Technology Madras",
  "category": "Engineering",
  "start_year": 2020,
  "end_year": 2025,
  "rank_improvement": 0,
  "best_rank": 1,
  "worst_rank": 1,
  "average_score": 89.69,
  "chronological_trajectory": [
    {"year": 2020, "is_observed": true, "rank": 1, "score": 89.93, "parameters": {"tlr": 95.42, "rpc": 94.64}},
    {"year": 2025, "is_observed": true, "rank": 1, "score": 90.04, "parameters": {"tlr": 95.77, "rpc": 96.18}}
  ]
}
```

---

## Function 2: Rank Movement Analysis (`get_rank_movement`)

- **Module**: `src.analytics.rankings`
- **Purpose**: Identifies institutions that improved or declined the most between two ranking editions.
- **Arguments**:
  - `category` (`str`): Standardized category (e.g. "Engineering").
  - `start_year` (`int`): Starting assessment edition (e.g. 2020).
  - `end_year` (`int`): Ending assessment edition (e.g. 2025).
  - `state` (`Optional[str]`): Optional state filter (e.g. "Karnataka").
  - `top_n` (`int`, default `10`): Max number of gainers/decliners to return.
  - `movement_type` (`str`, default `"both"`): `"both"`, `"improvement"`, or `"decline"`.
- **Calculation Methodology**:
  - `rank_improvement = start_year_rank - end_year_rank`.
  - Positive value indicates ranking improvement (e.g. Rank 50 to Rank 20 = `+30`).
  - Negative value indicates ranking decline (e.g. Rank 10 to Rank 35 = `-25`).
- **Missing-Value Behavior**:
  - Both endpoints must possess valid non-null numerical ranks.
  - Tracks cohort turnover: institutions that exited or newly entered the cohort are explicitly counted in `metadata["missing_data_info"]` rather than assigned rank 0.
- **Comparability Guardrails**:
  - Rejects comparisons across incompatible categories or unintroduced years.
  - Emits caution when cohort depth expanded (e.g. Management Top 50 to Top 100).

---

## Function 3: Category Performance Analysis (`get_category_performance`)

- **Module**: `src.analytics.performance`
- **Purpose**: Summarizes institutional performance within a category cohort and edition.
- **Arguments**:
  - `category` (`str`): Target discipline.
  - `year` (`int`): Edition year.
  - `state` (`Optional[str]`): State filter.
  - `top_n` (`Optional[int]`): Truncate ranked table to top N records.
- **Calculation Methodology**:
  - Parametric moments: mean, sample standard deviation (`ddof=1`), min, max.
  - Non-parametric summaries: median.
- **Missing-Value & Schema Behavior**:
  - For Rank-Only categories (e.g. Innovation, SDG, Skill University, Open University), composite scores are omitted in official NIRF publications. `scores_available` is set to `False` and score statistics are cleanly omitted (`None`).
  - Respects category parameters: standard 5 parameters for standard domains; 3 research parameters for Research Institutions.

---

## Function 4: Geographic Analysis (`get_geographic_analysis`)

- **Module**: `src.analytics.geography`
- **Purpose**: Evaluates spatial distribution, state-level institutional density, and zone breakdowns.
- **Arguments**:
  - `category` (`Optional[str]`): Discipline filter (if `None`, aggregates across all categories).
  - `year` (`Optional[int]`, default `2025`): Edition year.
  - `states` (`Optional[List[str]]`): Specific states to compare head-to-head.
  - `multi_year_trend` (`bool`, default `False`): Computes longitudinal state representation pivots across 2017–2025.
- **Counting Unit Rule**:
  - Respects institutional identity: counts unique `institution_uid` per state/cohort to avoid multi-counting campus duplicates.
- **Features**:
  - Top-tier counts: institutions in Top 10, Top 50, Top 100 per state.
  - State-level average and median composite scores.
  - Dedicated head-to-head comparison object for multiple requested states.

---

## Function 5: Parameter Correlation Analysis (`get_parameter_correlation`)

- **Module**: `src.analytics.correlations`
- **Purpose**: Calculates pairwise Pearson and Spearman correlation matrices across NIRF parameters.
- **Arguments**:
  - `category` (`str`): Discipline.
  - `year` (`int`): Edition.
  - `parameters` (`Optional[List[str]]`): Parameters to evaluate.
  - `method` (`str`, default `"both"`): `"pearson"`, `"spearman"`, or `"both"`.
- **Calculation Methodology**:
  - Uses `scipy.stats.pearsonr` and `scipy.stats.spearmanr`.
  - Enforces pairwise complete observations (drops nulls pairwise without zero-imputation).
  - Reports sample size $N$ and two-tailed p-values for every pair.
  - Surfaces strongest positive and strongest negative relationships.
  - Embeds explicit non-causality disclaimer.

---

## Function 6: Parameter Relationship Analysis (`get_parameter_relationship`)

- **Module**: `src.analytics.correlations`
- **Purpose**: Analyzes the bivariate relationship and linear regression between two parameters (e.g. RPC vs TLR).
- **Arguments**:
  - `category` (`str`): Discipline.
  - `year` (`int`): Edition.
  - `param_x` (`str`): Independent parameter.
  - `param_y` (`str`): Dependent parameter.
- **Calculation Methodology**:
  - Ordinary Least Squares regression via `scipy.stats.linregress`: slope, intercept, $R^2$, p-value, standard error.
  - Quadrant classification based on cohort medians: `high_x_low_y`, `low_x_high_y`, `high_x_high_y`, `low_x_low_y`.
  - Provides Plotly-ready coordinates: institution scatter points and regression trendline segment.

---

## Function 7: Multidimensional Performance Analysis (`get_multidimensional_performance`)

- **Module**: `src.analytics.performance`
- **Purpose**: Compares institutions across multiple parameters, identifying parameter balance and domain skews.
- **Arguments**:
  - `category` (`str`): Discipline.
  - `year` (`int`): Edition.
  - `institution_uids` (`Optional[List[str]]`): Target UIDs.
  - `institution_names` (`Optional[List[str]]`): Target names (supports acronym expansion like "IIT Bombay").
  - `parameters` (`Optional[List[str]]`): Parameter subset.
  - `top_n` (`int`, default `10`): Fallback top N institutions.
- **Calculation Methodology**:
  - Relative percentile rank for each parameter within the entire cohort via `scipy.stats.percentileofscore`.
  - Research vs Teaching gap: `rpc - tlr`.
  - Teaching vs Perception gap: `tlr - perception`.
  - Identifies strongest and weakest parameter per institution.

---

## Function 8: Score and Parameter Distribution Analysis (`get_score_distribution`)

- **Module**: `src.analytics.distributions`
- **Purpose**: Computes comprehensive distributional properties of scores or parameters.
- **Arguments**:
  - `category` (`str`): Discipline.
  - `year` (`int`): Edition.
  - `metric` (`str`, default `"score"`): Target numerical measure.
  - `state` (`Optional[str]`): Optional state filter.
  - `bins_count` (`int`, default `10`): Number of histogram bins.
- **Calculation Methodology**:
  - Moments: mean, sample standard deviation (`ddof=1`), sample variance, skewness, kurtosis.
  - Quantiles: min, 10th percentile, Q1 (25th percentile), median (50th percentile), Q3 (75th percentile), 90th percentile, max.
  - Dispersion: $IQR = Q3 - Q1$.
  - Discretized histogram bins with bin edges, frequencies, and percentages.
- **Comparability Guardrail**:
  - Blocks requests for composite scores in Rank-Only cohorts.

---

## Function 9: Rank Transition Analysis (`get_rank_transitions`)

- **Module**: `src.analytics.transitions`
- **Purpose**: Tracks institutional mobility across ordinal rank tiers between two editions.
- **Arguments**:
  - `category` (`str`): Discipline.
  - `start_year` (`int`): Starting edition.
  - `end_year` (`int`): Ending edition.
  - `custom_bands` (`Optional[List[Tuple[str, int, int]]]`): Configurable rank tiers. Defaults to:
    - Top 10 (1–10)
    - 11–25 (11–25)
    - 26–50 (26–50)
    - 51–100 (51–100)
    - Below 100 (101+)
    - Unranked / Absent
- **Calculation Methodology**:
  - Markovian transition matrix mapping each start band to each end band.
  - Mobility classifications: Upward Transition, Retained Band, Downward Transition, Cohort Exit, New Entrant.
  - Roster tracking: institutions entering/leaving Top 10 and entering/leaving Top 50.

---

## Function 10: Outlier and Volatility Analysis (`get_outlier_analysis`)

- **Module**: `src.analytics.outliers`
- **Purpose**: Identifies empirical statistical outliers, parameter divergence, and multi-year rank volatility.
- **Arguments**:
  - `category` (`str`): Discipline.
  - `year` (`int`): Target edition.
  - `metric` (`Optional[str]`, default `"score"`): Target measure.
  - `method` (`str`, default `"iqr"`): `"iqr"` (Tukey's fences) or `"z_score"`.
  - `threshold` (`float`, default `1.5`): Outlier multiplier ($1.5 \times IQR$ or $|z| \ge 2.5$).
  - `lookback_years` (`Optional[List[int]]`): Multi-year window for longitudinal rank volatility (standard deviation of rank).
- **Calculation Methodology**:
  - Metric outliers: flags observations exceeding empirical thresholds.
  - Parameter divergence: detects extreme $(RPC - TLR)$ divergence where research is disproportionately higher than teaching.
  - Rank volatility: standard deviation of numeric ranks across editions for institutions observed in multiple years.
  - Explicit disclaimer: Outliers reflect empirical extremity, not data errors.

