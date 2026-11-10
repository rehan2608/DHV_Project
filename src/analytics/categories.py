"""
Category Evolution Analysis for NIRF Historical Tracking.
Calculates the longitudinal evolution, availability, introductions, and counts
of NIRF institutional categories across editions from 2017 to 2025.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from src.config import VALID_YEARS
from src.data.loader import get_data_loader
from src.analytics.utils import build_analysis_metadata


def get_category_evolution(
    start_year: Optional[int] = 2017,
    end_year: Optional[int] = 2025,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes the longitudinal evolution of NIRF institutional categories.

    Calculates:
    1. Distinct institutional categories for each year.
    2. Number of categories for each year.
    3. Categories newly appearing in each year (first observed in dataset).
    4. Categories no longer appearing in subsequent years (discontinued).
    5. Categories present throughout the entire analyzed period (persistent).
    6. First observed year and last observed year for each category.
    7. Overall net expansion and category presence timeline.

    Args:
        start_year: Starting edition year (default 2017).
        end_year: Ending edition year (default 2025).
        category: Optional single category filter to inspect specific trajectory.

    Returns:
        Structured dictionary containing year-by-year counts, new introductions,
        persistent categories, and dataset provenance notes.
    """
    loader = get_data_loader()
    df = loader.master_df

    # Validate years
    min_dataset_year = int(df["year"].min())
    max_dataset_year = int(df["year"].max())

    sy = int(start_year) if start_year is not None else min_dataset_year
    ey = int(end_year) if end_year is not None else max_dataset_year

    if sy > ey:
        return {
            "success": False,
            "error": f"start_year ({sy}) cannot be greater than end_year ({ey}).",
            "metadata": build_analysis_metadata(
                query_type="category_evolution",
                calculation_method="dataset_category_census",
                records_considered=0,
                valid_observations=0,
                years=[sy, ey],
                comparability_status="Invalid Temporal Range",
            ),
        }

    # Filter dataset to available span
    sub_df = df[(df["year"] >= sy) & (df["year"] <= ey)]
    years = sorted([int(y) for y in sub_df["year"].unique()])

    if not years:
        return {
            "success": False,
            "error": f"No data available between {sy} and {ey}.",
            "metadata": build_analysis_metadata(
                query_type="category_evolution",
                calculation_method="dataset_category_census",
                records_considered=0,
                valid_observations=0,
                years=[sy, ey],
            ),
        }

    # Global first/last appearance across the entire master dataset
    all_dataset_cats = sorted(df["category"].dropna().unique())
    global_first_observed: Dict[str, int] = {}
    global_last_observed: Dict[str, int] = {}
    for cat_name in all_dataset_cats:
        c_years = sorted([int(y) for y in df[df["category"] == cat_name]["year"].unique()])
        global_first_observed[cat_name] = c_years[0]
        global_last_observed[cat_name] = c_years[-1]

    # Map categories by year within [sy, ey]
    year_to_cats: Dict[int, List[str]] = {}
    year_to_inst_count: Dict[int, int] = {}
    for y in years:
        year_rows = sub_df[sub_df["year"] == y]
        cats_in_y = sorted(year_rows["category"].dropna().unique().tolist())
        year_to_cats[y] = cats_in_y
        year_to_inst_count[y] = len(year_rows)

    all_window_cats = sorted(list({c for cats in year_to_cats.values() for c in cats}))

    # Build yearly metrics
    yearly_metrics: List[Dict[str, Any]] = []
    seen_in_window = set()
    for y in years:
        current_cats = set(year_to_cats[y])
        new_in_window = sorted([c for c in current_cats if c not in seen_in_window])
        seen_in_window.update(current_cats)

        # Discontinued compared to immediately preceding year
        if yearly_metrics:
            prev_cats = set(yearly_metrics[-1]["categories"])
            discontinued_from_prev = sorted(list(prev_cats - current_cats))
        else:
            discontinued_from_prev = []

        yearly_metrics.append({
            "year": y,
            "category_count": len(current_cats),
            "categories": sorted(list(current_cats)),
            "new_categories": new_in_window,
            "new_categories_count": len(new_in_window),
            "discontinued_categories": discontinued_from_prev,
            "institutions_ranked_count": year_to_inst_count[y],
        })

    # Persistent categories: present in every single year in the queried range
    persistent_categories = sorted([
        c for c in all_window_cats if all(c in year_to_cats[y] for y in years)
    ])

    # Discontinued categories: present earlier in range, but absent in end_year
    discontinued_by_end = sorted([
        c for c in all_window_cats if c in year_to_cats[years[0]] and c not in year_to_cats[years[-1]]
    ])
    all_discontinued = sorted([
        c for c in all_window_cats if c not in year_to_cats[years[-1]]
    ])

    # Detailed category records
    category_details: Dict[str, Dict[str, Any]] = {}
    for c in all_window_cats:
        c_years_window = [y for y in years if c in year_to_cats[y]]
        c_inst_counts = {}
        for y in c_years_window:
            cnt = len(sub_df[(sub_df["year"] == y) & (sub_df["category"] == c)])
            c_inst_counts[y] = cnt

        category_details[c] = {
            "category": c,
            "first_observed_year": global_first_observed[c],
            "last_observed_year": global_last_observed[c],
            "years_present_in_range": c_years_window,
            "total_years_in_range": len(c_years_window),
            "is_persistent": c in persistent_categories,
            "is_discontinued": c in all_discontinued,
            "institution_counts_by_year": c_inst_counts,
        }

    # Summary metrics
    start_count = yearly_metrics[0]["category_count"]
    end_count = yearly_metrics[-1]["category_count"]
    net_change = end_count - start_count

    evolution_summary = {
        "start_year": sy,
        "end_year": ey,
        "start_year_category_count": start_count,
        "end_year_category_count": end_count,
        "net_category_growth": net_change,
        "total_unique_categories_observed": len(all_window_cats),
        "persistent_categories_count": len(persistent_categories),
        "discontinued_categories_count": len(all_discontinued),
        "summary_text": (
            f"NIRF institutional categories expanded from {start_count} categories in {sy} to {end_count} categories in {ey} "
            f"(net growth of {net_change} categories). A total of {len(all_window_cats)} unique categories are observed across this period, "
            f"with {len(persistent_categories)} persistent categories appearing in every evaluated edition."
        ),
    }

    # Optional single-category focus
    target_category_info = None
    if category:
        cat_match = None
        c_lower = category.strip().lower()
        for cand in all_window_cats:
            if cand.lower() == c_lower or c_lower in cand.lower():
                cat_match = cand
                break
        if cat_match:
            target_category_info = category_details.get(cat_match)

    metadata = build_analysis_metadata(
        query_type="category_evolution",
        calculation_method="dataset_category_census",
        records_considered=len(sub_df),
        valid_observations=len(sub_df),
        years=years,
        comparability_status="Fully Comparable",
        warnings=[
            "First appearance in the dataset reflects data availability in the NIRF clean dataset and "
            "should not be assumed as the official gazette introduction date unless corroborated by Ministry notifications."
        ],
    )

    return {
        "success": True,
        "start_year": sy,
        "end_year": ey,
        "years": years,
        "yearly_metrics": yearly_metrics,
        "all_categories": all_window_cats,
        "persistent_categories": persistent_categories,
        "discontinued_categories": all_discontinued,
        "category_details": category_details,
        "target_category_info": target_category_info,
        "evolution_summary": evolution_summary,
        "notes": (
            "First appearance in the dataset reflects data availability in the NIRF clean dataset and "
            "distinguishes first observed appearance from official Ministry introduction."
        ),
        "metadata": metadata,
    }
