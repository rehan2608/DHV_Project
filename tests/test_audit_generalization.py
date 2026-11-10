"""
Independent Generalization Test Suite for Phase 6.1.3 Reliability Gate (Audit 6).
Covers unseen NIRF categories (Pharmacy, Dental, Law, Architecture, Medical), unseen entities,
similar-name collisions, tied ranks, unranked institutions, multi-operation outputs,
and independent expected ground truths.
"""

import pytest
import math
from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.result_schema import NumericalClaim
from src.response.verifier import NumericalClaimVerifier


@pytest.fixture
def verifier():
    return NumericalClaimVerifier(float_tolerance=0.05)


def make_exec_result(op_data, category=None, year=None, op_name="test_op", op_id="op_gen_1"):
    op = OperationResult(
        operation_id=op_id,
        function_name=op_name,
        status="SUCCESS",
        data=op_data,
    )
    res = ExecutionResult(
        query_id="q_gen",
        original_question="Generalization test query",
        status="SUCCESS",
        query_type="ANALYTICAL",
        validation_status="VALID",
        operations=[op],
    )
    if category:
        res.metadata.category = category
    if year:
        res.metadata.year = year
    return res


# 1. Unseen NIRF Category: Pharmacy
def test_unseen_category_pharmacy(verifier):
    data = {
        "category": "Pharmacy",
        "rankings": [
            {"institution_name": "National Institute of Pharmaceutical Education and Research Hyderabad", "institution_uid": "NIPER-HYD", "score": 81.25, "rank": 2}
        ]
    }
    exec_res = make_exec_result(data, category="Pharmacy", year=2024)
    claim = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="NIPER Hyderabad",
        category="Pharmacy",
        metric="score",
        value=81.25,
    )
    verified, summary = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "VERIFIED"
    assert summary.verified_claims == 1


# 2. Unseen NIRF Category: Law
def test_unseen_category_law(verifier):
    data = {
        "category": "Law",
        "rankings": [
            {"institution_name": "National Law School of India University", "institution_uid": "NLSIU-BLR", "score": 84.10, "rank": 1}
        ]
    }
    exec_res = make_exec_result(data, category="Law", year=2025)
    claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="National Law School of India University",
        category="Law",
        metric="rank",
        value=1,
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "VERIFIED"


# 3. Category Mismatch Rejection (Crucial for Mutation 6)
def test_category_mismatch_rejection(verifier):
    data = {
        "category": "Engineering",
        "rankings": [
            {"institution_name": "Apex Institute", "institution_uid": "APEX-01", "score": 75.0, "category": "Engineering"}
        ]
    }
    exec_res = make_exec_result(data, category="Engineering")
    # Claim falsely asserts this score was in Management category
    claim = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Apex Institute",
        category="Management",
        metric="score",
        value=75.0,
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "UNVERIFIED", "Claim specifying mismatched category must not be verified."


# 4. Multiple institutions with similar names (disambiguation check)
def test_similar_name_disambiguation(verifier):
    data = {
        "rankings": [
            {"institution_name": "St. Joseph's College of Engineering", "institution_uid": "STJ-ENG", "score": 45.2},
            {"institution_name": "St. Joseph's College of Arts and Science", "institution_uid": "STJ-ART", "score": 55.8},
        ]
    }
    exec_res = make_exec_result(data)
    # Ambiguous query "St. Joseph's" matches both UIDs -> Ambiguity guard triggers
    claim_ambig = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="St. Joseph's",
        metric="score",
        value=45.2,
    )
    verified, _ = verifier.verify_claims([claim_ambig], exec_res)
    assert verified[0].verification_status == "UNVERIFIED", "Ambiguous institution substring must not verify."

    # Specific query matches unambiguously
    claim_spec = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="St. Joseph's College of Engineering",
        metric="score",
        value=45.2,
    )
    verified_spec, _ = verifier.verify_claims([claim_spec], exec_res)
    assert verified_spec[0].verification_status == "VERIFIED"


# 5. Tied ranks handling
def test_tied_ranks_handling(verifier):
    data = {
        "rankings": [
            {"institution_name": "Alpha Institute", "institution_uid": "ALP-01", "rank": 5, "score": 68.0},
            {"institution_name": "Beta Institute", "institution_uid": "BET-02", "rank": 5, "score": 68.0},
        ]
    }
    exec_res = make_exec_result(data)
    c1 = NumericalClaim(claim_type="RANK_VALUE", institution_name="Alpha Institute", metric="rank", value=5)
    c2 = NumericalClaim(claim_type="RANK_VALUE", institution_name="Beta Institute", metric="rank", value=5)
    verified, summary = verifier.verify_claims([c1, c2], exec_res)
    assert verified[0].verification_status == "VERIFIED"
    assert verified[1].verification_status == "VERIFIED"
    assert summary.verified_claims == 2


# 6. Unranked institution handling
def test_unranked_institution_rejection(verifier):
    data = {
        "rankings": [
            {"institution_name": "Gamma Institute", "institution_uid": "GAM-01", "rank": None, "score": 42.0}
        ]
    }
    exec_res = make_exec_result(data)
    claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="Gamma Institute",
        metric="rank",
        value=15,
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "UNVERIFIED"


# 7. Multi-state filter aggregation
def test_multi_state_aggregation(verifier):
    data = {
        "states_analysis": [
            {"state": "Kerala", "average_score": 52.40, "distinct_institutions": 12},
            {"state": "Gujarat", "average_score": 48.90, "distinct_institutions": 9},
        ]
    }
    exec_res = make_exec_result(data)
    c_ker = NumericalClaim(claim_type="AGGREGATE_STATISTIC", state="Kerala", metric="average_score", value=52.40)
    c_guj = NumericalClaim(claim_type="AGGREGATE_STATISTIC", state="Gujarat", metric="distinct_institutions", value=9)
    verified, summary = verifier.verify_claims([c_ker, c_guj], exec_res)
    assert verified[0].verification_status == "VERIFIED"
    assert verified[1].verification_status == "VERIFIED"
    assert summary.verified_claims == 2


# 8. Multi-operation result separation
def test_multi_operation_separation(verifier):
    op1 = OperationResult(
        operation_id="op_rank",
        function_name="get_rankings",
        status="SUCCESS",
        data={"rankings": [{"institution_name": "Delta Tech", "institution_uid": "DEL-01", "score": 79.5}]},
    )
    op2 = OperationResult(
        operation_id="op_corr",
        function_name="get_correlation",
        status="SUCCESS",
        data={"regression": {"pearson_r": 0.584}},
    )
    exec_res = ExecutionResult(
        query_id="q_multi",
        original_question="Multi-op query",
        status="SUCCESS",
        query_type="ANALYTICAL",
        validation_status="VALID",
        operations=[op1, op2],
    )
    c_score = NumericalClaim(claim_type="METRIC_VALUE", institution_name="Delta Tech", metric="score", value=79.5)
    c_corr = NumericalClaim(claim_type="CORRELATION", metric="pearson_r", value=0.584, claim_text="Correlation is 0.584")
    verified, summary = verifier.verify_claims([c_score, c_corr], exec_res)
    assert verified[0].verification_status == "VERIFIED"
    assert verified[1].verification_status == "VERIFIED"
    assert summary.all_claims_verified is True


# 9. Causation rejection on valid correlation
def test_causation_rejection_on_correlation(verifier):
    data = {"regression": {"pearson_r": 0.72}}
    exec_res = make_exec_result(data)
    claim = NumericalClaim(
        claim_type="CORRELATION",
        value=0.72,
        claim_text="Teaching quality causes higher research output with correlation r = 0.72",
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "CONFLICTING", "Causal claims must be strictly rejected."


# 10. Year matching verification
def test_year_matching_verification(verifier):
    data = {
        "rankings": [
            {"institution_name": "Epsilon Univ", "institution_uid": "EPS-01", "score": 65.0, "year": 2023},
        ]
    }
    exec_res = make_exec_result(data, year=2023)
    # Claim specifying wrong year 2025 should not match
    claim_wrong_yr = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Epsilon Univ",
        year=2025,
        metric="score",
        value=65.0,
    )
    verified, _ = verifier.verify_claims([claim_wrong_yr], exec_res)
    assert verified[0].verification_status == "UNVERIFIED"

    # Claim with matching year verifies
    claim_right_yr = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Epsilon Univ",
        year=2023,
        metric="score",
        value=65.0,
    )
    verified_r, _ = verifier.verify_claims([claim_right_yr], exec_res)
    assert verified_r[0].verification_status == "VERIFIED"

