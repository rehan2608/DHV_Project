"""
End-to-end integration tests for Response Generation and Verification (Phase 6).
Tests live or end-to-end flow from Phase 4 QueryExecutor and Phase 5 RAGRetriever.
"""

import pytest

from src.execution.executor import QueryExecutor
from src.query_engine.parser import QueryParser
from src.query_engine.validator import QueryValidator
from src.rag.retriever import RAGRetriever
from src.response.generator import ResponseGenerator
from src.response.result_schema import GeneratedResponse


@pytest.fixture(scope="module")
def shared_pipeline():
    executor = QueryExecutor()
    retriever = RAGRetriever()
    if not retriever.is_ready():
        retriever.build_or_refresh_index()
    generator = ResponseGenerator()
    return {
        "executor": executor,
        "retriever": retriever,
        "generator": generator,
    }


def test_integration_documentation_only(shared_pipeline):
    retriever = shared_pipeline["retriever"]
    generator = shared_pipeline["generator"]

    q = "What does RPC mean in NIRF, and what are its sub-parameters?"
    rag_res = retriever.retrieve(q, top_k=3)
    assert rag_res.has_results()

    resp = generator.generate_response(
        original_question=q,
        query_id="int_rag_01",
        execution_result=None,
        retrieval_result=rag_res,
    )

    assert isinstance(resp, GeneratedResponse)
    assert resp.response_status in ("SUCCESS", "PARTIAL_SUCCESS")
    assert resp.generation_metadata.response_type == "DOCUMENTATION_ONLY"
    assert len(resp.citations) >= 1
    assert any("RPC" in c.document_name or "RPC" in (c.section_title or "") for c in resp.citations)
    assert len(resp.answer) > 50


def test_integration_analytical_execution(shared_pipeline):
    executor = shared_pipeline["executor"]
    generator = shared_pipeline["generator"]

    # Execute deterministic analytical operation
    from src.query_engine.schemas import QueryPlan, AnalyticalOperation

    op = AnalyticalOperation(
        operation_id="op_movers",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2020,
        end_year=2025,
        states=["Karnataka"],
        top_n=5,
    )
    plan = QueryPlan(
        query_id="plan_int_01",
        original_question="Which engineering colleges in Karnataka improved their rankings the most since 2020?",
        query_type="rank_movement",
        analytical_intent="Identify rank gainers",
        operations=[op],
    )

    exec_res = executor.execute(plan)
    assert exec_res.status in ("SUCCESS", "PARTIAL_SUCCESS")

    resp = generator.generate_response(
        original_question=plan.original_question,
        query_id=plan.query_id,
        execution_result=exec_res,
        retrieval_result=None,
    )

    assert isinstance(resp, GeneratedResponse)
    assert resp.generation_metadata.response_type == "ANALYTICAL_ONLY"
    assert len(resp.answer) > 50
    # Must preserve any warnings from execution
    if exec_res.warnings:
        assert len(resp.warnings) > 0


def test_integration_combined_analytical_and_documentation(shared_pipeline):
    executor = shared_pipeline["executor"]
    retriever = shared_pipeline["retriever"]
    generator = shared_pipeline["generator"]

    from src.query_engine.schemas import QueryPlan, AnalyticalOperation

    op = AnalyticalOperation(
        operation_id="op_compare",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        institution_names=["Indian Institute of Technology Bombay", "Indian Institute of Technology Madras"],
        parameters=["rpc", "score"],
    )
    plan = QueryPlan(
        query_id="plan_int_comb",
        original_question="Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025 and explain what RPC measures.",
        query_type="category_performance",
        analytical_intent="Compare institution research performance",
        operations=[op],
    )

    exec_res = executor.execute(plan)
    rag_res = retriever.retrieve("What does RPC measure in NIRF?", top_k=2)

    resp = generator.generate_response(
        original_question=plan.original_question,
        query_id=plan.query_id,
        execution_result=exec_res,
        retrieval_result=rag_res,
    )

    assert isinstance(resp, GeneratedResponse)
    assert resp.generation_metadata.response_type == "COMBINED"
    assert len(resp.citations) >= 1
    assert resp.evidence_summary["has_analytical_evidence"] is True
    assert resp.evidence_summary["has_documentation_evidence"] is True
