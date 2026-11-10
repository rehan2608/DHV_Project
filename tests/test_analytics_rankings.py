"""
Unit tests for Rank Movement Analysis (FUNCTION 2).
"""

import pytest
from src.analytics.rankings import get_rank_movement


def test_rank_movement_engineering_karnataka():
    res = get_rank_movement(
        category="Engineering",
        start_year=2020,
        end_year=2025,
        state="Karnataka",
        top_n=5,
    )
    assert res["success"] is True
    assert res["category"] == "Engineering"
    assert res["start_year"] == 2020
    assert res["end_year"] == 2025
    assert len(res["gainers"]) > 0

    # Verify positive rank improvement formula: start_rank - end_rank
    for g in res["gainers"]:
        expected_diff = g["start_rank"] - g["end_rank"]
        assert g["rank_improvement"] == expected_diff
        assert g["state_std"] == "Karnataka"


def test_rank_movement_decliners():
    res = get_rank_movement(
        category="Engineering",
        start_year=2020,
        end_year=2025,
        top_n=5,
        movement_type="decline",
    )
    assert res["success"] is True
    assert len(res["decliners"]) > 0
    for d in res["decliners"]:
        expected_diff = d["start_rank"] - d["end_rank"]
        assert d["rank_improvement"] == expected_diff
        assert d["rank_improvement"] <= 0


def test_rank_movement_invalid_category_year():
    # Research Institutions was not available in 2018
    res = get_rank_movement(
        category="Research Institutions",
        start_year=2018,
        end_year=2025,
    )
    assert res["success"] is False
    assert "invalid" in res["error"].lower()

