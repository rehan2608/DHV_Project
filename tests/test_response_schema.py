"""
Unit tests for Response Generation Schemas and strict JSON serialization (Phase 6).
"""

import json
from src.response.result_schema import (
    NumericalClaim,
    Citation,
    VerificationSummary,
    GenerationMetadata,
    GeneratedResponse,
)


def test_numerical_claim_serialization():
    claim = NumericalClaim(
        claim_id="claim_01",
        claim_text="IIT Bombay scored 91.2 in RPC.",
        claim_type="METRIC_VALUE",
        metric="rpc",
        institution_name="IIT Bombay",
        institution_uid="U-0456",
        claimed_value=91.2,
        actual_value=91.23,
        unit="marks",
        verification_status="VERIFIED",
        verification_notes="Matched within tolerance",
    )

    data = claim.model_dump()
    assert data["claim_id"] == "claim_01"
    assert data["claimed_value"] == 91.2
    assert data["verification_status"] == "VERIFIED"

    # Strict JSON test
    json_str = json.dumps(data)
    assert "IIT Bombay" in json_str


def test_citation_serialization():
    cite = Citation(
        citation_id="CITE-01",
        document_id="nirf_methodology_reference",
        document_name="RPC Methodology",
        source_reference="Ministry of Education",
        section_title="Research and Professional Practice",
        page_number=3,
        status="VALID",
    )
    data = cite.model_dump()
    assert data["citation_id"] == "CITE-01"
    assert data["page_number"] == 3
    assert data["status"] == "VALID"


def test_generated_response_json_roundtrip():
    claim = NumericalClaim(
        claim_id="c1",
        claim_text="Rank improved by 10 positions.",
        claim_type="RANK_CHANGE",
        claimed_value=10,
        actual_value=10,
        verification_status="VERIFIED",
    )
    summary = VerificationSummary(
        total_claims=1,
        verified_claims=1,
        all_claims_verified=True,
    )
    meta = GenerationMetadata(
        model_name="gemma4:31b-cloud",
        generation_duration_seconds=1.2,
        verification_duration_seconds=0.05,
        total_duration_seconds=1.25,
        response_type="ANALYTICAL_ONLY",
    )
    resp = GeneratedResponse(
        response_id="resp_test1",
        query_id="q_101",
        response_status="SUCCESS",
        original_question="How did the institution perform?",
        answer="The institution improved by 10 positions.",
        key_findings=["Improved by 10 ranks."],
        numerical_claims=[claim],
        verification_summary=summary,
        citations=[],
        warnings=["Sample size is limited."],
        limitations=["Longitudinal cohort shift."],
        evidence_summary={"has_analytical_evidence": True},
        generation_metadata=meta,
    )

    # Convert to JSON string
    json_output = resp.to_json()
    assert isinstance(json_output, str)
    assert "resp_test1" in json_output

    # Parse back
    loaded = json.loads(json_output)
    reconstructed = GeneratedResponse.model_validate(loaded)
    assert reconstructed.response_id == "resp_test1"
    assert reconstructed.has_warnings() is True
    assert reconstructed.verification_summary.all_claims_verified is True

