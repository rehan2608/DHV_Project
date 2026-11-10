"""
Custom exceptions for the NIRF Query Engine and Gemma Parser.
"""


class QueryEngineError(Exception):
    """Base exception for all query engine errors."""
    pass


class QueryParsingError(QueryEngineError):
    """Raised when natural language cannot be converted into structured query."""
    pass


class QueryValidationError(QueryEngineError):
    """Raised when a query plan fails structural, analytical, or comparability validation."""
    pass


class UnsupportedQueryError(QueryEngineError):
    """Raised when a query request exceeds NIRF dataset capabilities or analytical functions."""
    pass


class AmbiguousEntityError(QueryEngineError):
    """Raised when an institution name or geographic entity matches multiple conflicting records."""
    pass

