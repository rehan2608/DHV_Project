"""
Regression tests for Semantic Fact Deduplication in IndependentClaimAuditor (Audit 2).
Verifies that distinct facts are never merged across categories, cohorts, operations,
entities, statistics, or comparisons, while identical duplicate assertions are deduplicated.
"""

import pytest
from src.response.claim_auditor import IndependentClaimAuditor
from src.response.result_schema import NumericalClaim


def test_truly_identical_repeated_claims_are_deduplicated():
    auditor = IndependentClaimAuditor()
    c1 = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Indian Institute of Technology Madras",
        institution_uid="IN-ENG-01",
        category="Engineering",
        year=2025,
        metric="score",
        value=88.72,
        claim_text="IIT Madras scored 88.72 in Engineering.",
    )
    c2 = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Indian Institute of Technology Madras",
        institution_uid="IN-ENG-01",
        category="Engineering",
        year=2025,
        metric="score",
        value=88.72,
        claim_text="In summary, IIT Madras scored 88.72 in Engineering.",
    )

    reconciled, _ = auditor.audit_and_reconcile("", [c1, c2], None)
    assert len(reconciled) == 1, "Identical duplicate facts must be deduplicated."


def test_different_categories_are_never_merged():
    auditor = IndependentClaimAuditor()
    # Same institution, same year, same metric, same score, but different categories
    c_eng = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Indian Institute of Science",
        institution_uid="IN-UNIV-01",
        category="Engineering",
        year=2025,
        metric="score",
        value=85.00,
        claim_text="IISc scored 85.00 in Engineering.",
    )
    c_univ = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Indian Institute of Science",
        institution_uid="IN-UNIV-01",
        category="University",
        year=2025,
        metric="score",
        value=85.00,
        claim_text="IISc also scored 85.00 in University category.",
    )

    reconciled, _ = auditor.audit_and_reconcile("", [c_eng, c_univ], None)
    assert len(reconciled) == 2, "Distinct categories must never be merged even if value and metric match."


def test_different_cohorts_are_never_merged():
    auditor = IndependentClaimAuditor()
    c_top10 = NumericalClaim(
        claim_type="COUNT",
        metric="count",
        state="Tamil Nadu",
        value=2,
        claim_text="Tamil Nadu has 2 institutions in the top 10.",
    )
    c_outliers = NumericalClaim(
        claim_type="COUNT",
        metric="count",
        state="Tamil Nadu",
        value=2,
        claim_text="Tamil Nadu has 2 outlier institutions.",
    )

    reconciled, _ = auditor.audit_and_reconcile("", [c_top10, c_outliers], None)
    assert len(reconciled) == 2, "Different cohorts or scopes must never be merged."


def test_different_operations_are_not_merged_when_contexts_differ():
    auditor = IndependentClaimAuditor()
    c_op1 = NumericalClaim(
        claim_type="COUNT",
        operation_id="op_rankings",
        metric="count",
        value=10,
        claim_text="Rankings cohort size is 10.",
    )
    c_op2 = NumericalClaim(
        claim_type="COUNT",
        operation_id="op_clusters",
        metric="count",
        value=10,
        claim_text="Cluster count is 10.",
    )

    reconciled, _ = auditor.audit_and_reconcile("", [c_op1, c_op2], None)
    assert len(reconciled) == 2, "Distinct operations with different context must not be merged."


def test_different_entities_are_never_merged():
    auditor = IndependentClaimAuditor()
    c_tn = NumericalClaim(
        claim_type="AGGREGATE_STATISTIC",
        state="Tamil Nadu",
        metric="score",
        value=50.00,
        claim_text="Tamil Nadu average score is 50.00.",
    )
    c_ka = NumericalClaim(
        claim_type="AGGREGATE_STATISTIC",
        state="Karnataka",
        metric="score",
        value=50.00,
        claim_text="Karnataka average score is 50.00.",
    )

    reconciled, _ = auditor.audit_and_reconcile("", [c_tn, c_ka], None)
    assert len(reconciled) == 2, "Different entities with identical values must never be merged."


def test_different_statistic_types_are_never_merged():
    auditor = IndependentClaimAuditor()
    c_mean = NumericalClaim(
        claim_type="AGGREGATE_STATISTIC",
        state="Tamil Nadu",
        metric="score",
        statistic_type="mean",
        value=58.53,
        claim_text="Tamil Nadu average score is 58.53.",
    )
    c_median = NumericalClaim(
        claim_type="AGGREGATE_STATISTIC",
        state="Tamil Nadu",
        metric="score",
        statistic_type="median",
        value=58.53,
        claim_text="Tamil Nadu median score is 58.53.",
    )

    reconciled, _ = auditor.audit_and_reconcile("", [c_mean, c_median], None)
    assert len(reconciled) == 2, "Mean and median must never be merged even if identical in value."


def test_missing_metadata_handled_conservatively():
    auditor = IndependentClaimAuditor()
    # One claim has full metadata, second claim has missing category
    c_rich = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="IIT Delhi",
        category="Engineering",
        year=2025,
        metric="rpc",
        value=93.47,
        claim_text="IIT Delhi scored 93.47 in RPC for Engineering in 2025.",
    )
    c_sparse = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="IIT Delhi",
        metric="rpc",
        value=93.47,
        claim_text="IIT Delhi RPC was 93.47.",
    )

    # When categories are not conflicting (sparse category is None), auditor should not duplicate
    reconciled, _ = auditor.audit_and_reconcile("", [c_rich, c_sparse], None)
    assert len(reconciled) == 1, "Compatible assertion without conflicting metadata should not be duplicated."
    assert reconciled[0].category == "Engineering", "Richer metadata must be preserved."

