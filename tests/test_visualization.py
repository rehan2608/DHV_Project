"""
Comprehensive Test Suite for Phase 7 Visualization Layer.
Covers:
- Chart planner automatic & explicit selection rules
- Plotly renderer visual encodings, reversed rank axes, and error guards
- End-to-end integration service across single & multi-operation Phase 4 ExecutionResults
- Table fallbacks for lookups and small samples
- Warning and metadata preservation
- Non-fabrication invariants
"""

import pytest
import plotly.graph_objects as go

from src.analytics.engine import get_analytics_engine
from src.execution.result_schema import ExecutionResult, OperationResult, ExecutionMetadata
from src.query_engine.schemas import QueryPlan, AnalyticalOperation
from src.visualization.chart_planner import ChartPlanner, get_chart_planner
from src.visualization.plotly_renderer import PlotlyRenderer, RenderingError, get_plotly_renderer
from src.visualization.chart_schema import ChartSpecification, VisualizationResult
from src.visualization.visualization_service import VisualizationService, get_visualization_service


@pytest.fixture
def analytics_engine():
    return get_analytics_engine()


@pytest.fixture
def chart_planner():
    return get_chart_planner()


@pytest.fixture
def plotly_renderer():
    return get_plotly_renderer()


@pytest.fixture
def vis_service():
    return get_visualization_service()


# ===========================================================================
# A. Chart Planner Tests
# ===========================================================================

def test_planner_institution_trend_line_chart(chart_planner, analytics_engine):
    """Institution trend across multiple years plans a line chart with reversed rank axis."""
    raw = analytics_engine.get_institution_trend("Indian Institute of Technology Madras", "Engineering", 2020, 2025)
    op = OperationResult(operation_id="op_trend", function_name="get_institution_trend", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "line"
    assert spec.reverse_y_axis is True
    assert "Indian Institute of Technology Madras" in spec.title
    assert spec.x_field == "year"
    assert spec.y_field == "rank"
    assert len(spec.data) >= 5


def test_planner_rank_movement_horizontal_bar(chart_planner, analytics_engine):
    """Rank movement plans a horizontal bar chart showing gains and declines."""
    raw = analytics_engine.get_rank_movement("Engineering", 2020, 2025, top_n=5)
    op = OperationResult(operation_id="op_move", function_name="get_rank_movement", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type in ["horizontal_bar", "bar"]
    assert "rank_improvement" in [spec.x_field, spec.y_field]
    assert len(spec.data) > 0


def test_planner_category_performance_bar_chart(chart_planner, analytics_engine):
    """Category performance for multiple institutions plans a bar chart."""
    raw = analytics_engine.get_category_performance("Engineering", 2025, top_n=5)
    op = OperationResult(operation_id="op_cat", function_name="get_category_performance", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "bar"
    assert spec.x_field == "institution"
    assert spec.y_field == "score"
    assert len(spec.data) == 5


def test_planner_parameter_correlation_heatmap(chart_planner, analytics_engine):
    """Parameter correlation plans an annotated correlation heatmap."""
    raw = analytics_engine.get_parameter_correlation("Engineering", 2025)
    op = OperationResult(operation_id="op_corr", function_name="get_parameter_correlation", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "heatmap"
    assert spec.x_field == "param_x"
    assert spec.y_field == "param_y"
    assert len(spec.data) == 25  # 5x5 matrix


def test_planner_parameter_relationship_scatter(chart_planner, analytics_engine):
    """Parameter relationship plans a scatter plot with regression trendline."""
    raw = analytics_engine.get_parameter_relationship("Engineering", 2025, "rpc", "tlr")
    op = OperationResult(operation_id="op_rel", function_name="get_parameter_relationship", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "scatter"
    assert spec.include_trendline is True
    assert "x_val" in spec.data[0]
    assert "y_val" in spec.data[0]
    assert "institution" in spec.data[0]


def test_planner_score_distribution_histogram(chart_planner, analytics_engine):
    """Score distribution plans a frequency histogram."""
    raw = analytics_engine.get_score_distribution("Engineering", 2025, "score")
    op = OperationResult(operation_id="op_dist", function_name="get_score_distribution", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "histogram"
    assert spec.x_field == "bin_label"
    assert spec.y_field == "count"


def test_planner_geographic_analysis_bar_chart(chart_planner, analytics_engine):
    """Geographic state comparison plans a ranked bar chart."""
    raw = analytics_engine.get_geographic_analysis("Engineering", 2025, states=["Karnataka", "Tamil Nadu"])
    op = OperationResult(operation_id="op_geo", function_name="get_geographic_analysis", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "bar"
    assert spec.x_field == "state"
    assert spec.y_field == "distinct_institutions"


def test_planner_multidimensional_performance_grouped_bar(chart_planner, analytics_engine):
    """Multidimensional performance plans a grouped bar chart."""
    raw = analytics_engine.get_multidimensional_performance("Engineering", 2025, top_n=3)
    op = OperationResult(operation_id="op_multi", function_name="get_multidimensional_performance", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "grouped_bar"
    assert spec.x_field == "institution"
    assert spec.y_field == "score"
    assert spec.color_field == "parameter"


def test_planner_rank_transitions_heatmap(chart_planner, analytics_engine):
    """Rank transitions plans a transition matrix heatmap."""
    raw = analytics_engine.get_rank_transitions("Engineering", 2020, 2025)
    op = OperationResult(operation_id="op_trans", function_name="get_rank_transitions", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "heatmap"
    assert spec.x_field == "end_band"
    assert spec.y_field == "start_band"


def test_planner_simple_lookup_falls_back_to_table(chart_planner, analytics_engine):
    """Single observation lookup falls back to table representation."""
    raw = analytics_engine.get_institution_trend("Indian Institute of Technology Madras", "Engineering", 2025, 2025)
    op = OperationResult(operation_id="op_single", function_name="get_institution_trend", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op)

    assert spec.chart_type == "table"


def test_planner_explicit_supported_chart_preference(chart_planner, analytics_engine):
    """Explicit request for scatter plot is honored on parameter relationship."""
    raw = analytics_engine.get_parameter_relationship("Engineering", 2025, "rpc", "tlr")
    op = OperationResult(operation_id="op_pref", function_name="get_parameter_relationship", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op, user_query="Show me a scatter plot with dots")

    assert spec.chart_type == "scatter"


def test_planner_explicit_table_preference(chart_planner, analytics_engine):
    """Explicit request for table is honored even when chart is viable."""
    raw = analytics_engine.get_institution_trend("Indian Institute of Technology Madras", "Engineering", 2020, 2025)
    op = OperationResult(operation_id="op_table_pref", function_name="get_institution_trend", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op, user_query="Show me a table of the rankings")

    assert spec.chart_type == "table"


# ===========================================================================
# B. Plotly Renderer Tests
# ===========================================================================

def test_renderer_valid_line_chart(plotly_renderer):
    """Renderer produces valid Plotly figure for line specification."""
    spec = ChartSpecification(
        chart_type="line",
        title="Test Line Chart",
        x_field="year",
        y_field="rank",
        reverse_y_axis=True,
        data=[
            {"year": 2020, "rank": 10},
            {"year": 2021, "rank": 8},
            {"year": 2022, "rank": 5},
        ],
    )
    fig = plotly_renderer.render(spec)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    # Check reversed Y axis
    assert fig.layout.yaxis.autorange == "reversed"
    assert "Test Line Chart" in fig.layout.title.text


def test_renderer_valid_horizontal_bar_chart(plotly_renderer):
    """Renderer produces valid horizontal bar chart with reference zero line."""
    spec = ChartSpecification(
        chart_type="horizontal_bar",
        title="Rank Improvement",
        x_field="rank_improvement",
        y_field="institution",
        data=[
            {"institution": "Inst A", "rank_improvement": 15},
            {"institution": "Inst B", "rank_improvement": -5},
        ],
    )
    fig = plotly_renderer.render(spec)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].orientation == "h"


def test_renderer_valid_scatter_plot(plotly_renderer):
    """Renderer produces scatter plot with data points and trendline."""
    spec = ChartSpecification(
        chart_type="scatter",
        title="Test Scatter",
        x_field="x",
        y_field="y",
        include_trendline=True,
        data=[
            {"x": 10, "y": 20, "institution": "A"},
            {"x": 20, "y": 40, "institution": "B"},
            {"x": 30, "y": 50, "institution": "C"},
        ],
        metadata={
            "trendline": [{"x": 10, "y": 20}, {"x": 30, "y": 50}],
            "regression": {"r_squared": 0.95},
        },
    )
    fig = plotly_renderer.render(spec)
    assert isinstance(fig, go.Figure)
    # Scatter points trace + trendline trace
    assert len(fig.data) == 2


def test_renderer_valid_heatmap(plotly_renderer):
    """Renderer produces 2D annotated heatmap with formatted text values."""
    spec = ChartSpecification(
        chart_type="heatmap",
        title="Test Heatmap",
        x_field="col",
        y_field="row",
        color_field="val",
        data=[
            {"row": "R1", "col": "C1", "val": 0.85},
            {"row": "R1", "col": "C2", "val": 0.30},
            {"row": "R2", "col": "C1", "val": 0.30},
            {"row": "R2", "col": "C2", "val": 0.95},
        ],
    )
    fig = plotly_renderer.render(spec)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "heatmap"
    assert fig.data[0].z.shape == (2, 2)


def test_renderer_empty_data_raises_error(plotly_renderer):
    """Renderer raises RenderingError when data is empty."""
    spec = ChartSpecification(
        chart_type="line",
        title="Empty",
        x_field="year",
        y_field="rank",
        data=[],
    )
    with pytest.raises(RenderingError, match="contains no data records"):
        plotly_renderer.render(spec)


def test_renderer_missing_required_fields_raises_error(plotly_renderer):
    """Renderer raises RenderingError when required mapping fields are absent."""
    spec = ChartSpecification(
        chart_type="line",
        title="Missing Fields",
        x_field="nonexistent_x",
        y_field="nonexistent_y",
        data=[{"a": 1, "b": 2}],
    )
    with pytest.raises(RenderingError, match="Missing required fields"):
        plotly_renderer.render(spec)


def test_renderer_preserves_missing_values_without_interpolating(plotly_renderer):
    """Renderer does not interpolate across missing/None years (connectgaps=False)."""
    spec = ChartSpecification(
        chart_type="line",
        title="Missing Year",
        x_field="year",
        y_field="rank",
        data=[
            {"year": 2020, "rank": 10},
            {"year": 2021, "rank": None},
            {"year": 2022, "rank": 5},
        ],
    )
    fig = plotly_renderer.render(spec)
    assert fig.data[0].connectgaps is False
    assert fig.data[0].y[1] is None


# ===========================================================================
# C. Visualization Integration Service Tests
# ===========================================================================

def test_service_single_operation_execution(vis_service, analytics_engine):
    """VisualizationService successfully processes single OperationResult."""
    raw = analytics_engine.get_institution_trend("Indian Institute of Technology Madras", "Engineering", 2020, 2025)
    op = OperationResult(operation_id="op_single", function_name="get_institution_trend", status="SUCCESS", data=raw)
    res = vis_service.visualize_operation(op)

    assert res.status == "SUCCESS"
    assert res.has_chart is True
    assert isinstance(res.figure, go.Figure)
    assert res.to_csv() is not None
    assert "<html>" in res.to_html(full_html=True)


def test_service_multi_operation_dag_execution(vis_service, analytics_engine):
    """VisualizationService processes multi-operation DAG (BM-04)."""
    raw_cat = analytics_engine.get_category_performance("Engineering", 2025, top_n=10)
    raw_rel = analytics_engine.get_parameter_relationship("Engineering", 2025, "rpc", "tlr")

    op1 = OperationResult(operation_id="op_cat", function_name="get_category_performance", status="SUCCESS", data=raw_cat)
    op2 = OperationResult(operation_id="op_rel", function_name="get_parameter_relationship", status="SUCCESS", data=raw_rel)

    exec_res = ExecutionResult(
        query_id="multi_test",
        original_question="Top 10 RPC and relationship with TLR",
        status="SUCCESS",
        query_type="multi_operation",
        operations=[op1, op2],
        validation_status="VALID",
        warnings=["Test comparability limitation"],
    )

    vis_results = vis_service.visualize_execution_result(exec_res)
    assert len(vis_results) == 2

    # Op 1: Bar chart
    assert vis_results[0].status == "SUCCESS"
    assert vis_results[0].chart_spec.chart_type == "bar"
    assert "Test comparability limitation" in vis_results[0].warnings

    # Op 2: Scatter plot
    assert vis_results[1].status == "SUCCESS"
    assert vis_results[1].chart_spec.chart_type == "scatter"
    assert "Test comparability limitation" in vis_results[1].warnings


def test_service_handles_partial_operation_failure(vis_service, analytics_engine):
    """VisualizationService handles partial failures in multi-operation DAGs."""
    raw_cat = analytics_engine.get_category_performance("Engineering", 2025, top_n=5)
    op1 = OperationResult(operation_id="op_ok", function_name="get_category_performance", status="SUCCESS", data=raw_cat)
    op2 = OperationResult(
        operation_id="op_fail",
        function_name="get_rank_movement",
        status="FAILED",
        error_message="Invalid category supplied",
    )

    exec_res = ExecutionResult(
        query_id="partial_fail_test",
        original_question="Test partial fail",
        status="PARTIAL_SUCCESS",
        query_type="multi_operation",
        operations=[op1, op2],
        validation_status="VALID",
    )

    vis_results = vis_service.visualize_execution_result(exec_res)
    assert len(vis_results) == 2
    assert vis_results[0].status == "SUCCESS"
    assert vis_results[0].has_chart is True

    assert vis_results[1].status == "FAILED"
    assert vis_results[1].has_chart is False
    assert "Invalid category supplied" in vis_results[1].explanation


def test_service_table_fallback_csv_export(vis_service, analytics_engine):
    """Table fallback correctly exposes structured table_data and CSV export."""
    raw = analytics_engine.get_institution_trend("Indian Institute of Technology Madras", "Engineering", 2025, 2025)
    op = OperationResult(operation_id="op_table", function_name="get_institution_trend", status="SUCCESS", data=raw)
    res = vis_service.visualize_operation(op)

    assert res.status == "FALLBACK_TABLE"
    assert res.has_chart is False
    assert res.table_data is not None
    assert len(res.table_data) > 0
    csv_str = res.to_csv()
    assert csv_str is not None
    assert "year" in csv_str


def test_service_propagates_comparability_warnings(vis_service, analytics_engine):
    """Comparability warnings are preserved in VisualizationResult."""
    raw = analytics_engine.get_rank_movement("Management", 2017, 2025, top_n=5)
    op = OperationResult(
        operation_id="op_warn",
        function_name="get_rank_movement",
        status="SUCCESS",
        data=raw,
        warnings=["Cohort depth expanded from 50 to 100."],
    )
    res = vis_service.visualize_operation(op)

    assert any("Cohort depth expanded" in w for w in res.warnings)
    assert any("Cohort depth expanded" in w for w in res.chart_spec.warnings)


def test_horizontal_bar_rendering_positive_scores(chart_planner, plotly_renderer, analytics_engine):
    """Horizontal bar chart for absolute scores applies focal dark pine for the top performer and short names."""
    raw = analytics_engine.get_category_performance("Engineering", 2025, top_n=5)
    op = OperationResult(operation_id="op_horiz", function_name="get_category_performance", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(op, explicit_chart_type="horizontal_bar")
    assert spec.chart_type == "horizontal_bar"
    assert spec.x_field == "score"
    assert spec.y_field == "institution"

    fig = plotly_renderer.render(spec)
    assert isinstance(fig, go.Figure)
    trace = fig.data[0]
    assert trace.orientation == "h"
    # Highest score has FOCUS_DARK_COLOR (#163D34)
    assert "#163D34" in trace.marker.color
    # Institutions are shortened
    assert any("IIT" in name for name in trace.y)


def test_lollipop_chart_planning_and_rendering(chart_planner, plotly_renderer, analytics_engine):
    """Lollipop chart is planned on user request and renders stem lines and circle markers without capping 'all'."""
    raw = analytics_engine.get_category_performance("Engineering", 2024)
    op = OperationResult(operation_id="op_lollipop", function_name="get_category_performance", status="SUCCESS", data=raw)
    spec = chart_planner.plan_chart(
        op,
        user_query="give me ranking of all enginnering colleges in 2024\ngenerate a lollipop graph to show",
        explicit_chart_type="lollipop",
    )
    assert spec.chart_type == "lollipop"
    assert spec.x_field == "score"
    assert spec.y_field == "institution"
    # When user asks for "all", cohort should NOT be capped to 10
    assert len(spec.data) == len(raw["institutions"])
    assert len(spec.data) > 50

    fig = plotly_renderer.render(spec)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    # Trace 0: lines (stems)
    assert fig.data[0].mode == "lines"
    # Trace 1: markers (lollipop heads)
    assert "markers" in fig.data[1].mode
    # Highest score has dark pine contrast
    assert "#163D34" in fig.data[1].marker.color


def test_no_spurious_automatic_histogram(vis_service, analytics_engine):
    """Category performance does NOT generate automatic histograms unless requested."""
    raw = analytics_engine.get_category_performance("Research Institutions", 2025)
    op = OperationResult(operation_id="op_research", function_name="get_category_performance", status="SUCCESS", data=raw)
    exec_res = ExecutionResult(
        query_id="no_auto_hist_test",
        original_question="how many research institutions in 2025",
        status="SUCCESS",
        query_type="category_performance",
        operations=[op],
        validation_status="VALID",
    )
    vis_results = vis_service.visualize_execution_result(exec_res)
    # Exactly one primary comparison chart, NOT a companion histogram
    assert len(vis_results) == 1
    assert vis_results[0].chart_spec.chart_type == "bar"

    # But when explicitly requested, histogram IS generated
    hist_results = vis_service.visualize_execution_result(exec_res, user_query="show histogram of scores", chart_preference="histogram")
    assert len(hist_results) == 1
    assert hist_results[0].chart_spec.chart_type == "histogram"


