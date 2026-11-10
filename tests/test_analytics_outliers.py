"""
Unit tests for Outlier and Volatility Analysis (FUNCTION 10).
"""

import pytest
from src.analytics.outliers import get_outlier_analysis


def test_outlier_analysis_iqr():
    res = get_outlier_analysis(
        category="Engineering",
        year=2025,
        metric="score",
        method="iqr",
        threshold=1.5,
    )
    assert res["success"] is True
    assert res["detection_method"] == "iqr"
    assert "metric_outliers" in res
    assert "parameter_divergence_outliers" in res


def test_outlier_analysis_z_score():
    res = get_outlier_analysis(
        category="Engineering",
        year=2025,
        metric="rpc",
        method="z_score",
        threshold=2.0,
    )
    assert res["success"] is True
    assert res["detection_method"] == "z_score"


def test_outlier_analysis_volatility_lookback():
    res = get_outlier_analysis(
        category="Engineering",
        year=2025,
        lookback_years=[2020, 2021, 2022, 2023, 2024, 2025],
    )
    assert res["success"] is True
    assert res["longitudinal_rank_volatility"] is not None
    assert len(res["longitudinal_rank_volatility"]) > 0

