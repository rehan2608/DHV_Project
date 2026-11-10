"""
Unit tests for Institution Trend Analysis (FUNCTION 1).
"""

import pytest
from src.analytics.trends import get_institution_trend


def test_institution_trend_iit_madras():
    res = get_institution_trend(
        institution_id_or_name="Indian Institute of Technology Madras",
        category="Engineering",
        start_year=2020,
        end_year=2025,
    )
    assert res["success"] is True
    assert res["category"] == "Engineering"
    assert res["start_year"] == 2020
    assert res["end_year"] == 2025
    assert len(res["chronological_trajectory"]) == 6

    # IIT Madras has maintained Rank 1 in Engineering
    for entry in res["chronological_trajectory"]:
        assert entry["is_observed"] is True
        assert entry["rank"] == 1
        assert "rpc" in entry["parameters"]
        assert "tlr" in entry["parameters"]


def test_institution_trend_uid_lookup():
    # Use exact UID
    res = get_institution_trend(
        institution_id_or_name="IR-E-U-0456",
        category="Engineering",
        start_year=2024,
        end_year=2025,
    )
    assert res["success"] is True
    assert "IIT" in res["institute_name_std"] or "Institute" in res["institute_name_std"]


def test_institution_trend_missing_years():
    # An institution that entered ranking later or wasn't in 2017
    res = get_institution_trend(
        institution_id_or_name="Indian Institute of Technology Dharwad",
        category="Engineering",
        start_year=2017,
        end_year=2025,
    )
    assert res["success"] is True
    # In earlier years IIT Dharwad was not ranked
    obs_map = {r["year"]: r["is_observed"] for r in res["chronological_trajectory"]}
    assert obs_map[2017] is False
    assert 2017 in res["metadata"]["missing_data_info"]["missing_years"]


def test_institution_trend_not_found():
    res = get_institution_trend(
        institution_id_or_name="NonExistentFictionalInstitute123",
        category="Engineering",
    )
    assert res["success"] is False
    assert "not found" in res["error"].lower()

