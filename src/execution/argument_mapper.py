"""
Argument Mapper for NIRF Query Execution Engine (Phase 4).
Maps AnalyticalOperation schemas to the exact keyword arguments expected by Phase 2 functions,
enforcing required fields, rejecting unsupported parameters, and normalizing types.
"""

from typing import Dict, Any, Optional, List
import logging

from src.query_engine.schemas import AnalyticalOperation
from src.execution.exceptions import ArgumentMappingError

logger = logging.getLogger(__name__)


class ArgumentMapper:
    """
    Translates an AnalyticalOperation into a deterministic dictionary of keyword arguments
    customized for each of the 10 Phase 2 analytical functions.
    """

    def map_arguments(self, op: AnalyticalOperation) -> Dict[str, Any]:
        """
        Routes and maps arguments for a given operation.

        Args:
            op: Validated AnalyticalOperation.

        Returns:
            Dictionary of exact keyword arguments for the target Phase 2 function.

        Raises:
            ArgumentMappingError: If mandatory parameters are missing or invalid.
        """
        fn = op.function_name
        mapper_method_name = f"_map_{fn}"
        mapper_method = getattr(self, mapper_method_name, None)

        if not mapper_method:
            raise ArgumentMappingError(f"No argument mapping implemented for function '{fn}'.")

        return mapper_method(op)

    def _map_get_institution_trend(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: institution_id_or_name, category
        inst_target = None
        if op.institution_uids:
            inst_target = op.institution_uids[0]
        elif op.institution_names:
            inst_target = op.institution_names[0]

        if not inst_target:
            raise ArgumentMappingError("get_institution_trend requires at least one institution UID or name.")
        if not op.category:
            raise ArgumentMappingError("get_institution_trend requires a category.")

        return {
            "institution_id_or_name": str(inst_target),
            "category": str(op.category),
            "start_year": int(op.start_year) if op.start_year is not None else 2017,
            "end_year": int(op.end_year) if op.end_year is not None else 2025,
            "parameters": op.parameters if op.parameters else None,
        }

    def _map_get_rank_movement(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, start_year, end_year
        if not op.category:
            raise ArgumentMappingError("get_rank_movement requires a category.")
        if op.start_year is None:
            raise ArgumentMappingError("get_rank_movement requires start_year.")
        if op.end_year is None:
            raise ArgumentMappingError("get_rank_movement requires end_year.")

        return {
            "category": str(op.category),
            "start_year": int(op.start_year),
            "end_year": int(op.end_year),
            "state": str(op.states[0]) if op.states else None,
            "top_n": int(op.top_n) if op.top_n is not None else 10,
            "movement_type": str(op.movement_type) if op.movement_type else "both",
        }

    def _map_get_category_performance(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, year
        if not op.category:
            raise ArgumentMappingError("get_category_performance requires a category.")
        if op.year is None:
            raise ArgumentMappingError("get_category_performance requires year.")

        return {
            "category": str(op.category),
            "year": int(op.year),
            "state": str(op.states[0]) if op.states else None,
            "top_n": int(op.top_n) if op.top_n is not None else None,
        }

    def _map_get_geographic_analysis(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Optional: category, year, states, multi_year_trend
        return {
            "category": str(op.category) if op.category else None,
            "year": int(op.year) if op.year is not None else 2025,
            "states": [str(s) for s in op.states] if op.states else None,
            "multi_year_trend": bool(op.multi_year_trend) if op.multi_year_trend is not None else False,
        }

    def _map_get_parameter_correlation(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, year
        if not op.category:
            raise ArgumentMappingError("get_parameter_correlation requires a category.")
        if op.year is None:
            raise ArgumentMappingError("get_parameter_correlation requires year.")

        return {
            "category": str(op.category),
            "year": int(op.year),
            "parameters": [str(p) for p in op.parameters] if op.parameters else None,
            "method": str(op.correlation_method) if op.correlation_method else "both",
        }

    def _map_get_parameter_relationship(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, year, param_x, param_y
        if not op.category:
            raise ArgumentMappingError("get_parameter_relationship requires a category.")
        if op.year is None:
            raise ArgumentMappingError("get_parameter_relationship requires year.")

        px = op.param_x or (op.parameters[0] if op.parameters and len(op.parameters) >= 1 else None)
        py = op.param_y or (op.parameters[1] if op.parameters and len(op.parameters) >= 2 else None)

        if not px or not py:
            raise ArgumentMappingError("get_parameter_relationship requires param_x and param_y.")

        return {
            "category": str(op.category),
            "year": int(op.year),
            "param_x": str(px).lower(),
            "param_y": str(py).lower(),
            "institution_uids": [str(u) for u in op.institution_uids] if op.institution_uids else None,
        }

    def _map_get_multidimensional_performance(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, year
        if not op.category:
            raise ArgumentMappingError("get_multidimensional_performance requires a category.")
        if op.year is None:
            raise ArgumentMappingError("get_multidimensional_performance requires year.")

        return {
            "category": str(op.category),
            "year": int(op.year),
            "institution_uids": [str(u) for u in op.institution_uids] if op.institution_uids else None,
            "institution_names": [str(n) for n in op.institution_names] if op.institution_names else None,
            "parameters": [str(p) for p in op.parameters] if op.parameters else None,
            "top_n": int(op.top_n) if op.top_n is not None else 10,
        }

    def _map_get_score_distribution(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, year
        if not op.category:
            raise ArgumentMappingError("get_score_distribution requires a category.")
        if op.year is None:
            raise ArgumentMappingError("get_score_distribution requires year.")

        metric_target = op.metric or (op.parameters[0] if op.parameters else "score")

        return {
            "category": str(op.category),
            "year": int(op.year),
            "metric": str(metric_target).lower(),
            "state": str(op.states[0]) if op.states else None,
            "bins_count": int(op.bins_count) if op.bins_count is not None else 10,
        }

    def _map_get_rank_transitions(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, start_year, end_year
        if not op.category:
            raise ArgumentMappingError("get_rank_transitions requires a category.")
        if op.start_year is None:
            raise ArgumentMappingError("get_rank_transitions requires start_year.")
        if op.end_year is None:
            raise ArgumentMappingError("get_rank_transitions requires end_year.")

        return {
            "category": str(op.category),
            "start_year": int(op.start_year),
            "end_year": int(op.end_year),
            "custom_bands": op.custom_bands,
        }

    def _map_get_outlier_analysis(self, op: AnalyticalOperation) -> Dict[str, Any]:
        # Required: category, year
        if not op.category:
            raise ArgumentMappingError("get_outlier_analysis requires a category.")
        if op.year is None:
            raise ArgumentMappingError("get_outlier_analysis requires year.")

        metric_target = op.metric or (op.parameters[0] if op.parameters else "score")

        return {
            "category": str(op.category),
            "year": int(op.year),
            "metric": str(metric_target).lower() if metric_target else "score",
            "method": str(op.outlier_method) if op.outlier_method else "iqr",
            "threshold": float(op.outlier_threshold) if op.outlier_threshold is not None else 1.5,
            "lookback_years": [int(y) for y in op.lookback_years] if op.lookback_years else None,
        }

    def _map_get_category_evolution(self, op: AnalyticalOperation) -> Dict[str, Any]:
        return {
            "start_year": int(op.start_year) if op.start_year is not None else 2017,
            "end_year": int(op.end_year) if op.end_year is not None else 2025,
            "category": str(op.category) if op.category else None,
        }


def get_argument_mapper() -> ArgumentMapper:
    """Returns singleton ArgumentMapper instance."""
    return ArgumentMapper()

