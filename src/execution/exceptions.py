"""
Custom exceptions for the NIRF Query Execution Engine (Phase 4).
"""


class ExecutionError(Exception):
    """Base exception for all query execution errors."""
    pass


class RouterError(ExecutionError):
    """Raised when an operation cannot be routed to a valid analytical function."""
    pass


class ArgumentMappingError(ExecutionError):
    """Raised when query arguments cannot be safely mapped to analytical function parameters."""
    pass


class DependencyError(ExecutionError):
    """Raised when multi-operation dependencies are circular, missing, or failed."""
    pass


class OperationExecutionError(ExecutionError):
    """Raised when an analytical operation fails during execution."""
    pass


class SerializationError(ExecutionError):
    """Raised when an execution result cannot be serialized to valid JSON."""
    pass

