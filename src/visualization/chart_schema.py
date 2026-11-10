"""
Structured Chart Specification and Visualization Schemas (Phase 7).
Defines predictable Pydantic models for chart specifications, rendering configurations,
and visualization integration results for NIRF Analytics.
"""

from typing import Dict, Any, List, Optional, Literal, Union
import json
import io
import csv
from pydantic import BaseModel, Field, ConfigDict


ChartType = Literal[
    "line",
    "bar",
    "grouped_bar",
    "horizontal_bar",
    "lollipop",
    "scatter",
    "heatmap",
    "histogram",
    "box_plot",
    "map",
    "table",
    "none",
]

VisualizationStatus = Literal[
    "SUCCESS",
    "FALLBACK_TABLE",
    "SKIPPED",
    "FAILED",
]


class ChartSpecification(BaseModel):
    """
    Validated declarative specification for rendering a chart.
    Describes visual mappings, axes, sorting, and source data without coupled rendering logic.
    """
    model_config = ConfigDict(extra="ignore")

    chart_type: ChartType = Field(description="The determined or requested chart type.")
    title: str = Field(description="Descriptive chart title including entity/year/category context.")
    subtitle: Optional[str] = Field(default=None, description="Optional secondary subtitle.")
    x_field: Optional[str] = Field(default=None, description="Field name to map to the X-axis.")
    y_field: Optional[str] = Field(default=None, description="Field name to map to the Y-axis.")
    color_field: Optional[str] = Field(default=None, description="Field name for series color coding.")
    group_field: Optional[str] = Field(default=None, description="Field name for grouping categories.")
    hover_fields: List[str] = Field(default_factory=list, description="Fields to include in hover tooltip.")
    axis_labels: Dict[str, str] = Field(
        default_factory=dict,
        description="User-facing axis labels, e.g. {'x': 'Year', 'y': 'NIRF Rank'}.",
    )
    sort_order: Optional[Literal["ascending", "descending", "chronological", "none"]] = Field(
        default=None,
        description="Explicit ordering of X categories or bars.",
    )
    reverse_y_axis: bool = Field(
        default=False,
        description="True for ordinal rank metrics where rank 1 is highest on visual axis.",
    )
    include_trendline: bool = Field(
        default=False,
        description="Whether to overlay regression trendline on scatter plots.",
    )
    lat_field: Optional[str] = Field(default=None, description="Field name for latitude coordinate.")
    lon_field: Optional[str] = Field(default=None, description="Field name for longitude coordinate.")
    geo_scope: Optional[str] = Field(default="india", description="Geographic bounding scope (e.g. 'india', 'asia').")
    show_legend: bool = Field(
        default=True,
        description="Whether to render legend entries.",
    )
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Clean numerical/categorical records extracted strictly from analytical execution.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Analytical comparability warnings and visualization limitations.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual metadata (category, years, sample size, filters).",
    )


class VisualizationResult(BaseModel):
    """
    Structured outcome of visualization planning and rendering.
    Consumed directly by Phase 8 conversational UI or API layer.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    operation_id: str = Field(description="ID of the source analytical operation.")
    function_name: str = Field(description="Name of the analytical function.")
    status: VisualizationStatus = Field(description="Execution standing of visualization.")
    has_chart: bool = Field(default=False, description="Whether an interactive chart was generated.")
    chart_spec: Optional[ChartSpecification] = Field(default=None, description="The validated chart specification.")
    figure: Optional[Any] = Field(default=None, description="Plotly Graph Object Figure if rendered.")
    table_data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Structured tabular records if result is best presented or backed as a table.",
    )
    table_columns: Optional[List[str]] = Field(
        default=None,
        description="Display headers for tabular fallback data.",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the chart or reason for table fallback.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Aggregated execution warnings, comparability limits, and visualization caveats.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analytical metadata preserving valid observations, categories, and filters.",
    )

    def to_html(self, include_plotlyjs: Union[bool, str] = "cdn", full_html: bool = False) -> Optional[str]:
        """
        Exports the Plotly figure as standalone or embeddable HTML string.
        Returns None if no chart figure is present.
        """
        if self.figure is not None and hasattr(self.figure, "to_html"):
            return self.figure.to_html(include_plotlyjs=include_plotlyjs, full_html=full_html)
        return None

    def to_csv(self) -> Optional[str]:
        """
        Exports the underlying chart or tabular data as a CSV formatted string.
        Returns None if no structured data exists.
        """
        records = None
        if self.chart_spec and self.chart_spec.data:
            records = self.chart_spec.data
        elif self.table_data:
            records = self.table_data

        if not records:
            return None

        output = io.StringIO()
        # Collect distinct fieldnames preserving order
        fieldnames = []
        for r in records:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)
        return output.getvalue()

    def to_dict_summary(self) -> Dict[str, Any]:
        """Safe dictionary representation omitting complex figure objects."""
        return {
            "operation_id": self.operation_id,
            "function_name": self.function_name,
            "status": self.status,
            "has_chart": self.has_chart,
            "chart_type": self.chart_spec.chart_type if self.chart_spec else None,
            "title": self.chart_spec.title if self.chart_spec else None,
            "explanation": self.explanation,
            "table_rows": len(self.table_data) if self.table_data else (len(self.chart_spec.data) if self.chart_spec else 0),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

