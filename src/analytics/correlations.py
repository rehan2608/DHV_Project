"""
Parameter Correlation and Bivariate Relationship Analysis (FUNCTIONS 5 & 6).
Computes Pearson and Spearman correlation matrices, bivariate linear regressions,
and quadrant divergence profiles, strictly enforcing pairwise completeness and non-causality.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, get_available_parameters_for_category, build_analysis_metadata


def get_parameter_correlation(
    category: str,
    year: int,
    parameters: Optional[List[str]] = None,
    method: str = "both",
) -> Dict[str, Any]:
    """
    Computes pairwise Pearson and Spearman correlation matrices between NIRF parameters (FUNCTION 5).

    Args:
        category: Standardized NIRF category.
        year: Assessment edition year.
        parameters: Optional list of parameter names to include.
        method: 'pearson', 'spearman', or 'both'.

    Returns:
        Structured dictionary with correlation matrices, pairwise sample sizes,
        strongest relationships, and statistical disclaimers.
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
                query_type="parameter_correlation",
                calculation_method="pairwise_correlation_matrix",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
            )
        }

    available_params = get_available_parameters_for_category(category, year)
    if not available_params:
        return {
            "success": False,
            "error": f"Category '{category}' in {year} publishes no numerical parameters (Rank-Only).",
            "metadata": build_analysis_metadata(
                query_type="parameter_correlation",
                calculation_method="pairwise_correlation_matrix",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                comparability_status=comp_check.status,
                warnings=comp_check.warnings + ["Parameters unavailable for Rank-Only categories."],
            )
        }

    target_params = [p for p in (parameters or available_params) if p in available_params]
    if len(target_params) < 2:
        return {
            "success": False,
            "error": f"At least 2 valid parameters required for correlation. Available: {available_params}",
            "metadata": build_analysis_metadata(
                query_type="parameter_correlation",
                calculation_method="pairwise_correlation_matrix",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                parameters=target_params,
            )
        }

    cat_mask = df["category"].str.lower() == category.strip().lower()
    yr_mask = df["year"] == year
    sub_df = df[cat_mask & yr_mask][target_params].copy()

    pearson_matrix: Dict[str, Dict[str, Optional[float]]] = {p: {} for p in target_params}
    spearman_matrix: Dict[str, Dict[str, Optional[float]]] = {p: {} for p in target_params}
    sample_sizes: Dict[str, Dict[str, int]] = {p: {} for p in target_params}

    pair_correlations: List[Dict[str, Any]] = []

    for i, p1 in enumerate(target_params):
        for j, p2 in enumerate(target_params):
            if p1 == p2:
                pearson_matrix[p1][p2] = 1.0
                spearman_matrix[p1][p2] = 1.0
                valid_n = int(sub_df[p1].dropna().count())
                sample_sizes[p1][p2] = valid_n
                continue

            paired = sub_df[[p1, p2]].dropna()
            n = len(paired)
            sample_sizes[p1][p2] = n

            if n < 3 or paired[p1].std() == 0 or paired[p2].std() == 0:
                pearson_matrix[p1][p2] = None
                spearman_matrix[p1][p2] = None
                continue

            r_val, p_val = stats.pearsonr(paired[p1], paired[p2])
            rho_val, rho_p = stats.spearmanr(paired[p1], paired[p2])

            clean_r = round(float(r_val), 4)
            clean_rho = round(float(rho_val), 4)

            pearson_matrix[p1][p2] = clean_r
            spearman_matrix[p1][p2] = clean_rho

            if i < j:
                pair_correlations.append({
                    "param1": p1,
                    "param2": p2,
                    "sample_size": n,
                    "pearson_r": clean_r,
                    "pearson_p_value": round(float(p_val), 6),
                    "spearman_rho": clean_rho,
                    "spearman_p_value": round(float(rho_p), 6),
                })

    # Find strongest positive and negative
    valid_pairs = [p for p in pair_correlations if p["pearson_r"] is not None]
    strongest_pos = max(valid_pairs, key=lambda x: x["pearson_r"]) if valid_pairs else None
    strongest_neg = min(valid_pairs, key=lambda x: x["pearson_r"]) if valid_pairs else None

    metadata = build_analysis_metadata(
        query_type="parameter_correlation",
        calculation_method="pairwise_complete_correlation (Pearson r & Spearman rho)",
        records_considered=len(sub_df),
        valid_observations=max([p["sample_size"] for p in pair_correlations], default=0),
        category=category,
        years=[year],
        parameters=target_params,
        comparability_status=comp_check.status,
        warnings=comp_check.warnings + ["Statistical correlation does not establish causation."],
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "year": year,
        "parameters": target_params,
        "method": method,
        "pearson_matrix": pearson_matrix if method in ("pearson", "both") else None,
        "spearman_matrix": spearman_matrix if method in ("spearman", "both") else None,
        "sample_sizes": sample_sizes,
        "strongest_positive_correlation": strongest_pos,
        "strongest_negative_correlation": strongest_neg,
        "pairwise_details": pair_correlations,
        "disclaimer": "Correlation measures linear/monotonic co-movement; it does not indicate causal influence.",
        "metadata": metadata,
    }


def get_parameter_relationship(
    category: str,
    year: int,
    param_x: str,
    param_y: str,
    institution_uids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes the bivariate relationship and linear regression between two NIRF parameters (FUNCTION 6).

    Args:
        category: Standardized NIRF category.
        year: Assessment edition year.
        param_x: Name of independent / X parameter (e.g. 'rpc').
        param_y: Name of dependent / Y parameter (e.g. 'tlr').
        institution_uids: Optional list of institution UIDs to restrict the analysis to a subset.

    Returns:
        Structured dictionary with paired observations for plotting, regression statistics,
        trendline coordinates, and quadrant divergence analysis.
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
                query_type="parameter_relationship",
                calculation_method="bivariate_linear_regression",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
            )
        }

    available_params = get_available_parameters_for_category(category, year)
    px = param_x.strip().lower()
    py = param_y.strip().lower()

    if px not in available_params or py not in available_params:
        return {
            "success": False,
            "error": f"Both parameters must be available for '{category}' in {year}. Available: {available_params}",
            "metadata": build_analysis_metadata(
                query_type="parameter_relationship",
                calculation_method="bivariate_linear_regression",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                parameters=[px, py],
            )
        }

    cat_mask = df["category"].str.lower() == category.strip().lower()
    yr_mask = df["year"] == year
    sub_df = df[cat_mask & yr_mask][[
        "institution_uid", "institute_name_std", "rank", "score", px, py
    ]].dropna(subset=[px, py]).copy()

    if institution_uids:
        sub_df = sub_df[sub_df["institution_uid"].isin(institution_uids)]

    n = len(sub_df)
    if n < 3:
        return {
            "success": False,
            "error": f"Insufficient paired observations (n={n}) to fit regression.",
            "metadata": build_analysis_metadata(
                query_type="parameter_relationship",
                calculation_method="bivariate_linear_regression",
                records_considered=len(sub_df),
                valid_observations=n,
                category=category,
                years=[year],
                parameters=[px, py],
            )
        }

    # Bivariate statistics
    x_vals = sub_df[px].values
    y_vals = sub_df[py].values

    r_val, p_val = stats.pearsonr(x_vals, y_vals)
    rho_val, rho_p = stats.spearmanr(x_vals, y_vals)
    reg = stats.linregress(x_vals, y_vals)

    min_x, max_x = float(np.min(x_vals)), float(np.max(x_vals))
    trendline_start = {"x": min_x, "y": round(float(reg.intercept + reg.slope * min_x), 4)}
    trendline_end = {"x": max_x, "y": round(float(reg.intercept + reg.slope * max_x), 4)}

    # Quadrant Classification (based on median values)
    med_x = float(np.median(x_vals))
    med_y = float(np.median(y_vals))

    points = []
    quadrant_counts = {"high_x_low_y": 0, "low_x_high_y": 0, "high_x_high_y": 0, "low_x_low_y": 0}

    for _, row in sub_df.iterrows():
        x_i = float(row[px])
        y_i = float(row[py])

        if x_i >= med_x and y_i < med_y:
            q_name = "high_x_low_y"
        elif x_i < med_x and y_i >= med_y:
            q_name = "low_x_high_y"
        elif x_i >= med_x and y_i >= med_y:
            q_name = "high_x_high_y"
        else:
            q_name = "low_x_low_y"

        quadrant_counts[q_name] += 1

        points.append({
            "institution_uid": str(row["institution_uid"]),
            "institute_name_std": str(row["institute_name_std"]),
            "rank": clean_numeric(row["rank"]),
            "score": clean_numeric(row["score"]),
            "x": round(x_i, 2),
            "y": round(y_i, 2),
            "quadrant": q_name,
        })

    regression_stats = {
        "slope": round(float(reg.slope), 4),
        "intercept": round(float(reg.intercept), 4),
        "r_squared": round(float(reg.rvalue ** 2), 4),
        "pearson_r": round(float(r_val), 4),
        "pearson_p_value": round(float(p_val), 6),
        "spearman_rho": round(float(rho_val), 4),
        "spearman_p_value": round(float(rho_p), 6),
        "std_err": round(float(reg.stderr), 6),
    }

    metadata = build_analysis_metadata(
        query_type="parameter_relationship",
        calculation_method="ordinary_least_squares_regression_and_quadrant_analysis",
        records_considered=len(df[cat_mask & yr_mask]),
        valid_observations=n,
        category=category,
        years=[year],
        parameters=[px, py],
        comparability_status=comp_check.status,
        warnings=comp_check.warnings + ["Fitted regression line models co-variation; do not infer causal mechanics."],
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "year": year,
        "param_x": px,
        "param_y": py,
        "sample_size": n,
        "regression": regression_stats,
        "trendline": [trendline_start, trendline_end],
        "medians": {"x_median": round(med_x, 2), "y_median": round(med_y, 2)},
        "quadrant_counts": quadrant_counts,
        "points": points,
        "metadata": metadata,
    }

