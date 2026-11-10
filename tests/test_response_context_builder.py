"""
Unit tests for ContextBuilder module (Phase 6).
"""

from src.execution.result_schema import ExecutionResult, OperationResult
from src.rag.result_schema import RetrievalResult, RetrievedChunk, RetrievalMetadata
from src.response.context_builder import ContextBuilder


def test_context_builder_analytical_only():
    op = OperationResult(
        operation_id="op_1",
        function_name="get_rank_movers",
        status="SUCCESS",
        data={
            "trends": [
                {
                    "institution_uid": "U-0456",
                    "institution_name": "IIT Bombay",
                    "rank_start": 4,
                    "rank_end": 2,
                    "rank_diff": 2,
                    "score": 88.5,
                }
            ]
        },
        warnings=["Cohort depth changed."],
    )
    exec_res = ExecutionResult(
        execution_id="e1",
        query_id="q1",
        original_question="Rank movers?",
        status="SUCCESS",
        query_type="RANKING_MOVEMENT",
        operations=[op],
        validation_status="VALID",
    )

    builder = ContextBuilder()
    context, resp_type, summary = builder.build_context(
        original_question="Rank movers?",
        execution_result=exec_res,
        retrieval_result=None,
    )

    assert resp_type == "ANALYTICAL_ONLY"
    assert "SECTION 1: EMPIRICAL ANALYTICAL EVIDENCE" in context
    assert "IIT Bombay" in context
    assert "Movement: +2 ranks (improved" in context
    assert "Cohort depth changed" in context
    assert summary["has_analytical_evidence"] is True
    assert summary["has_documentation_evidence"] is False


def test_context_builder_documentation_only():
    chunk = RetrievedChunk(
        chunk_id="chunk_01",
        document_id="nirf_methodology_reference",
        text="Teaching, Learning and Resources (TLR) measures student strength and faculty.",
        score=0.88,
        section_title="TLR Definition",
        source_reference="Ministry of Education",
    )
    rag_res = RetrievalResult(
        query="What is TLR?",
        chunks=[chunk],
        metadata=RetrievalMetadata(
            total_candidates=100,
            returned_count=1,
            top_k=5,
            execution_time_ms=10.0,
        ),
    )

    builder = ContextBuilder()
    context, resp_type, summary = builder.build_context(
        original_question="What is TLR?",
        execution_result=None,
        retrieval_result=rag_res,
    )

    assert resp_type == "DOCUMENTATION_ONLY"
    assert "SECTION 2: RETRIEVED AUTHORITATIVE NIRF DOCUMENTATION" in context
    assert "[CITE-01]" in context
    assert "Teaching, Learning and Resources" in context
    assert summary["has_analytical_evidence"] is False
    assert summary["has_documentation_evidence"] is True


def test_context_builder_combined():
    op = OperationResult(
        operation_id="op_compare",
        function_name="compare_institutions",
        status="SUCCESS",
        data={
            "institutions": [
                {"institution_name": "IIT Bombay", "rpc": 92.4},
                {"institution_name": "IIT Madras", "rpc": 94.1},
            ]
        },
    )
    exec_res = ExecutionResult(
        execution_id="e2",
        query_id="q2",
        original_question="Compare RPC?",
        status="SUCCESS",
        query_type="INSTITUTION_COMPARISON",
        operations=[op],
        validation_status="VALID",
    )
    chunk = RetrievedChunk(
        chunk_id="chunk_02",
        document_id="nirf_methodology_reference",
        text="RPC measures publication output, citation quality, and patents.",
        score=0.82,
        section_title="RPC Definition",
    )
    rag_res = RetrievalResult(
        query="Explain RPC?",
        chunks=[chunk],
        metadata=RetrievalMetadata(total_candidates=50, returned_count=1, top_k=5, execution_time_ms=5.0),
    )

    builder = ContextBuilder()
    context, resp_type, summary = builder.build_context(
        original_question="Compare and explain?",
        execution_result=exec_res,
        retrieval_result=rag_res,
    )

    assert resp_type == "COMBINED"
    assert "SECTION 1: EMPIRICAL ANALYTICAL EVIDENCE" in context
    assert "SECTION 2: RETRIEVED AUTHORITATIVE NIRF DOCUMENTATION" in context
    assert summary["has_analytical_evidence"] is True
    assert summary["has_documentation_evidence"] is True


def test_context_builder_no_evidence():
    builder = ContextBuilder()
    context, resp_type, summary = builder.build_context(
        original_question="Future prediction 2030?",
        execution_result=None,
        retrieval_result=None,
    )
    assert resp_type == "NO_EVIDENCE"
    assert "NO GROUNDED EVIDENCE AVAILABLE" in context

