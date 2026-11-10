"""
Plotly Renderer Module for NIRF Analytics (Phase 7).
Transforms validated ChartSpecifications into interactive, publication-quality Plotly figures.
Enforces reversed rank axes, non-interpolation of missing periods, clean hover templates,
and professional styling.
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from src.visualization.chart_schema import ChartSpecification
from src.analytics.utils import shorten_institution_name


class RenderingError(Exception):
    """Raised when rendering a ChartSpecification fails."""
    pass


# Consistent NIRF Assistant design palette (Storytelling with Data / Focal Contrast)
THEME_TEMPLATE = "plotly_white"
PRIMARY_COLOR = "#8CBDB1"       # Uniform Soothing Sage for all baseline data points
FOCUS_DARK_COLOR = "#163D34"    # Deep Contrast Forest Pine for the top / focus data point
SECONDARY_COLOR = "#D98871"     # Warm Terracotta Coral (when bivariate contrast is needed)
GAINER_COLOR = "#8CBDB1"        # Baseline Gainers
GAINER_DARK_COLOR = "#163D34"   # Top Gainer (Dark Focal Point)
DECLINER_COLOR = "#E2A394"      # Baseline Decliners (Soft Coral)
DECLINER_DARK_COLOR = "#B84A39" # Top Decliner (Dark Coral Focal Point)
NEUTRAL_COLOR = "#A2C3BB"       # Neutral Sage
MUTED_GRID = "#F1F5F9"          # Light subtle grid (Tufte: minimal non-data ink)
MUTED_BORDER = "#C9DED8"        # Soft Sage Border
TEXT_MAIN = "#14352D"           # Deep Forest Sage Pine for maximum legibility
TEXT_MUTED = "#557D74"          # Soothing Sage subtext


class PlotlyRenderer:
    """
    Renders ChartSpecifications into interactive Plotly figures using
    Plotly Graph Objects and Plotly Express.
    """

    def render(self, spec: ChartSpecification) -> go.Figure:
        """
        Main entry point for rendering a ChartSpecification.

        Args:
            spec: Validated ChartSpecification.

        Returns:
            Plotly Graph Objects Figure.

        Raises:
            RenderingError: If chart type is unsupported, data is empty, or rendering fails.
        """
        if not spec or spec.chart_type in ["none", "table"]:
            raise RenderingError(f"Cannot render figure for chart_type='{spec.chart_type if spec else 'None'}'.")

        if not spec.data:
            raise RenderingError(f"ChartSpecification for '{spec.title}' contains no data records.")

        render_method = getattr(self, f"_render_{spec.chart_type}", None)
        if render_method is None:
            raise RenderingError(f"Unsupported chart_type '{spec.chart_type}'.")

        fig = render_method(spec)
        self._apply_common_layout(fig, spec)
        return fig

    # -------------------------------------------------------------------------
    # 1. Line Chart (e.g. Longitudinal Trajectories)
    # -------------------------------------------------------------------------
    def _render_line(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError(f"Missing required fields '{spec.x_field}' or '{spec.y_field}' in data.")

        # Ensure chronological ordering
        df = df.sort_values(by=spec.x_field)

        fig = go.Figure()

        color_col = spec.color_field if spec.color_field and spec.color_field in df.columns else None
        groups = df.groupby(color_col) if color_col else [("Overall", df)]

        for group_name, group_df in groups:
            # Drop trailing/leading all-null, but preserve internal nulls without connecting gaps
            x_vals = group_df[spec.x_field].tolist()
            y_vals = [None if (pd.isna(v) or v is None) else v for v in group_df[spec.y_field].tolist()]

            hover_text = []
            for _, row in group_df.iterrows():
                parts = [f"<b>{spec.axis_labels.get('x', spec.x_field)}:</b> {row[spec.x_field]}"]
                for hf in spec.hover_fields:
                    if hf in row and row[hf] is not None:
                        label = hf.replace("_", " ").capitalize()
                        parts.append(f"<b>{label}:</b> {row[hf]}")
                hover_text.append("<br>".join(parts))

            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                name=str(group_name),
                mode="lines+markers",
                connectgaps=False,  # Strict: Never interpolate across unobserved/missing years
                hoverinfo="text",
                hovertext=hover_text,
                line=dict(width=3),
                marker=dict(size=8),
            ))

        # Enforce reversed Y-axis for ordinal rank metrics
        if spec.reverse_y_axis:
            fig.update_yaxes(autorange="reversed")

        return fig

    # -------------------------------------------------------------------------
    # 2. Bar Chart (e.g. Categorical Rankings & Outliers)
    # -------------------------------------------------------------------------
    def _render_bar(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError(f"Missing required fields for bar chart.")

        if spec.sort_order == "descending":
            df = df.sort_values(by=spec.y_field, ascending=False)
        elif spec.sort_order == "ascending":
            df = df.sort_values(by=spec.y_field, ascending=True)

        fig = go.Figure()

        # Tufte Direct Data Labels & Cleveland/McGill Common Scale Position
        y_is_numeric = pd.to_numeric(df[spec.y_field], errors="coerce").notnull().all()
        text_template = "%{y:.1f}" if y_is_numeric else None

        # Monochromatic Base Palette with Dark Focal Point on Max / Focus Entity
        numeric_y = pd.to_numeric(df[spec.y_field], errors="coerce")
        max_idx = numeric_y.idxmax() if numeric_y.notnull().any() else df.index[0]
        focus_entity = spec.metadata.get("institution") or spec.metadata.get("focus_institution")

        bar_colors = []
        for idx, row in df.iterrows():
            is_focus = False
            if focus_entity and str(row.get(spec.x_field, "")).lower() == str(focus_entity).lower():
                is_focus = True
            elif not focus_entity and idx == max_idx:
                is_focus = True
            bar_colors.append(FOCUS_DARK_COLOR if is_focus else PRIMARY_COLOR)

        hover_text = self._build_hover_text(df, spec)
        # Shorten institution names for clean X-axis readability while preserving full names in hovertext
        x_display = [shorten_institution_name(n) for n in df[spec.x_field]] if spec.x_field == "institution" else df[spec.x_field]

        fig.add_trace(go.Bar(
            x=x_display,
            y=df[spec.y_field],
            marker=dict(
                color=bar_colors,
                line=dict(width=1, color="#FFFFFF"),
            ),
            hoverinfo="text",
            hovertext=hover_text,
            texttemplate=text_template if len(df) <= 15 else None,
            textposition="outside" if len(df) <= 15 else "none",
            textfont=dict(size=11, color=TEXT_MAIN),
            showlegend=False,
        ))

        # 18% headroom above highest bar so direct data labels are NEVER clipped at the top
        if numeric_y.notnull().any():
            max_val = float(numeric_y.max())
            fig.update_yaxes(rangemode="tozero", range=[0, max_val * 1.18])
        else:
            fig.update_yaxes(rangemode="tozero")

        # Tufte clean horizontal gridlines only with slight angle for short names
        fig.update_xaxes(tickangle=-18 if len(df) > 5 else 0)
        return fig

    # -------------------------------------------------------------------------
    # 3. Horizontal Bar Chart (e.g. Gainers & Decliners or Absolute Rankings)
    # -------------------------------------------------------------------------
    def _render_horizontal_bar(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError(f"Missing required fields for horizontal bar chart.")

        # Sort so highest values are at the top (ascending order on y-axis in Plotly renders bottom-to-top)
        df = df.sort_values(by=spec.x_field, ascending=True)

        numeric_vals = pd.to_numeric(df[spec.x_field], errors="coerce")
        has_negative = (numeric_vals < 0).any()

        if has_negative:
            # Bipolar rank movements (gainers/decliners)
            max_gain = numeric_vals.max() if (numeric_vals > 0).any() else None
            min_loss = numeric_vals.min() if (numeric_vals < 0).any() else None

            colors = []
            for val in numeric_vals:
                if pd.notnull(val) and val > 0:
                    colors.append(GAINER_DARK_COLOR if val == max_gain else GAINER_COLOR)
                elif pd.notnull(val) and val < 0:
                    colors.append(DECLINER_DARK_COLOR if val == min_loss else DECLINER_COLOR)
                else:
                    colors.append(NEUTRAL_COLOR)

            text_template = "%{x:+.1f}"
        else:
            # Positive values (scores, counts) - highest value is focal dark pine
            max_val = numeric_vals.max() if not numeric_vals.dropna().empty else None
            colors = [
                FOCUS_DARK_COLOR if pd.notnull(val) and val == max_val else PRIMARY_COLOR
                for val in numeric_vals
            ]
            text_template = "%{x:.1f}"

        hover_text = self._build_hover_text(df, spec)
        y_display = [shorten_institution_name(n) for n in df[spec.y_field]] if spec.y_field == "institution" else df[spec.y_field]

        fig = go.Figure(go.Bar(
            x=df[spec.x_field],
            y=y_display,
            orientation="h",
            marker=dict(color=colors),
            hoverinfo="text",
            hovertext=hover_text,
            texttemplate=text_template if len(df) <= 15 else None,
            textposition="outside" if len(df) <= 15 else "none",
            textfont=dict(size=10, color=TEXT_MAIN),
            cliponaxis=False,
        ))

        if has_negative:
            fig.add_vline(x=0, line_width=1.2, line_dash="dash", line_color=MUTED_BORDER)
        else:
            # Give headroom for data labels on positive horizontal bars
            if not numeric_vals.dropna().empty:
                max_x = float(numeric_vals.max())
                fig.update_xaxes(range=[0, max_x * 1.18])

        if len(df) > 15:
            fig.update_layout(height=max(500, len(df) * 22))

        return fig

    # -------------------------------------------------------------------------
    # 3b. Lollipop Chart (Stem and Marker Dot Plot)
    # -------------------------------------------------------------------------
    def _render_lollipop(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError("Missing required fields for lollipop chart.")

        # Sort so highest values are at the top (ascending order on y-axis renders bottom-to-top)
        df = df.sort_values(by=spec.x_field, ascending=True)

        numeric_vals = pd.to_numeric(df[spec.x_field], errors="coerce")
        has_negative = (numeric_vals < 0).any()

        if has_negative:
            max_gain = numeric_vals.max() if (numeric_vals > 0).any() else None
            min_loss = numeric_vals.min() if (numeric_vals < 0).any() else None
            colors = []
            for val in numeric_vals:
                if pd.notnull(val) and val > 0:
                    colors.append(GAINER_DARK_COLOR if val == max_gain else GAINER_COLOR)
                elif pd.notnull(val) and val < 0:
                    colors.append(DECLINER_DARK_COLOR if val == min_loss else DECLINER_COLOR)
                else:
                    colors.append(NEUTRAL_COLOR)
            text_labels = [f"{v:+.1f}" if pd.notnull(v) else "" for v in numeric_vals]
        else:
            max_val = numeric_vals.max() if not numeric_vals.dropna().empty else None
            colors = [
                FOCUS_DARK_COLOR if pd.notnull(val) and val == max_val else PRIMARY_COLOR
                for val in numeric_vals
            ]
            text_labels = [f"{v:.1f}" if pd.notnull(v) else "" for v in numeric_vals]

        hover_text = self._build_hover_text(df, spec)
        y_display = [shorten_institution_name(n) for n in df[spec.y_field]] if spec.y_field == "institution" else df[spec.y_field]

        fig = go.Figure()

        # 1. Stem lines from 0 to value
        x_lines = []
        y_lines = []
        baseline = 0
        for val, y_name in zip(df[spec.x_field], y_display):
            if pd.notnull(val):
                x_lines.extend([baseline, val, None])
                y_lines.extend([y_name, y_name, None])

        fig.add_trace(go.Scatter(
            x=x_lines,
            y=y_lines,
            mode="lines",
            line=dict(color=MUTED_BORDER, width=2.5),
            hoverinfo="none",
            showlegend=False,
        ))

        # 2. Lollipop circle markers at the data points
        fig.add_trace(go.Scatter(
            x=df[spec.x_field],
            y=y_display,
            mode="markers+text" if len(df) <= 30 else "markers",
            marker=dict(
                size=12,
                color=colors,
                line=dict(width=1.5, color="#FFFFFF"),
            ),
            hoverinfo="text",
            hovertext=hover_text,
            text=text_labels if len(df) <= 30 else None,
            textposition="middle right",
            textfont=dict(size=10, color=TEXT_MAIN),
            showlegend=False,
        ))

        if has_negative:
            fig.add_vline(x=0, line_width=1.2, line_dash="dash", line_color=MUTED_BORDER)
        else:
            if not numeric_vals.dropna().empty:
                max_x = float(numeric_vals.max())
                fig.update_xaxes(range=[0, max_x * 1.15])

        # Dynamic height for comfortable spacing
        cal_height = max(500, len(df) * 22)
        fig.update_layout(height=cal_height)

        return fig

    # -------------------------------------------------------------------------
    # 4. Grouped Bar Chart (e.g. Multidimensional Parameters)
    # -------------------------------------------------------------------------
    def _render_grouped_bar(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError(f"Missing required fields for grouped bar chart.")

        group_col = spec.color_field or "parameter"
        if group_col not in df.columns:
            group_col = spec.x_field

        fig = go.Figure()
        unique_groups = df[group_col].unique()

        for g in unique_groups:
            gdf = df[df[group_col] == g]
            hover_text = self._build_hover_text(gdf, spec)
            x_display = [shorten_institution_name(n) for n in gdf[spec.x_field]] if spec.x_field == "institution" else gdf[spec.x_field]
            fig.add_trace(go.Bar(
                x=x_display,
                y=gdf[spec.y_field],
                name=str(g),
                hoverinfo="text",
                hovertext=hover_text,
            ))

        fig.update_layout(barmode="group")
        return fig

    # -------------------------------------------------------------------------
    # 5. Scatter Plot (e.g. Parameter Relationships & Correlation)
    # -------------------------------------------------------------------------
    def _render_scatter(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError(f"Missing required fields for scatter plot.")

        fig = go.Figure()

        color_col = spec.color_field if spec.color_field and spec.color_field in df.columns else None
        groups = df.groupby(color_col) if color_col else [("Points", df)]

        for g_name, gdf in groups:
            hover_text = self._build_hover_text(gdf, spec)
            fig.add_trace(go.Scatter(
                x=gdf[spec.x_field],
                y=gdf[spec.y_field],
                mode="markers",
                name=str(g_name).replace("_", " ").capitalize(),
                marker=dict(size=9, opacity=0.85),
                hoverinfo="text",
                hovertext=hover_text,
            ))

        # Overlay regression trendline if provided in metadata
        trend_pts = spec.metadata.get("trendline")
        if spec.include_trendline and trend_pts and len(trend_pts) == 2:
            tx = [p["x"] for p in trend_pts]
            ty = [p["y"] for p in trend_pts]
            r2 = spec.metadata.get("regression", {}).get("r_squared")
            r2_label = f"Linear Trend (R² = {r2:.2f})" if r2 is not None else "Linear Trend"
            fig.add_trace(go.Scatter(
                x=tx,
                y=ty,
                mode="lines",
                name=r2_label,
                line=dict(color="#333333", width=2, dash="dash"),
                hoverinfo="skip",
            ))

        # Add median quadrant lines if available
        medians = spec.metadata.get("medians") or {}
        if "x_median" in medians and "y_median" in medians:
            fig.add_vline(x=medians["x_median"], line_width=1, line_dash="dot", line_color="#888888")
            fig.add_hline(y=medians["y_median"], line_width=1, line_dash="dot", line_color="#888888")

        return fig

    # -------------------------------------------------------------------------
    # 6. Heatmap (e.g. Correlation Matrix & Transition Matrix)
    # -------------------------------------------------------------------------
    def _render_heatmap(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty or spec.x_field not in df.columns or spec.y_field not in df.columns:
            raise RenderingError(f"Missing required fields for heatmap.")

        val_col = spec.color_field or "correlation"
        if val_col not in df.columns:
            val_col = df.columns[-1]

        pivot = df.pivot(index=spec.y_field, columns=spec.x_field, values=val_col)

        # Build clean formatted text annotations
        z_vals = pivot.values
        x_labels = list(pivot.columns)
        y_labels = list(pivot.index)

        text_annotations = []
        for r in range(len(y_labels)):
            row_ann = []
            for c in range(len(x_labels)):
                v = z_vals[r][c]
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    row_ann.append("N/A")
                elif isinstance(v, float):
                    row_ann.append(f"{v:.2f}")
                else:
                    row_ann.append(str(v))
            text_annotations.append(row_ann)

        is_corr = "correlation" in spec.title.lower()
        colorscale = "RdBu_r" if is_corr else "Blues"
        zmin = -1.0 if is_corr else 0
        zmax = 1.0 if is_corr else None

        fig = go.Figure(go.Heatmap(
            z=z_vals,
            x=x_labels,
            y=y_labels,
            text=text_annotations,
            texttemplate="%{text}",
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            colorbar=dict(title="Value"),
            hoverongaps=False,
        ))

        return fig

    # -------------------------------------------------------------------------
    # 7. Histogram (Score Frequency Distribution)
    # -------------------------------------------------------------------------
    def _render_histogram(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty:
            raise RenderingError(f"Empty data for histogram.")

        # If data is pre-binned
        if "bin_label" in df.columns and "count" in df.columns:
            hover_text = self._build_hover_text(df, spec)
            max_cnt = df["count"].max() if not df.empty else 10
            fig = go.Figure(go.Bar(
                x=df["bin_label"],
                y=df["count"],
                marker=dict(color=PRIMARY_COLOR, line=dict(width=1.5, color="#FFFFFF")),
                text=df["count"],
                textposition="outside",
                textfont=dict(size=11, color=TEXT_MAIN),
                hoverinfo="text",
                hovertext=hover_text,
            ))
            fig.update_layout(
                bargap=0.04,  # Minimal gap so it reads as a true continuous histogram
            )
            fig.update_yaxes(range=[0, max_cnt * 1.18])
            return fig

        # Otherwise raw distribution
        if spec.x_field in df.columns:
            fig = px.histogram(
                df,
                x=spec.x_field,
                template=THEME_TEMPLATE,
                labels=spec.axis_labels,
                color_discrete_sequence=[PRIMARY_COLOR],
            )
            fig.update_traces(
                marker=dict(line=dict(width=1, color="#FFFFFF")),
            )
            fig.update_layout(bargap=0.04)
            return fig

        raise RenderingError("Histogram data lacks 'bin_label' or target x_field.")

    # -------------------------------------------------------------------------
    # 8. Box Plot (Quartile Distributions)
    # -------------------------------------------------------------------------
    def _render_box_plot(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        if df.empty:
            raise RenderingError(f"Empty data for box plot.")

        stats = spec.metadata.get("statistics") or {}
        y_field = spec.y_field or spec.x_field or "score"

        fig = go.Figure()

        if y_field in df.columns:
            # Full raw distribution box plot with jittered points and outlier detection
            hover_txt = [
                f"<b>{shorten_institution_name(row.get('institution', ''))}</b><br>Score: {row.get(y_field):.2f}"
                if 'institution' in row and pd.notnull(row.get('institution')) else f"Score: {row.get(y_field):.2f}"
                for _, row in df.iterrows()
            ]
            fig.add_trace(go.Box(
                y=df[y_field],
                name=spec.metadata.get("category", "Cohort"),
                boxpoints="all",
                jitter=0.35,
                pointpos=-1.8,
                marker=dict(color=PRIMARY_COLOR, size=5, line=dict(width=1, color=TEXT_MAIN)),
                line=dict(color=FOCUS_DARK_COLOR, width=2),
                fillcolor="#BCE0D7",
                hovertext=hover_txt,
                hoverinfo="text",
            ))
        elif "q1_25th_percentile" in stats and "median" in stats:
            # Precomputed quartiles
            fig.add_trace(go.Box(
                q1=[stats["q1_25th_percentile"]],
                median=[stats["median"]],
                q3=[stats["q3_75th_percentile"]],
                lowerfence=[stats["min"]],
                upperfence=[stats["max"]],
                mean=[stats["mean"]],
                name=spec.metadata.get("category", "Cohort"),
                marker_color=PRIMARY_COLOR,
                line=dict(color=FOCUS_DARK_COLOR, width=2),
                fillcolor="#BCE0D7",
            ))
        else:
            raise RenderingError("Box plot requires raw 'score' points or precomputed quartile statistics.")

        fig.update_layout(
            yaxis_title=spec.axis_labels.get("y", "Score"),
            showlegend=False,
        )
        return fig

    # -------------------------------------------------------------------------
    # 9. Geographic Map (India Institution / State Scattergeo)
    # -------------------------------------------------------------------------
    def _render_map(self, spec: ChartSpecification) -> go.Figure:
        df = pd.DataFrame(spec.data)
        lat_col = spec.lat_field or "latitude"
        lon_col = spec.lon_field or "longitude"

        if df.empty or lat_col not in df.columns or lon_col not in df.columns:
            raise RenderingError(f"Map requires '{lat_col}' and '{lon_col}' coordinates.")

        fig = go.Figure()
        hover_text = self._build_hover_text(df, spec)

        # Perceptual scaling: circle size proportional to score or institution count
        marker_sizes = []
        if "score" in df.columns:
            scores = pd.to_numeric(df["score"], errors="coerce").fillna(50)
            s_min, s_max = scores.min(), scores.max()
            if s_max > s_min:
                marker_sizes = [11 + 13 * (float(s) - s_min) / (s_max - s_min) for s in scores]
            else:
                marker_sizes = [15] * len(df)
        elif "distinct_institutions" in df.columns:
            counts = pd.to_numeric(df["distinct_institutions"], errors="coerce").fillna(1)
            c_min, c_max = counts.min(), counts.max()
            if c_max > c_min:
                marker_sizes = [11 + 15 * (float(c) - c_min) / (c_max - c_min) for c in counts]
            else:
                marker_sizes = [15] * len(df)
        else:
            marker_sizes = [14] * len(df)

        # Monochromatic map palette with dark focal point for top performer / focus entity
        metric_col = "score" if "score" in df.columns else ("distinct_institutions" if "distinct_institutions" in df.columns else None)
        focus_idx = None
        if metric_col:
            num_vals = pd.to_numeric(df[metric_col], errors="coerce")
            if num_vals.notnull().any():
                focus_idx = num_vals.idxmax()

        focus_inst = spec.metadata.get("institution") or spec.metadata.get("focus_institution")

        marker_colors = []
        for idx, row in df.iterrows():
            is_focus = False
            if focus_inst and str(row.get("institution", "")).lower() == str(focus_inst).lower():
                is_focus = True
            elif not focus_inst and idx == focus_idx:
                is_focus = True
            marker_colors.append(FOCUS_DARK_COLOR if is_focus else PRIMARY_COLOR)

        # Map Graph: Dot only (mode="markers") with full institution details displayed on hover
        fig.add_trace(go.Scattergeo(
            lon=df[lon_col],
            lat=df[lat_col],
            mode="markers",
            hoverinfo="text",
            hovertext=hover_text,
            marker=dict(
                size=marker_sizes,
                color=marker_colors,
                opacity=0.92,
                line=dict(width=2, color="#FFFFFF"),
            ),
            showlegend=False,
        ))

        fig.update_geos(
            visible=False,
            resolution=50,
            showcountries=True,
            countrycolor="#6E9C91",
            countrywidth=1.2,
            showsubunits=True,
            subunitcolor="#D3E4DF",
            subunitwidth=0.8,
            showland=True,
            landcolor="#F4F8F6",
            showocean=True,
            oceancolor="#E2EDE9",
            center=dict(lat=22.0, lon=82.0),
            projection_scale=4.3,
        )
        return fig

    # -------------------------------------------------------------------------
    # Helper Layout and Tooltip Builders
    # -------------------------------------------------------------------------
    def _build_hover_text(self, df: pd.DataFrame, spec: ChartSpecification) -> List[str]:
        hover_text = []
        for _, row in df.iterrows():
            parts = []
            for hf in spec.hover_fields:
                if hf in row and row[hf] is not None:
                    label = hf.replace("_", " ").capitalize()
                    val = row[hf]
                    if isinstance(val, float):
                        val_str = f"{val:.2f}"
                    else:
                        val_str = str(val)
                    parts.append(f"<b>{label}:</b> {val_str}")
            hover_text.append("<br>".join(parts) if parts else str(row.to_dict()))
        return hover_text

    def _apply_common_layout(self, fig: go.Figure, spec: ChartSpecification) -> None:
        """Applies consistent typography, responsive dimensions, and subtitle context."""
        subtitle_text = ""
        meta = spec.metadata
        if "category" in meta or "year" in meta or "start_year" in meta:
            cat = meta.get("category", "")
            yr = meta.get("year") or f"{meta.get('start_year')}–{meta.get('end_year')}"
            stats = meta.get("statistics") or {}
            n = meta.get("sample_size") or meta.get("valid_observations") or stats.get("sample_size") or meta.get("states_count") or meta.get("count") or len(spec.data)
            subtitle_text = f"Category: {cat} | Period: {yr} | Observations: {n}"

        full_title = f"<b>{spec.title}</b>"
        if subtitle_text:
            full_title += f"<br><span style='font-size: 11px; color: {TEXT_MUTED}; font-weight: normal;'>{subtitle_text}</span>"

        is_geo = spec.chart_type == "map"

        fig.update_layout(
            template=THEME_TEMPLATE,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            colorway=[
                "#3D7A6D",  # Botanical Sage Teal
                "#D98871",  # Warm Terracotta Coral
                "#5A9E8F",  # Soft Mint
                "#C29B7F",  # Warm Sand
                "#2D6357",  # Deep Pine Green
                "#8EA89D",  # Muted Sage
                "#E6A08D",  # Peach Coral
                "#466960",  # Dark Olive Slate
            ],
            font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", color=TEXT_MAIN),
            title=dict(text=full_title, font=dict(size=15, color=TEXT_MAIN)),
            xaxis_title=spec.axis_labels.get("x", spec.x_field) if not is_geo else None,
            yaxis_title=spec.axis_labels.get("y", spec.y_field) if not is_geo else None,
            showlegend=spec.show_legend and (len(fig.data) > 1),  # Tufte: eliminate single redundant legend
            legend=dict(
                font=dict(color=TEXT_MAIN, size=11),
                title_font=dict(color=TEXT_MAIN, size=12),
                bgcolor="rgba(255, 255, 255, 0.95)",
                bordercolor=MUTED_BORDER,
                borderwidth=1,
            ),
            margin=dict(l=55, r=35, t=70, b=55),
            hoverlabel=dict(bgcolor="white", font_size=12, font_family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"),
        )

        if not is_geo:
            # Tufte: No vertical gridlines on categorical/bar charts; subtle horizontal gridlines only
            show_x_grid = spec.chart_type in ["scatter", "line", "histogram"]
            fig.update_xaxes(
                showgrid=show_x_grid,
                gridcolor=MUTED_GRID,
                linecolor=MUTED_BORDER,
                tickfont=dict(size=11, color=TEXT_MUTED),
                title_font=dict(size=12, color=TEXT_MAIN),
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor=MUTED_GRID,
                linecolor=MUTED_BORDER,
                tickfont=dict(size=11, color=TEXT_MUTED),
                title_font=dict(size=12, color=TEXT_MAIN),
            )

        # Include comparability warning as an annotation badge if present
        if spec.warnings:
            first_warn = spec.warnings[0]
            if len(first_warn) > 85:
                first_warn = first_warn[:82] + "..."
            fig.add_annotation(
                text=f"⚠️ {first_warn}",
                xref="paper", yref="paper",
                x=0.0, y=-0.22,
                showarrow=False,
                font=dict(size=10, color="#b35900"),
                align="left",
            )


def get_plotly_renderer() -> PlotlyRenderer:
    """Returns singleton instance of PlotlyRenderer."""
    return PlotlyRenderer()
