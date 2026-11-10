"""
Unit tests for ResponseGenerator lifecycle, regeneration loop, and failure handling (Phase 6).
"""

from unittest.mock import MagicMock
import pytest

from src.execution.result_schema import ExecutionResult, OperationResult
from src.rag.result_schema import RetrievalResult, RetrievedChunk, RetrievalMetadata
from src.response.generator import ResponseGenerator
from src.response.result_schema import GeneratedResponse


@pytest.fixture
def mock_exec_data() -> ExecutionResult:
    op = OperationResult(
        operation_id="op_1",
        function_name="get_top_institutions",
        status="SUCCESS",
        data={
            "rankings": [
                {"institution_name": "IIT Madras", "institution_uid": "I-1074", "score": 89.5, "rpc": 92.4},
                {"institution_name": "IIT Bombay", "institution_uid": "U-0456", "score": 88.0, "rpc": 91.2},
            ]
        },
    )
    return ExecutionResult(
        execution_id="e1",
        query_id="q1",
        original_question="Top engineering?",
        status="SUCCESS",
        query_type="TOP_INSTITUTIONS",
        operations=[op],
        validation_status="VALID",
    )


def test_generator_successful_first_attempt(mock_exec_data):
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"
    mock_llm.generate.return_value = (
        "### Key Findings\n- IIT Madras ranked top with score 89.5.\n\n"
        "IIT Madras achieved a score of 89.5 and RPC of 92.4, while IIT Bombay scored 88.0."
    )

    gen = ResponseGenerator(gemma_client=mock_llm, max_regeneration_attempts=1)
    resp = gen.generate_response("Top engineering?", execution_result=mock_exec_data)

    assert resp.response_status == "SUCCESS"
    assert resp.verification_summary.all_claims_verified is True
    assert resp.verification_summary.regeneration_attempted is False
    assert mock_llm.generate.call_count == 1


def test_generator_regeneration_after_failure(mock_exec_data):
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"
    # First response has wrong score (99.9), second response corrects to 89.5
    mock_llm.generate.side_effect = [
        "IIT Madras achieved a score of 99.9.",  # Wrong
        "IIT Madras achieved a score of 89.5.",  # Corrected
    ]

    gen = ResponseGenerator(gemma_client=mock_llm, max_regeneration_attempts=1)
    resp = gen.generate_response("Top engineering?", execution_result=mock_exec_data)

    assert mock_llm.generate.call_count == 2
    assert resp.verification_summary.regeneration_attempted is True
    assert resp.verification_summary.regeneration_count == 1
    assert resp.verification_summary.all_claims_verified is True
    assert resp.response_status == "SUCCESS"


def test_generator_persistent_failure_handling(mock_exec_data):
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"
    # Both attempts return wrong score
    mock_llm.generate.side_effect = [
        "IIT Madras achieved a score of 99.9.",
        "IIT Madras scored 98.8.",
    ]

    gen = ResponseGenerator(gemma_client=mock_llm, max_regeneration_attempts=1)
    resp = gen.generate_response("Top engineering?", execution_result=mock_exec_data)

    assert mock_llm.generate.call_count == 2
    assert not resp.verification_summary.all_claims_verified
    assert resp.response_status in ("VERIFICATION_FAILED", "PARTIAL_SUCCESS")
    assert any("could not be fully reconciled" in lim for lim in resp.limitations)


def test_generator_clarification_required():
    exec_res = ExecutionResult(
        execution_id="e_clarify",
        query_id="q_clarify",
        original_question="Show colleges?",
        status="CLARIFICATION_REQUIRED",
        query_type="UNKNOWN",
        operations=[],
        validation_status="NEEDS_CLARIFICATION",
        errors=["Target category is ambiguous: could be College or Engineering."],
    )

    gen = ResponseGenerator(gemma_client=MagicMock(), max_regeneration_attempts=0)
    resp = gen.generate_response("Show colleges?", execution_result=exec_res)

    assert resp.response_status == "CLARIFICATION_REQUIRED"
    assert "clarify your question" in resp.answer.lower()
    assert "Target category is ambiguous" in resp.answer


def test_generator_failed_operation():
    exec_res = ExecutionResult(
        execution_id="e_fail",
        query_id="q_fail",
        original_question="Invalid request",
        status="FAILED",
        query_type="ANALYTICAL",
        operations=[],
        validation_status="VALID",
        errors=["Data file not found for requested year."],
    )

    gen = ResponseGenerator(gemma_client=MagicMock(), max_regeneration_attempts=0)
    resp = gen.generate_response("Invalid request", execution_result=exec_res)

    assert resp.response_status == "FAILED"
    assert "could not be completed" in resp.answer.lower()

