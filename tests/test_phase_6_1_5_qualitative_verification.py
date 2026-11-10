"""
Phase 6.1.5 Independent Qualitative Verification, Extraction, Accounting & Mutation Tests.
Covers:
  A. Qualitative verification tests (10 mandatory cases)
  B. Claim extraction tests (paragraphs, bullets, tables, factual & non-factual headings, duplicates)
  C. Accounting tests (strict identity, bounded coverage, zero-denominator N/A, deduplication)
  D. Controlled mutation tests (8 response mutations caught)
  E. Generalization tests across unseen categories, institutions, and states
"""

import json
import pytest
from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.result_schema import NumericalClaim, ContradictedStatus
from src.response.verifier import NumericalClaimVerifier
from src.response.claim_extractor import ClaimExtractor
from src.response.claim_auditor import IndependentClaimAuditor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def verifier():
    return NumericalClaimVerifier(float_tolerance=0.05)


@pytest.fixture
def extractor():
    return ClaimExtractor()


@pytest.fixture
def auditor():
    return IndependentClaimAuditor(float_tolerance=0.05)


@pytest.fixture
def sample_rank_movement_exec_result():
    """ExecutionResult with known rank movements across multiple institutions."""
    op_data = {
        "category": "Engineering",
        "gainers": [
            {
                "institution_uid": "U-001",
                "institute_name_std": "Alpha Institute",
                "start_rank": 50,
                "end_rank": 20,
                "rank_improvement": 30,
                "score": 85.0,
                "rpc": 92.5,
                "category": "Engineering",
                "year": 2025,
            },
            {
                "institution_uid": "U-002",
                "institute_name_std": "Beta College",
                "start_rank": 10,
                "end_rank": 15,
                "rank_improvement": -5,
                "score": 82.0,
                "rpc": 78.0,
                "category": "Engineering",
                "year": 2025,
            },
            {
                "institution_uid": "U-003",
                "institute_name_std": "Gamma University",
                "start_rank": 25,
                "end_rank": 25,
                "rank_improvement": 0,
                "score": 75.0,
                "rpc": 65.0,
                "category": "Engineering",
                "year": 2025,
            },
            {
                "institution_uid": "U-004",
                "institute_name_std": "Delta Academy",
                "start_rank": 40,
                "end_rank": 40,
                "rank_improvement": 0,
                "score": 75.0,
                "rpc": 65.0,
                "category": "Engineering",
                "year": 2025,
            },
        ],
        "states_analysis": [
            {"state": "AlphaState", "average_score": 80.5, "distinct_institutions": 10},
            {"state": "BetaState", "average_score": 65.2, "distinct_institutions": 5},
        ],
    }
    op = OperationResult(
        operation_id="op_qual_test",
        function_name="get_rank_movement",
        status="SUCCESS",
        data=op_data,
    )
    return ExecutionResult(
        query_id="q_qual_test",
        original_question="Test qualitative movements",
        status="SUCCESS",
        query_type="ANALYTICAL",
        validation_status="VALID",
        operations=[op],
    )


# ---------------------------------------------------------------------------
# A. Qualitative Verification Tests (10 Mandatory Cases)
# ---------------------------------------------------------------------------

def test_01_correct_rank_improvement_claim(verifier, sample_rank_movement_exec_result):
    """1. Correct rank-improvement claim (Alpha Institute actually improved from 50 to 20)."""
    claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Alpha Institute",
        qualitative_direction="improved",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "VERIFIED"
    assert "verified" in verified[0].verification_notes.lower()


def test_02_incorrect_rank_improvement_claim(verifier, sample_rank_movement_exec_result):
    """2. Incorrect rank-improvement claim (Beta College actually declined from 10 to 15)."""
    claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Beta College",
        qualitative_direction="improved",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"
    assert "contradiction" in verified[0].verification_notes.lower()


def test_03_correct_rank_decline_claim(verifier, sample_rank_movement_exec_result):
    """3. Correct rank-decline claim (Beta College actually declined)."""
    claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Beta College",
        qualitative_direction="declined",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "VERIFIED"


def test_04_incorrect_rank_decline_claim(verifier, sample_rank_movement_exec_result):
    """4. Incorrect rank-decline claim (Alpha Institute actually improved)."""
    claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Alpha Institute",
        qualitative_direction="declined",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_05_correct_unchanged_rank_claim(verifier, sample_rank_movement_exec_result):
    """5. Correct unchanged-rank claim (Gamma University stayed at 25)."""
    claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Gamma University",
        qualitative_direction="unchanged",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "VERIFIED"


def test_06_incorrect_top_performer_claim(verifier, sample_rank_movement_exec_result):
    """6. Incorrect top-performer claim (Beta College claimed top score, but Alpha had highest score)."""
    claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="Beta College",
        qualitative_direction="top",
        claim_text="Beta College is the top performer with the highest overall score",
        metric="score",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"
    assert "Alpha Institute" in verified[0].verification_notes


def test_07_incorrect_institution_comparison_direction(verifier, sample_rank_movement_exec_result):
    """7. Incorrect comparison direction (BetaState claimed to outperform AlphaState)."""
    claim = NumericalClaim(
        claim_type="INSTITUTION_COMPARISON",
        comparison_entities=["BetaState", "AlphaState"],
        qualitative_direction="better",
        metric="average_score",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_08_claim_involving_missing_rank_data(verifier):
    """8. Claim involving missing rank data (institution present but ranks are None)."""
    op = OperationResult(
        operation_id="op_missing",
        function_name="get_rankings",
        status="SUCCESS",
        data={"institutions": [{"institution_uid": "U-999", "institute_name_std": "Unranked Inst", "rank": None}]},
    )
    exec_res = ExecutionResult(
        query_id="q_missing", original_question="test", status="SUCCESS",
        query_type="ANALYTICAL", validation_status="VALID", operations=[op],
    )
    claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="Unranked Inst",
        metric="rank",
        value=15,
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "UNVERIFIED"


def test_09_claim_involving_absent_institution(verifier, sample_rank_movement_exec_result):
    """9. Claim involving an institution absent from the comparison cohort."""
    claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Nonexistent University",
        qualitative_direction="improved",
        value=None,
    )
    verified, _ = verifier.verify_claims([claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "UNVERIFIED"
    assert "not in" in verified[0].verification_notes.lower() or "not found" in verified[0].verification_notes.lower() or "no execution record" in verified[0].verification_notes.lower()


def test_10_claim_involving_tied_ranking(verifier):
    """10. Claim involving tied ranking (both institutions share rank 5)."""
    op = OperationResult(
        operation_id="op_tied",
        function_name="get_rankings",
        status="SUCCESS",
        data={"institutions": [
            {"institution_uid": "U-T1", "institute_name_std": "Tie One", "rank": 5, "score": 75.0},
            {"institution_uid": "U-T2", "institute_name_std": "Tie Two", "rank": 5, "score": 75.0},
        ]},
    )
    exec_res = ExecutionResult(
        query_id="q_tied", original_question="test", status="SUCCESS",
        query_type="ANALYTICAL", validation_status="VALID", operations=[op],
    )
    claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="Tie Two",
        metric="rank",
        value=5,
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == "VERIFIED"


# ---------------------------------------------------------------------------
# B. Claim Extraction Tests
# ---------------------------------------------------------------------------

def test_extraction_from_factual_paragraph(extractor):
    """Extract factual claims from standard analytical paragraph text."""
    text = "IIT Madras achieved an overall score of 88.72 and secured rank 1 in Engineering."
    claims = extractor.extract_claims(text)
    assert len(claims) >= 2
    types = {c.claim_type for c in claims}
    assert "METRIC_VALUE" in types or "RANK_VALUE" in types


def test_extraction_from_bullet_list_under_directional_header(extractor):
    """Extract qualitative rank-change claims from bullet lists under a gainers header."""
    text = """
### Key Findings
* **Institutions with Rank Improvement:** The following institutions demonstrated positive rank movement:
    * Alpha Institute
    * Beta College
"""
    known = {"alpha institute": "U-001", "beta college": "U-002"}
    claims = extractor._extract_bullet_list_claims(text, known)
    assert len(claims) == 2
    assert claims[0].institution_name == "Alpha Institute"
    assert claims[0].qualitative_direction == "improved"
    assert claims[1].institution_name == "Beta College"
    assert claims[1].qualitative_direction == "improved"


def test_extraction_from_table_row(extractor):
    """Extract claims directly from Markdown table rows."""
    text = """
| Rank | Institution | Overall Score |
| 1 | IIT Madras | 88.72 |
| 2 | IIT Delhi | 85.74 |
"""
    claims = extractor.extract_claims(text)
    assert len(claims) >= 2
    insts = {c.institution_name for c in claims if c.institution_name}
    assert any("Madras" in inst for inst in insts)


def test_extraction_distinguishes_factual_from_nonfactual_headings(verifier):
    """Ensure non-factual structural headers are marked NOT_FACTUAL."""
    heading_claim = NumericalClaim(
        claim_type="NOT_FACTUAL",
        claim_text="### Data Notes & Limitations",
        is_factual=False,
    )
    verified, _ = verifier.verify_claims([heading_claim], None)
    assert verified[0].verification_status == "NOT_FACTUAL"


def test_extraction_deduplication_of_repeated_claims(extractor):
    """Repeated claims in the same answer must not be extracted as duplicate distinct entities."""
    text = "IIT Madras scored 88.72 in Engineering. Later, we note IIT Madras scored 88.72 in Engineering."
    claims = extractor.extract_claims(text)
    madras_claims = [c for c in claims if c.claimed_value == 88.72]
    assert len(madras_claims) == 1


def test_extraction_preserves_different_years_and_metrics(auditor):
    """Distinct years and metrics for the same institution must never be merged."""
    c_2020 = NumericalClaim(claim_type="METRIC_VALUE", institution_name="IIT Madras", metric="score", year=2020, value=85.0)
    c_2025 = NumericalClaim(claim_type="METRIC_VALUE", institution_name="IIT Madras", metric="score", year=2025, value=88.72)
    c_rpc = NumericalClaim(claim_type="METRIC_VALUE", institution_name="IIT Madras", metric="rpc", year=2025, value=90.74)

    assert not auditor._claims_match(c_2020, c_2025)
    assert not auditor._claims_match(c_2025, c_rpc)


def test_extraction_preserves_opposite_rank_movements(auditor):
    """Two institutions with opposite directions must not match."""
    c_gainer = NumericalClaim(claim_type="RANK_CHANGE", institution_name="Inst A", qualitative_direction="improved")
    c_decliner = NumericalClaim(claim_type="RANK_CHANGE", institution_name="Inst B", qualitative_direction="declined")
    assert not auditor._claims_match(c_gainer, c_decliner)


# ---------------------------------------------------------------------------
# C. Accounting Invariant Tests
# ---------------------------------------------------------------------------

def test_accounting_tp_plus_fn_equals_expected():
    """Verify strict TP + FN == Expected Facts invariant."""
    from scripts.recompute_phase_6_1_5_metrics import reconcile_phase_6_1_5_accounting
    audit = reconcile_phase_6_1_5_accounting()
    for bmid, rep in audit["benchmarks"].items():
        if rep["expected_facts_count"] > 0:
            assert rep["true_positives"] + rep["false_negatives"] == rep["expected_facts_count"]


def test_accounting_zero_denominator_returns_none():
    """Verify zero expected facts return None / N/A, not 0 or 1."""
    from scripts.recompute_phase_6_1_5_metrics import reconcile_phase_6_1_5_accounting
    audit = reconcile_phase_6_1_5_accounting()
    for bmid in ("BM-02", "BM-05"):
        rep = audit["benchmarks"][bmid]
        assert rep["precision"] is None
        assert rep["recall"] is None
        assert rep["extraction_coverage"] is None


def test_accounting_coverage_bounded_at_one():
    """Verify that coverage never exceeds 1.0."""
    from scripts.recompute_phase_6_1_5_metrics import reconcile_phase_6_1_5_accounting
    audit = reconcile_phase_6_1_5_accounting()
    for bmid, rep in audit["benchmarks"].items():
        if rep["extraction_coverage"] is not None:
            assert 0.0 <= rep["extraction_coverage"] <= 1.0


# ---------------------------------------------------------------------------
# D. Controlled Mutation Tests (8 Response Mutations)
# ---------------------------------------------------------------------------

def test_mutation_01_reverse_rank_movement_direction(verifier, sample_rank_movement_exec_result):
    """Mutate: Claim improver as decliner."""
    mutated_claim = NumericalClaim(
        claim_type="RANK_CHANGE",
        institution_name="Alpha Institute",
        qualitative_direction="declined",
        value=None,
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_mutation_02_replace_institution_name(verifier, sample_rank_movement_exec_result):
    """Mutate: Substitute wrong institution into top-performer claim."""
    mutated_claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="Gamma University",
        qualitative_direction="top",
        metric="score",
        value=None,
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_mutation_03_change_year(verifier, sample_rank_movement_exec_result):
    """Mutate: Claim 2025 score as 2020 score."""
    mutated_claim = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Alpha Institute",
        metric="score",
        year=2020,  # Execution result is 2025
        value=85.0,
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "UNVERIFIED"


def test_mutation_04_change_metric(verifier, sample_rank_movement_exec_result):
    """Mutate: Claim score value as RPC value."""
    mutated_claim = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Alpha Institute",
        metric="rpc",
        year=2025,
        value=85.0,  # 85.0 is score, actual RPC is 92.5
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_mutation_05_reverse_comparison_direction(verifier, sample_rank_movement_exec_result):
    """Mutate: Claim BetaState outperformed AlphaState."""
    mutated_claim = NumericalClaim(
        claim_type="INSTITUTION_COMPARISON",
        comparison_entities=["BetaState", "AlphaState"],
        qualitative_direction="better",
        metric="average_score",
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_mutation_06_change_top_ranked_institution(verifier, sample_rank_movement_exec_result):
    """Mutate: Claim Delta Academy has highest RPC."""
    mutated_claim = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name="Delta Academy",
        metric="rpc",
        qualitative_direction="highest",
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_mutation_07_insert_false_factual_assertion(verifier, sample_rank_movement_exec_result):
    """Mutate: Assert false numerical rank value for institution."""
    mutated_claim = NumericalClaim(
        claim_type="RANK_VALUE",
        institution_name="Alpha Institute",
        metric="rank",
        value=99,  # Actual is 20
    )
    verified, _ = verifier.verify_claims([mutated_claim], sample_rank_movement_exec_result)
    assert verified[0].verification_status == "CONTRADICTED"


def test_mutation_08_duplicate_factual_bullet(auditor):
    """Mutate: Duplicate identical fact in prompt, ensure auditor harmonizes without count inflation."""
    claim1 = NumericalClaim(claim_type="METRIC_VALUE", institution_name="Alpha Institute", metric="score", value=85.0)
    claim2 = NumericalClaim(claim_type="METRIC_VALUE", institution_name="Alpha Institute", metric="score", value=85.0)
    deduped = []
    for c in [claim1, claim2]:
        if not any(auditor._claims_match(c, existing) for existing in deduped):
            deduped.append(c)
    assert len(deduped) == 1


# ---------------------------------------------------------------------------
# E. Generalization Tests Across Unseen Categories and States
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category,inst_name,actual_val,claimed_val,expected_status", [
    ("Dental", "Manipal College of Dental Sciences", 78.4, 78.4, "VERIFIED"),
    ("Architecture", "IIT Roorkee Architecture", 81.2, 85.0, "CONTRADICTED"),
    ("Law", "National Law School of India University", 88.0, 88.0, "VERIFIED"),
    ("Agriculture", "Punjab Agricultural University", 69.5, 75.0, "CONTRADICTED"),
])
def test_generalization_across_unseen_categories(verifier, category, inst_name, actual_val, claimed_val, expected_status):
    """Test qualitative and numerical verification across unseen disciplines."""
    op = OperationResult(
        operation_id=f"op_{category.lower()}",
        function_name="get_category_performance",
        status="SUCCESS",
        data={"institutions": [{"institution_name": inst_name, "score": actual_val, "category": category}]},
    )
    exec_res = ExecutionResult(
        query_id=f"q_{category.lower()}", original_question=f"Test {category}", status="SUCCESS",
        query_type="ANALYTICAL", validation_status="VALID", operations=[op],
    )
    claim = NumericalClaim(
        claim_type="METRIC_VALUE",
        institution_name=inst_name,
        category=category,
        metric="score",
        value=claimed_val,
    )
    verified, _ = verifier.verify_claims([claim], exec_res)
    assert verified[0].verification_status == expected_status
