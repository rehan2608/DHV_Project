"""
Execution Engine Package for NIRF Query Routing, Argument Mapping, and Execution.
"""

from src.execution.router import QueryRouter, get_query_router
from src.execution.argument_mapper import ArgumentMapper, get_argument_mapper
from src.execution.operation_runner import OperationRunner, get_operation_runner
from src.execution.executor import QueryExecutor, get_query_executor
from src.execution.result_schema import (
    ExecutionResult,
    OperationResult,
    ExecutionMetadata,
    ExecutionStatus,
    OperationStatus,
    clean_for_json,
)
from src.execution.exceptions import (
    ExecutionError,
    RouterError,
    ArgumentMappingError,
    DependencyError,
    OperationExecutionError,
    SerializationError,
)

__all__ = [
    "QueryRouter",
    "get_query_router",
    "ArgumentMapper",
    "get_argument_mapper",
    "OperationRunner",
    "get_operation_runner",
    "QueryExecutor",
    "get_query_executor",
    "ExecutionResult",
    "OperationResult",
    "ExecutionMetadata",
    "ExecutionStatus",
    "OperationStatus",
    "clean_for_json",
    "ExecutionError",
    "RouterError",
    "ArgumentMappingError",
    "DependencyError",
    "OperationExecutionError",
    "SerializationError",
]

