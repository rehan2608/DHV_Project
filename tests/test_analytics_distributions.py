"""
Unit tests for Score and Parameter Distribution Analysis (FUNCTION 8).
"""

import pytest
from src.analytics.distributions import get_score_distribution


def test_score_distribution_engineering_2025():
    res = get_score_distribution(
        category="Engineering",
        year=2025,
        metric="score",
        bins_count=10,
    )
    assert res["success"] is True
    stats = res["statistics"]
    assert stats["sample_size"] >= 100
    assert stats["min"] <= stats["median"] <= stats["max"]
    assert stats["q1_25th_percentile"] <= stats["q3_75th_percentile"]
    assert stats["iqr"] == round(stats["q3_75th_percentile"] - stats["q1_25th_percentile"], 2)
    assert len(res["histogram_bins"]) == 10


def test_score_distribution_rank_only_fails():
    res = get_score_distribution(
        category="Innovation",
        year=2025,
        metric="score",
    )
    assert res["success"] is False
    assert "invalid" in res["error"].lower() or "not available" in res["error"].lower()

