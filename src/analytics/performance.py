"""
Category and Multidimensional Performance Analysis (FUNCTIONS 3 & 7).
Provides category cohort performance summaries and multi-parameter institutional profiles,
respecting category-specific parameter schemas and rank-only designations.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import (
    clean_numeric,
    get_available_parameters_for_category,
    build_analysis_metadata,
    matches_institution_name,
)


def get_category_performance(
    category: str,
    year: int,
    state: Optional[str] = None,
    top_n: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Analyzes institutional performance within a selected NIRF category and year (FUNCTION 3).

    Args:
        category: NIRF category (e.g. 'Engineering', 'College', 'Innovation').
        year: Assessment year (2017–2025).
        state: Optional state filter.
        top_n: Number of institutions to return in the ranked table (default all).

    Returns:
        Structured dictionary with cohort statistical summary, parameter averages,
        and ranked institution list.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    comp_check = validator.validate_single_cohort(category, year)
    if not comp_check.is_comparable:
        return {
            "success": False,
            "error": f"Invalid cohort: {'; '.join(comp_check.errors)}",
            "metadata": build_analysis_metadata(
                query_type="category_performance",
                calculation_method="cohort_statistical_aggregation",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                comparability_status=comp_check.status,
                warnings=comp_check.warnings,
                limitations=comp_check.notes,
            )
        }

    # Filter cohort
    cat_mask = df["category"].str.lower() == category.strip().lower()
    yr_mask = df["year"] == year
    state_mask = pd.Series(True, index=df.index)
    if state:
        state_mask = df["state_std"].str.lower() == state.strip().lower()

    cohort_df = df[cat_mask & yr_mask & state_mask].sort_values("rank", na_position="last").copy()

    total_count = len(cohort_df)
    active_params = get_available_parameters_for_category(category, year)
    scores_available = comp_check.metric_schema != "Rank Only"

    # Score statistics
    score_stats: Optional[Dict[str, Any]] = None
    if scores_available:
        valid_scores = cohort_df["score"].dropna()
        if not valid_scores.empty:
            score_stats = {
                "count": int(len(valid_scores)),
                "mean": round(float(valid_scores.mean()), 2),
                "median": round(float(valid_scores.median()), 2),
                "std": round(float(valid_scores.std(ddof=1)), 2) if len(valid_scores) > 1 else 0.0,
                "min": round(float(valid_scores.min()), 2),
                "max": round(float(valid_scores.max()), 2),
            }

    # Parameter statistics
    param_stats: Dict[str, Any] = {}
    for p in active_params:
        if p in cohort_df.columns:
            vals = cohort_df[p].dropna()
            if not vals.empty:
                param_stats[p] = {
                    "count": int(len(vals)),
                    "mean": round(float(vals.mean()), 2),
                    "median": round(float(vals.median()), 2),
                    "std": round(float(vals.std(ddof=1)), 2) if len(vals) > 1 else 0.0,
                    "min": round(float(vals.min()), 2),
                    "max": round(float(vals.max()), 2),
                }

    # Institutions list
    records_to_take = cohort_df.head(top_n) if top_n is not None else cohort_df
    institutions_list = []
    for _, row in records_to_take.iterrows():
        p_dict = {p: clean_numeric(row.get(p, None)) for p in active_params}
        institutions_list.append({
            "institution_uid": str(row["institution_uid"]),
            "institute_name_std": str(row["institute_name_std"]),
            "state_std": str(row["state_std"]),
            "city_std": str(row["city_std"]),
            "rank": clean_numeric(row["rank"]),
            "rank_label": str(row["rank_label"]) if pd.notna(row["rank_label"]) else None,
            "score": clean_numeric(row["score"]),
            "parameters": p_dict,
            "validation_status": str(row["rank_validation_status"]),
        })

    metadata = build_analysis_metadata(
        query_type="category_performance",
        calculation_method="cohort_descriptive_statistics",
        records_considered=total_count,
        valid_observations=len(institutions_list),
        category=category,
        years=[year],
        parameters=active_params,
        missing_data_info={
            "total_institutions": total_count,
            "missing_scores": int(cohort_df["score"].isnull().sum()),
            "missing_ranks": int(cohort_df["rank"].isnull().sum()),
        },
        comparability_status=comp_check.status,
        warnings=comp_check.warnings,
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "year": year,
        "state_filter": state,
        "total_institutions": total_count,
        "scores_available": scores_available,
        "score_summary": score_stats,
        "parameter_summary": param_stats,
        "institutions": institutions_list,
        "metadata": metadata,
    }


def get_multidimensional_performance(
    category: str,
    year: int,
    institution_uids: Optional[List[str]] = None,
    institution_names: Optional[List[str]] = None,
    parameters: Optional[List[str]] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Compares institutions across multiple NIRF parameters and analyzes parameter balance (FUNCTION 7).

    Args:
        category: NIRF category (e.g. 'Engineering', 'Overall').
        year: Assessment edition year.
        institution_uids: Optional list of target institution UIDs.
        institution_names: Optional list of institution names to match.
        parameters: Optional parameter list (defaults to category available parameters).
        top_n: Fallback count if no specific institutions provided (default 10).

    Returns:
        Structured dictionary with parameter profiles, parameter gaps,
        strongest/weakest parameters, and cohort percentiles.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    comp_check = validator.validate_single_cohort(category, year)
    if not comp_check.is_comparable:
        return {
            "success": False,
            "error": f"Invalid cohort: {'; '.join(comp_check.errors)}",
            "metadata": build_analysis_metadata(
                query_type="multidimensional_performance",
                calculation_method="multi_parameter_profiling",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                comparability_status=comp_check.status,
                warnings=comp_check.warnings,
                limitations=comp_check.notes,
            )
        }

    # Available parameters
    active_params = parameters or get_available_parameters_for_category(category, year)
    if not active_params:
        return {
            "success": False,
            "error": f"Category '{category}' in {year} publishes no numerical parameters (Rank-Only).",
            "metadata": build_analysis_metadata(
                query_type="multidimensional_performance",
                calculation_method="multi_parameter_profiling",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                comparability_status=comp_check.status,
                warnings=comp_check.warnings + ["Parameters unavailable for Rank-Only categories."],
            )
        }

    # Get cohort baseline for percentiles
    cat_mask = df["category"].str.lower() == category.strip().lower()
    yr_mask = df["year"] == year
    cohort_df = df[cat_mask & yr_mask].copy()

    # Filter target institutions
    target_df = pd.DataFrame()
    if institution_uids:
        target_df = cohort_df[cohort_df["institution_uid"].isin(institution_uids)]
    elif institution_names:
        target_df = cohort_df[
            cohort_df["institute_name_std"].apply(lambda v: matches_institution_name(v, institution_names))
        ]
    else:
        target_df = cohort_df.sort_values("rank", na_position="last").head(top_n)

    if target_df.empty:
        return {
            "success": False,
            "error": "No matching institutions found in the specified cohort.",
            "metadata": build_analysis_metadata(
                query_type="multidimensional_performance",
                calculation_method="multi_parameter_profiling",
                records_considered=len(cohort_df),
                valid_observations=0,
                category=category,
                years=[year],
                parameters=active_params,
            )
        }

    # Compute cohort percentiles for each parameter
    profiles: List[Dict[str, Any]] = []
    high_rpc_low_tlr: List[str] = []
    high_tlr_low_perception: List[str] = []

    has_tlr_rpc = "tlr" in active_params and "rpc" in active_params
    has_tlr_per = "tlr" in active_params and "perception" in active_params

    # Median thresholds for quadrant flags
    median_rpc = cohort_df["rpc"].dropna().median() if "rpc" in cohort_df.columns else None
    median_tlr = cohort_df["tlr"].dropna().median() if "tlr" in cohort_df.columns else None
    median_per = cohort_df["perception"].dropna().median() if "perception" in cohort_df.columns else None

    for _, row in target_df.iterrows():
        inst_params: Dict[str, Optional[float]] = {}
        inst_percentiles: Dict[str, Optional[float]] = {}
        valid_p_items = []

        for p in active_params:
            val = clean_numeric(row.get(p, None))
            inst_params[p] = val
            if val is not None and p in cohort_df.columns:
                cohort_series = cohort_df[p].dropna()
                pct = round(float(stats.percentileofscore(cohort_series, val, kind="rank")), 2)
                inst_percentiles[p] = pct
                valid_p_items.append((p, val, pct))
            else:
                inst_percentiles[p] = None

        strongest_param = max(valid_p_items, key=lambda x: x[2])[0] if valid_p_items else None
        weakest_param = min(valid_p_items, key=lambda x: x[2])[0] if valid_p_items else None

        # Gaps
        rpc_tlr_gap = None
        if has_tlr_rpc and inst_params.get("rpc") is not None and inst_params.get("tlr") is not None:
            rpc_tlr_gap = round(inst_params["rpc"] - inst_params["tlr"], 2)
            if median_rpc is not None and median_tlr is not None:
                if inst_params["rpc"] > median_rpc and inst_params["tlr"] < median_tlr:
                    high_rpc_low_tlr.append(str(row["institute_name_std"]))

        tlr_per_gap = None
        if has_tlr_per and inst_params.get("tlr") is not None and inst_params.get("perception") is not None:
            tlr_per_gap = round(inst_params["tlr"] - inst_params["perception"], 2)
            if median_tlr is not None and median_per is not None:
                if inst_params["tlr"] > median_tlr and inst_params["perception"] < median_per:
                    high_tlr_low_perception.append(str(row["institute_name_std"]))

        profiles.append({
            "institution_uid": str(row["institution_uid"]),
            "institute_name_std": str(row["institute_name_std"]),
            "rank": clean_numeric(row["rank"]),
            "score": clean_numeric(row["score"]),
            "parameters": inst_params,
            "percentiles": inst_percentiles,
            "strongest_parameter": strongest_param,
            "weakest_parameter": weakest_param,
            "research_vs_teaching_gap": rpc_tlr_gap,
            "teaching_vs_perception_gap": tlr_per_gap,
        })

    metadata = build_analysis_metadata(
        query_type="multidimensional_performance",
        calculation_method="parameter_profiling_and_cohort_percentiles",
        records_considered=len(cohort_df),
        valid_observations=len(profiles),
        category=category,
        years=[year],
        parameters=active_params,
        comparability_status=comp_check.status,
        warnings=comp_check.warnings,
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "year": year,
        "profiles": profiles,
        "high_rpc_low_tlr_institutions": high_rpc_low_tlr,
        "high_tlr_low_perception_institutions": high_tlr_low_perception,
        "metadata": metadata,
    }
