"""
End-to-End Verification Test Script for NIRF Query Playground.
Tests the 10 representative query types through the actual Phase 3-7 pipeline:
Gemma parser -> Validator -> Executor -> Generator -> Verifier -> VisualizationService.
"""

import sys
from pathlib import Path
import time
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.query_engine.parser import get_query_parser
from src.query_engine.validator import get_query_validator
from src.execution.executor import QueryExecutor
from src.response.generator import ResponseGenerator
from src.visualization.visualization_service import get_visualization_service

TEST_QUESTIONS = [
    # 1. Institution Trend
    ("1. Institution Trend", "How has IIT Madras performed in Engineering from 2017 to 2025?"),
    # 2. Institution Comparison
    ("2. Institution Comparison", "Compare IIT Bombay, IIT Delhi and IIT Madras in Engineering for 2025."),
    # 3. Geographic Query
    ("3. Geographic Analysis", "Which states have the highest number of ranked Engineering institutions in 2025?"),
    # 4. Correlation Query
    ("4. Parameter Correlation", "Show the correlation between TLR, RPC, GO, OI and Perception for Engineering institutions in 2025."),
    # 5. Relationship Query
    ("5. Parameter Relationship", "Is there a relationship between TLR and RPC among Engineering institutions in 2025?"),
    # 6. Score Distribution
    ("6. Score Distribution", "Show the distribution of NIRF scores in Engineering for 2025."),
    # 7. Rank Movement
    ("7. Rank Movement", "Which institutions improved their Engineering rankings the most between 2020 and 2025?"),
    # 8. Multidimensional Query
    ("8. Multidimensional", "Compare the multidimensional performance of the top five Engineering institutions in 2025."),
    # 9. Unsupported Query (Future Year 2030)
    ("9. Unsupported Query", "Which engineering institution will rank first in NIRF 2030?"),
    # 10. Ambiguous / Incomplete Query
    ("10. Incomplete Query", "What is the rank?"),
]


def run_e2e_tests():
    parser = get_query_parser()
    validator = get_query_validator()
    executor = QueryExecutor()
    generator = ResponseGenerator()
    vis_service = get_visualization_service()

    print("=" * 115)
    print("RUNNING END-TO-END PIPELINE VERIFICATION (10 TEST CASES)")
    print("=" * 115)

    results = []

    for label, question in TEST_QUESTIONS:
        print(f"\n---> Testing: {label}")
        print(f"     Question: \"{question}\"")
        t0 = time.time()

        # Step 1: Parse
        plan = parser.parse(question)
        print(f"     Parsed Query Type: {plan.query_type} | Op Count: {len(plan.operations)}")

        # Step 2: Validate
        val = validator.validate(plan)
        print(f"     Validation Status: {val.status} | Is Valid: {val.is_valid}")

        if not val.is_valid or val.status in ["CLARIFICATION_REQUIRED", "UNSUPPORTED", "INVALID"]:
            print(f"     [BLOCKED / CLARIFICATION] Clarification: {plan.clarification_message or val.errors}")
            results.append({
                "label": label,
                "question": question,
                "query_type": plan.query_type,
                "status": val.status,
                "op_name": None,
                "chart_type": "None (Blocked/Clarification)",
                "verified_claims": 0,
                "has_chart": False,
                "latency": round(time.time() - t0, 2),
            })
            continue

        # Step 3: Execute
        exec_res = executor.execute(val.validated_plan)
        op_name = exec_res.operations[0].function_name if exec_res.operations else None
        print(f"     Execution Status: {exec_res.status} | Function: {op_name}")

        # Step 4: Verify Response
        resp = generator.generate_response(question, query_id=plan.query_id, execution_result=exec_res)
        vs = resp.verification_summary
        print(f"     Response Status: {resp.response_status} | Claims: {vs.verified_claims}/{vs.total_claims} verified")

        # Step 5: Visualize
        vis_results = vis_service.visualize_execution_result(exec_res, user_query=question)
        v0 = vis_results[0] if vis_results else None
        chart_type = v0.chart_spec.chart_type if v0 and v0.chart_spec else "None"
        has_chart = v0.has_chart if v0 else False
        print(f"     Visualization: Has Chart: {has_chart} | Chart Type: {chart_type} | Status: {v0.status if v0 else None}")

        elapsed = round(time.time() - t0, 2)
        results.append({
            "label": label,
            "question": question,
            "query_type": plan.query_type,
            "status": exec_res.status,
            "op_name": op_name,
            "chart_type": chart_type,
            "verified_claims": vs.verified_claims,
            "has_chart": has_chart,
            "latency": elapsed,
        })

    print("\n" + "=" * 115)
    print("SUMMARY OF E2E QUERY PLAYGROUND TESTS")
    print("=" * 115)
    fmt = "{:<28} | {:<24} | {:<12} | {:<15} | {:<9} | {:<8}"
    print(fmt.format("Test Case", "Function / Status", "Chart Type", "Claims Ver.", "Has Chart", "Latency"))
    print("-" * 115)

    for r in results:
        fn_or_st = r["op_name"] or r["status"]
        print(fmt.format(
            r["label"],
            str(fn_or_st)[:24],
            r["chart_type"],
            str(r["verified_claims"]),
            str(r["has_chart"]),
            f"{r['latency']}s",
        ))
    print("=" * 115)
    return results


if __name__ == "__main__":
    run_e2e_tests()

