# NIRF Query Execution Engine Documentation (Phase 4)

This document details the architectural design, routing mechanisms, argument mapping, dependency scheduling, result schemas, and serialization rules for the Phase 4 Query Execution Engine.

---

## 1. Execution Pipeline Architecture

```text
       Validated QueryPlan (from Phase 3)
                      │
                      ▼
            [1. Mandatory Revalidation]
            ├── QueryValidator.validate(plan)
            └── Halts immediately if INVALID, UNSUPPORTED,
                or CLARIFICATION_REQUIRED
                      │
                      ▼
          [2. Dependency Graph Resolution]
          ├── Validates unique operation IDs
          ├── Detects circular dependencies (Kahn's DAG Algorithm)
          └── Computes topological execution order
                      │
                      ▼
          [3. Sequential Operation Execution]
          ┌──────────────────────────────────────────────┐
          │ For each operation in topological order:     │
          │   1. Check if predecessor succeeded          │
          │      (if failed -> SKIPPED_DEPENDENCY_FAILED)│
          │   2. Extract outputs from predecessor        │
          │      (e.g. top 10 institutions -> UIDs)      │
          │   3. QueryRouter: allowlist resolution       │
          │   4. ArgumentMapper: explicit kwargs mapping │
          │   5. OperationRunner: invoke Phase 2 callable│
          │   6. Measure latency and isolate exceptions  │
          └──────────────────────────────────────────────┘
                      │
                      ▼
          [4. Result Packaging & Serialization]
          ├── Builds OperationResult & ExecutionMetadata
          ├── Determines overall status: SUCCESS / PARTIAL_SUCCESS / FAILED
          └── Serializes strictly to JSON (cleaning NaNs, Infs, DataFrames)
                      │
                      ▼
             ExecutionResult (Structured Object)
```

---

## 2. Public Interface: `QueryExecutor`

The execution layer provides a simple, unified public entry point:

```python
from src.execution import get_query_executor

executor = get_query_executor()
result = executor.execute(query_plan)
```

The method accepts either an instantiated `QueryPlan` or a raw dictionary matching the schema.

---

## 3. Query Router & Allowlist

The `QueryRouter` resolves analytical function names to callable functions on `NIRFAnalyticsEngine` using an immutable allowlist. Dynamic module loading, `eval()`, `exec()`, or LLM reflection are strictly prohibited.

### Allowlist Mapping:

| Function Identifier | Phase 2 Engine Target | Primary Analytical Responsibility |
|---|---|---|
| `get_institution_trend` | `engine.get_institution_trend` | Multi-year trajectory tracking for single institution. |
| `get_rank_movement` | `engine.get_rank_movement` | Rank improvement/decline (`start_rank - end_rank`). |
| `get_category_performance` | `engine.get_category_performance` | Cohort performance summary and ranked table. |
| `get_geographic_analysis` | `engine.get_geographic_analysis` | State institutional density and comparative metrics. |
| `get_parameter_correlation` | `engine.get_parameter_correlation` | Pearson and Spearman correlation matrices. |
| `get_parameter_relationship` | `engine.get_parameter_relationship` | Bivariate linear regression, trendlines, quadrants. |
| `get_multidimensional_performance` | `engine.get_multidimensional_performance` | Multi-parameter profiles and research-teaching gaps. |
| `get_score_distribution` | `engine.get_score_distribution` | Central tendency, dispersion, quartiles, and histogram bins. |
| `get_rank_transitions` | `engine.get_rank_transitions` | Mobility matrix across ordinal ranking tiers. |
| `get_outlier_analysis` | `engine.get_outlier_analysis` | Tukey IQR / Z-score outliers and domain divergence. |

---

## 4. Argument Mapper

The `ArgumentMapper` translates the `AnalyticalOperation` schema into exact, typed keyword arguments for Phase 2 functions.

### Signature Mapping Matrix:

| Analytical Function | Required Arguments | Optional Arguments | Mapping Logic |
|---|---|---|---|
| `get_institution_trend` | `institution_id_or_name`, `category` | `start_year`, `end_year`, `parameters` | Resolves target from `institution_uids[0]` or `institution_names[0]`. Defaults start=2017, end=2025. |
| `get_rank_movement` | `category`, `start_year`, `end_year` | `state`, `top_n`, `movement_type` | Takes `states[0]`, defaults `top_n=10`, `movement_type="both"`. |
| `get_category_performance` | `category`, `year` | `state`, `top_n` | Takes `states[0]`. |
| `get_geographic_analysis` | *(none)* | `category`, `year`, `states`, `multi_year_trend` | Preserves multiple states as a list; defaults `year=2025`. |
| `get_parameter_correlation` | `category`, `year` | `parameters`, `method` | Preserves parameter list; maps `correlation_method` to `method`. |
| `get_parameter_relationship` | `category`, `year`, `param_x`, `param_y` | `institution_uids` | Falls back to `parameters[0]` and `parameters[1]` if `param_x`/`param_y` not populated. Supports predecessor UID injection. |
| `get_multidimensional_performance` | `category`, `year` | `institution_uids`, `institution_names`, `parameters`, `top_n` | Preserves both UIDs and names for multi-entity comparison. |
| `get_score_distribution` | `category`, `year` | `metric`, `state`, `bins_count` | Defaults `metric="score"`, `bins_count=10`. |
| `get_rank_transitions` | `category`, `start_year`, `end_year` | `custom_bands` | Maps custom band tuples if defined. |
| `get_outlier_analysis` | `category`, `year` | `metric`, `method`, `threshold`, `lookback_years` | Defaults `metric="score"`, `method="iqr"`, `threshold=1.5`. |

---

## 5. Multi-Operation Scheduling & Output Flow

### Dependency Validation:
- Uses Kahn's algorithm on a directed acyclic graph (DAG).
- Throws `DependencyError` if circular dependencies or references to non-existent operation IDs are encountered.

### Predecessor-to-Successor Output Passing:
When an operation specifies `depends_on="op_1"`:
1. **Cohort Subsetting**: If `op_1` produces an institution table (e.g. `get_category_performance` top 10 by research) and `op_2` is `get_parameter_relationship` without explicit target institutions, `QueryExecutor` extracts `institution_uids` from `op_1`'s output and passes them to `op_2`.
2. **Failure Isolation**: If `op_1` fails, `op_2` is not executed; it is marked `SKIPPED_DEPENDENCY_FAILED`. Independent operations in other branches continue executing.

---

## 6. Structured Result Schema & Strict JSON Serialization

Defined in [`src/execution/result_schema.py`](file:///Users/mohammadrehan/Documents/DHV%20Project/src/execution/result_schema.py):

```python
class ExecutionResult(BaseModel):
    execution_id: str
    query_id: str
    original_question: str
    status: ExecutionStatus  # SUCCESS, PARTIAL_SUCCESS, FAILED, REJECTED, CLARIFICATION_REQUIRED
    query_type: str
    operations: List[OperationResult]
    combined_result: Optional[Dict[str, Any]]
    validation_status: str
    warnings: List[str]
    errors: List[str]
    metadata: ExecutionMetadata
```

### Strict JSON Handling:
NIRF statistical operations produce `NaN` (for unreported scores in rank-only categories), `np.float64`, `np.int64`, and nested Pandas structures. Standard JSON encoders crash or emit invalid tokens when encountering `NaN` or `Infinity`.
- The execution layer runs `clean_for_json()`, transforming:
  - `NaN`, `np.nan`, `inf`, `-inf` $\to$ `None` (`null` in JSON).
  - `np.int64`, `np.float64` $\to$ standard Python `int`, `float`.
  - `pd.DataFrame`, `pd.Series` $\to$ standard lists and dictionaries.
  - `datetime` $\to$ ISO 8601 strings.
- Calling `result.to_json()` uses `allow_nan=False` to guarantee strict JSON conformity.

---

## 7. Example Execution Output

```json
{
  "execution_id": "exec_7b29a1ef",
  "query_id": "qp_rank_movement_karnataka_2020_2025",
  "original_question": "Which engineering colleges in Karnataka have improved their rankings the most since 2020?",
  "status": "SUCCESS",
  "query_type": "rank_movement",
  "operations": [
    {
      "operation_id": "op_1",
      "function_name": "get_rank_movement",
      "status": "SUCCESS",
      "data": {
        "success": true,
        "category": "Engineering",
        "start_year": 2020,
        "end_year": 2025,
        "state_filter": "Karnataka",
        "tracked_institutions_count": 7,
        "gainers": [
          {
            "institution_uid": "C-1273",
            "institute_name_std": "B.M.S. College of Engineering",
            "state_std": "Karnataka",
            "start_rank": 73,
            "end_rank": 40,
            "rank_improvement": 33
          }
        ]
      },
      "execution_duration_seconds": 0.0125
    }
  ],
  "validation_status": "VALID_WITH_WARNINGS",
  "warnings": [
    "Cohort depth expanded across [2020, 2025] (published depths: [200, 100]). For strict longitudinal consistency, restrict comparison to Top 100 institutions."
  ],
  "metadata": {
    "category": "Engineering",
    "year_range": [2020, 2025],
    "state_filters": ["Karnataka"],
    "total_duration_seconds": 0.0189
  }
}
```

