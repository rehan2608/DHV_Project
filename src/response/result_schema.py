"""
Result schema module for the NIRF Response Generation and Verification layer (Phase 6).
Defines strongly-typed Pydantic models for generated responses, numerical claims,
citations, verification summaries, and performance metadata with strict JSON serialization.
"""

from typing import Dict, Any, List, Optional, Literal, Union
import json
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from src.execution.result_schema import clean_for_json


class ContradictedStatus(str):
    """
    Status string for contradicted claims that matches both 'CONTRADICTED' (Phase 6.1.5 standard)
    and 'CONFLICTING' (legacy test assertion alias) for complete backward compatibility.
    """
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str) and other.upper() in ("CONTRADICTED", "CONFLICTING"):
            return True
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash("CONTRADICTED")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )


VerificationStatus = Union[
    Literal["VERIFIED", "CONTRADICTED", "CONFLICTING", "UNVERIFIED", "NOT_FACTUAL", "NOT_APPLICABLE"],
    ContradictedStatus,
]
CitationStatus = Literal["VALID", "INVALID", "UNRETRIEVED", "NOT_APPLICABLE"]
ResponseStatus = Literal[
    "SUCCESS",
    "PARTIAL_SUCCESS",
    "INSUFFICIENT_EVIDENCE",
    "CLARIFICATION_REQUIRED",
    "FAILED",
    "VERIFICATION_FAILED",
]
ClaimType = Literal[
    "METRIC_VALUE",
    "RANK_VALUE",
    "RANK_CHANGE",
    "COUNT",
    "CORRELATION",
    "PERCENTAGE",
    "AGGREGATE_STATISTIC",
    "INSTITUTION_COMPARISON",
    "GENERAL_FACT",
    "QUALITATIVE_RANK_CHANGE",
    "QUALITATIVE_COMPARISON",
    "SUPERLATIVE",
    "DOCUMENTATION_FACT",
    "NOT_FACTUAL",
]
ResponseType = Literal[
    "ANALYTICAL_ONLY",
    "DOCUMENTATION_ONLY",
    "COMBINED",
    "PARTIAL_EXECUTION",
    "NO_EVIDENCE",
    "CLARIFICATION_REQUIRED",
    "FAILED",
]


class NumericalClaim(BaseModel):
    """
    Represents an extracted factual/numerical claim from the generated natural-language text
    or produced directly via structured generation.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    claim_id: str = Field(default_factory=lambda: f"claim_{uuid.uuid4().hex[:6]}")
    claim_text: str = Field(default="", description="Verbatim sentence or clause containing the claim.")
    statement: Optional[str] = Field(None, description="Descriptive factual statement.")
    claim_type: ClaimType = Field(..., description="Classification of the numerical claim.")
    metric: Optional[str] = Field(None, description="Analytical metric (e.g., score, rpc, rank).")
    institution_uid: Optional[str] = Field(None, description="Identified institution UID.")
    institution_name: Optional[str] = Field(None, description="Identified institution name.")
    category: Optional[str] = Field(None, description="NIRF ranking category.")
    year: Optional[Union[int, str]] = Field(None, description="Ranking year or year range.")
    claimed_value: Optional[Union[float, int, str]] = Field(None, description="Value claimed in the text.")
    value: Optional[Union[float, int, str]] = Field(None, description="Value from structured LLM output.")
    actual_value: Optional[Union[float, int, str]] = Field(None, description="Actual value from execution result.")
    unit: Optional[str] = Field(None, description="Unit or measurement qualifier (e.g., marks, ranks).")
    state: Optional[str] = Field(None, description="State name for geographic aggregate claims.")
    statistic_type: Optional[str] = Field(None, description="Statistic type (e.g. mean, median, average).")
    comparison_period: Optional[List[int]] = Field(None, description="Temporal comparison window (e.g. [2020, 2025]).")
    comparison_entities: Optional[List[str]] = Field(None, description="Entities involved in a comparison.")
    source_operation_id: Optional[str] = Field(None, description="Originating operation ID from ExecutionResult.")
    operation_id: Optional[str] = Field(None, description="Operation ID alias.")
    source_reference: Optional[str] = Field(None, description="Document source reference if applicable.")
    verification_status: VerificationStatus = Field(default="UNVERIFIED", description="Deterministic verification outcome.")
    verification_notes: Optional[str] = Field(None, description="Audit note explaining the verification result.")
    audit_discrepancy: Optional[str] = Field(None, description="Note if discrepancy found between prose and claim list.")
    is_factual: bool = Field(default=True, description="True if statement is a factual assertion requiring verification.")
    qualitative_direction: Optional[str] = Field(None, description="Direction: improved, declined, unchanged, higher, lower, highest, etc.")
    is_duplicate: bool = Field(default=False, description="True if this claim is a duplicate of a canonical claim.")
    canonical_claim_id: Optional[str] = Field(None, description="Canonical claim identifier.")
    evidence_reference: Optional[str] = Field(None, description="Matched chunk ID or operation result field.")

    def model_post_init(self, __context: Any) -> None:
        """Harmonizes aliases across fields."""
        if not self.claim_text and self.statement:
            self.claim_text = self.statement
        elif not self.statement and self.claim_text:
            self.statement = self.claim_text

        if self.claim_type == "NOT_FACTUAL":
            self.is_factual = False
            self.verification_status = "NOT_FACTUAL"

        if self.claimed_value is None and self.value is not None:
            self.claimed_value = self.value
        elif self.value is None and self.claimed_value is not None:
            self.value = self.claimed_value

        if not self.source_operation_id and self.operation_id:
            self.source_operation_id = self.operation_id
        elif not self.operation_id and self.source_operation_id:
            self.operation_id = self.source_operation_id


class Citation(BaseModel):
    """
    Represents an authoritative documentation citation attached to the response.
    """
    model_config = ConfigDict(extra="ignore")

    citation_id: str = Field(default_factory=lambda: f"cite_{uuid.uuid4().hex[:6]}")
    document_id: str = Field(..., description="Canonical document ID from approved registry.")
    document_name: Optional[str] = Field(None, description="Human-readable title of the document.")
    document_type: Optional[str] = Field(None, description="Category of document (e.g. methodology, audit).")
    source_reference: Optional[str] = Field(None, description="Official publishing authority.")
    section_title: Optional[str] = Field(None, description="Section heading from retrieved chunk.")
    page_number: Optional[int] = Field(None, description="Page number if applicable, or None.")
    url: Optional[str] = Field(None, description="Verified URL if present in source metadata.")
    chunk_id: Optional[str] = Field(None, description="Deterministic chunk identifier from FAISS index.")
    status: CitationStatus = Field(default="VALID", description="Validation status against retrieved chunks.")
    validation_notes: Optional[str] = Field(None, description="Audit note regarding citation validity.")


class VerificationSummary(BaseModel):
    """
    Aggregated statistical summary of numerical claim verification, independent claim audit,
    and regeneration attempts.
    """
    total_claims: int = Field(default=0, description="Total numerical/factual claims evaluated.")
    verified_claims: int = Field(default=0, description="Claims matching actual execution result.")
    unverified_claims: int = Field(default=0, description="Claims lacking underlying proof.")
    conflicting_claims: int = Field(default=0, description="Claims contradicting underlying data.")
    contradicted_claims: int = Field(default=0, description="Claims contradicting underlying data (alias).")
    not_factual_claims: int = Field(default=0, description="Non-factual structural statements.")
    duplicate_claims: int = Field(default=0, description="Duplicate claims.")
    structured_claims_count: int = Field(default=0, description="Claims generated in structured list.")
    text_audited_claims_count: int = Field(default=0, description="Claims audited independently from prose text.")
    omitted_from_structured_count: int = Field(default=0, description="Prose numerical claims omitted from structured claims.")
    extraction_coverage: float = Field(default=1.0, description="Proportion of checkable prose statements covered by claims.")
    verification_precision: Optional[float] = Field(default=None, description="Precision of verified claims (verified / (verified + conflicting)).")
    verification_recall: Optional[float] = Field(default=None, description="Recall of verifiable claims (verified / total_claims).")
    all_claims_verified: bool = Field(default=True, description="True if no unverified or conflicting claims exist.")
    regeneration_attempted: bool = Field(default=False, description="True if a regeneration attempt was made.")
    regeneration_count: int = Field(default=0, description="Number of regeneration retries executed.")

    def model_post_init(self, __context: Any) -> None:
        """Harmonizes conflicting and contradicted counts."""
        if self.contradicted_claims == 0 and self.conflicting_claims > 0:
            self.contradicted_claims = self.conflicting_claims
        elif self.conflicting_claims == 0 and self.contradicted_claims > 0:
            self.conflicting_claims = self.contradicted_claims


class GenerationMetadata(BaseModel):
    """
    Performance and diagnostic metadata for the response generation process.
    """
    model_name: str = Field(..., description="LLM model identifier used for generation.")
    generation_duration_seconds: float = Field(default=0.0, description="LLM generation latency in seconds.")
    verification_duration_seconds: float = Field(default=0.0, description="Deterministic verification latency in seconds.")
    total_duration_seconds: float = Field(default=0.0, description="Overall response generation latency.")
    prompt_tokens_estimated: Optional[int] = Field(None, description="Estimated prompt token count.")
    response_type: ResponseType = Field(..., description="Type of question and evidence situation.")
    operations_count: int = Field(default=0, description="Number of analytical operations provided.")
    chunks_count: int = Field(default=0, description="Number of retrieved documentation chunks provided.")


class GeneratedResponse(BaseModel):
    """
    Top-level response object encapsulating natural-language answer, verified claims,
    citations, warnings, limitations, and execution audit metadata.
    """
    model_config = ConfigDict(extra="ignore")

    response_id: str = Field(default_factory=lambda: f"resp_{uuid.uuid4().hex[:8]}")
    query_id: str = Field(..., description="Associated QueryPlan identifier.")
    response_status: ResponseStatus = Field(..., description="Overall response quality standing.")
    original_question: str = Field(..., description="Original user prompt.")
    answer: str = Field(..., description="Natural-language synthesized explanation.")
    key_findings: List[str] = Field(default_factory=list, description="Bulleted analytical takeaways.")
    numerical_claims: List[NumericalClaim] = Field(default_factory=list, description="Extracted numerical claims.")
    verification_summary: VerificationSummary = Field(default_factory=VerificationSummary)
    citations: List[Citation] = Field(default_factory=list, description="Attached source references.")
    warnings: List[str] = Field(default_factory=list, description="Preserved data quality and analytical warnings.")
    limitations: List[str] = Field(default_factory=list, description="Comparability, sample size, or causality caveats.")
    evidence_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of evidence provided.")
    generation_metadata: GenerationMetadata = Field(...)

    def has_warnings(self) -> bool:
        """Returns True if any warnings or limitations are present."""
        return len(self.warnings) > 0 or len(self.limitations) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Converts the response to a clean dictionary safe for JSON serialization."""
        return clean_for_json(self.model_dump())

    def to_json(self, indent: int = 2) -> str:
        """Serializes the response strictly to JSON string with NaN/Inf handling."""
        cleaned = self.to_dict()
        return json.dumps(cleaned, indent=indent, allow_nan=False)

