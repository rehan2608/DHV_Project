"""
Institution Trend Analysis for NIRF Longitudinal Tracking (FUNCTION 1).
Analyzes an institution's historical trajectory across editions, tracking rank shifts,
composite scores, and parameter evolutions without imputing missing years.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, get_available_parameters_for_category, build_analysis_metadata


def get_institution_trend(
    institution_id_or_name: str,
    category: str,
    start_year: Optional[int] = 2017,
    end_year: Optional[int] = 2025,
    parameters: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes how an institution performed over time in a given category.

    Args:
        institution_id_or_name: Exact institution_uid or institution name substring.
        category: Standardized NIRF category (e.g. 'Engineering', 'Overall').
        start_year: Beginning year of analysis (default 2017).
        end_year: Ending year of analysis (default 2025).
        parameters: Optional list of parameter column names to track.

    Returns:
        Structured dictionary with chronological records, rank improvements,
        missing years, and comparability metadata.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    # 1. Resolve Institution
    query = institution_id_or_name.strip()
    id_match = df[
        (df["institution_uid"].str.lower() == query.lower()) |
        (df["institution_uid_raw"].str.lower() == query.lower()) |
        (df["institute_id"].astype(str).str.lower() == query.lower())
    ]

    if not id_match.empty:
        target_uid = id_match.iloc[0]["institution_uid"]
        std_name = id_match.iloc[0]["institute_name_std"]
    else:
        # Search by name with acronym expansion
        query_variants = [institution_id_or_name]
        matches = loader.search_institutions(query, limit=10)
        if matches.empty:
            # Try expanded acronym search
            from src.analytics.utils import expand_institution_query
            for var in expand_institution_query(query):
                matches = loader.search_institutions(var, limit=10)
                if not matches.empty:
                    break
        if matches.empty:
            return {
                "success": False,
                "error": f"Institution '{query}' not found in NIRF dataset.",
                "metadata": build_analysis_metadata(
                    query_type="institution_trend",
                    calculation_method="longitudinal_chronological_tracking",
                    records_considered=0,
                    valid_observations=0,
                    category=category,
                )
            }
        if len(matches) > 1:
            candidate_list = [
                {"institution_uid": r["institution_uid"], "institute_name_std": r["institute_name_std"], "state": r["state_std"]}
                for _, r in matches.iterrows()
            ]
            # Check if one matches exactly
            exact = [c for c in candidate_list if c["institute_name_std"].lower() == query.lower()]
            if len(exact) == 1:
                target_uid = exact[0]["institution_uid"]
                std_name = exact[0]["institute_name_std"]
            else:
                return {
                    "success": False,
                    "error": f"Multiple institutions matched '{query}'. Please specify institution_uid.",
                    "candidates": candidate_list,
                    "metadata": build_analysis_metadata(
                        query_type="institution_trend",
                        calculation_method="longitudinal_chronological_tracking",
                        records_considered=0,
                        valid_observations=0,
                        category=category,
                    )
                }
        else:
            target_uid = matches.iloc[0]["institution_uid"]
            std_name = matches.iloc[0]["institute_name_std"]

    # 2. Determine Year Range & Validate Comparability
    start_yr = int(start_year) if start_year is not None else 2017
    end_yr = int(end_year) if end_year is not None else 2025
    years_range = list(range(start_yr, end_yr + 1))

    comp_check = validator.validate_multi_year_comparison(category, years_range, requested_metrics=parameters)

    # 3. Filter Records for Target Institution
    cat_mask = df["category"].str.lower() == category.strip().lower()
    inst_mask = df["institution_uid"] == target_uid
    sub_df = df[cat_mask & inst_mask & df["year"].isin(years_range)].sort_values("year")

    # Determine default parameters if none specified
    if not parameters:
        sample_yr = end_yr if end_yr in years_range else years_range[-1]
        active_params = get_available_parameters_for_category(category, sample_yr)
    else:
        active_params = parameters

    chronological_data: List[Dict[str, Any]] = []
    missing_years: List[int] = []
    valid_ranks: List[float] = []
    valid_scores: List[float] = []

    for yr in years_range:
        yr_rows = sub_df[sub_df["year"] == yr]
        if yr_rows.empty:
            missing_years.append(yr)
            chronological_data.append({
                "year": yr,
                "is_observed": False,
                "rank": None,
                "rank_label": None,
                "score": None,
                "parameters": {p: None for p in active_params},
                "status": "Not Ranked / Not Published",
            })
        else:
            row = yr_rows.iloc[0]
            r_val = clean_numeric(row["rank"])
            s_val = clean_numeric(row["score"])
            if r_val is not None:
                valid_ranks.append(r_val)
            if s_val is not None:
                valid_scores.append(s_val)

            param_dict = {}
            for p in active_params:
                param_dict[p] = clean_numeric(row.get(p, None))

            chronological_data.append({
                "year": yr,
                "is_observed": True,
                "rank": r_val,
                "rank_label": str(row["rank_label"]) if pd.notna(row["rank_label"]) else None,
                "score": s_val,
                "parameters": param_dict,
                "status": str(row["rank_validation_status"]),
            })

    # 4. Rank Improvement Calculation (start_rank - end_rank)
    start_row = next((r for r in chronological_data if r["year"] == start_yr and r["is_observed"]), None)
    end_row = next((r for r in chronological_data if r["year"] == end_yr and r["is_observed"]), None)

    rank_improvement = None
    rank_improvement_note = None
    if start_row and end_row and start_row["rank"] is not None and end_row["rank"] is not None:
        rank_improvement = int(start_row["rank"] - end_row["rank"])
    else:
        missing_endpoints = []
        if not start_row or start_row["rank"] is None:
            missing_endpoints.append(str(start_yr))
        if not end_row or end_row["rank"] is None:
            missing_endpoints.append(str(end_yr))
        rank_improvement_note = f"Rank improvement could not be calculated because institution has no valid rank in: {', '.join(missing_endpoints)}"

    best_rank = int(min(valid_ranks)) if valid_ranks else None
    worst_rank = int(max(valid_ranks)) if valid_ranks else None
    avg_score = round(float(sum(valid_scores) / len(valid_scores)), 2) if valid_scores else None

    warnings = list(comp_check.warnings)
    if rank_improvement_note:
        warnings.append(rank_improvement_note)

    metadata = build_analysis_metadata(
        query_type="institution_trend",
        calculation_method="longitudinal_chronological_tracking",
        records_considered=len(years_range),
        valid_observations=len(valid_ranks),
        category=category,
        years=years_range,
        parameters=active_params,
        missing_data_info={"missing_years": missing_years, "missing_count": len(missing_years)},
        comparability_status=comp_check.status,
        warnings=warnings,
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "institution_uid": target_uid,
        "institute_name_std": std_name,
        "category": category,
        "start_year": start_yr,
        "end_year": end_yr,
        "rank_improvement": rank_improvement,
        "best_rank": best_rank,
        "worst_rank": worst_rank,
        "average_score": avg_score,
        "chronological_trajectory": chronological_data,
        "metadata": metadata,
    }
