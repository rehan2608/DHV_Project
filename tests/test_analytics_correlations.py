"""
Unit tests for Parameter Correlation and Relationship Analysis (FUNCTIONS 5 & 6).
"""

import pytest
from src.analytics.correlations import get_parameter_correlation, get_parameter_relationship


def test_parameter_correlation_engineering_2025():
    res = get_parameter_correlation(
        category="Engineering",
        year=2025,
        parameters=["tlr", "rpc", "go", "oi", "perception"],
    )
    assert res["success"] is True
    assert res["pearson_matrix"] is not None
    assert res["spearman_matrix"] is not None
    assert res["pearson_matrix"]["tlr"]["tlr"] == 1.0
    assert res["strongest_positive_correlation"] is not None
    assert "disclaimer" in res


def test_parameter_relationship_rpc_vs_tlr():
    res = get_parameter_relationship(
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="tlr",
    )
    assert res["success"] is True
    assert res["sample_size"] >= 100
    assert "slope" in res["regression"]
    assert "r_squared" in res["regression"]
    assert len(res["points"]) >= 100
    assert len(res["trendline"]) == 2
    assert "high_x_low_y" in res["quadrant_counts"]


def test_parameter_correlation_rank_only_fails():
    res = get_parameter_correlation(
        category="Innovation",
        year=2025,
    )
    assert res["success"] is False
    assert "rank-only" in res["error"].lower()

