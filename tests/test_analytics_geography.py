"""
Unit tests for Geographic Analysis (FUNCTION 4).
"""

import pytest
from src.analytics.geography import get_geographic_analysis


def test_geographic_analysis_engineering_2025():
    res = get_geographic_analysis(
        category="Engineering",
        year=2025,
    )
    assert res["success"] is True
    assert res["total_states_represented"] > 10
    assert len(res["states_analysis"]) > 0

    top_state = res["states_analysis"][0]
    assert top_state["distinct_institutions"] > 0
    assert top_state["state"] in ["Tamil Nadu", "Maharashtra", "Karnataka", "Delhi", "Uttar Pradesh"]


def test_geographic_head_to_head_karnataka_tamil_nadu():
    res = get_geographic_analysis(
        category="Engineering",
        year=2025,
        states=["Karnataka", "Tamil Nadu"],
    )
    assert res["success"] is True
    assert res["head_to_head_comparison"] is not None
    compared = res["head_to_head_comparison"]["compared_states"]
    assert "Karnataka" in compared
    assert "Tamil Nadu" in compared


def test_geographic_multi_year_trend():
    res = get_geographic_analysis(
        category="Engineering",
        multi_year_trend=True,
    )
    assert res["success"] is True
    assert res["yearly_trajectory"] is not None
    assert "Karnataka" in res["yearly_trajectory"]
    assert 2017 in res["yearly_trajectory"]["Karnataka"]
    assert 2025 in res["yearly_trajectory"]["Karnataka"]

