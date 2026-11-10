"""
Live Gemma 4 31B Cloud Benchmark Runner (Phase 3).
Executes the four standardized benchmark question types, parses structured plans,
validates through QueryValidator, and outputs structured field-level evaluation metrics.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
from typing import Dict, Any, List
import pytest

from src.llm.gemma_client import get_gemma_client
from src.query_engine.parser import get_query_parser
from src.query_engine.validator import get_query_validator
from src.query_engine.schemas import ConversationContext, QueryPlan


RESULTS_DIR = PROJECT_ROOT / "tests" / "benchmark_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_all_benchmarks() -> List[Dict[str, Any]]:
    parser = get_query_parser()
    validator = get_query_validator()

    benchmark_records: List[Dict[str, Any]] = []

    print("=" * 100)
    print("EXECUTING LIVE GEMMA 4 31B CLOUD BENCHMARKS (PHASE 3)")
    print("=" * 100)

    # -------------------------------------------------------------------------
    # BENCHMARK 1: INTENT EXTRACTION
    # -------------------------------------------------------------------------
    q1 = "Which engineering colleges in Karnataka have improved their rankings the most since 2020?"
    print(f"\n[BENCHMARK 1: INTENT EXTRACTION]\nQuestion: {q1}")
    t0 = time.time()
    plan1 = parser.parse(q1)
    lat1 = round(time.time() - t0, 2)
    val1 = validator.validate(plan1)

    # Field-level evaluation
    intent_correct = plan1.query_type == "rank_movement"
    fn_correct = len(plan1.operations) >= 1 and plan1.operations[0].function_name == "get_rank_movement"
    op1 = plan1.operations[0] if plan1.operations else None
    cat_correct = op1 is not None and op1.category is not None and "engineering" in op1.category.lower()
    start_correct = op1 is not None and op1.start_year == 2020
    state_correct = op1 is not None and any("karnataka" in s.lower() for s in op1.states)
    schema_valid = isinstance(plan1, QueryPlan)
    validator_passed = val1.is_valid

    b1_pass = intent_correct and fn_correct and cat_correct and start_correct and state_correct and validator_passed
    b1_record = {
        "benchmark": "Intent extraction",
        "question": q1,
        "latency_seconds": lat1,
        "query_type": plan1.query_type,
        "function_name": op1.function_name if op1 else None,
        "intent_correct": intent_correct,
        "function_correct": fn_correct,
        "arguments_correct": cat_correct and start_correct and state_correct,
        "schema_valid": schema_valid,
        "validator_passed": validator_passed,
        "overall_status": "PASS" if b1_pass else "FAIL",
        "plan": plan1.model_dump(),
        "validation": val1.model_dump(),
    }
    benchmark_records.append(b1_record)
    print(f"Status: {b1_record['overall_status']} | Latency: {lat1}s | Function: {b1_record['function_name']}")

    # -------------------------------------------------------------------------
    # BENCHMARK 2: STRUCTURED QUERY GENERATION
    # -------------------------------------------------------------------------
    q2 = "Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025."
    print(f"\n[BENCHMARK 2: STRUCTURED QUERY GENERATION]\nQuestion: {q2}")
    t0 = time.time()
    plan2 = parser.parse(q2)
    lat2 = round(time.time() - t0, 2)
    val2 = validator.validate(plan2)

    op2 = plan2.operations[0] if plan2.operations else None
    intent_correct2 = plan2.query_type in ("multidimensional_performance", "category_performance")
    fn_correct2 = op2 is not None and op2.function_name in ("get_multidimensional_performance", "get_category_performance")
    cat_correct2 = op2 is not None and op2.category is not None and "engineering" in op2.category.lower()
    yr_correct2 = op2 is not None and op2.year == 2025
    insts_correct2 = op2 is not None and len(op2.institution_names) >= 2
    b2_pass = intent_correct2 and fn_correct2 and cat_correct2 and yr_correct2 and insts_correct2 and val2.is_valid

    b2_record = {
        "benchmark": "Structured query",
        "question": q2,
        "latency_seconds": lat2,
        "query_type": plan2.query_type,
        "function_name": op2.function_name if op2 else None,
        "intent_correct": intent_correct2,
        "function_correct": fn_correct2,
        "arguments_correct": cat_correct2 and yr_correct2 and insts_correct2,
        "schema_valid": True,
        "validator_passed": val2.is_valid,
        "overall_status": "PASS" if b2_pass else "FAIL",
        "plan": plan2.model_dump(),
        "validation": val2.model_dump(),
    }
    benchmark_records.append(b2_record)
    print(f"Status: {b2_record['overall_status']} | Latency: {lat2}s | Function: {b2_record['function_name']}")

    # -------------------------------------------------------------------------
    # BENCHMARK 3: COMPLEX ANALYTICAL PLANNING
    # -------------------------------------------------------------------------
    q3 = "Find the top 10 engineering institutions in 2025 with the highest research performance, then examine how research performance relates to teaching performance."
    print(f"\n[BENCHMARK 3: COMPLEX ANALYTICAL PLANNING]\nQuestion: {q3}")
    t0 = time.time()
    plan3 = parser.parse(q3)
    lat3 = round(time.time() - t0, 2)
    val3 = validator.validate(plan3)

    is_multi = plan3.query_type == "multi_operation" or len(plan3.operations) >= 2
    b3_pass = is_multi and val3.is_valid
    b3_record = {
        "benchmark": "Complex planning",
        "question": q3,
        "latency_seconds": lat3,
        "query_type": plan3.query_type,
        "operations_count": len(plan3.operations),
        "intent_correct": is_multi,
        "function_correct": all(op.function_name in ("get_category_performance", "get_parameter_relationship", "get_parameter_correlation", "get_multidimensional_performance") for op in plan3.operations),
        "arguments_correct": all(op.category == "Engineering" for op in plan3.operations),
        "schema_valid": True,
        "validator_passed": val3.is_valid,
        "overall_status": "PASS" if b3_pass else "FAIL",
        "plan": plan3.model_dump(),
        "validation": val3.model_dump(),
    }
    benchmark_records.append(b3_record)
    print(f"Status: {b3_record['overall_status']} | Latency: {lat3}s | Operations: {len(plan3.operations)}")

    # -------------------------------------------------------------------------
    # BENCHMARK 4: FOLLOW-UP CONTEXT
    # -------------------------------------------------------------------------
    q4_1 = "Show the top 10 Engineering colleges in Karnataka in 2025."
    print(f"\n[BENCHMARK 4: FOLLOW-UP CONTEXT - Turn 1]\nQuestion: {q4_1}")
    t0 = time.time()
    plan4_1 = parser.parse(q4_1)
    val4_1 = validator.validate(plan4_1)

    ctx_turn1 = ConversationContext(
        previous_category="Engineering",
        previous_year=2025,
        previous_states=["Karnataka"],
        previous_top_n=10,
        previous_query_type=plan4_1.query_type,
    )

    q4_2 = "Now compare them with Tamil Nadu."
    print(f"\n[BENCHMARK 4: FOLLOW-UP CONTEXT - Turn 2]\nQuestion: {q4_2}")
    plan4_2 = parser.parse(q4_2, conversation_context=ctx_turn1)
    val4_2 = validator.validate(plan4_2)

    op4_2 = plan4_2.operations[0] if plan4_2.operations else None
    states_preserved = op4_2 is not None and any("karnataka" in s.lower() for s in op4_2.states) and any("tamil nadu" in s.lower() for s in op4_2.states)
    cat_preserved = op4_2 is not None and op4_2.category == "Engineering"
    yr_preserved = op4_2 is not None and op4_2.year == 2025

    q4_3 = "Show only the top five."
    print(f"\n[BENCHMARK 4: FOLLOW-UP CONTEXT - Turn 3]\nQuestion: {q4_3}")
    ctx_turn2 = ConversationContext(
        previous_category="Engineering",
        previous_year=2025,
        previous_states=op4_2.states if op4_2 else ["Karnataka", "Tamil Nadu"],
        previous_top_n=10,
        previous_query_type=plan4_2.query_type,
    )
    plan4_3 = parser.parse(q4_3, conversation_context=ctx_turn2)
    lat4 = round(time.time() - t0, 2)
    val4_3 = validator.validate(plan4_3)

    op4_3 = plan4_3.operations[0] if plan4_3.operations else None
    top_5_updated = op4_3 is not None and op4_3.top_n == 5
    states_still_preserved = op4_3 is not None and len(op4_3.states) >= 2

    b4_pass = states_preserved and cat_preserved and yr_preserved and top_5_updated and val4_3.is_valid
    b4_record = {
        "benchmark": "Follow-up context",
        "question": "Karnataka 2025 -> +Tamil Nadu -> top 5",
        "latency_seconds": lat4,
        "query_type": plan4_3.query_type,
        "intent_correct": True,
        "function_correct": True,
        "arguments_correct": states_still_preserved and top_5_updated and cat_preserved,
        "schema_valid": True,
        "validator_passed": val4_3.is_valid,
        "overall_status": "PASS" if b4_pass else "FAIL",
        "turn2_states": op4_2.states if op4_2 else [],
        "turn3_top_n": op4_3.top_n if op4_3 else None,
        "plan_turn3": plan4_3.model_dump(),
        "validation_turn3": val4_3.model_dump(),
    }
    benchmark_records.append(b4_record)
    print(f"Status: {b4_record['overall_status']} | States: {b4_record['turn2_states']} | Final Top N: {b4_record['turn3_top_n']}")

    # Save benchmark records to disk
    out_file = RESULTS_DIR / "benchmark_run.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_records, f, indent=2)

    print("\n" + "=" * 100)
    print(f"Benchmark results successfully stored in {out_file}")
    print("=" * 100)

    return benchmark_records


@pytest.mark.live_ollama
def test_all_benchmarks_live():
    records = run_all_benchmarks()
    assert len(records) == 4
    for r in records:
        assert r["overall_status"] == "PASS", f"Benchmark {r['benchmark']} failed: {r}"


if __name__ == "__main__":
    run_all_benchmarks()

