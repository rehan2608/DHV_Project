"""
Unit and regression tests for Phase 6.1.4 Benchmark Accounting Reconciliation.
Enforces mathematical rigor:
  - Strict 1-to-1 claim-to-fact mapping
  - TP + FN == Expected Facts identity across all benchmarks and pooled
  - BM-04 9 TP vs 9 Expected Facts (Coverage == 1.0000, not 1.2857)
  - BM-01 1 TP + 4 FN == 5 Expected Facts
  - Zero-denominator handling for BM-02 and BM-05 (None / N/A)
  - Pooled accounting: 36 Expected Facts == 32 TP + 4 FN (Micro Recall = 88.89%)
"""

import json
import pytest
from pathlib import Path
from scripts.recompute_phase_6_1_4_metrics import reconcile_benchmark_accounting, build_expected_facts_inventory


@pytest.fixture(scope="module")
def audit_results():
    """Run reconciliation and return structured audit results."""
    return reconcile_benchmark_accounting()


@pytest.fixture(scope="module")
def claim_records():
    """Load claim-level reconciliation records."""
    reconciliation_file = Path("docs/phase_6_1_4_claim_level_reconciliation.json")
    with open(reconciliation_file, "r", encoding="utf-8") as f:
        return json.load(f)


def test_bm04_accounting_reconciliation(audit_results):
    """
    Verify BM-04 resolution:
    9 claims generated, 9 expected facts derived from analytical execution,
    9 TP, 0 FP, 0 FN. Coverage is exactly 1.0000, not 1.2857.
    """
    bm04 = audit_results["benchmarks"]["BM-04"]
    assert bm04["expected_facts_count"] == 9
    assert bm04["generated_claims_count"] == 9
    assert bm04["true_positives"] == 9
    assert bm04["false_positives"] == 0
    assert bm04["false_negatives"] == 0
    assert bm04["precision"] == 1.0
    assert bm04["recall"] == 1.0
    assert bm04["extraction_coverage"] == 1.0
    assert bm04["verification_coverage"] == 1.0
    assert bm04["accounting_identity_holds"] is True
    # Mathematical assertion: TP + FN == Expected Facts
    assert bm04["true_positives"] + bm04["false_negatives"] == bm04["expected_facts_count"]


def test_bm01_accounting_reconciliation(audit_results):
    """
    Verify BM-01 accounting:
    5 expected facts, 1 TP (valid observations = 5), 4 FN (Jain +33, departed=16, new=2, excluded=23).
    Identity holds: 1 TP + 4 FN == 5 Expected Facts.
    """
    bm01 = audit_results["benchmarks"]["BM-01"]
    assert bm01["expected_facts_count"] == 5
    assert bm01["true_positives"] == 1
    assert bm01["false_negatives"] == 4
    assert bm01["false_positives"] == 0
    assert bm01["precision"] == 1.0
    assert round(bm01["recall"], 2) == 0.20
    assert round(bm01["extraction_coverage"], 2) == 0.20
    assert bm01["accounting_identity_holds"] is True
    assert bm01["true_positives"] + bm01["false_negatives"] == bm01["expected_facts_count"]


def test_zero_denominator_handling_bm02_and_bm05(audit_results):
    """
    Verify zero-denominator benchmarks BM-02 and BM-05:
    Must report None (N/A) rather than 1.0 or 0.0 for precision, recall, and coverage.
    """
    for bmid in ["BM-02", "BM-05"]:
        rep = audit_results["benchmarks"][bmid]
        assert rep["expected_facts_count"] == 0
        assert rep["true_positives"] == 0
        assert rep["false_negatives"] == 0
        assert rep["false_positives"] == 0
        assert rep["precision"] is None
        assert rep["recall"] is None
        assert rep["extraction_coverage"] is None
        assert rep["verification_coverage"] is None
        assert rep["unresolved_rate"] is None


def test_pooled_accounting_identity(audit_results):
    """
    Verify global pooled accounting identity:
    Pooled TP (32) + Pooled FN (4) == Total Expected Facts (36).
    Micro precision = 100%, Micro recall = 88.89%.
    """
    pooled = audit_results["pooled_metrics"]
    tp = pooled["pooled_true_positives"]
    fn = pooled["pooled_false_negatives"]
    fp = pooled["pooled_false_positives"]
    total = pooled["total_expected_numerical_facts"]

    assert total == 36
    assert tp == 32
    assert fn == 4
    assert fp == 0
    assert tp + fn == total
    assert pooled["micro_precision"] == 1.0
    assert round(pooled["micro_recall"], 4) == round(32 / 36, 4)
    assert pooled["macro_precision"] == 1.0
    assert round(pooled["macro_recall"], 4) == round((0.20 + 1.0 + 1.0 + 1.0 + 1.0) / 5, 4)


def test_one_to_one_claim_to_fact_mapping(claim_records):
    """
    Verify that no expected fact is credited multiple times across claims.
    """
    matched_facts = set()
    for record in claim_records:
        fid = record.get("matching_expected_fact_id")
        if fid is not None:
            assert fid not in matched_facts, f"Duplicate credit detected for fact {fid} in claim {record['claim_id']}"
            matched_facts.add(fid)

    # Exactly 32 distinct facts matched
    assert len(matched_facts) == 32


def test_strict_coverage_bounds(audit_results):
    """
    Verify that all coverage and recall values for eligible benchmarks are strictly in [0.0, 1.0].
    """
    for bmid, rep in audit_results["benchmarks"].items():
        if rep["expected_facts_count"] > 0:
            cov = rep["extraction_coverage"]
            rec = rep["recall"]
            prec = rep["precision"]
            assert 0.0 <= cov <= 1.0, f"Extraction coverage {cov} out of bounds for {bmid}"
            assert 0.0 <= rec <= 1.0, f"Recall {rec} out of bounds for {bmid}"
            assert 0.0 <= prec <= 1.0, f"Precision {prec} out of bounds for {bmid}"

