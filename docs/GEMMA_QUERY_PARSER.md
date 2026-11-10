# Gemma Query Parser and Independent Validation Architecture (Phase 3)

This document describes the design, prompt engineering, validation stages, and benchmark evaluation for the natural-language-to-structured-query system powered by `gemma4:31b-cloud`.

---

## 1. Gemma Integration & Configuration

The assistant interfaces with Google Gemma using the official `ollama` Python client.

- **Model Identifier**: `gemma4:31b-cloud`
- **Transport**: Ollama Cloud HTTP client (`ollama.Client`)
- **Timeout**: `60.0s` (configurable via `OLLAMA_TIMEOUT`)
- **Retry Strategy**: Exponential backoff (1s, 2s, 4s) up to 3 attempts
- **Structured Output Mechanism**:
  - Automatically injects JSON Schema into the prompt instructions.
  - Passes `format="json"` to Ollama.
  - Sanitizes markdown code fences (````json ... ````) and conversational preamble.
  - Validates output against Pydantic model (`QueryPlan.model_validate()`).

---

## 2. Prompt Engineering Workflow

The `QueryParser` builds a constrained prompt:

```text
QUERY_PARSER_SYSTEM_PROMPT:
- System role definition: Query Planner for NIRF Analytics.
- Prohibition of calculations: Gemma never calculates math, rankings, or averages.
- Canonical function catalog: 10 allowed function names.
- Schema constraints: Parameter structures (Standard 5 vs Research 3 vs Rank-Only).
- Temporal bounds: 2017 to 2025.
- Conversation inheritance instructions: Keep category, add states, track slices.

build_parser_user_prompt(question, context):
- Injects user question.
- Injects previous conversation context (category, year, states, top_n).
- Mandates strictly valid JSON matching QueryPlan schema.
```

---

## 3. Five-Stage Independent Validation Pipeline

The `QueryValidator` operates completely independently of Gemma:

```text
               QueryPlan
                   │
                   ▼
       [1. Structural Validation]
       ├── Validates Pydantic schema integrity
       ├── Checks required top-level attributes
       └── Handles unsupported & clarification requests
                   │
                   ▼
       [2. Analytical API Validation]
       ├── Validates function_name exists in Phase 2
       └── Verifies required arguments per function
                   │
                   ▼
       [3. Dataset Validation]
       ├── Validates against 18 canonical categories
       ├── Validates years against 2017–2025
       ├── Validates states against 33 standardized regions
       └── Resolves institution names (with acronym expansion)
                   │
                   ▼
    [4. Comparability Rule Validation]
    ├── Evaluates 103 cohort rules from comparability_rules.csv
    ├── Checks valid_comparison_start_year
    ├── Enforces schema boundaries (SFC/QNR/QLR vs TLR/RPC/GO)
    └── Surfaces cohort depth expansion cautions
                   │
                   ▼
         [5. Logical Validation]
         ├── Enforces start_year <= end_year
         ├── Asserts top_n > 0
         └── Ensures distinct param_x and param_y
                   │
                   ▼
          QueryValidationResult
```

### Validation Status Outputs:
- `VALID`: Query plan is executable by the analytical engine with no warnings.
- `VALID_WITH_WARNINGS`: Query plan is executable, but includes official NIRF audit warnings (e.g. cohort depth expansion caution).
- `CLARIFICATION_REQUIRED`: Ambiguous institution name matching multiple entities or missing mandatory dimensional anchor.
- `INVALID`: Query requests impossible criteria (e.g. start year > end year, unintroduced year).
- `UNSUPPORTED`: Query requests capabilities outside NIRF scope (e.g. campus hostel fees, international universities).

---

## 4. Benchmark Evaluation Results

The four benchmark question types were executed against live `gemma4:31b-cloud` and evaluated through the validator:

| Benchmark | Question | Intent Correct | Function Correct | Arguments Correct | Schema Valid | Validator Passed | Latency |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Intent Extraction** | *"Which engineering colleges in Karnataka have improved their rankings the most since 2020?"* | **YES** (`rank_movement`) | **YES** (`get_rank_movement`) | **YES** (`Engineering`, `Karnataka`, `2020-2025`) | **YES** | **YES** (`VALID_WITH_WARNINGS`) | 2.25s |
| **2. Structured Query** | *"Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025."* | **YES** (`multidimensional_performance`) | **YES** (`get_multidimensional_performance`) | **YES** (`Engineering`, `2025`, `IIT Bombay`, `IIT Madras`, `rpc`) | **YES** | **YES** (`VALID`) | 1.76s |
| **3. Complex Planning** | *"Find the top 10 engineering institutions in 2025 with the highest research performance, then examine how research performance relates to teaching performance."* | **YES** (`multi_operation`) | **YES** (`get_category_performance` + `get_parameter_relationship`) | **YES** (`Engineering`, `2025`, `rpc`, `tlr`, `top_n=10`) | **YES** | **YES** (`VALID`) | 1.96s |
| **4. Follow-up Context** | *Turn 1: "Top 10 Engineering Karnataka 2025"*<br>*Turn 2: "Now compare them with Tamil Nadu"*<br>*Turn 3: "Show only the top five"* | **YES** (Context preserved) | **YES** | **YES** (`states=['Karnataka', 'Tamil Nadu']`, `top_n=5`, `Engineering`, `2025`) | **YES** | **YES** (`VALID`) | 2.10s |

All benchmark execution details are persisted in `tests/benchmark_results/benchmark_run.json`.

---

## 5. Known Limitations & Edge Cases

1. **Vague Academic Scope**:
   When users ask generic questions like *"Who is the best college in India?"* without naming a category, the parser requests clarification because NIRF evaluates colleges separately under "College" vs "Overall" vs "University".
2. **Multi-Discipline Ambiguity**:
   Certain universities (e.g. Manipal Academy of Higher Education, BITS Pilani) rank under Overall, Engineering, Pharmacy, and Medical in the same year. Analytical questions must anchor the discipline category.
3. **Complex Multi-Step Dependency Chaining**:
   Multi-operation query plans currently support sequential dependency chains (`depends_on`). Dynamic branching based on intermediate runtime data will be executed in Phase 4.

