"""
Unit tests for NumericalClaimVerifier module (Phase 6).
"""

import pytest
from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.result_schema import NumericalClaim
from src.response.verifier import NumericalClaimVerifier


@pytest.fixture
def mock_exec_result() -> ExecutionResult:
    op_ranks = OperationResult(
        operation_id="op_ranks",
        function_name="get_rank_movers",
        status="SUCCESS",
        data={
            "trends": [
                {
                    "institution_uid": "U-0456",
                    "institution_name": "Indian Institute of Technology Bombay",
                    "rank_start": 35,
                    "rank_end": 20,
                    "rank_diff": 15,  # Improved by 15
                    "score": 91.234,
                    "rpc": 88.5,
                    "missing_metric": None,  # Missing
                },
                {
                    "institution_uid": "U-0100",
                    "institution_name": "Decline University",
                    "rank_start": 10,
                    "rank_end": 18,
                    "rank_diff": -8,  # Declined by 8
                    "score": 65.0,
                },
            ]
        },
    )
    op_corr = OperationResult(
        operation_id="op_corr",
        function_name="get_parameter_relationship",
        status="SUCCESS",
        data={
            "correlation": 0.7245,
            "method": "pearson",
            "n": 100,
        },
    )
    return ExecutionResult(
        execution_id="e1",
        query_id="q1",
        original_question="Perform analysis",
        status="SUCCESS",
        query_type="COMBINED_ANALYTICS",
        operations=[op_ranks, op_corr],
        validation_status="VALID",
    )


def test_verify_correct_metric_claim(mock_exec_result):
    verifier = NumericalClaimVerifier(float_tolerance=0.05)
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="IIT Bombay achieved an RPC score of 88.5.",
        claim_type="METRIC_VALUE",
        metric="rpc",
        institution_name="IIT Bombay",
        claimed_value=88.5,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "VERIFIED"
    assert summary.verified_claims == 1
    assert summary.all_claims_verified is True


def test_verify_metric_claim_within_rounding_tolerance(mock_exec_result):
    verifier = NumericalClaimVerifier(float_tolerance=0.05)
    # Actual score is 91.234 -> claimed 91.23
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="IIT Bombay had a composite score of 91.23.",
        claim_type="METRIC_VALUE",
        metric="score",
        institution_name="IIT Bombay",
        claimed_value=91.23,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "VERIFIED"
    assert summary.all_claims_verified is True


def test_verify_incorrect_metric_claim(mock_exec_result):
    verifier = NumericalClaimVerifier(float_tolerance=0.05)
    # Actual is 88.5 -> claimed 75.0
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="IIT Bombay had an RPC of 75.0.",
        claim_type="METRIC_VALUE",
        metric="rpc",
        institution_name="IIT Bombay",
        claimed_value=75.0,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "CONFLICTING"
    assert summary.conflicting_claims == 1
    assert summary.all_claims_verified is False


def test_verify_incorrect_rank_movement_direction(mock_exec_result):
    verifier = NumericalClaimVerifier()
    # Actual diff is +15 (improvement). Claim says declined by 15 (-15).
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="IIT Bombay declined by 15 ranks.",
        claim_type="RANK_CHANGE",
        metric="rank_diff",
        institution_name="IIT Bombay",
        claimed_value=-15,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "CONFLICTING"
    assert "Rank direction reversed" in claims[0].verification_notes


def test_verify_correct_correlation_claim(mock_exec_result):
    verifier = NumericalClaimVerifier(float_tolerance=0.05)
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="The correlation between RPC and TLR is 0.72.",
        claim_type="CORRELATION",
        metric="correlation",
        claimed_value=0.72,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "VERIFIED"
    assert summary.verified_claims == 1


def test_verify_unsupported_causal_statement(mock_exec_result):
    verifier = NumericalClaimVerifier()
    # Contains causal buzzword 'causes'
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="High RPC causes an increase in TLR score.",
        claim_type="CORRELATION",
        metric="correlation",
        claimed_value=0.72,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "CONFLICTING"
    assert "causal" in claims[0].verification_notes.lower()


def test_verify_missing_value_represented_as_zero(mock_exec_result):
    verifier = NumericalClaimVerifier()
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="The institution had 0.0 for missing metric.",
        claim_type="METRIC_VALUE",
        metric="missing_metric",
        institution_name="IIT Bombay",
        claimed_value=0.0,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "CONFLICTING"
    assert "missing data rule" in claims[0].verification_notes.lower()


def test_verify_unmatched_institution(mock_exec_result):
    verifier = NumericalClaimVerifier()
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="Unknown University scored 80.0 in score.",
        claim_type="METRIC_VALUE",
        metric="score",
        institution_name="Nonexistent University XYZ",
        claimed_value=80.0,
    )
    claims, summary = verifier.verify_claims([claim], mock_exec_result)
    assert claims[0].verification_status == "UNVERIFIED"
    assert summary.unverified_claims == 1

