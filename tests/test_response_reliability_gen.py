"""
Phase 6.1 Generalization & Reliability Test Suite.
Verifies numerical verification, claim auditing, and structured generation
across unseen institutions, categories, metrics, geographic aggregates, and response formats
without relying on any hardcoded benchmark constants.
"""

import json
from unittest.mock import MagicMock
import pytest

from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.claim_auditor import IndependentClaimAuditor
from src.response.claim_extractor import ClaimExtractor
from src.response.generator import ResponseGenerator
from src.response.result_schema import NumericalClaim
from src.response.verifier import NumericalClaimVerifier


# ---------------------------------------------------------------------------
# Test Fixtures for Diverse Unseen Cohorts
# ---------------------------------------------------------------------------

@pytest.fixture
def management_exec_result() -> ExecutionResult:
    """Unseen Management cohort execution data (IIMs and private B-schools)."""
    op = OperationResult(
        operation_id="op_mgmt",
        function_name="get_top_institutions",
        status="SUCCESS",
        data={
            "rankings": [
                {
                    "institution_name": "Indian Institute of Management Ahmedabad",
                    "institute_name_std": "Indian Institute of Management Ahmedabad",
                    "institution_uid": "MGMT-001",
                    "rank": 1,
                    "score": 83.20,
                    "parameters": {"tlr": 85.10, "rpc": 78.40, "go": 89.20, "oi": 72.10, "perception": 100.0},
                },
                {
                    "institution_name": "Indian Institute of Management Bangalore",
                    "institute_name_std": "Indian Institute of Management Bangalore",
                    "institution_uid": "MGMT-002",
                    "rank": 2,
                    "score": 80.50,
                    "parameters": {"tlr": 82.30, "rpc": 76.10, "go": 87.50, "oi": 70.40, "perception": 98.2},
                },
                {
                    "institution_name": "XLRI Xavier School of Management",
                    "institute_name_std": "XLRI Xavier School of Management",
                    "institution_uid": "MGMT-008",
                    "rank": 8,
                    "score": 70.15,
                    "parameters": {"tlr": 72.00, "rpc": 55.40, "go": 81.30, "oi": 68.00, "perception": 84.0},
                },
            ]
        },
    )
    return ExecutionResult(
        execution_id="e_mgmt",
        query_id="q_mgmt",
        original_question="Top management institutions in 2024?",
        status="SUCCESS",
        query_type="category_performance",
        operations=[op],
        validation_status="VALID",
    )


@pytest.fixture
def pharmacy_regression_exec_result() -> ExecutionResult:
    """Unseen Pharmacy cohort regression data between TLR and RPC."""
    op = OperationResult(
        operation_id="op_pharm_reg",
        function_name="get_parameter_relationship",
        status="SUCCESS",
        data={
            "param_x": "rpc",
            "param_y": "tlr",
            "regression": {
                "slope": 0.4512,
                "intercept": 42.1850,
                "r_squared": 0.3845,
                "pearson_r": 0.6201,
                "spearman_rho": 0.5892,
            },
            "points": [
                {
                    "institution_name": "Jamia Hamdard",
                    "institute_name_std": "Jamia Hamdard",
                    "institution_uid": "PHARM-01",
                    "rank": 1,
                    "score": 82.50,
                    "x": 80.20,
                    "y": 85.10,
                },
                {
                    "institution_name": "Panjab University",
                    "institute_name_std": "Panjab University",
                    "institution_uid": "PHARM-02",
                    "rank": 2,
                    "score": 79.40,
                    "x": 75.30,
                    "y": 81.20,
                },
            ],
        },
    )
    return ExecutionResult(
        execution_id="e_pharm",
        query_id="q_pharm",
        original_question="Relationship between RPC and TLR in Pharmacy?",
        status="SUCCESS",
        query_type="parameter_relationship",
        operations=[op],
        validation_status="VALID",
    )


@pytest.fixture
def geographic_multi_state_exec_result() -> ExecutionResult:
    """Unseen multi-state geographic comparison data."""
    op = OperationResult(
        operation_id="op_geo",
        function_name="get_geographic_analysis",
        status="SUCCESS",
        data={
            "states_analysis": [
                {
                    "state": "Maharashtra",
                    "distinct_institutions": 42,
                    "total_ranked_entries": 45,
                    "average_score": 54.32,
                    "median_score": 51.10,
                    "average_rpc": 44.80,
                    "average_tlr": 58.90,
                    "top_10_institutions": 2,
                    "top_50_institutions": 8,
                },
                {
                    "state": "Delhi",
                    "distinct_institutions": 28,
                    "total_ranked_entries": 30,
                    "average_score": 62.15,
                    "median_score": 59.40,
                    "average_rpc": 55.20,
                    "average_tlr": 66.80,
                    "top_10_institutions": 4,
                    "top_50_institutions": 11,
                },
            ]
        },
    )
    return ExecutionResult(
        execution_id="e_geo",
        query_id="q_geo",
        original_question="Compare Maharashtra and Delhi institutional performance?",
        status="SUCCESS",
        query_type="geographic_analysis",
        operations=[op],
        validation_status="VALID",
    )


# ---------------------------------------------------------------------------
# 1. Unseen Institution & Metric Verification Tests
# ---------------------------------------------------------------------------

def test_unseen_management_parameter_verification(management_exec_result):
    """Verifies that un-hardcoded Management institutions and parameters are verified accurately."""
    verifier = NumericalClaimVerifier(float_tolerance=0.05)

    claims = [
        NumericalClaim(
            claim_type="METRIC_VALUE",
            institution_name="IIM Ahmedabad",
            metric="score",
            claimed_value=83.20,
        ),
        NumericalClaim(
            claim_type="METRIC_VALUE",
            institution_name="IIM Bangalore",
            metric="rpc",
            claimed_value=76.10,
        ),
        NumericalClaim(
            claim_type="RANK_VALUE",
            institution_name="XLRI Xavier School of Management",
            metric="rank",
            claimed_value=8,
        ),
        NumericalClaim(
            claim_type="METRIC_VALUE",
            institution_name="IIM Ahmedabad",
            metric="score",
            claimed_value=99.00,  # Discrepant
        ),
    ]

    verified_claims, summary = verifier.verify_claims(claims, management_exec_result)

    assert summary.total_claims == 4
    assert summary.verified_claims == 3
    assert summary.conflicting_claims == 1
    assert verified_claims[0].verification_status == "VERIFIED"
    assert verified_claims[1].verification_status == "VERIFIED"
    assert verified_claims[2].verification_status == "VERIFIED"
    assert verified_claims[3].verification_status == "CONFLICTING"


# ---------------------------------------------------------------------------
# 2. Nested Regression & Correlation Verification Tests
# ---------------------------------------------------------------------------

def test_nested_regression_statistics_verification(pharmacy_regression_exec_result):
    """Ensures nested regression coefficients (pearson_r, spearman_rho, r_squared) are correctly indexed and verified."""
    verifier = NumericalClaimVerifier(float_tolerance=0.05)

    claims = [
        NumericalClaim(
            claim_type="CORRELATION",
            claim_text="The Pearson correlation between RPC and TLR was 0.6201.",
            metric="correlation",
            claimed_value=0.6201,
        ),
        NumericalClaim(
            claim_type="CORRELATION",
            claim_text="The Spearman rank correlation was 0.5892.",
            metric="spearman_rho",
            claimed_value=0.5892,
        ),
        NumericalClaim(
            claim_type="METRIC_VALUE",
            institution_name="Jamia Hamdard",
            metric="rpc",
            claimed_value=80.20,
        ),
    ]

    verified_claims, summary = verifier.verify_claims(claims, pharmacy_regression_exec_result)

    assert summary.all_claims_verified is True
    assert summary.verified_claims == 3
    assert verified_claims[0].verification_status == "VERIFIED"
    assert verified_claims[1].verification_status == "VERIFIED"
    assert verified_claims[2].verification_status == "VERIFIED"


def test_causality_prohibition_rejection(pharmacy_regression_exec_result):
    """Enforces rejection of correlation claims that assert causal relationships."""
    verifier = NumericalClaimVerifier(float_tolerance=0.05)

    claims = [
        NumericalClaim(
            claim_type="CORRELATION",
            claim_text="Higher RPC causes a substantial increase in TLR with r = 0.6201.",
            statement="Higher RPC causes TLR",
            claimed_value=0.6201,
        ),
    ]

    verified_claims, summary = verifier.verify_claims(claims, pharmacy_regression_exec_result)

    assert summary.conflicting_claims == 1
    assert verified_claims[0].verification_status == "CONFLICTING"
    assert "causal" in verified_claims[0].verification_notes.lower()


# ---------------------------------------------------------------------------
# 3. Geographic Aggregate Statistics Verification Tests
# ---------------------------------------------------------------------------

def test_geographic_aggregate_statistics_verification(geographic_multi_state_exec_result):
    """Verifies state average scores, parameter averages, and institution counts."""
    verifier = NumericalClaimVerifier(float_tolerance=0.05)

    claims = [
        NumericalClaim(
            claim_type="AGGREGATE_STATISTIC",
            state="Maharashtra",
            metric="average_score",
            claimed_value=54.32,
        ),
        NumericalClaim(
            claim_type="AGGREGATE_STATISTIC",
            state="Delhi",
            metric="average_rpc",
            claimed_value=55.20,
        ),
        NumericalClaim(
            claim_type="AGGREGATE_STATISTIC",
            state="Delhi",
            metric="distinct_institutions",
            claimed_value=28,
        ),
        NumericalClaim(
            claim_type="AGGREGATE_STATISTIC",
            state="Maharashtra",
            metric="average_score",
            claimed_value=65.00,  # Discrepant
        ),
    ]

    verified_claims, summary = verifier.verify_claims(claims, geographic_multi_state_exec_result)

    assert summary.total_claims == 4
    assert summary.verified_claims == 3
    assert summary.conflicting_claims == 1
    assert verified_claims[0].verification_status == "VERIFIED"
    assert verified_claims[1].verification_status == "VERIFIED"
    assert verified_claims[2].verification_status == "VERIFIED"
    assert verified_claims[3].verification_status == "CONFLICTING"


# ---------------------------------------------------------------------------
# 4. Independent Claim Auditor & Coverage Tests
# ---------------------------------------------------------------------------

def test_auditor_identifies_omitted_prose_claims(management_exec_result):
    """
    Tests that if the model's structured claim list omits a numerical assertion made in prose,
    the IndependentClaimAuditor detects it, adds it to the claims audit, and reduces extraction coverage.
    """
    auditor = IndependentClaimAuditor(float_tolerance=0.05)

    prose = (
        "IIM Ahmedabad led with a score of 83.20. "
        "IIM Bangalore followed closely with a score of 80.50 and an RPC of 76.10."
    )

    # Model provides only 1 of the 3 numbers in its structured claims
    llm_claims = [
        {
            "statement": "IIM Ahmedabad led with a score of 83.20.",
            "claim_type": "METRIC_VALUE",
            "institution_name": "IIM Ahmedabad",
            "metric": "score",
            "value": 83.20,
        }
    ]

    reconciled_claims, audit_meta = auditor.audit_and_reconcile(
        prose_answer=prose,
        structured_claims=llm_claims,
        execution_result=management_exec_result,
    )

    # The 2 missing numbers (score 80.50 and rpc 76.10) must be flagged and reconciled
    assert audit_meta["structured_claims_count"] == 1
    assert audit_meta["omitted_from_structured_count"] >= 1
    assert audit_meta["extraction_coverage"] < 1.0

    # Ensure all claims (including omitted ones) are present for verifier
    verifier = NumericalClaimVerifier(float_tolerance=0.05)
    audited_claims, summary = verifier.verify_claims(reconciled_claims, management_exec_result)

    # Even the prose-only assertions are audited against ground truth
    assert summary.verified_claims >= 2


def test_auditor_full_coverage_when_complete(management_exec_result):
    """Tests that full claim coverage (1.0) is achieved when all prose facts are represented in structured claims."""
    auditor = IndependentClaimAuditor(float_tolerance=0.05)

    prose = "IIM Ahmedabad achieved a score of 83.20."
    llm_claims = [
        {
            "statement": "IIM Ahmedabad achieved a score of 83.20.",
            "claim_type": "METRIC_VALUE",
            "institution_name": "IIM Ahmedabad",
            "metric": "score",
            "value": 83.20,
        }
    ]

    reconciled_claims, audit_meta = auditor.audit_and_reconcile(
        prose_answer=prose,
        structured_claims=llm_claims,
        execution_result=management_exec_result,
    )

    assert audit_meta["extraction_coverage"] == 1.0
    assert audit_meta["omitted_from_structured_count"] == 0


# ---------------------------------------------------------------------------
# 5. Generator JSON Parsing & Fallback Tests
# ---------------------------------------------------------------------------

def test_generator_parses_json_with_code_fences(management_exec_result):
    """Ensures ResponseGenerator cleanly handles LLM outputs wrapped in ```json markdown fences."""
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"

    payload = {
        "answer": "### Key Findings\n- IIM Ahmedabad ranked #1 with 83.20 score.",
        "claims": [
            {
                "statement": "IIM Ahmedabad ranked #1 with 83.20 score.",
                "claim_type": "METRIC_VALUE",
                "institution_name": "IIM Ahmedabad",
                "metric": "score",
                "value": 83.20,
            }
        ],
    }
    mock_llm.generate.return_value = f"```json\n{json.dumps(payload)}\n```"

    gen = ResponseGenerator(gemma_client=mock_llm)
    resp = gen.generate_response("Top management?", execution_result=management_exec_result)

    assert resp.response_status == "SUCCESS"
    assert resp.verification_summary.all_claims_verified is True
    assert len(resp.numerical_claims) >= 1
    assert resp.numerical_claims[0].verification_status == "VERIFIED"


def test_generator_raw_text_fallback_handling(management_exec_result):
    """Ensures ResponseGenerator safely falls back to text extraction when LLM returns plain prose."""
    mock_llm = MagicMock()
    mock_llm.model = "mock-gemma"
    mock_llm.generate.return_value = (
        "### Key Findings\n- IIM Ahmedabad achieved a score of 83.20 and IIM Bangalore achieved 80.50."
    )

    gen = ResponseGenerator(gemma_client=mock_llm)
    resp = gen.generate_response("Top management?", execution_result=management_exec_result)

    assert resp.response_status == "SUCCESS"
    assert resp.verification_summary.all_claims_verified is True
    assert len(resp.numerical_claims) >= 2
    assert all(c.verification_status == "VERIFIED" for c in resp.numerical_claims)


# ---------------------------------------------------------------------------
# 6. Evaluation Metrics Verification Test
# ---------------------------------------------------------------------------

def test_summary_evaluation_metrics_computation():
    """Validates accuracy of precision, recall, and extraction coverage in VerificationSummary."""
    verifier = NumericalClaimVerifier(float_tolerance=0.05)

    claims = [
        NumericalClaim(claim_type="COUNT", claimed_value=42),
        NumericalClaim(claim_type="COUNT", claimed_value=999),  # Unverified
    ]

    mock_exec = ExecutionResult(
        execution_id="e_eval",
        query_id="q_eval",
        original_question="Eval test",
        status="SUCCESS",
        query_type="TOP_INSTITUTIONS",
        operations=[
            OperationResult(
                operation_id="op_eval",
                function_name="get_top_institutions",
                status="SUCCESS",
                data={"counts": 42},
            )
        ],
        validation_status="VALID",
    )

    verified_claims, summary = verifier.verify_claims(claims, mock_exec)

    assert summary.total_claims == 2
    assert summary.verified_claims == 1
    assert summary.unverified_claims == 1
    assert summary.conflicting_claims == 0
    assert summary.verification_precision == 1.0
    assert summary.verification_recall == 0.5

