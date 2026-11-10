"""
Score and Parameter Distribution Analysis (FUNCTION 8).
Calculates parametric and non-parametric distribution statistics, quartiles, IQR,
and histogram frequency bins suitable for visualization in Plotly.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, build_analysis_metadata


def get_score_distribution(
    category: str,
    year: int,
    metric: str = "score",
    state: Optional[str] = None,
    bins_count: int = 10,
) -> Dict[str, Any]:
    """
    Computes statistical distribution properties of scores or parameters within a cohort.

    Args:
        category: Standardized NIRF category.
        year: Assessment edition year.
        metric: Metric to analyze ('score', 'tlr', 'rpc', 'go', 'oi', 'perception', etc.).
        state: Optional state filter.
        bins_count: Number of bins for histogram discretization (default 10).

    Returns:
        Structured dictionary with central tendency, dispersion, quartiles, IQR,
        skewness, kurtosis, and histogram bin edges/counts.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    m_clean = metric.strip().lower()
    comp_check = validator.validate_single_cohort(category, year, requested_metrics=[m_clean])
    if not comp_check.is_comparable:
        return {
            "success": False,
            "error": f"Invalid distribution request: {'; '.join(comp_check.errors)}",
            "metadata": build_analysis_metadata(
                query_type="score_distribution",
                calculation_method="distribution_moments_and_quantiles",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[year],
                parameters=[m_clean],
            )
        }

    cat_mask = df["category"].str.lower() == category.strip().lower()
    yr_mask = df["year"] == year
    state_mask = pd.Series(True, index=df.index)
    if state:
        state_mask = df["state_std"].str.lower() == state.strip().lower()

    sub_df = df[cat_mask & yr_mask & state_mask]
    total_records = len(sub_df)

    if m_clean not in sub_df.columns:
        return {
            "success": False,
            "error": f"Metric '{metric}' not found in dataset columns.",
            "metadata": build_analysis_metadata(
                query_type="score_distribution",
                calculation_method="distribution_moments_and_quantiles",
                records_considered=total_records,
                valid_observations=0,
                category=category,
                years=[year],
                parameters=[m_clean],
            )
        }

    valid_series = sub_df[m_clean].dropna()
    valid_n = len(valid_series)
    missing_n = total_records - valid_n

    if valid_n == 0:
        return {
            "success": False,
            "error": f"No valid non-null values for metric '{metric}' in {category} ({year}).",
            "metadata": build_analysis_metadata(
                query_type="score_distribution",
                calculation_method="distribution_moments_and_quantiles",
                records_considered=total_records,
                valid_observations=0,
                category=category,
                years=[year],
                parameters=[m_clean],
            )
        }

    vals = valid_series.values
    mean_val = float(np.mean(vals))
    std_val = float(np.std(vals, ddof=1)) if valid_n > 1 else 0.0
    var_val = float(np.var(vals, ddof=1)) if valid_n > 1 else 0.0
    median_val = float(np.median(vals))
    min_val = float(np.min(vals))
    max_val = float(np.max(vals))

    q1 = float(np.percentile(vals, 25))
    q3 = float(np.percentile(vals, 75))
    iqr = q3 - q1

    p10 = float(np.percentile(vals, 10))
    p90 = float(np.percentile(vals, 90))

    skewness = float(stats.skew(vals)) if valid_n >= 3 else 0.0
    kurt = float(stats.kurtosis(vals)) if valid_n >= 4 else 0.0

    # Histogram calculation
    counts, bin_edges = np.histogram(vals, bins=bins_count)
    bins_data = []
    for i in range(len(counts)):
        low_edge = round(float(bin_edges[i]), 2)
        high_edge = round(float(bin_edges[i + 1]), 2)
        cnt = int(counts[i])
        bins_data.append({
            "bin_index": i,
            "bin_label": f"{low_edge} - {high_edge}",
            "bin_start": low_edge,
            "bin_end": high_edge,
            "count": cnt,
            "percentage": round((cnt / valid_n) * 100, 2),
        })

    summary_stats = {
        "metric": m_clean,
        "sample_size": valid_n,
        "missing_count": missing_n,
        "mean": round(mean_val, 2),
        "std_dev_sample": round(std_val, 2),
        "variance_sample": round(var_val, 2),
        "median": round(median_val, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "q1_25th_percentile": round(q1, 2),
        "q3_75th_percentile": round(q3, 2),
        "iqr": round(iqr, 2),
        "10th_percentile": round(p10, 2),
        "90th_percentile": round(p90, 2),
        "skewness": round(skewness, 4),
        "kurtosis": round(kurt, 4),
    }

    metadata = build_analysis_metadata(
        query_type="score_distribution",
        calculation_method="distribution_moments_and_quantiles (ddof=1 sample std)",
        records_considered=total_records,
        valid_observations=valid_n,
        category=category,
        years=[year],
        parameters=[m_clean],
        missing_data_info={"missing_count": missing_n, "missing_pct": round(missing_n / total_records * 100, 2) if total_records > 0 else 0},
        comparability_status=comp_check.status,
        warnings=comp_check.warnings,
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "year": year,
        "metric": m_clean,
        "state_filter": state,
        "statistics": summary_stats,
        "histogram_bins": bins_data,
        "scores": [
            {"institution": row.get("institute_name_std"), "score": round(float(row[m_clean]), 2)}
            for _, row in sub_df.dropna(subset=[m_clean]).iterrows()
        ],
        "metadata": metadata,
    }

