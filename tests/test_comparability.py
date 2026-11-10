"""
Unit tests for ComparabilityValidator.
"""

import pytest
from src.data.comparability import get_comparability_validator


def test_engineering_longitudinal_comparability():
    validator = get_comparability_validator()
    res = validator.validate_multi_year_comparison(
        category="Engineering",
        years=[2020, 2025],
        requested_metrics=["score", "tlr", "rpc"]
    )
    assert res.is_comparable is True
    assert res.metric_schema == "Standard (5 Parameters)"


def test_research_institution_schema_blocking():
    validator = get_comparability_validator()
    # Research institutions uses SFC, QNR, QLR; TLR must be blocked
    res = validator.validate_single_cohort(
        category="Research Institutions",
        year=2024,
        requested_metrics=["tlr"]
    )
    assert res.is_comparable is False
    assert any("Research Specific Schema" in err for err in res.errors)

    # Valid research metric should pass
    res_valid = validator.validate_single_cohort(
        category="Research Institutions",
        year=2024,
        requested_metrics=["research_sfc", "research_qnr"]
    )
    assert res_valid.is_comparable is True


def test_rank_only_category_blocks_score_calculation():
    validator = get_comparability_validator()
    # Innovation is Rank-Only; score comparison must be blocked
    res = validator.validate_multi_year_comparison(
        category="Innovation",
        years=[2024, 2025],
        requested_metrics=["score"]
    )
    assert res.is_comparable is False
    assert any("Rank Only" in err for err in res.errors)


def test_invalid_start_year_blocking():
    validator = get_comparability_validator()
    # Research Institutions started in 2021; year 2019 must fail
    res = validator.validate_multi_year_comparison(
        category="Research Institutions",
        years=[2019, 2025]
    )
    assert res.is_comparable is False
    assert any("2019" in err for err in res.errors)


def test_cohort_depth_expansion_caution():
    validator = get_comparability_validator()
    # Management published Top 75 in 2020, expanded to Top 100 in 2025
    res_2020 = validator.validate_multi_year_comparison(
        category="Management",
        years=[2020, 2025],
        requested_metrics=["score"]
    )
    assert res_2020.is_comparable is True
    assert "Caution" in res_2020.status
    assert res_2020.recommended_rank_cutoff == 75
    assert any("expanded" in w.lower() for w in res_2020.warnings)

    # Management published Top 50 in 2017, expanded to Top 100 in 2025
    res_2017 = validator.validate_multi_year_comparison(
        category="Management",
        years=[2017, 2025],
        requested_metrics=["score"]
    )
    assert res_2017.recommended_rank_cutoff == 50
