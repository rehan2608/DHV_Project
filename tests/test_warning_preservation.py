"""
Unit tests for warning and limitation preservation in generated responses (Phase 6).
"""

from unittest.mock import MagicMock
from src.execution.result_schema import ExecutionResult, OperationResult, ExecutionMetadata
from src.response.generator import ResponseGenerator


def test_warning_preservation_from_execution_result():
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"
    mock_llm.generate.return_value = (
        "### Key Findings\n- IIT Bombay improved by 5 ranks.\n\n"
        "IIT Bombay moved from rank 15 to rank 10.\n\n"
        "### Data Notes & Limitations\n"
        "Only 8 institutions had valid observations for both years."
    )

    op = OperationResult(
        operation_id="op_movers",
        function_name="get_rank_movers",
        status="SUCCESS",
        data={
            "trends": [
                {
                    "institution_uid": "U-0456",
                    "institution_name": "IIT Bombay",
                    "rank_start": 15,
                    "rank_end": 10,
                    "rank_diff": 5,
                }
            ]
        },
        warnings=["Sample size warning: Only 8 institutions have continuous longitudinal data."],
    )
    exec_meta = ExecutionMetadata(
        comparability_warnings=["Management ranking depth expanded from Top 50 to Top 75 in 2020."],
    )
    exec_res = ExecutionResult(
        execution_id="e_warn",
        query_id="q_warn",
        original_question="Rank movers?",
        status="SUCCESS",
        query_type="RANKING_MOVEMENT",
        operations=[op],
        validation_status="VALID",
        warnings=["Global warning: Data normalization shift occurred across years."],
        metadata=exec_meta,
    )

    generator = ResponseGenerator(gemma_client=mock_llm, max_regeneration_attempts=0)
    response = generator.generate_response(
        original_question="Rank movers?",
        execution_result=exec_res,
        retrieval_result=None,
    )

    # Check that all warnings and comparability limitations are preserved
    assert len(response.warnings) >= 2
    assert any("Sample size warning" in w for w in response.warnings)
    assert any("Global warning" in w for w in response.warnings)
    assert any("Management ranking depth" in lim for lim in response.limitations)
    assert response.has_warnings() is True


def test_unverified_claim_adds_limitation_warning():
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"
    # Claims an unverified value 99.9 that does not exist in data
    mock_llm.generate.return_value = "IIT Bombay scored 99.9 in RPC."

    op = OperationResult(
        operation_id="op_1",
        function_name="get_top_institutions",
        status="SUCCESS",
        data={
            "rankings": [
                {"institution_name": "IIT Bombay", "institution_uid": "U-0456", "rpc": 88.0}
            ]
        },
    )
    exec_res = ExecutionResult(
        execution_id="e_unv",
        query_id="q_unv",
        original_question="Score check",
        status="SUCCESS",
        query_type="TOP_INSTITUTIONS",
        operations=[op],
        validation_status="VALID",
    )

    generator = ResponseGenerator(gemma_client=mock_llm, max_regeneration_attempts=0)
    response = generator.generate_response(
        original_question="Score check",
        execution_result=exec_res,
        retrieval_result=None,
    )

    assert not response.verification_summary.all_claims_verified
    assert any("could not be fully reconciled" in lim for lim in response.limitations)

