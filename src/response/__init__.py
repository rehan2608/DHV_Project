"""
Response generation and verification package for the NIRF Conversational Assistant (Phase 6).
Provides controlled context compilation, Gemma response synthesis, deterministic numerical
claim verification, citation auditing, and strict JSON-serializable GeneratedResponse schemas.
"""

from src.response.exceptions import (
    ResponseError,
    ContextBuildingError,
    GenerationError,
    ClaimExtractionError,
    VerificationError,
    CitationValidationError,
)
from src.response.result_schema import (
    NumericalClaim,
    Citation,
    VerificationSummary,
    GenerationMetadata,
    GeneratedResponse,
    VerificationStatus,
    CitationStatus,
    ResponseStatus,
    ClaimType,
    ResponseType,
)
from src.response.context_builder import ContextBuilder
from src.response.claim_extractor import ClaimExtractor
from src.response.verifier import NumericalClaimVerifier
from src.response.citation_validator import CitationValidator
from src.response.generator import ResponseGenerator

__all__ = [
    "ResponseError",
    "ContextBuildingError",
    "GenerationError",
    "ClaimExtractionError",
    "VerificationError",
    "CitationValidationError",
    "NumericalClaim",
    "Citation",
    "VerificationSummary",
    "GenerationMetadata",
    "GeneratedResponse",
    "VerificationStatus",
    "CitationStatus",
    "ResponseStatus",
    "ClaimType",
    "ResponseType",
    "ContextBuilder",
    "ClaimExtractor",
    "NumericalClaimVerifier",
    "CitationValidator",
    "ResponseGenerator",
]

