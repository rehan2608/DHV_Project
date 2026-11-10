"""
Rank Movement Analysis across NIRF Editions (FUNCTION 2).
Identifies institutions with the largest rank gains and declines over time,
applying the official rank_improvement = start_rank - end_rank definition
while preventing imputation of missing years.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, build_analysis_metadata


def get_rank_movement(
    category: str,
    start_year: int,
    end_year: int,
    state: Optional[str] = None,
    top_n: int = 10,
    movement_type: str = "both",
) -> Dict[str, Any]:
    """
    Computes ranking improvement and decline for institutions between two years.

    Formula:
        rank_improvement = start_year_rank - end_year_rank
        (Positive = improvement, Negative = decline, 0 = unchanged)

    Args:
        category: NIRF category (e.g. 'Engineering').
        start_year: Beginning assessment year.
        end_year: Ending assessment year.
        state: Optional state filter (case-insensitive).
        top_n: Number of top gainers/decliners to return (default 10).
        movement_type: 'both', 'improvement', or 'decline'.

    Returns:
        Structured dictionary with top gainers, top decliners, cohort turnover counts,
        and comparability metadata.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    # 1. Comparability Check
    comp_check = validator.validate_multi_year_comparison(category, [start_year, end_year])
    if not comp_check.is_comparable:
        return {
            "success": False,
            "error": f"Comparison invalid: {'; '.join(comp_check.errors)}",
            "metadata": build_analysis_metadata(
                query_type="rank_movement",
                calculation_method="endpoint_rank_differential",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[start_year, end_year],
                comparability_status=comp_check.status,
                warnings=comp_check.warnings,
                limitations=comp_check.notes,
            )
        }

    # 2. Filter Cohorts for Start and End Year
    cat_mask = df["category"].str.lower() == category.strip().lower()
    state_mask = pd.Series(True, index=df.index)
    if state:
        state_mask = df["state_std"].str.lower() == state.strip().lower()

    start_df = df[cat_mask & state_mask & (df["year"] == start_year) & df["rank"].notnull()].copy()
    end_df = df[cat_mask & state_mask & (df["year"] == end_year) & df["rank"].notnull()].copy()

    start_insts = set(start_df["institution_uid"])
    end_insts = set(end_df["institution_uid"])

    # Turnover tracking
    common_insts = start_insts.intersection(end_insts)
    departed_insts = start_insts - end_insts
    new_entrant_insts = end_insts - start_insts

    # 3. Inner Merge on institution_uid
    merged = pd.merge(
        start_df[[
            "institution_uid", "institute_name_std", "state_std", "city_std",
            "rank", "score", "rank_label"
        ]],
        end_df[[
            "institution_uid", "institute_name_std", "state_std", "city_std",
            "rank", "score", "rank_label"
        ]],
        on="institution_uid",
        suffixes=("_start", "_end"),
    )

    if merged.empty:
        return {
            "success": True,
            "category": category,
            "start_year": start_year,
            "end_year": end_year,
            "gainers": [],
            "decliners": [],
            "metadata": build_analysis_metadata(
                query_type="rank_movement",
                calculation_method="start_rank - end_rank",
                records_considered=len(start_df) + len(end_df),
                valid_observations=0,
                category=category,
                years=[start_year, end_year],
                missing_data_info={
                    "start_year_total": len(start_df),
                    "end_year_total": len(end_df),
                    "common_count": 0,
                    "departed_count": len(departed_insts),
                    "new_entrants_count": len(new_entrant_insts),
                },
                comparability_status=comp_check.status,
                warnings=comp_check.warnings + ["No institutions with valid ranks found in both years."],
            )
        }

    # 4. Calculate Rank Movement
    merged["rank_improvement"] = merged["rank_start"] - merged["rank_end"]

    # 5. Extract Gainers and Decliners
    gainers_df = merged.sort_values(by=["rank_improvement", "rank_end"], ascending=[False, True])
    decliners_df = merged.sort_values(by=["rank_improvement", "rank_end"], ascending=[True, True])

    def serialize_records(rec_df: pd.DataFrame, n: int) -> List[Dict[str, Any]]:
        results = []
        for _, row in rec_df.head(n).iterrows():
            results.append({
                "institution_uid": str(row["institution_uid"]),
                "institute_name_std": str(row["institute_name_std_end"]),
                "state_std": str(row["state_std_end"]),
                "city_std": str(row["city_std_end"]),
                "start_year": start_year,
                "end_year": end_year,
                "start_rank": int(row["rank_start"]),
                "end_rank": int(row["rank_end"]),
                "rank_improvement": int(row["rank_improvement"]),
                "start_score": clean_numeric(row["score_start"]),
                "end_score": clean_numeric(row["score_end"]),
                "start_rank_label": str(row["rank_label_start"]) if pd.notna(row["rank_label_start"]) else None,
                "end_rank_label": str(row["rank_label_end"]) if pd.notna(row["rank_label_end"]) else None,
            })
        return results

    gainers = serialize_records(gainers_df, top_n) if movement_type in ("both", "improvement") else []
    decliners = serialize_records(decliners_df, top_n) if movement_type in ("both", "decline") else []

    metadata = build_analysis_metadata(
        query_type="rank_movement",
        calculation_method="start_rank - end_rank (positive = improvement, negative = decline)",
        records_considered=len(start_df) + len(end_df),
        valid_observations=len(merged),
        category=category,
        years=[start_year, end_year],
        missing_data_info={
            "start_year_institutions": len(start_df),
            "end_year_institutions": len(end_df),
            "tracked_paired_institutions": len(merged),
            "departed_institutions": len(departed_insts),
            "new_entrant_institutions": len(new_entrant_insts),
        },
        comparability_status=comp_check.status,
        warnings=comp_check.warnings,
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "start_year": start_year,
        "end_year": end_year,
        "state_filter": state,
        "tracked_institutions_count": len(merged),
        "gainers": gainers,
        "decliners": decliners,
        "metadata": metadata,
    }

