"""
Outlier, Parameter Divergence, and Rank Volatility Analysis (FUNCTION 10).
Detects statistical anomalies, research-teaching divergence, and extreme longitudinal volatility
using IQR fences and standardized Z-scores with explicit threshold reporting.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, get_available_parameters_for_category, build_analysis_metadata


def get_outlier_analysis(
    category: str,
    year: int,
    metric: Optional[str] = "score",
    method: str = "iqr",
    threshold: float = 1.5,
    lookback_years: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Detects statistical outliers, parameter divergence, and rank volatility (FUNCTION 10).

    Args:
        category: Standardized NIRF category.
        year: Target assessment edition year.
        metric: Primary metric to inspect ('score', 'tlr', 'rpc', etc., or None for multi-metric).
        method: 'iqr' (Tukey's fences) or 'z_score'.
        threshold: Outlier multiplier (default 1.5 for IQR, 2.5 for Z-score).
        lookback_years: Optional list of years to calculate longitudinal rank volatility.

    Returns:
        Structured dictionary with detected statistical outliers, parameter divergence cases,
        rank volatility leaders, and methodological metadata.
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
                query_type="outlier_analysis",
                calculation_method="statistical_outlier_detection",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
            )
        }

    cat_mask = df["category"].str.lower() == category.strip().lower()
    yr_mask = df["year"] == year
    cohort_df = df[cat_mask & yr_mask].copy()

    total_records = len(cohort_df)
    active_params = get_available_parameters_for_category(category, year)

    outliers_detected: List[Dict[str, Any]] = []

    # 1. Single or Multi-Metric Statistical Outliers
    metrics_to_check = [metric] if metric and metric in cohort_df.columns else ([m for m in ["score"] + active_params if m in cohort_df.columns])

    for m in metrics_to_check:
        series = cohort_df[m].dropna()
        n = len(series)
        if n < 5:
            continue

        vals = series.values
        if method == "iqr":
            q1 = float(np.percentile(vals, 25))
            q3 = float(np.percentile(vals, 75))
            iqr = q3 - q1
            lower_bound = q1 - (threshold * iqr)
            upper_bound = q3 + (threshold * iqr)

            for _, row in cohort_df[cohort_df[m].notnull()].iterrows():
                val = float(row[m])
                if val < lower_bound or val > upper_bound:
                    outliers_detected.append({
                        "institution_uid": str(row["institution_uid"]),
                        "institute_name_std": str(row["institute_name_std"]),
                        "metric": m,
                        "observed_value": round(val, 2),
                        "expected_range": [round(lower_bound, 2), round(upper_bound, 2)],
                        "direction": "high" if val > upper_bound else "low",
                        "detection_method": f"IQR (threshold={threshold})",
                        "rank": clean_numeric(row["rank"]),
                    })

        elif method == "z_score":
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1))
            if std_val > 0:
                for _, row in cohort_df[cohort_df[m].notnull()].iterrows():
                    val = float(row[m])
                    z = (val - mean_val) / std_val
                    if abs(z) >= threshold:
                        outliers_detected.append({
                            "institution_uid": str(row["institution_uid"]),
                            "institute_name_std": str(row["institute_name_std"]),
                            "metric": m,
                            "observed_value": round(val, 2),
                            "z_score": round(float(z), 2),
                            "expected_range": [round(mean_val - threshold * std_val, 2), round(mean_val + threshold * std_val, 2)],
                            "direction": "high" if z > 0 else "low",
                            "detection_method": f"Z-score (threshold={threshold})",
                            "rank": clean_numeric(row["rank"]),
                        })

    # 2. Domain Divergence Outliers: High Research (RPC) vs Low Teaching (TLR)
    divergence_cases: List[Dict[str, Any]] = []
    if "rpc" in cohort_df.columns and "tlr" in cohort_df.columns:
        valid_paired = cohort_df.dropna(subset=["rpc", "tlr"]).copy()
        if len(valid_paired) >= 5:
            valid_paired["rpc_tlr_gap"] = valid_paired["rpc"] - valid_paired["tlr"]
            gap_q1 = float(np.percentile(valid_paired["rpc_tlr_gap"], 25))
            gap_q3 = float(np.percentile(valid_paired["rpc_tlr_gap"], 75))
            gap_iqr = gap_q3 - gap_q1
            gap_upper = gap_q3 + (1.5 * gap_iqr)

            for _, row in valid_paired[valid_paired["rpc_tlr_gap"] > gap_upper].iterrows():
                divergence_cases.append({
                    "institution_uid": str(row["institution_uid"]),
                    "institute_name_std": str(row["institute_name_std"]),
                    "rpc": round(float(row["rpc"]), 2),
                    "tlr": round(float(row["tlr"]), 2),
                    "research_teaching_gap": round(float(row["rpc_tlr_gap"]), 2),
                    "divergence_type": "High Research / Low Teaching Outlier",
                    "rank": clean_numeric(row["rank"]),
                })

    # 3. Longitudinal Rank Volatility (if lookback years provided)
    volatility_cases: List[Dict[str, Any]] = []
    if lookback_years and len(lookback_years) >= 2:
        vol_df = df[cat_mask & df["year"].isin(lookback_years) & df["rank"].notnull()]
        inst_counts = vol_df.groupby("institution_uid")["rank"].agg(["count", "std", "min", "max"])
        # filter to institutions present in at least 3 years or half the lookback period
        min_years_needed = max(2, len(lookback_years) // 2)
        qualified = inst_counts[inst_counts["count"] >= min_years_needed].dropna(subset=["std"])
        top_volatile = qualified.sort_values("std", ascending=False).head(10)

        for u_id, stats_row in top_volatile.iterrows():
            name = df[df["institution_uid"] == u_id]["institute_name_std"].iloc[0]
            volatility_cases.append({
                "institution_uid": str(u_id),
                "institute_name_std": str(name),
                "rank_std_dev": round(float(stats_row["std"]), 2),
                "rank_range": [int(stats_row["min"]), int(stats_row["max"])],
                "years_observed": int(stats_row["count"]),
            })

    metadata = build_analysis_metadata(
        query_type="outlier_analysis",
        calculation_method=f"statistical_anomaly_detection ({method.upper()}, threshold={threshold})",
        records_considered=total_records,
        valid_observations=len(outliers_detected) + len(divergence_cases),
        category=category,
        years=[year],
        parameters=metrics_to_check,
        comparability_status=comp_check.status,
        warnings=comp_check.warnings + ["Outliers indicate unusual empirical performance and are not automatically erroneous."],
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "year": year,
        "detection_method": method,
        "threshold": threshold,
        "metric_outliers": outliers_detected,
        "parameter_divergence_outliers": divergence_cases,
        "longitudinal_rank_volatility": volatility_cases if lookback_years else None,
        "disclaimer": "Outliers highlight exceptional or divergent institutional patterns; they do not imply invalid data.",
        "metadata": metadata,
    }

