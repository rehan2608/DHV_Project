"""
Unit tests for Category and Multidimensional Performance Analysis (FUNCTIONS 3 & 7).
"""

import pytest
from src.analytics.performance import get_category_performance, get_multidimensional_performance


def test_category_performance_engineering_2025():
    res = get_category_performance(
        category="Engineering",
        year=2025,
        top_n=10,
    )
    assert res["success"] is True
    assert res["scores_available"] is True
    assert res["total_institutions"] >= 100
    assert len(res["institutions"]) == 10

    # Scores summary
    ss = res["score_summary"]
    assert ss is not None
    assert ss["min"] <= ss["median"] <= ss["max"]

    # Parameter summaries
    assert "tlr" in res["parameter_summary"]
    assert "rpc" in res["parameter_summary"]


def test_category_performance_rank_only_innovation():
    # Innovation publishes rank order only
    res = get_category_performance(
        category="Innovation",
        year=2025,
    )
    assert res["success"] is True
    assert res["scores_available"] is False
    assert res["score_summary"] is None


def test_multidimensional_performance_iit_comparison():
    res = get_multidimensional_performance(
        category="Engineering",
        year=2025,
        institution_names=["IIT Madras", "IIT Bombay", "IIT Delhi"],
    )
    assert res["success"] is True
    assert len(res["profiles"]) >= 3

    for p in res["profiles"]:
        assert p["strongest_parameter"] is not None
        assert p["weakest_parameter"] is not None
        assert p["research_vs_teaching_gap"] is not None

