"""
Query Executor for NIRF Analytics Execution Engine (Phase 4).
Orchestrates revalidation, topological dependency resolution, predecessor-to-successor
data flow, operation running, error isolation, and structured result packaging.
"""

from typing import Dict, Any, List, Optional, Union, Set
import time
import logging
from collections import defaultdict, deque

from src.query_engine.schemas import QueryPlan, AnalyticalOperation
from src.query_engine.validator import QueryValidator, get_query_validator
from src.execution.router import QueryRouter, get_query_router
from src.execution.argument_mapper import ArgumentMapper, get_argument_mapper
from src.execution.operation_runner import OperationRunner, get_operation_runner
from src.execution.result_schema import (
    ExecutionResult,
    OperationResult,
    ExecutionMetadata,
    ExecutionStatus,
    clean_for_json,
)
from src.execution.exceptions import ExecutionError, DependencyError

logger = logging.getLogger(__name__)


class QueryExecutor:
    """
    Main entry point for executing validated NIRF QueryPlans.
    Re-validates plans, schedules multi-operation dependency graphs, and executes operations safely.
    """

    def __init__(
        self,
        validator: Optional[QueryValidator] = None,
        router: Optional[QueryRouter] = None,
        mapper: Optional[ArgumentMapper] = None,
        runner: Optional[OperationRunner] = None,
    ) -> None:
        self.validator = validator or get_query_validator()
        self.router = router or get_query_router()
        self.mapper = mapper or get_argument_mapper()
        self.runner = runner or get_operation_runner()

    def execute(self, plan: Union[QueryPlan, Dict[str, Any]]) -> ExecutionResult:
        """
        Executes a QueryPlan after mandatory revalidation and dependency resolution.

        Args:
            plan: QueryPlan instance or raw dictionary.

        Returns:
            Structured ExecutionResult.
        """
        start_time = time.time()

        # 1. Parse into QueryPlan if dict
        if isinstance(plan, dict):
            try:
                query_plan = QueryPlan.model_validate(plan)
            except Exception as e:
                return ExecutionResult(
                    query_id="unknown",
                    original_question="",
                    status="REJECTED",
                    query_type="unsupported",
                    validation_status="INVALID",
                    errors=[f"Invalid QueryPlan structure: {e}"],
                    metadata=ExecutionMetadata(total_duration_seconds=round(time.time() - start_time, 4)),
                )
        else:
            query_plan = plan

        # 2. Mandatory Revalidation
        val_result = self.validator.validate(query_plan)
        if not val_result.is_valid:
            status_map: Dict[str, ExecutionStatus] = {
                "CLARIFICATION_REQUIRED": "CLARIFICATION_REQUIRED",
                "UNSUPPORTED": "REJECTED",
                "INVALID": "REJECTED",
            }
            exec_status = status_map.get(val_result.status, "REJECTED")

            return ExecutionResult(
                query_id=query_plan.query_id,
                original_question=query_plan.original_question,
                status=exec_status,
                query_type=query_plan.query_type,
                validation_status=val_result.status,
                warnings=val_result.warnings,
                errors=val_result.errors,
                metadata=ExecutionMetadata(
                    comparability_warnings=val_result.comparability_notes,
                    total_duration_seconds=round(time.time() - start_time, 4),
                ),
            )

        # 3. Multi-Operation Dependency Resolution & Topological Ordering
        try:
            ordered_operations = self._resolve_execution_order(query_plan.operations)
        except DependencyError as de:
            return ExecutionResult(
                query_id=query_plan.query_id,
                original_question=query_plan.original_question,
                status="FAILED",
                query_type=query_plan.query_type,
                validation_status=val_result.status,
                warnings=val_result.warnings,
                errors=[str(de)],
                metadata=ExecutionMetadata(total_duration_seconds=round(time.time() - start_time, 4)),
            )

        # 4. Sequential Execution with Output Passing
        completed_results: Dict[str, OperationResult] = {}
        all_warnings: List[str] = list(val_result.warnings)
        all_errors: List[str] = []

        for op in ordered_operations:
            op_id = op.operation_id

            # Check if predecessor dependency failed
            if op.depends_on and op.depends_on in completed_results:
                dep_res = completed_results[op.depends_on]
                if dep_res.status != "SUCCESS":
                    logger.warning("Skipping operation %s because dependency %s failed.", op_id, op.depends_on)
                    completed_results[op_id] = OperationResult(
                        operation_id=op_id,
                        function_name=op.function_name,
                        status="SKIPPED_DEPENDENCY_FAILED",
                        error_message=f"Skipped because dependency '{op.depends_on}' failed.",
                    )
                    continue

            # Extract outputs from predecessor to pass into successor
            overrides = self._extract_dependency_overrides(op, completed_results)

            # Run operation
            op_result = self.runner.run_operation(op, overrides=overrides)
            completed_results[op_id] = op_result

            if op_result.warnings:
                all_warnings.extend(op_result.warnings)
            if op_result.status == "FAILED" and op_result.error_message:
                all_errors.append(f"Operation {op_id} failed: {op_result.error_message}")

        # 5. Aggregate Status and Metadata
        operations_list = [completed_results[op.operation_id] for op in query_plan.operations]
        success_count = sum(1 for r in operations_list if r.status == "SUCCESS")
        total_ops = len(operations_list)

        if success_count == total_ops:
            overall_status: ExecutionStatus = "SUCCESS"
        elif success_count > 0:
            overall_status = "PARTIAL_SUCCESS"
        else:
            overall_status = "FAILED"

        # Build combined result convenience view
        combined_result = None
        if len(operations_list) == 1 and operations_list[0].data:
            combined_result = operations_list[0].data
        elif len(operations_list) > 1:
            combined_result = {
                r.operation_id: r.data for r in operations_list if r.data is not None
            }

        total_duration = round(time.time() - start_time, 4)
        exec_metadata = self._build_execution_metadata(query_plan, operations_list, val_result, total_duration)

        return ExecutionResult(
            query_id=query_plan.query_id,
            original_question=query_plan.original_question,
            status=overall_status,
            query_type=query_plan.query_type,
            operations=operations_list,
            combined_result=clean_for_json(combined_result),
            validation_status=val_result.status,
            warnings=all_warnings,
            errors=all_errors,
            metadata=exec_metadata,
        )

    def _resolve_execution_order(self, operations: List[AnalyticalOperation]) -> List[AnalyticalOperation]:
        """
        Topologically sorts operations based on depends_on.
        Detects missing dependencies, duplicate IDs, and circular dependency cycles.
        """
        op_map = {}
        for op in operations:
            if op.operation_id in op_map:
                raise DependencyError(f"Duplicate operation_id '{op.operation_id}' in query plan.")
            op_map[op.operation_id] = op

        # Build in-degree and graph
        in_degree: Dict[str, int] = {op_id: 0 for op_id in op_map}
        adj_list: Dict[str, List[str]] = defaultdict(list)

        for op in operations:
            if op.depends_on:
                if op.depends_on not in op_map:
                    raise DependencyError(
                        f"Operation '{op.operation_id}' depends on non-existent operation '{op.depends_on}'."
                    )
                adj_list[op.depends_on].append(op.operation_id)
                in_degree[op.operation_id] += 1

        # Kahn's algorithm
        queue = deque([op_id for op_id, deg in in_degree.items() if deg == 0])
        ordered_ids = []

        while queue:
            curr = queue.popleft()
            ordered_ids.append(curr)

            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_ids) != len(op_map):
            raise DependencyError("Circular dependency detected among analytical operations.")

        return [op_map[op_id] for op_id in ordered_ids]

    def _extract_dependency_overrides(
        self,
        target_op: AnalyticalOperation,
        completed_results: Dict[str, OperationResult],
    ) -> Dict[str, Any]:
        """
        Extracts relevant outputs from a predecessor operation to feed into the successor operation.
        """
        if not target_op.depends_on:
            return {}

        pred_result = completed_results.get(target_op.depends_on)
        if not pred_result or not pred_result.data:
            return {}

        overrides = {}
        pred_data = pred_result.data

        # Case 1: Predecessor produced a list of institutions (e.g. from get_category_performance)
        # Successor accepts institution_uids (e.g. get_parameter_relationship or get_multidimensional_performance)
        if "institutions" in pred_data and isinstance(pred_data["institutions"], list):
            inst_uids = [
                str(inst["institution_uid"]) for inst in pred_data["institutions"] if "institution_uid" in inst
            ]
            if inst_uids and target_op.function_name in ("get_parameter_relationship", "get_multidimensional_performance"):
                # If target_op didn't specify distinct institutions, filter to the top cohort from op 1
                if not target_op.institution_uids:
                    overrides["institution_uids"] = inst_uids

        # Case 2: Predecessor produced gainers from get_rank_movement
        elif "gainers" in pred_data and isinstance(pred_data["gainers"], list):
            inst_uids = [
                str(g["institution_uid"]) for g in pred_data["gainers"] if "institution_uid" in g
            ]
            if inst_uids and target_op.function_name in ("get_parameter_relationship", "get_multidimensional_performance"):
                if not target_op.institution_uids:
                    overrides["institution_uids"] = inst_uids

        return overrides

    def _build_execution_metadata(
        self,
        plan: QueryPlan,
        results: List[OperationResult],
        val_result: Any,
        duration: float,
    ) -> ExecutionMetadata:
        """Constructs aggregated metadata across all executed operations."""
        categories = set()
        years = set()
        all_params = set()
        methods = set()
        states = set()
        insts = set()
        records_considered = 0
        valid_obs = 0
        output_recs = 0

        for r in results:
            if r.metadata:
                m = r.metadata
                if "category" in m and m["category"]:
                    categories.add(m["category"])
                if "parameters" in m and m["parameters"]:
                    all_params.update(m["parameters"])
                if "calculation_method" in m and m["calculation_method"]:
                    methods.add(m["calculation_method"])
                if "records_considered" in m and isinstance(m["records_considered"], int):
                    records_considered += m["records_considered"]
                if "valid_observations" in m and isinstance(m["valid_observations"], int):
                    valid_obs += m["valid_observations"]

            if r.data:
                d = r.data
                if "institutions" in d and isinstance(d["institutions"], list):
                    output_recs += len(d["institutions"])
                elif "gainers" in d and isinstance(d["gainers"], list):
                    output_recs += len(d["gainers"])

        for op in plan.operations:
            if op.year:
                years.add(op.year)
            if op.states:
                states.update(op.states)
            if op.institution_names:
                insts.update(op.institution_names)
            if op.institution_uids:
                insts.update(op.institution_uids)

        return ExecutionMetadata(
            category=list(categories)[0] if len(categories) == 1 else (", ".join(categories) if categories else None),
            year=list(years)[0] if len(years) == 1 else None,
            year_range=sorted(list(years)) if len(years) > 1 else None,
            institution_filters=sorted(list(insts)),
            state_filters=sorted(list(states)),
            selected_parameters=sorted(list(all_params)),
            analytical_methods=sorted(list(methods)),
            records_considered=records_considered if records_considered > 0 else None,
            valid_observations=valid_obs if valid_obs > 0 else None,
            output_records=output_recs if output_recs > 0 else None,
            comparability_warnings=val_result.comparability_notes,
            total_duration_seconds=duration,
        )


def get_query_executor() -> QueryExecutor:
    """Returns singleton QueryExecutor instance."""
    return QueryExecutor()

