"""
Unit tests for ClaimExtractor module (Phase 6).
"""

from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.claim_extractor import ClaimExtractor


def _get_mock_exec_result() -> ExecutionResult:
    op = OperationResult(
        operation_id="op_1",
        function_name="get_rank_movers",
        status="SUCCESS",
        data={
            "trends": [
                {
                    "institution_uid": "U-0456",
                    "institution_name": "Indian Institute of Technology Bombay",
                    "rank_start": 40,
                    "rank_end": 28,
                    "rank_diff": 12,
                    "score": 91.2,
                    "rpc": 85.5,
                }
            ]
        },
    )
    return ExecutionResult(
        execution_id="e1",
        query_id="q1",
        original_question="Rank movers?",
        status="SUCCESS",
        query_type="RANKING_MOVEMENT",
        operations=[op],
        validation_status="VALID",
    )


def test_extract_rank_movement_claim():
    extractor = ClaimExtractor()
    exec_res = _get_mock_exec_result()
    text = "IIT Bombay improved by 12 ranks from 2020 to 2025."
    claims = extractor.extract_claims(text, exec_res)

    assert len(claims) >= 1
    movement_claim = [c for c in claims if c.claim_type == "RANK_CHANGE"][0]
    assert movement_claim.claimed_value == 12
    assert movement_claim.institution_uid == "U-0456"
    assert movement_claim.unit == "ranks"


def test_extract_metric_score_claim():
    extractor = ClaimExtractor()
    exec_res = _get_mock_exec_result()
    text = "IIT Bombay scored 85.5 in RPC during the 2025 ranking."
    claims = extractor.extract_claims(text, exec_res)

    assert len(claims) >= 1
    metric_claim = [c for c in claims if c.claim_type == "METRIC_VALUE"][0]
    assert metric_claim.metric == "rpc"
    assert metric_claim.claimed_value == 85.5
    assert metric_claim.institution_uid == "U-0456"


def test_extract_correlation_claim():
    extractor = ClaimExtractor()
    text = "The correlation coefficient between RPC and TLR was 0.72."
    claims = extractor.extract_claims(text, None)

    assert len(claims) >= 1
    corr_claim = [c for c in claims if c.claim_type == "CORRELATION"][0]
    assert corr_claim.claimed_value == 0.72
    assert corr_claim.metric == "correlation"


def test_extract_count_claim():
    extractor = ClaimExtractor()
    text = "A total of 14 institutions met the inclusion criteria."
    claims = extractor.extract_claims(text, None)

    assert len(claims) >= 1
    count_claim = [c for c in claims if c.claim_type == "COUNT"][0]
    assert count_claim.claimed_value == 14

