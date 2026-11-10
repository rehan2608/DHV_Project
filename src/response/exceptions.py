"""
Exceptions module for the NIRF Response Generation and Verification layer (Phase 6).
Defines strongly-typed exceptions for context building, response generation,
claim extraction, numerical verification, and citation validation.
"""

class ResponseError(Exception):
    """Base exception for all response generation and verification errors."""
    pass


class ContextBuildingError(ResponseError):
    """Raised when evidence compilation from analytical or retrieval results fails."""
    pass


class GenerationError(ResponseError):
    """Raised when LLM text generation encounters an unrecoverable error."""
    pass


class ClaimExtractionError(ResponseError):
    """Raised when factual or numerical claim extraction encounters an internal error."""
    pass


class VerificationError(ResponseError):
    """Raised when numerical claim verification fails unexpectedly."""
    pass


class CitationValidationError(ResponseError):
    """Raised when citation validation against retrieved chunks fails unexpectedly."""
    pass

