"""
Independent Synthetic Generalization Tests for Phase 6.1.1 Audit.
Verifies 60 deterministic synthetic test cases across Numerical, Structural,
and Claim-Quality categories using NumericalClaimVerifier.
"""

import json
from pathlib import Path
import pytest

from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.result_schema import NumericalClaim
from src.response.verifier import NumericalClaimVerifier


def load_synthetic_cases():
    fixture_path = Path(__file__).parent / "synthetic_fixtures" / "synthetic_generalization_cases.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


CASES = load_synthetic_cases()


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_synthetic_generalization_case(case):
    verifier = NumericalClaimVerifier(float_tolerance=0.05)
    
    # Construct minimal ExecutionResult
    op = OperationResult(
        operation_id="op_synth",
        function_name="synthetic_function",
        status="SUCCESS",
        data=case["op_data"],
    )
    exec_result = ExecutionResult(
        query_id="synth_query",
        original_question="Synthetic audit query",
        status="SUCCESS",
        query_type="ANALYTICAL",
        validation_status="VALID",
        operations=[op],
    )
    
    # Construct NumericalClaim
    claim = NumericalClaim(**case["claim"])
    
    # Verify claims
    verified_claims, summary = verifier.verify_claims([claim], exec_result)
    
    assert len(verified_claims) == 1
    actual_status = verified_claims[0].verification_status
    expected_status = case["expected_status"]
    
    assert actual_status == expected_status, (
        f"Case {case['case_id']} ({case['category']}: {case['description']}) "
        f"expected {expected_status} but got {actual_status}. "
        f"Notes: {verified_claims[0].verification_notes}"
    )

