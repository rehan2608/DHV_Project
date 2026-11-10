"""
Rank Transition and Mobility Analysis across NIRF Editions (FUNCTION 9).
Tracks institutional movement between ordinal rank bands, computing transition matrices,
tier upgrades/downgrades, and entrant/departure dynamics.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import clean_numeric, build_analysis_metadata


DEFAULT_RANK_BANDS: List[Tuple[str, int, int]] = [
    ("Top 10", 1, 10),
    ("11–25", 11, 25),
    ("26–50", 26, 50),
    ("51–100", 51, 100),
    ("Below 100", 101, 10000),
]


def _assign_rank_band(rank: Optional[float], bands: List[Tuple[str, int, int]]) -> str:
    """Helper to map a numeric rank to a categorical band label."""
    if rank is None or pd.isna(rank):
        return "Unranked / Absent"
    r = float(rank)
    for label, low, high in bands:
        if low <= r <= high:
            return label
    return "Below 100"


def get_rank_transitions(
    category: str,
    start_year: int,
    end_year: int,
    custom_bands: Optional[List[Tuple[str, int, int]]] = None,
) -> Dict[str, Any]:
    """
    Analyzes how institutions transition across ranking tiers between two editions (FUNCTION 9).

    Args:
        category: Standardized NIRF category.
        start_year: Baseline assessment year.
        end_year: Follow-up assessment year.
        custom_bands: Optional list of tuples (label, min_rank, max_rank).

    Returns:
        Structured dictionary with transition matrix, tier mobility summary,
        Top-10 and Top-50 entry/exit rosters, and institution records.
    """
    loader = get_data_loader()
    df = loader.master_df
    validator = get_comparability_validator()

    comp_check = validator.validate_multi_year_comparison(category, [start_year, end_year])
    if not comp_check.is_comparable:
        return {
            "success": False,
            "error": f"Invalid comparison: {'; '.join(comp_check.errors)}",
            "metadata": build_analysis_metadata(
                query_type="rank_transitions",
                calculation_method="markovian_band_transitions",
                records_considered=0,
                valid_observations=0,
                category=category,
                years=[start_year, end_year],
            )
        }

    bands = custom_bands or DEFAULT_RANK_BANDS
    all_band_labels = [b[0] for b in bands] + ["Unranked / Absent"]

    cat_mask = df["category"].str.lower() == category.strip().lower()

    # Institutions active in either year
    start_sub = df[cat_mask & (df["year"] == start_year)].copy()
    end_sub = df[cat_mask & (df["year"] == end_year)].copy()

    all_uids = set(start_sub["institution_uid"]).union(set(end_sub["institution_uid"]))

    start_dict = {
        row["institution_uid"]: row for _, row in start_sub.iterrows()
    }
    end_dict = {
        row["institution_uid"]: row for _, row in end_sub.iterrows()
    }

    transitions: List[Dict[str, Any]] = []
    matrix_counts: Dict[str, Dict[str, int]] = {b1: {b2: 0 for b2 in all_band_labels} for b1 in all_band_labels}

    entered_top_10: List[Dict[str, Any]] = []
    left_top_10: List[Dict[str, Any]] = []
    entered_top_50: List[Dict[str, Any]] = []
    left_top_50: List[Dict[str, Any]] = []

    upward_count = 0
    downward_count = 0
    retained_count = 0
    exited_count = 0
    new_entrant_count = 0

    # Build band index mapping for ordinal comparison (lower index = better tier)
    tier_order = {b[0]: idx for idx, b in enumerate(bands)}
    tier_order["Unranked / Absent"] = len(bands)

    for uid in all_uids:
        s_row = start_dict.get(uid)
        e_row = end_dict.get(uid)

        name = str(e_row["institute_name_std"] if e_row is not None else s_row["institute_name_std"])
        state = str(e_row["state_std"] if e_row is not None else s_row["state_std"])

        s_rank = clean_numeric(s_row["rank"]) if s_row is not None else None
        e_rank = clean_numeric(e_row["rank"]) if e_row is not None else None

        s_band = _assign_rank_band(s_rank, bands)
        e_band = _assign_rank_band(e_rank, bands)

        matrix_counts[s_band][e_band] += 1

        # Determine mobility status
        s_tier = tier_order[s_band]
        e_tier = tier_order[e_band]

        if s_band == "Unranked / Absent" and e_band != "Unranked / Absent":
            mobility = "New Entrant"
            new_entrant_count += 1
        elif s_band != "Unranked / Absent" and e_band == "Unranked / Absent":
            mobility = "Exited Cohort"
            exited_count += 1
        elif e_tier < s_tier:
            mobility = "Upward Transition"
            upward_count += 1
        elif e_tier > s_tier:
            mobility = "Downward Transition"
            downward_count += 1
        else:
            mobility = "Retained Band"
            retained_count += 1

        record = {
            "institution_uid": uid,
            "institute_name_std": name,
            "state_std": state,
            "start_rank": s_rank,
            "end_rank": e_rank,
            "start_band": s_band,
            "end_band": e_band,
            "mobility": mobility,
        }
        transitions.append(record)

        # Track Top 10 and Top 50 dynamics
        is_start_top10 = s_rank is not None and s_rank <= 10
        is_end_top10 = e_rank is not None and e_rank <= 10
        if not is_start_top10 and is_end_top10:
            entered_top_10.append(record)
        elif is_start_top10 and not is_end_top10:
            left_top_10.append(record)

        is_start_top50 = s_rank is not None and s_rank <= 50
        is_end_top50 = e_rank is not None and e_rank <= 50
        if not is_start_top50 and is_end_top50:
            entered_top_50.append(record)
        elif is_start_top50 and not is_end_top50:
            left_top_50.append(record)

    total_tracked = len(all_uids)

    mobility_summary = {
        "total_institutions_tracked": total_tracked,
        "upward_transitions": upward_count,
        "downward_transitions": downward_count,
        "retained_same_band": retained_count,
        "cohort_exits": exited_count,
        "new_entrants": new_entrant_count,
        "upward_pct": round(upward_count / total_tracked * 100, 2) if total_tracked else 0,
        "retained_pct": round(retained_count / total_tracked * 100, 2) if total_tracked else 0,
        "downward_pct": round(downward_count / total_tracked * 100, 2) if total_tracked else 0,
    }

    metadata = build_analysis_metadata(
        query_type="rank_transitions",
        calculation_method="ordinal_tier_transition_matrix",
        records_considered=len(start_sub) + len(end_sub),
        valid_observations=total_tracked,
        category=category,
        years=[start_year, end_year],
        comparability_status=comp_check.status,
        warnings=comp_check.warnings,
        limitations=comp_check.notes,
    )

    return {
        "success": True,
        "category": category,
        "start_year": start_year,
        "end_year": end_year,
        "bands": [b[0] for b in bands],
        "mobility_summary": mobility_summary,
        "transition_matrix": matrix_counts,
        "entered_top_10": entered_top_10,
        "left_top_10": left_top_10,
        "entered_top_50": entered_top_50,
        "left_top_50": left_top_50,
        "institution_transitions": transitions,
        "metadata": metadata,
    }

