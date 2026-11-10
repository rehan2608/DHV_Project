"""
Operation Runner for NIRF Query Execution Engine (Phase 4).
Executes individual analytical operations safely, timing execution latency and
capturing structured data, metadata, and runtime warnings.
"""

from typing import Dict, Any, Optional
import time
import logging

from src.query_engine.schemas import AnalyticalOperation
from src.execution.router import QueryRouter, get_query_router
from src.execution.argument_mapper import ArgumentMapper, get_argument_mapper
from src.execution.result_schema import OperationResult, clean_for_json
from src.execution.exceptions import OperationExecutionError, ArgumentMappingError, RouterError

logger = logging.getLogger(__name__)


class OperationRunner:
    """
    Executes a single validated AnalyticalOperation through the router and mapper,
    returning an isolated, structured OperationResult.
    """

    def __init__(
        self,
        router: Optional[QueryRouter] = None,
        mapper: Optional[ArgumentMapper] = None,
    ) -> None:
        self.router = router or get_query_router()
        self.mapper = mapper or get_argument_mapper()

    def run_operation(
        self,
        operation: AnalyticalOperation,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """
        Executes an AnalyticalOperation with optional runtime argument overrides (e.g. from predecessors).

        Args:
            operation: Validated AnalyticalOperation.
            overrides: Optional dictionary of keyword arguments passed from predecessor dependencies.

        Returns:
            OperationResult containing status, data, metadata, latency, and warnings.
        """
        op_id = operation.operation_id
        fn_name = operation.function_name
        start_time = time.time()

        try:
            # 1. Resolve function
            func = self.router.resolve_function(fn_name)

            # 2. Map arguments
            kwargs = self.mapper.map_arguments(operation)

            # 3. Apply predecessor overrides if present
            if overrides:
                kwargs.update(overrides)

            logger.debug("Executing %s (%s) with kwargs: %s", fn_name, op_id, list(kwargs.keys()))

            # 4. Execute analytical function
            raw_result = func(**kwargs)
            duration = round(time.time() - start_time, 4)

            # 5. Extract metadata and warnings
            op_meta = raw_result.get("metadata", {})
            warnings = []
            if isinstance(op_meta, dict):
                warnings.extend(op_meta.get("warnings", []))
            if "warning" in raw_result:
                warnings.append(str(raw_result["warning"]))

            is_success = raw_result.get("success", True)
            if not is_success:
                err_msg = raw_result.get("error", "Analytical function reported failure.")
                return OperationResult(
                    operation_id=op_id,
                    function_name=fn_name,
                    status="FAILED",
                    data=clean_for_json(raw_result),
                    metadata=clean_for_json(op_meta),
                    warnings=warnings,
                    execution_duration_seconds=duration,
                    error_message=err_msg,
                )

            return OperationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="SUCCESS",
                data=clean_for_json(raw_result),
                metadata=clean_for_json(op_meta),
                warnings=warnings,
                execution_duration_seconds=duration,
                error_message=None,
            )

        except (RouterError, ArgumentMappingError) as me:
            duration = round(time.time() - start_time, 4)
            logger.warning("Operation %s setup failed: %s", op_id, me)
            return OperationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FAILED",
                execution_duration_seconds=duration,
                error_message=str(me),
            )
        except Exception as e:
            duration = round(time.time() - start_time, 4)
            logger.error("Unexpected error executing %s (%s): %s", fn_name, op_id, e)
            return OperationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FAILED",
                execution_duration_seconds=duration,
                error_message=f"Analytical execution error: {e}",
            )


def get_operation_runner() -> OperationRunner:
    """Returns singleton OperationRunner instance."""
    return OperationRunner()

