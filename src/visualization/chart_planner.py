"""
Chart Planner Module for NIRF Analytics (Phase 7).
Determines the most appropriate, mathematically sound, and informative visualization
for analytical execution results, supporting automatic selection, explicit user requests,
misleading-visualization guards, and graceful table fallbacks.
"""

from typing import Dict, Any, List, Optional, Tuple
import re

from src.execution.result_schema import OperationResult
from src.visualization.chart_schema import ChartSpecification, ChartType


# Explicit keywords to detect user chart requests
CHART_KEYWORD_MAP = {
    "map": ["map", "map graph", "geo", "geographic", "geographic map", "locations", "spatial", "choropleth"],
    "lollipop": [
        "lollipop", "lollipop graph", "lollipop chart", "stem", "stem and leaf",
        "dot plot", "cleveland dot", "cleveland", "dot graph", "lollipop plot"
    ],
    "horizontal_bar": [
        "horizontal bar", "horizontal graph", "horizontal chart", "horizontal",
        "horizontally", "rank change bar", "gainer bar", "sideways"
    ],
    "histogram": [
        "histogram", "frequency", "bins", "score distribution",
        "distribution", "spread", "density", "bell curve"
    ],
    "box_plot": ["box plot", "boxplot", "box and whisker", "quartiles"],
    "line": ["line", "trend", "trajectory", "over time", "progress"],
    "grouped_bar": ["grouped bar", "multi bar", "parameter comparison"],
    "bar": ["bar", "column", "compare", "ranking bar"],
    "scatter": ["scatter", "relationship", "xy", "correlation plot", "dots"],
    "heatmap": ["heatmap", "heat map", "matrix", "correlation matrix"],
    "table": ["table", "tabular", "rows", "list", "grid"],
}


class ChartPlanner:
    """
    Plans declarative ChartSpecifications from Phase 4 OperationResults.
    Strictly forbids data fabrication, preserves missing values, enforces reversed rank axes,
    and falls back to structured tables for small lookups or insufficient data.
    """

    def plan_chart(
        self,
        operation_result: OperationResult,
        user_query: Optional[str] = None,
        explicit_chart_type: Optional[str] = None,
    ) -> ChartSpecification:
        """
        Coordinates chart planning for a single OperationResult.

        Args:
            operation_result: Validated OperationResult from Phase 4 execution.
            user_query: Optional user prompt text to detect explicit chart preferences.
            explicit_chart_type: Programmatic chart preference if provided.

        Returns:
            Validated ChartSpecification.
        """
        fn_name = operation_result.function_name
        data = operation_result.data or {}
        meta = operation_result.metadata or {}
        warnings = list(operation_result.warnings or [])

        # Check for empty or failed execution data
        if not data or not data.get("success", True):
            return self._plan_empty_or_failed(operation_result, "Analytical operation yielded no successful data.")

        # Determine user requested chart preference if any
        requested_type = self._detect_chart_preference(user_query, explicit_chart_type)

        # Dispatch to specialized operation planners
        planner_method = getattr(self, f"_plan_{fn_name}", None)
        if planner_method is None:
            return self._plan_generic_fallback(operation_result, requested_type)

        # Pass user_query if planner method supports it
        import inspect
        sig = inspect.signature(planner_method)
        if "user_query" in sig.parameters:
            spec = planner_method(data, meta, warnings, requested_type, user_query=user_query)
        else:
            spec = planner_method(data, meta, warnings, requested_type)
        return spec

    def _detect_chart_preference(
        self, user_query: Optional[str], explicit_chart_type: Optional[str]
    ) -> Optional[ChartType]:
        """Detects if an explicit chart type was requested."""
        if explicit_chart_type:
            cleaned = explicit_chart_type.lower().strip().replace("-", "_").replace(" ", "_")
            if cleaned == "table":
                # Only honor table if the user explicitly typed table/tabular/grid/csv
                q_text = (user_query or "").lower()
                if any(w in q_text for w in ["table", "tabular", "rows", "spreadsheet", "csv", "grid"]):
                    return "table"
            elif cleaned in [
                "line", "bar", "grouped_bar", "horizontal_bar", "lollipop",
                "scatter", "heatmap", "histogram", "box_plot", "map"
            ]:
                return cleaned  # type: ignore

        if not user_query:
            return None

        q_lower = user_query.lower()
        for ctype, keywords in CHART_KEYWORD_MAP.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                    return ctype  # type: ignore
        return None

    # -------------------------------------------------------------------------
    # 1. get_institution_trend
    # -------------------------------------------------------------------------
    def _plan_get_institution_trend(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        inst_name = data.get("institute_name_std", "Institution")
        category = data.get("category", "")
        traj = data.get("chronological_trajectory", [])

        # Filter observed points while maintaining chronological sequence
        valid_points = [p for p in traj if p.get("is_observed") and p.get("rank") is not None]

        # Table fallback for single-year lookup or insufficient observations
        if len(valid_points) <= 1 or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Trend Data: {inst_name} ({category})",
                data=traj,
                warnings=warnings,
                metadata={"category": category, "institution": inst_name, "sample_size": len(traj)},
            )

        # Flatten records for line chart
        plot_records = []
        for p in traj:
            year = p.get("year")
            is_obs = p.get("is_observed", False)
            rank_val = p.get("rank") if is_obs else None
            score_val = p.get("score") if is_obs else None
            rec = {
                "year": year,
                "institution": inst_name,
                "rank": rank_val,
                "rank_label": p.get("rank_label", "Unranked"),
                "score": score_val,
                "status": p.get("status", "Observed"),
            }
            # Add parameters if available
            params = p.get("parameters") or {}
            for pk, pv in params.items():
                rec[pk] = pv
            plot_records.append(rec)

        # Decide Y axis: rank (default) or score if requested
        use_score = requested in ["bar"] or "score" in meta.get("parameters", [])
        y_field = "score" if use_score else "rank"
        y_label = f"Overall Score (0–100)" if use_score else "NIRF Rank (Lower is Better)"
        reverse_y = not use_score

        title = f"{inst_name} — Longitudinal {y_field.capitalize()} Trend ({category})"
        return ChartSpecification(
            chart_type="line",
            title=title,
            x_field="year",
            y_field=y_field,
            color_field="institution",
            hover_fields=["year", "rank_label", "score", "status"],
            axis_labels={"x": "Year", "y": y_label},
            reverse_y_axis=reverse_y,
            sort_order="chronological",
            data=plot_records,
            warnings=warnings,
            metadata={"institution": inst_name, "category": category, "valid_observations": len(valid_points)},
        )

    # -------------------------------------------------------------------------
    # 2. get_rank_movement
    # -------------------------------------------------------------------------
    def _plan_get_rank_movement(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        start_year = data.get("start_year")
        end_year = data.get("end_year")
        gainers = data.get("gainers", [])
        decliners = data.get("decliners", [])

        all_items = []
        for g in gainers:
            item = dict(g)
            item["movement_category"] = "Gainer"
            all_items.append(item)
        for d in decliners:
            item = dict(d)
            item["movement_category"] = "Decliner"
            all_items.append(item)

        if not all_items or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Rank Movement Summary: {category} ({start_year}–{end_year})",
                data=all_items or [{"message": "No paired institutions found"}],
                warnings=warnings,
                metadata={"category": category, "start_year": start_year, "end_year": end_year},
            )

        # Format records for horizontal bar chart
        plot_records = []
        for it in all_items:
            inst = it.get("institute_name_std", "Unknown")
            imp = it.get("rank_improvement", 0)
            plot_records.append({
                "institution": inst,
                "rank_improvement": imp,
                "start_rank": it.get("start_rank"),
                "end_rank": it.get("end_rank"),
                "movement_category": it.get("movement_category"),
                "state": it.get("state_std"),
            })

        chart_type = "lollipop" if requested == "lollipop" else ("horizontal_bar" if requested in ["horizontal_bar", None] else "bar")
        title = f"Rank Changes in {category} ({start_year} to {end_year})"
        return ChartSpecification(
            chart_type=chart_type,
            title=title,
            x_field="rank_improvement" if chart_type in ["horizontal_bar", "lollipop"] else "institution",
            y_field="institution" if chart_type in ["horizontal_bar", "lollipop"] else "rank_improvement",
            color_field="movement_category",
            hover_fields=["institution", "rank_improvement", "start_rank", "end_rank", "state"],
            axis_labels={
                "x": "Rank Improvement (Ranks Gained / Lost)" if chart_type in ["horizontal_bar", "lollipop"] else "Institution",
                "y": "Institution" if chart_type in ["horizontal_bar", "lollipop"] else "Rank Improvement",
            },
            sort_order="ascending" if chart_type in ["horizontal_bar", "lollipop"] else "descending",
            data=plot_records,
            warnings=warnings,
            metadata={"category": category, "start_year": start_year, "end_year": end_year, "count": len(plot_records)},
        )

    # -------------------------------------------------------------------------
    # 3. get_category_performance
    # -------------------------------------------------------------------------
    def _plan_get_category_performance(
        self,
        data: Dict[str, Any],
        meta: Dict[str, Any],
        warnings: List[str],
        requested: Optional[ChartType],
        user_query: Optional[str] = None,
    ) -> ChartSpecification:
        category = data.get("category", "")
        year = data.get("year")
        institutions = data.get("institutions", [])

        if len(institutions) <= 1 or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Category Performance: {category} ({year})",
                data=institutions,
                warnings=warnings,
                metadata={"category": category, "year": year, "total": len(institutions)},
            )

        # Check if histogram/distribution requested
        if requested in ["histogram", "box_plot"]:
            plot_data = [{"institution": inst.get("institute_name_std"), "score": inst.get("score")} for inst in institutions if inst.get("score") is not None]
            return ChartSpecification(
                chart_type=requested,
                title=f"Score Distribution: {category} ({year})",
                x_field="score",
                axis_labels={"x": "Score", "y": "Frequency" if requested == "histogram" else "Score"},
                data=plot_data,
                warnings=warnings,
                metadata={"category": category, "year": year},
            )

        # Check if geographic map requested
        if requested == "map":
            from src.visualization.geo_data import get_coordinates
            map_records = []
            for inst in institutions:
                city = inst.get("city_std")
                state = inst.get("state_std")
                lat, lon = get_coordinates(city=city, state=state)
                rec = {
                    "institution": inst.get("institute_name_std", "Unknown"),
                    "rank": inst.get("rank"),
                    "score": inst.get("score"),
                    "city": city or "Unknown",
                    "state": state or "Unknown",
                    "latitude": lat,
                    "longitude": lon,
                }
                params = inst.get("parameters") or {}
                for pk, pv in params.items():
                    rec[pk] = pv
                map_records.append(rec)
            title = f"Geographic Map: Top Institutions in {category} ({year})"
            return ChartSpecification(
                chart_type="map",
                title=title,
                lat_field="latitude",
                lon_field="longitude",
                color_field=None,
                hover_fields=["institution", "rank", "score", "city", "state"],
                data=map_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "count": len(map_records)},
            )

        # Institution comparison charts (Lollipop, Horizontal Bar, Vertical Bar)
        cohort_size = len(institutions)
        query_text = (user_query or meta.get("user_query") or "").lower()

        # Check if user explicitly asked for a limited number (e.g. "top 10", "top 5")
        explicit_top_match = re.search(r"\btop\s*(\d+)\b", query_text)
        explicit_top = int(explicit_top_match.group(1)) if explicit_top_match else None

        # Check if user asked for all institutions
        wants_all = any(w in query_text for w in ["all", "entire", "every", "complete", "full", "whole", "100", "50", "200"])

        is_lollipop = requested == "lollipop"
        is_horizontal = requested == "horizontal_bar"

        if explicit_top:
            display_institutions = institutions[:explicit_top]
        elif wants_all or is_lollipop or is_horizontal:
            # Display all institutions without arbitrary capping
            display_institutions = institutions
        elif cohort_size > 25 and (requested == "bar" or requested is None):
            # Only cap vertical bar charts if the cohort is huge and user did not request all
            display_institutions = institutions[:15]
        else:
            display_institutions = institutions

        plot_records = []
        for inst in display_institutions:
            rec = {
                "institution": inst.get("institute_name_std", "Unknown"),
                "rank": inst.get("rank"),
                "score": inst.get("score"),
                "state": inst.get("state_std"),
            }
            params = inst.get("parameters") or {}
            for pk, pv in params.items():
                rec[pk] = pv
            plot_records.append(rec)

        if is_lollipop:
            title = f"Institution Performance (Lollipop Chart): {category} ({year})" if len(plot_records) == cohort_size else f"Top {len(plot_records)} Institutions (Lollipop Chart): {category} ({year})"
            return ChartSpecification(
                chart_type="lollipop",
                title=title,
                x_field="score",
                y_field="institution",
                color_field=None,
                hover_fields=["institution", "rank", "score", "state"],
                axis_labels={"x": "Overall Score", "y": "Institution"},
                sort_order="ascending",  # so #1 is at top
                data=plot_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "sample_size": len(plot_records), "cohort_size": cohort_size},
            )
        elif is_horizontal:
            title = f"Institution Performance: {category} ({year})" if len(plot_records) == cohort_size else f"Top {len(plot_records)} Institution Performance in {category} ({year})"
            return ChartSpecification(
                chart_type="horizontal_bar",
                title=title,
                x_field="score",
                y_field="institution",
                color_field=None,
                hover_fields=["institution", "rank", "score", "state"],
                axis_labels={"x": "Overall Score", "y": "Institution"},
                sort_order="ascending",  # so #1 is at top
                data=plot_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "sample_size": len(plot_records), "cohort_size": cohort_size},
            )
        else:
            title = f"Top {len(plot_records)} Institution Performance in {category} ({year})" if len(plot_records) < cohort_size else f"Institution Performance in {category} ({year})"
            return ChartSpecification(
                chart_type="bar",
                title=title,
                x_field="institution",
                y_field="score",
                color_field=None,
                hover_fields=["institution", "rank", "score", "state"],
                axis_labels={"x": "Institution", "y": "Overall Score"},
                sort_order="descending",
                data=plot_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "sample_size": len(plot_records), "cohort_size": cohort_size},
            )

    # -------------------------------------------------------------------------
    # 4. get_geographic_analysis
    # -------------------------------------------------------------------------
    def _plan_get_geographic_analysis(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "NIRF")
        year = data.get("year", 2025)
        states = data.get("states_analysis", [])

        if len(states) <= 1 or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Geographic Distribution: {category} ({year})",
                data=states,
                warnings=warnings,
                metadata={"category": category, "year": year, "states_count": len(states)},
            )

        # Check if map requested
        if requested == "map":
            from src.visualization.geo_data import get_coordinates
            map_records = []
            for s in states:
                st_name = s.get("state", "Unknown")
                lat, lon = get_coordinates(state=st_name)
                map_records.append({
                    "state": st_name,
                    "zone": s.get("zone", "Other"),
                    "distinct_institutions": s.get("distinct_institutions", 0),
                    "top_10_institutions": s.get("top_10_institutions", 0),
                    "top_50_institutions": s.get("top_50_institutions", 0),
                    "average_score": s.get("average_score"),
                    "latitude": lat,
                    "longitude": lon,
                })
            title = f"Geographic Map: Institutional Representation by State ({category} {year})"
            return ChartSpecification(
                chart_type="map",
                title=title,
                lat_field="latitude",
                lon_field="longitude",
                color_field=None,
                hover_fields=["state", "distinct_institutions", "top_10_institutions", "top_50_institutions", "average_score"],
                data=map_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "states_count": len(map_records)},
            )

        # Format records for ranked state bar chart
        plot_records = []
        for s in states:
            plot_records.append({
                "state": s.get("state", "Unknown"),
                "zone": s.get("zone", "Other"),
                "distinct_institutions": s.get("distinct_institutions", 0),
                "top_10_institutions": s.get("top_10_institutions", 0),
                "top_50_institutions": s.get("top_50_institutions", 0),
                "average_score": s.get("average_score"),
                "average_rpc": s.get("average_rpc"),
                "average_tlr": s.get("average_tlr"),
            })

        title = f"State-wise Institutional Representation: {category} ({year})"
        if requested in ["horizontal_bar", "lollipop"]:
            return ChartSpecification(
                chart_type=requested,
                title=title,
                x_field="distinct_institutions",
                y_field="state",
                color_field=None,
                hover_fields=["state", "distinct_institutions", "top_10_institutions", "top_50_institutions", "average_score"],
                axis_labels={"x": "Number of Ranked Institutions", "y": "State"},
                sort_order="ascending",
                data=plot_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "states_count": len(plot_records)},
            )

        return ChartSpecification(
            chart_type="bar",
            title=title,
            x_field="state",
            y_field="distinct_institutions",
            color_field="zone",
            hover_fields=["state", "distinct_institutions", "top_10_institutions", "top_50_institutions", "average_score"],
            axis_labels={"x": "State", "y": "Number of Ranked Institutions"},
            sort_order="descending",
            data=plot_records,
            warnings=warnings,
            metadata={"category": category, "year": year, "states_count": len(plot_records)},
        )

    # -------------------------------------------------------------------------
    # 5. get_parameter_correlation
    # -------------------------------------------------------------------------
    def _plan_get_parameter_correlation(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        year = data.get("year")
        params = data.get("parameters", [])
        matrix = data.get("pearson_matrix") or data.get("spearman_matrix") or {}

        if not matrix or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Parameter Correlation Matrix: {category} ({year})",
                data=[{"parameter": p, **matrix.get(p, {})} for p in params],
                warnings=warnings,
                metadata={"category": category, "year": year},
            )

        # Flatten correlation matrix for heatmap rendering
        heatmap_data = []
        for p1 in params:
            for p2 in params:
                val = matrix.get(p1, {}).get(p2)
                heatmap_data.append({
                    "param_x": p1.upper(),
                    "param_y": p2.upper(),
                    "correlation": val,
                })

        title = f"NIRF Parameter Correlation Heatmap — {category} ({year})"
        return ChartSpecification(
            chart_type="heatmap",
            title=title,
            x_field="param_x",
            y_field="param_y",
            color_field="correlation",
            hover_fields=["param_x", "param_y", "correlation"],
            axis_labels={"x": "Parameter", "y": "Parameter"},
            data=heatmap_data,
            warnings=warnings,
            metadata={"category": category, "year": year, "parameters": params},
        )

    # -------------------------------------------------------------------------
    # 6. get_parameter_relationship
    # -------------------------------------------------------------------------
    def _plan_get_parameter_relationship(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        year = data.get("year")
        px = data.get("param_x", "x").upper()
        py = data.get("param_y", "y").upper()
        points = data.get("points", [])
        regression = data.get("regression") or {}

        if len(points) <= 1 or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Relationship: {px} vs {py} ({category} {year})",
                data=points,
                warnings=warnings,
                metadata={"category": category, "year": year},
            )

        # Format points for scatter plot
        plot_records = []
        for p in points:
            plot_records.append({
                "institution": p.get("institute_name_std", "Unknown"),
                "rank": p.get("rank"),
                "score": p.get("score"),
                "x_val": p.get("x"),
                "y_val": p.get("y"),
                "quadrant": p.get("quadrant", "Unclassified"),
            })

        has_trendline = regression.get("slope") is not None and len(points) >= 3
        r2_str = f" (R² = {regression.get('r_squared'):.2f})" if regression.get("r_squared") is not None else ""
        title = f"{px} vs. {py} Relationship — {category} {year}{r2_str}"

        return ChartSpecification(
            chart_type="scatter",
            title=title,
            x_field="x_val",
            y_field="y_val",
            color_field="quadrant",
            hover_fields=["institution", "rank", "score", "x_val", "y_val", "quadrant"],
            axis_labels={"x": f"{px} Score", "y": f"{py} Score"},
            include_trendline=has_trendline,
            data=plot_records,
            warnings=warnings,
            metadata={
                "category": category,
                "year": year,
                "param_x": px,
                "param_y": py,
                "sample_size": len(points),
                "regression": regression,
                "trendline": data.get("trendline"),
                "medians": data.get("medians"),
            },
        )

    # -------------------------------------------------------------------------
    # 7. get_multidimensional_performance
    # -------------------------------------------------------------------------
    def _plan_get_multidimensional_performance(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        year = data.get("year")
        profiles = data.get("profiles") or data.get("institutions") or []

        if not profiles or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Multidimensional Performance: {category} ({year})",
                data=profiles,
                warnings=warnings,
                metadata={"category": category, "year": year},
            )

        # Check if map requested
        if requested == "map":
            from src.visualization.geo_data import get_coordinates
            map_records = []
            for inst in profiles:
                city = inst.get("city_std")
                state = inst.get("state_std")
                lat, lon = get_coordinates(city=city, state=state)
                map_records.append({
                    "institution": inst.get("institute_name_std", "Unknown"),
                    "rank": inst.get("rank"),
                    "score": inst.get("score"),
                    "city": city or "Unknown",
                    "state": state or "Unknown",
                    "latitude": lat,
                    "longitude": lon,
                })
            title = f"Geographic Map: Institution Comparison in {category} ({year})"
            return ChartSpecification(
                chart_type="map",
                title=title,
                lat_field="latitude",
                lon_field="longitude",
                color_field=None,
                hover_fields=["institution", "rank", "score", "city", "state"],
                data=map_records,
                warnings=warnings,
                metadata={"category": category, "year": year, "institutions_count": len(profiles)},
            )

        # Flatten records for grouped bar chart (parameters per institution)
        plot_records = []
        for inst in profiles:
            inst_name = inst.get("institute_name_std", "Unknown")
            params = inst.get("parameters") or {}
            for param_name, param_val in params.items():
                if param_val is not None:
                    plot_records.append({
                        "institution": inst_name,
                        "parameter": param_name.upper(),
                        "score": param_val,
                    })

        title = f"Multidimensional Parameter Profiles — {category} ({year})"
        return ChartSpecification(
            chart_type="grouped_bar",
            title=title,
            x_field="institution",
            y_field="score",
            color_field="parameter",
            group_field="institution",
            hover_fields=["institution", "parameter", "score"],
            axis_labels={"x": "Institution", "y": "Parameter Score (0–100)"},
            sort_order="ascending",
            data=plot_records,
            warnings=warnings,
            metadata={"category": category, "year": year, "institutions_count": len(profiles)},
        )

    # -------------------------------------------------------------------------
    # 8. get_score_distribution
    # -------------------------------------------------------------------------
    def _plan_get_score_distribution(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        year = data.get("year")
        metric = data.get("metric", "score").upper()
        bins = data.get("histogram_bins", [])
        stats = data.get("statistics", {})

        if not bins or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"{metric} Distribution Summary: {category} ({year})",
                data=bins,
                warnings=warnings,
                metadata={"category": category, "year": year, "statistics": stats, "sample_size": stats.get("sample_size")},
            )

        if requested == "box_plot":
            scores = data.get("scores") or []
            title = f"Score Box Plot (Quartiles & Spread) — {metric} in {category} ({year})"
            return ChartSpecification(
                chart_type="box_plot",
                title=title,
                y_field="score",
                axis_labels={"y": f"{metric} Score"},
                data=scores,
                warnings=warnings,
                metadata={
                    "category": category,
                    "year": year,
                    "metric": metric,
                    "statistics": stats,
                    "sample_size": stats.get("sample_size", len(scores)),
                },
            )

        plot_records = []
        for b in bins:
            plot_records.append({
                "bin_label": b.get("bin_label", f"{b.get('bin_start')} - {b.get('bin_end')}"),
                "bin_start": b.get("bin_start"),
                "bin_end": b.get("bin_end"),
                "count": b.get("count", 0),
                "percentage": b.get("percentage", 0.0),
            })

        title = f"Score Frequency Distribution — {metric} in {category} ({year})"
        return ChartSpecification(
            chart_type="histogram",
            title=title,
            x_field="bin_label",
            y_field="count",
            hover_fields=["bin_label", "count", "percentage"],
            axis_labels={"x": f"{metric} Range", "y": "Frequency (Number of Institutions)"},
            sort_order="ascending",
            data=plot_records,
            warnings=warnings,
            metadata={
                "category": category,
                "year": year,
                "metric": metric,
                "statistics": stats,
                "sample_size": stats.get("sample_size"),
            },
        )

    # -------------------------------------------------------------------------
    # 9. get_rank_transitions
    # -------------------------------------------------------------------------
    def _plan_get_rank_transitions(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        start_year = data.get("start_year")
        end_year = data.get("end_year")
        matrix = data.get("transition_matrix", {})
        bands = data.get("bands", [])

        if not matrix or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Rank Transitions Matrix: {category} ({start_year}–{end_year})",
                data=[{"start_band": b1, **matrix.get(b1, {})} for b1 in matrix],
                warnings=warnings,
                metadata={"category": category, "start_year": start_year, "end_year": end_year},
            )

        # Flatten transition matrix for heatmap
        plot_records = []
        for b_start, targets in matrix.items():
            for b_end, count in targets.items():
                plot_records.append({
                    "start_band": b_start,
                    "end_band": b_end,
                    "transitions_count": count,
                })

        title = f"Tier Transition Matrix: {category} ({start_year} to {end_year})"
        return ChartSpecification(
            chart_type="heatmap",
            title=title,
            x_field="end_band",
            y_field="start_band",
            color_field="transitions_count",
            hover_fields=["start_band", "end_band", "transitions_count"],
            axis_labels={"x": f"Ending Band ({end_year})", "y": f"Starting Band ({start_year})"},
            data=plot_records,
            warnings=warnings,
            metadata={"category": category, "start_year": start_year, "end_year": end_year},
        )

    # -------------------------------------------------------------------------
    # 10. get_outlier_analysis
    # -------------------------------------------------------------------------
    def _plan_get_outlier_analysis(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        category = data.get("category", "")
        year = data.get("year")
        metric = data.get("metric", "score").upper()
        outliers = data.get("metric_outliers", [])

        if not outliers or requested == "table":
            return ChartSpecification(
                chart_type="table",
                title=f"Statistical Outliers: {metric} in {category} ({year})",
                data=outliers or [{"message": "No statistical outliers detected in this cohort."}],
                warnings=warnings,
                metadata={"category": category, "year": year, "metric": metric},
            )

        plot_records = []
        for o in outliers:
            plot_records.append({
                "institution": o.get("institute_name_std", "Unknown"),
                "observed_value": o.get("observed_value"),
                "direction": o.get("direction", "outlier").capitalize(),
                "rank": o.get("rank"),
                "detection_method": o.get("detection_method"),
            })

        title = f"Statistical Outliers ({metric}) — {category} ({year})"
        return ChartSpecification(
            chart_type="bar",
            title=title,
            x_field="institution",
            y_field="observed_value",
            color_field="direction",
            hover_fields=["institution", "observed_value", "direction", "rank", "detection_method"],
            axis_labels={"x": "Outlier Institution", "y": f"Observed {metric} Value"},
            sort_order="descending",
            data=plot_records,
            warnings=warnings,
            metadata={"category": category, "year": year, "metric": metric, "outliers_count": len(plot_records)},
        )

    def _plan_get_category_evolution(
        self, data: Dict[str, Any], meta: Dict[str, Any], warnings: List[str], requested: Optional[ChartType]
    ) -> ChartSpecification:
        start_year = data.get("start_year", 2017)
        end_year = data.get("end_year", 2025)
        yearly_metrics = data.get("yearly_metrics", [])

        if not yearly_metrics:
            return ChartSpecification(
                chart_type="table",
                title=f"NIRF Category Evolution ({start_year}–{end_year})",
                data=[],
                warnings=warnings + ["No yearly category metrics available."],
                metadata={"start_year": start_year, "end_year": end_year},
            )

        if requested == "table":
            table_records = []
            for ym in yearly_metrics:
                table_records.append({
                    "Year": ym.get("year"),
                    "Total Categories": ym.get("category_count"),
                    "New Categories": ", ".join(ym.get("new_categories", [])) if ym.get("new_categories") else "None",
                    "Discontinued Categories": ", ".join(ym.get("discontinued_categories", [])) if ym.get("discontinued_categories") else "None",
                    "Ranked Institutions": ym.get("institutions_ranked_count", 0),
                })
            return ChartSpecification(
                chart_type="table",
                title=f"NIRF Category Evolution Table ({start_year}–{end_year})",
                data=table_records,
                warnings=warnings,
                metadata={"start_year": start_year, "end_year": end_year, "total_records": len(table_records)},
            )

        plot_records = []
        for ym in yearly_metrics:
            new_cats_str = ", ".join(ym.get("new_categories", [])) if ym.get("new_categories") else "None"
            plot_records.append({
                "year": ym.get("year"),
                "category_count": ym.get("category_count"),
                "new_categories_count": ym.get("new_categories_count", 0),
                "new_categories": new_cats_str,
                "institutions_ranked_count": ym.get("institutions_ranked_count", 0),
            })

        chart_type: ChartType = "line" if requested == "line" else "bar"
        title = f"NIRF Institutional Category Expansion ({start_year}–{end_year})"

        return ChartSpecification(
            chart_type=chart_type,
            title=title,
            x_field="year",
            y_field="category_count",
            hover_fields=["year", "category_count", "new_categories", "institutions_ranked_count"],
            axis_labels={"x": "Assessment Edition (Year)", "y": "Number of NIRF Categories"},
            data=plot_records,
            warnings=warnings,
            metadata={
                "start_year": start_year,
                "end_year": end_year,
                "net_growth": data.get("evolution_summary", {}).get("net_category_growth", 0),
            },
        )

    # -------------------------------------------------------------------------
    # Generic / Fallback Planning
    # -------------------------------------------------------------------------
    def _plan_generic_fallback(
        self, operation_result: OperationResult, requested: Optional[ChartType]
    ) -> ChartSpecification:
        data = operation_result.data or {}
        return ChartSpecification(
            chart_type="table",
            title=f"Analytical Data: {operation_result.function_name}",
            data=[data] if isinstance(data, dict) else (data if isinstance(data, list) else []),
            warnings=list(operation_result.warnings or []),
            metadata={"function_name": operation_result.function_name},
        )

    def _plan_empty_or_failed(
        self, operation_result: OperationResult, reason: str
    ) -> ChartSpecification:
        return ChartSpecification(
            chart_type="none",
            title=f"Unavailable Data: {operation_result.function_name}",
            warnings=[reason] + list(operation_result.warnings or []),
            data=[],
            metadata={"status": "FAILED", "operation_id": operation_result.operation_id},
        )


def get_chart_planner() -> ChartPlanner:
    """Returns singleton instance of ChartPlanner."""
    return ChartPlanner()
