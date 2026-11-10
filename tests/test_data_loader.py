"""
Unit tests for NIRFDataLoader.
"""

import pytest
import pandas as pd
from src.data.loader import NIRFDataLoader, get_data_loader


def test_loader_singleton():
    loader1 = get_data_loader()
    loader2 = NIRFDataLoader()
    assert loader1 is loader2


def test_master_dataset_loaded():
    loader = get_data_loader()
    df = loader.master_df
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 6980
    assert len(df.columns) == 40


def test_comparability_rules_loaded():
    loader = get_data_loader()
    rules = loader.comparability_df
    assert isinstance(rules, pd.DataFrame)
    assert len(rules) == 103
    assert "comparability_status" in rules.columns


def test_available_dimensions():
    loader = get_data_loader()
    years = loader.get_available_years()
    categories = loader.get_available_categories()
    states = loader.get_available_states()

    assert years == list(range(2017, 2026))
    assert "Engineering" in categories
    assert "Overall" in categories
    assert "Research Institutions" in categories
    assert "Karnataka" in states
    assert "Tamil Nadu" in states


def test_filter_records():
    loader = get_data_loader()
    eng_karnataka_2025 = loader.filter_records(
        category="Engineering",
        years=[2025],
        states=["Karnataka"]
    )
    assert not eng_karnataka_2025.empty
    assert (eng_karnataka_2025["category"] == "Engineering").all()
    assert (eng_karnataka_2025["year"] == 2025).all()
    assert (eng_karnataka_2025["state_std"] == "Karnataka").all()


def test_search_institutions():
    loader = get_data_loader()
    results = loader.search_institutions("Indian Institute of Science", limit=5)
    assert not results.empty
    assert "institution_uid" in results.columns
    assert any("Indian Institute of Science" in name for name in results["institute_name_std"])

