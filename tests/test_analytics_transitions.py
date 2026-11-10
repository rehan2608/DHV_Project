"""
Unit tests for Rank Transitions Analysis (FUNCTION 9).
"""

import pytest
from src.analytics.transitions import get_rank_transitions


def test_rank_transitions_overall_2020_2025():
    res = get_rank_transitions(
        category="Overall",
        start_year=2020,
        end_year=2025,
    )
    assert res["success"] is True
    assert res["start_year"] == 2020
    assert res["end_year"] == 2025

    summary = res["mobility_summary"]
    assert summary["total_institutions_tracked"] >= 100
    assert summary["retained_same_band"] > 0
    assert "Top 10" in res["transition_matrix"]
    assert len(res["institution_transitions"]) == summary["total_institutions_tracked"]


def test_rank_transitions_top10_stability():
    res = get_rank_transitions(
        category="Engineering",
        start_year=2024,
        end_year=2025,
    )
    assert res["success"] is True
    # Most top 10 engineering institutions remain in Top 10 between consecutive years
    matrix = res["transition_matrix"]
    assert matrix["Top 10"]["Top 10"] >= 8

