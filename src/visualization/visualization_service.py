"""
Visualization Integration Service (Phase 7).
Connects Phase 4 ExecutionResult and OperationResults with the ChartPlanner and PlotlyRenderer.
Handles single and multi-operation workflows, graceful table fallbacks, export utilities,
and warning propagation for seamless consumption by Phase 8 conversational interfaces.
"""

from typing import Dict, Any, List, Optional, Union
import logging

from src.execution.result_schema import ExecutionResult, OperationResult
from src.visualization.chart_planner import ChartPlanner, get_chart_planner
from src.visualization.chart_schema import (
    ChartSpecification,
    VisualizationResult,
    VisualizationStatus,
)
from src.visualization.plotly_renderer import PlotlyRenderer, RenderingError, get_plotly_renderer

logger = logging.getLogger(__name__)


class VisualizationService:
    """
    Central visualization service for the NIRF Conversational Assistant.
    Converts Phase 4 analytical outputs into publication-quality Plotly figures
    or structured tabular data without data fabrication or ungrounded transformations.
    """

    def __init__(
        self,
        planner: Optional[ChartPlanner] = None,
        renderer: Optional[PlotlyRenderer] = None,
    ):
        self.planner = planner or get_chart_planner()
        self.renderer = renderer or get_plotly_renderer()

    def visualize_execution_result(
        self,
        execution_result: ExecutionResult,
        user_query: Optional[str] = None,
        chart_preference: Optional[str] = None,
    ) -> List[VisualizationResult]:
        """
        Processes a full Phase 4 ExecutionResult (single or multi-operation DAG).
        Generates an independent VisualizationResult for each operation in the plan.

        Args:
            execution_result: Validated ExecutionResult from Phase 4 QueryExecutor.
            user_query: Optional original user question (for explicit chart requests).
            chart_preference: Optional explicit chart type parameter.

        Returns:
            List of VisualizationResult objects, one per operation in the execution plan.
        """
        results: List[VisualizationResult] = []

        if not execution_result.operations:
            logger.warning("ExecutionResult %s contains no operations to visualize.", execution_result.execution_id)
            return results

        # Pass aggregated comparability and validation warnings
        global_warnings = list(execution_result.warnings or [])

        for op in execution_result.operations:
            vis_res = self.visualize_operation(
                operation_result=op,
                user_query=user_query or execution_result.original_question,
                chart_preference=chart_preference,
                inherited_warnings=global_warnings,
            )
            results.append(vis_res)

            # If a map was planned, also generate the companion comparison chart so user sees both map and graph
            if vis_res.chart_spec and vis_res.chart_spec.chart_type == "map":
                try:
                    companion_spec = self.planner.plan_chart(
                        operation_result=op,
                        user_query=None,
                        explicit_chart_type="bar",
                    )
                    if companion_spec and companion_spec.chart_type not in ["map", "none", "table"]:
                        comp_fig = self.renderer.render(companion_spec)
                        comp_table_cols = list(companion_spec.data[0].keys()) if companion_spec.data else []
                        comp_res = VisualizationResult(
                            operation_id=f"{op.operation_id}_comp_bar",
                            function_name=op.function_name,
                            status="SUCCESS",
                            has_chart=True,
                            chart_spec=companion_spec,
                            figure=comp_fig,
                            table_data=companion_spec.data,
                            table_columns=comp_table_cols,
                            explanation=f"Analytical Comparison Graph for {companion_spec.title}",
                            warnings=companion_spec.warnings,
                            metadata=companion_spec.metadata,
                        )
                        results.append(comp_res)
                except Exception as ce:
                    logger.debug("Could not plan companion chart: %s", ce)

        return results

    def visualize_operation(
        self,
        operation_result: OperationResult,
        user_query: Optional[str] = None,
        chart_preference: Optional[str] = None,
        inherited_warnings: Optional[List[str]] = None,
    ) -> VisualizationResult:
        """
        Processes a single Phase 4 OperationResult through planning and rendering.

        Args:
            operation_result: Validated OperationResult.
            user_query: Optional user prompt text.
            chart_preference: Optional explicit chart request (e.g. 'scatter', 'line').
            inherited_warnings: Optional warnings from predecessor operations or execution plan.

        Returns:
            Structured VisualizationResult with Plotly figure or table fallback data.
        """
        op_id = operation_result.operation_id
        fn_name = operation_result.function_name
        warnings = list(operation_result.warnings or [])
        if inherited_warnings:
            for w in inherited_warnings:
                if w not in warnings:
                    warnings.append(w)

        # 1. Handle failed or skipped operations
        if operation_result.status != "SUCCESS":
            err_msg = operation_result.error_message or f"Operation {op_id} ended with status: {operation_result.status}"
            return VisualizationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FAILED",
                has_chart=False,
                chart_spec=None,
                figure=None,
                explanation=err_msg,
                warnings=warnings,
                metadata={"status": operation_result.status},
            )

        # 2. Plan chart specification
        try:
            spec = self.planner.plan_chart(
                operation_result=operation_result,
                user_query=user_query,
                explicit_chart_type=chart_preference,
            )
            # Propagate any inherited warnings into spec
            for w in warnings:
                if w not in spec.warnings:
                    spec.warnings.append(w)
        except Exception as e:
            logger.error("Chart planning failed for %s (%s): %s", fn_name, op_id, e)
            return VisualizationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FAILED",
                has_chart=False,
                chart_spec=None,
                figure=None,
                explanation=f"Visualization planning failed: {str(e)}",
                warnings=warnings,
                metadata={"error": str(e)},
            )

        # 3. Handle explicit table fallback
        if spec.chart_type in ["table", "none"]:
            table_cols = []
            if spec.data and isinstance(spec.data[0], dict):
                table_cols = list(spec.data[0].keys())

            return VisualizationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FALLBACK_TABLE" if spec.chart_type == "table" else "SKIPPED",
                has_chart=False,
                chart_spec=spec,
                figure=None,
                table_data=spec.data,
                table_columns=table_cols,
                explanation=f"Table representation selected for {spec.title} (insufficient observations or lookup format).",
                warnings=spec.warnings,
                metadata=spec.metadata,
            )

        # 4. Render Plotly figure
        try:
            fig = self.renderer.render(spec)
            table_cols = []
            if spec.data and isinstance(spec.data[0], dict):
                table_cols = list(spec.data[0].keys())

            return VisualizationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="SUCCESS",
                has_chart=True,
                chart_spec=spec,
                figure=fig,
                table_data=spec.data,
                table_columns=table_cols,
                explanation=f"Rendered interactive {spec.chart_type} chart: '{spec.title}'.",
                warnings=spec.warnings,
                metadata=spec.metadata,
            )
        except RenderingError as re:
            logger.warning("Rendering failed for %s (%s), falling back to table: %s", fn_name, op_id, re)
            table_cols = []
            if spec.data and isinstance(spec.data[0], dict):
                table_cols = list(spec.data[0].keys())

            return VisualizationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FALLBACK_TABLE",
                has_chart=False,
                chart_spec=spec,
                figure=None,
                table_data=spec.data,
                table_columns=table_cols,
                explanation=f"Figure rendering unfeasible ({str(re)}). Structured tabular fallback provided.",
                warnings=spec.warnings + [f"Rendering fallback: {str(re)}"],
                metadata=spec.metadata,
            )
        except Exception as e:
            logger.error("Unexpected error rendering %s (%s): %s", fn_name, op_id, e)
            return VisualizationResult(
                operation_id=op_id,
                function_name=fn_name,
                status="FAILED",
                has_chart=False,
                chart_spec=spec,
                figure=None,
                explanation=f"Unexpected rendering failure: {str(e)}",
                warnings=warnings + [str(e)],
                metadata={"error": str(e)},
            )


def get_visualization_service() -> VisualizationService:
    """Returns singleton instance of VisualizationService."""
    return VisualizationService()

