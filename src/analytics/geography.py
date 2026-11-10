"""
Geographic Analysis for NIRF Spatial and State-Level Performance (FUNCTION 4).
Analyzes state-wise institutional representation, top-tier institutional density,
and state-level score distributions across zones and editions.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, build_analysis_metadata


def get_geographic_analysis(
    category: Optional[str] = None,
    year: Optional[int] = 2025,
    states: Optional[List[str]] = None,
    multi_year_trend: bool = False,
) -> Dict[str, Any]:
    """
    Analyzes geographic distribution, state representation, and regional performance.

    Args:
        category: Optional category filter (e.g. 'Engineering'). If None, analyzes across all categories.
        year: Target assessment year (default 2025).
        states: Optional list of specific states to analyze / compare (e.g. ['Karnataka', 'Tamil Nadu']).
        multi_year_trend: If True, computes state representation trajectory across 2017–2025.

    Returns:
        Structured dictionary with state rankings, top-tier institution counts,
        average scores, state-to-state comparisons, and geographic metadata.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    warnings: List[str] = []
    comparability_status = "Fully Comparable"

    # Base filters
    mask = pd.Series(True, index=df.index)
    if category:
        mask = mask & (df["category"].str.lower() == category.strip().lower())
        if year:
            comp_check = validator.validate_single_cohort(category, year)
            comparability_status = comp_check.status
            warnings.extend(comp_check.warnings)
    else:
        warnings.append("Multi-category analysis: aggregates distinct institutions across all disciplines.")

    if not multi_year_trend and year:
        mask = mask & (df["year"] == year)

    sub_df = df[mask].copy()

    if states:
        states_lower = [s.strip().lower() for s in states]
        sub_df = sub_df[sub_df["state_std"].str.lower().isin(states_lower)]

    if sub_df.empty:
        return {
            "success": False,
            "error": "No records matched the specified geographic criteria.",
            "metadata": build_analysis_metadata(
                query_type="geographic_analysis",
                calculation_method="distinct_institution_state_aggregation",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year] if year else None,
            )
        }

    # If single year snapshot
    # Calculate state-level metrics
    # Counting unit: distinct institution_uid per state
    state_groups = sub_df.groupby("state_std")
    state_metrics = []

    for state_name, group in state_groups:
        zone = group["zone"].iloc[0] if "zone" in group.columns and pd.notna(group["zone"].iloc[0]) else "Unknown"
        distinct_insts = group["institution_uid"].nunique()
        total_records = len(group)

        # Top tier counts
        top_10 = group[(group["rank"].notnull()) & (group["rank"] <= 10)]["institution_uid"].nunique()
        top_50 = group[(group["rank"].notnull()) & (group["rank"] <= 50)]["institution_uid"].nunique()
        top_100 = group[(group["rank"].notnull()) & (group["rank"] <= 100)]["institution_uid"].nunique()

        valid_scores = group["score"].dropna()
        avg_score = round(float(valid_scores.mean()), 2) if not valid_scores.empty else None
        median_score = round(float(valid_scores.median()), 2) if not valid_scores.empty else None

        valid_rpc = group["rpc"].dropna() if "rpc" in group.columns else pd.Series(dtype=float)
        avg_rpc = round(float(valid_rpc.mean()), 2) if not valid_rpc.empty else None

        valid_tlr = group["tlr"].dropna() if "tlr" in group.columns else pd.Series(dtype=float)
        avg_tlr = round(float(valid_tlr.mean()), 2) if not valid_tlr.empty else None

        state_metrics.append({
            "state": state_name,
            "zone": zone,
            "distinct_institutions": distinct_insts,
            "total_ranked_entries": total_records,
            "top_10_institutions": top_10,
            "top_50_institutions": top_50,
            "top_100_institutions": top_100,
            "average_score": avg_score,
            "median_score": median_score,
            "average_rpc": avg_rpc,
            "average_tlr": avg_tlr,
        })

    # Sort states by distinct institutions descending, then by average_score
    state_metrics.sort(key=lambda s: (s["distinct_institutions"], s["average_score"] or 0.0), reverse=True)

    # Multi-year state representation trend if requested
    yearly_trajectory = {}
    if multi_year_trend:
        pivot = sub_df.pivot_table(
            index="state_std",
            columns="year",
            values="institution_uid",
            aggfunc="nunique",
            fill_value=0
        )
        for s_name in pivot.index:
            yearly_trajectory[s_name] = {int(yr): int(cnt) for yr, cnt in pivot.loc[s_name].items()}

    # Direct Head-to-Head Comparison if specific states selected
    comparison_summary = None
    if states and len(states) >= 2:
        selected_metrics = [m for m in state_metrics if m["state"].lower() in [s.lower() for s in states]]
        comparison_summary = {
            "compared_states": [m["state"] for m in selected_metrics],
            "metrics": selected_metrics,
        }

    metadata = build_analysis_metadata(
        query_type="geographic_analysis",
        calculation_method="distinct_institution_state_aggregation (counting unit: unique institution_uid)",
        records_considered=len(sub_df),
        valid_observations=len(sub_df["institution_uid"].unique()),
        category=category,
        years=[year] if year and not multi_year_trend else sorted(sub_df["year"].unique().tolist()),
        comparability_status=comparability_status,
        warnings=warnings,
    )

    return {
        "success": True,
        "category": category,
        "year": year if not multi_year_trend else "2017-2025",
        "counting_unit": "Distinct institution_uid per state cohort",
        "total_states_represented": len(state_metrics),
        "states_analysis": state_metrics,
        "head_to_head_comparison": comparison_summary,
        "yearly_trajectory": yearly_trajectory if multi_year_trend else None,
        "metadata": metadata,
    }

