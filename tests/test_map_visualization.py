"""
Unit Tests for Map Visualizations and Graphical Perception Principles (Phase 7 & 8).
Validates India geographic coordinates, map chart planning, Plotly Scattergeo rendering,
and Edward Tufte Data-Ink / Cleveland & McGill Graphical Perception compliance.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go

from src.visualization.geo_data import get_coordinates, STATE_COORDINATES, CITY_COORDINATES
from src.visualization.chart_planner import ChartPlanner
from src.visualization.plotly_renderer import PlotlyRenderer
from src.visualization.chart_schema import ChartSpecification
from src.execution.result_schema import OperationResult
from src.analytics.engine import NIRFAnalyticsEngine


@pytest.fixture
def analytics_engine():
    return NIRFAnalyticsEngine()


@pytest.fixture
def chart_planner():
    return ChartPlanner()


@pytest.fixture
def renderer():
    return PlotlyRenderer()


class TestGeographicCoordinates:
    """Verifies precision coordinate mapping for Indian institutions and states."""

    def test_state_centroids(self):
        tn_coords = get_coordinates(state="Tamil Nadu")
        assert abs(tn_coords[0] - 11.1271) < 0.1
        assert abs(tn_coords[1] - 78.6569) < 0.1

        delhi_coords = get_coordinates(state="Delhi")
        assert abs(delhi_coords[0] - 28.7041) < 0.1
        assert abs(delhi_coords[1] - 77.1025) < 0.1

    def test_city_level_precedence_over_state(self):
        # Chennai city coordinates should be returned, not state centroid
        coords = get_coordinates(city="Chennai", state="Tamil Nadu")
        assert abs(coords[0] - 13.0827) < 0.1
        assert abs(coords[1] - 80.2707) < 0.1

    def test_unknown_location_fallback(self):
        # Unknown city falls back to state centroid
        coords = get_coordinates(city="UnknownCity123", state="Karnataka")
        assert coords == STATE_COORDINATES["karnataka"]


class TestMapChartPlanning:
    """Verifies that ChartPlanner creates valid Map ChartSpecifications when requested."""

    def test_plan_map_for_top_institutions(self, chart_planner, analytics_engine):
        raw = analytics_engine.get_category_performance("Engineering", 2025, top_n=10)
        op = OperationResult(operation_id="op_cat", function_name="get_category_performance", status="SUCCESS", data=raw)

        # Plan with explicit "map" preference
        spec = chart_planner.plan_chart(op, explicit_chart_type="map")

        assert spec.chart_type == "map"
        assert "Geographic Map" in spec.title
        assert spec.lat_field == "latitude"
        assert spec.lon_field == "longitude"
        assert len(spec.data) == 10
        assert "latitude" in spec.data[0]
        assert "longitude" in spec.data[0]
        assert "city" in spec.data[0]

    def test_plan_map_for_geographic_analysis(self, chart_planner, analytics_engine):
        raw = analytics_engine.get_geographic_analysis("Engineering", 2025)
        op = OperationResult(operation_id="op_geo", function_name="get_geographic_analysis", status="SUCCESS", data=raw)

        spec = chart_planner.plan_chart(op, user_query="show state distribution on map")
        assert spec.chart_type == "map"
        assert len(spec.data) > 0
        assert "distinct_institutions" in spec.data[0]


class TestPlotlyMapRendering:
    """Verifies that PlotlyRenderer renders publication-quality India maps."""

    def test_render_map_scattergeo(self, renderer):
        spec = ChartSpecification(
            chart_type="map",
            title="Top Engineering Institutions on Map",
            lat_field="latitude",
            lon_field="longitude",
            color_field="state",
            hover_fields=["institution", "rank", "score", "city", "state"],
            data=[
                {"institution": "IIT Madras", "rank": 1, "score": 88.72, "city": "Chennai", "state": "Tamil Nadu", "latitude": 13.08, "longitude": 80.27},
                {"institution": "IIT Delhi", "rank": 2, "score": 85.74, "city": "New Delhi", "state": "Delhi", "latitude": 28.61, "longitude": 77.20},
                {"institution": "IIT Bombay", "rank": 3, "score": 83.65, "city": "Mumbai", "state": "Maharashtra", "latitude": 19.07, "longitude": 72.87},
            ],
        )

        fig = renderer.render(spec)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.data[0].type == "scattergeo"

        # Check geo projection bounds
        geo_dict = fig.layout.geo
        assert geo_dict.center.lat == 22.0
        assert geo_dict.center.lon == 82.0
        assert geo_dict.showcountries is True


class TestGraphicalPerceptionAndDataInkRatio:
    """Verifies compliance with Tufte's Data-Ink ratio and Cleveland-McGill perception rules."""

    def test_bar_chart_data_ink_and_zero_baseline(self, renderer):
        spec = ChartSpecification(
            chart_type="bar",
            title="Top 5 Scores",
            x_field="institution",
            y_field="score",
            data=[
                {"institution": "IIT Madras", "score": 88.72},
                {"institution": "IIT Delhi", "score": 85.74},
            ],
            axis_labels={"x": "Institution", "y": "Score"},
        )
        fig = renderer.render(spec)

        # 1. Cleveland & McGill: Bar charts must anchor strictly to zero baseline
        assert fig.layout.yaxis.rangemode == "tozero"

        # 2. Tufte Data-Ink: Categorical axis must not have distracting vertical gridlines
        assert fig.layout.xaxis.showgrid is False

        # 3. Tufte Data-Ink: Subtle horizontal gridlines only
        assert fig.layout.yaxis.showgrid is True
        assert fig.layout.yaxis.gridcolor == "#F1F5F9"

        # 4. Tufte Direct Data Labels on Bars (reduces cognitive load and lookup eye travel)
        assert fig.data[0].textposition in ["outside", "auto"]
        assert fig.data[0].texttemplate == "%{y:.1f}"

        # 5. Redundant single-trace legend must be suppressed
        assert fig.layout.showlegend is False

    def test_horizontal_bar_gainers_decliners_direct_labels(self, renderer):
        spec = ChartSpecification(
            chart_type="horizontal_bar",
            title="Rank Gainers",
            x_field="rank_improvement",
            y_field="institution",
            data=[
                {"institution": "College A", "rank_improvement": 12},
                {"institution": "College B", "rank_improvement": -5},
            ],
            axis_labels={"x": "Rank Improvement", "y": "Institution"},
        )
        fig = renderer.render(spec)
        assert fig.data[0].orientation == "h"
        assert fig.data[0].texttemplate == "%{x:+.1f}"

    def test_render_map_dots_only_with_hover(self, renderer):
        spec = ChartSpecification(
            chart_type="map",
            title="Top Institutions",
            lat_field="latitude",
            lon_field="longitude",
            hover_fields=["institution", "rank", "score", "city", "state"],
            data=[
                {"institution": "Indian Institute of Technology Madras", "rank": 1, "score": 88.72, "city": "Chennai", "state": "Tamil Nadu", "latitude": 13.08, "longitude": 80.27},
            ],
        )
        fig = renderer.render(spec)
        # Dot only on map canvas: no text clutter
        assert fig.data[0].mode == "markers"
        assert fig.data[0].hoverinfo == "text"
        assert "Indian Institute of Technology Madras" in fig.data[0].hovertext[0]

    def test_bar_chart_shortened_institution_names(self, renderer):
        spec = ChartSpecification(
            chart_type="bar",
            title="Top Engineering Institutions",
            x_field="institution",
            y_field="score",
            data=[
                {"institution": "Indian Institute of Technology Madras", "score": 88.72},
                {"institution": "National Institute of Technology Tiruchirappalli", "score": 75.40},
            ],
            axis_labels={"x": "Institution", "y": "Score"},
        )
        fig = renderer.render(spec)
        # Verify X-axis uses clean short acronyms
        assert fig.data[0].x == ("IIT Madras", "NIT Trichy") or list(fig.data[0].x) == ["IIT Madras", "NIT Trichy"]
        # Hover text preserves full official name
        assert "Indian Institute of Technology Madras" in fig.data[0].hovertext[0]
        assert "National Institute of Technology Tiruchirappalli" in fig.data[0].hovertext[1]


