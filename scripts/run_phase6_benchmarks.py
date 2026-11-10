"""
Phase 6 End-to-End Benchmark Runner.
Executes the seven standardized Phase 6 evaluation queries, verifies factual and numerical claims,
audits documentation citations, preserves warnings, and records latency.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.execution.executor import QueryExecutor
from src.query_engine.schemas import QueryPlan, AnalyticalOperation
from src.rag.retriever import RAGRetriever
from src.response.generator import ResponseGenerator
from src.response.result_schema import GeneratedResponse


def run_benchmark_1(executor: QueryExecutor, generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 1 — Analytical only"""
    q = "Which engineering colleges in Karnataka improved their rankings the most since 2020?"
    op = AnalyticalOperation(
        operation_id="op_b1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2020,
        end_year=2025,
        states=["Karnataka"],
        top_n=5,
    )
    plan = QueryPlan(
        query_id="bm_01",
        original_question=q,
        query_type="rank_movement",
        analytical_intent="Identify rank gainers",
        operations=[op],
    )
    exec_res = executor.execute(plan)
    return generator.generate_response(q, query_id="bm_01", execution_result=exec_res)


def run_benchmark_2(retriever: RAGRetriever, generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 2 — Documentation only"""
    q = "What does RPC mean in NIRF, and what are its sub-parameters?"
    rag_res = retriever.retrieve(q, top_k=3)
    return generator.generate_response(q, query_id="bm_02", retrieval_result=rag_res)


def run_benchmark_3(executor: QueryExecutor, retriever: RAGRetriever, generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 3 — Combined"""
    q = "Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025 and explain what RPC measures."
    op = AnalyticalOperation(
        operation_id="op_b3",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        institution_names=["Indian Institute of Technology Bombay", "Indian Institute of Technology Madras"],
        parameters=["rpc", "score"],
        top_n=5,
    )
    plan = QueryPlan(
        query_id="bm_03",
        original_question=q,
        query_type="category_performance",
        analytical_intent="Compare institution performance",
        operations=[op],
    )
    exec_res = executor.execute(plan)
    rag_res = retriever.retrieve("What does RPC measure in NIRF and what are its sub-parameters?", top_k=2)
    return generator.generate_response(q, query_id="bm_03", execution_result=exec_res, retrieval_result=rag_res)


def run_benchmark_4(executor: QueryExecutor, generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 4 — Complex analytical response (Top 10 Research + Correlation with TLR)"""
    q = "Find the top 10 engineering institutions by research performance in 2025, then explain how research performance relates to teaching performance among them."
    op1 = AnalyticalOperation(
        operation_id="op_top_rpc",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        parameters=["rpc"],
        top_n=10,
    )
    op2 = AnalyticalOperation(
        operation_id="op_rel",
        function_name="get_parameter_relationship",
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="tlr",
        depends_on="op_top_rpc",
    )
    plan = QueryPlan(
        query_id="bm_04",
        original_question=q,
        query_type="multi_operation",
        analytical_intent="Top 10 institutions and parameter relationship",
        operations=[op1, op2],
    )
    exec_res = executor.execute(plan)
    return generator.generate_response(q, query_id="bm_04", execution_result=exec_res)


def run_benchmark_5(generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 5 — Missing evidence (future year 2027)"""
    q = "Which institution will rank first in NIRF 2027?"
    return generator.generate_response(
        original_question=q,
        query_id="bm_05",
        execution_result=None,
        retrieval_result=None,
        custom_instructions="The NIRF dataset only contains historical records from 2017 to 2025. 2027 is out-of-bounds.",
    )


def run_benchmark_6(executor: QueryExecutor, generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 6 — Comparability limitation (Management 2017 to 2025 cohort depth expansion)"""
    q = "Which institution improved the most between two years where its category methodology changed?"
    op = AnalyticalOperation(
        operation_id="op_comp_shift",
        function_name="get_rank_movement",
        category="Management",
        start_year=2017,
        end_year=2025,
        top_n=5,
    )
    plan = QueryPlan(
        query_id="bm_06",
        original_question=q,
        query_type="rank_movement",
        analytical_intent="Longitudinal rank movement",
        operations=[op],
    )
    exec_res = executor.execute(plan)
    return generator.generate_response(q, query_id="bm_06", execution_result=exec_res)


def run_benchmark_7(executor: QueryExecutor, generator: ResponseGenerator) -> GeneratedResponse:
    """Benchmark 7 — Follow-up style response (State comparison: Karnataka vs Tamil Nadu in 2025 Engineering)"""
    q = "Compare Karnataka and Tamil Nadu Engineering institutions in 2025."
    op = AnalyticalOperation(
        operation_id="op_state_comp",
        function_name="get_geographic_analysis",
        category="Engineering",
        year=2025,
        states=["Karnataka", "Tamil Nadu"],
        parameters=["score", "rpc", "tlr"],
    )
    plan = QueryPlan(
        query_id="bm_07",
        original_question=q,
        query_type="geographic_analysis",
        analytical_intent="Geographic state comparison",
        operations=[op],
    )
    exec_res = executor.execute(plan)
    return generator.generate_response(q, query_id="bm_07", execution_result=exec_res)


def run_all_phase6_benchmarks() -> Dict[str, Any]:
    print("=" * 80)
    print("STARTING PHASE 6 BENCHMARK EVALUATION (7 BENCHMARK QUERIES)")
    print("=" * 80)

    executor = QueryExecutor()
    retriever = RAGRetriever()
    if not retriever.is_ready():
        retriever.build_or_refresh_index()
    generator = ResponseGenerator(max_regeneration_attempts=1)

    benchmarks = [
        ("Benchmark 1 (Analytical Only)", lambda: run_benchmark_1(executor, generator)),
        ("Benchmark 2 (Documentation Only)", lambda: run_benchmark_2(retriever, generator)),
        ("Benchmark 3 (Combined Analytical + Documentation)", lambda: run_benchmark_3(executor, retriever, generator)),
        ("Benchmark 4 (Complex Analytical Multi-Op)", lambda: run_benchmark_4(executor, generator)),
        ("Benchmark 5 (Missing Evidence / Future 2027)", lambda: run_benchmark_5(generator)),
        ("Benchmark 6 (Comparability Limitation)", lambda: run_benchmark_6(executor, generator)),
        ("Benchmark 7 (Geographic Follow-up Comparison)", lambda: run_benchmark_7(executor, generator)),
    ]

    all_results = []
    output_dir = Path("tests/benchmark_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, bench_fn in benchmarks:
        print(f"\n---> Running: {name}")
        t0 = time.time()
        resp = bench_fn()
        elapsed = round(time.time() - t0, 2)

        record = {
            "name": name,
            "query_id": resp.query_id,
            "status": resp.response_status,
            "question": resp.original_question,
            "answer_preview": resp.answer[:250] + "..." if len(resp.answer) > 250 else resp.answer,
            "total_claims": resp.verification_summary.total_claims,
            "verified_claims": resp.verification_summary.verified_claims,
            "unverified_claims": resp.verification_summary.unverified_claims,
            "conflicting_claims": resp.verification_summary.conflicting_claims,
            "all_verified": resp.verification_summary.all_claims_verified,
            "extraction_coverage": resp.verification_summary.extraction_coverage,
            "verification_precision": resp.verification_summary.verification_precision,
            "verification_recall": resp.verification_summary.verification_recall,
            "citations_count": len(resp.citations),
            "warnings_count": len(resp.warnings),
            "limitations_count": len(resp.limitations),
            "latency_seconds": elapsed,
            "generation_time": resp.generation_metadata.generation_duration_seconds,
            "verification_time": resp.generation_metadata.verification_duration_seconds,
        }
        all_results.append(record)

        print(f"Status: {resp.response_status} | Elapsed: {elapsed}s (Gen: {resp.generation_metadata.generation_duration_seconds}s, Ver: {resp.generation_metadata.verification_duration_seconds}s)")
        prec_str = f"{resp.verification_summary.verification_precision:.2f}" if resp.verification_summary.verification_precision is not None else "N/A"
        rec_str = f"{resp.verification_summary.verification_recall:.2f}" if resp.verification_summary.verification_recall is not None else "N/A"
        cov_str = f"{resp.verification_summary.extraction_coverage:.2f}" if resp.verification_summary.extraction_coverage is not None else "N/A"
        print(f"Claims: {resp.verification_summary.verified_claims}/{resp.verification_summary.total_claims} verified (Prec: {prec_str}, Rec: {rec_str}, Cov: {cov_str}) | Citations: {len(resp.citations)} | Warnings: {len(resp.warnings)}")
        print(f"Preview: {resp.answer[:150]}...")

        # Save individual JSON
        with open(output_dir / f"{resp.query_id}.json", "w", encoding="utf-8") as f:
            f.write(resp.to_json(indent=2))

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_benchmarks": len(benchmarks),
        "results": all_results,
    }

    with open(output_dir / "phase6_benchmarks_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("PHASE 6 BENCHMARK EVALUATION COMPLETED")
    print("=" * 80)
    return summary


if __name__ == "__main__":
    run_all_phase6_benchmarks()
