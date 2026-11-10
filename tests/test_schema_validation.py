"""
Unit tests for SchemaValidator and data integrity.
"""

import pytest
import pandas as pd
from src.data.loader import get_data_loader
from src.data.schema import SchemaValidator, EXPECTED_COLUMNS, PRIMARY_KEY


def test_schema_validation_passes():
    loader = get_data_loader()
    df = loader.master_df
    report = SchemaValidator.validate_dataset(df)

    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.total_rows == 6980
    assert report.total_columns == 40


def test_primary_key_uniqueness():
    loader = get_data_loader()
    df = loader.master_df
    dups = df.duplicated(subset=PRIMARY_KEY, keep=False)
    assert dups.sum() == 0, f"Found {dups.sum()} duplicate primary keys"


def test_expected_columns_complete():
    loader = get_data_loader()
    df = loader.master_df
    for col in EXPECTED_COLUMNS:
        assert col in df.columns, f"Expected column missing: {col}"


def test_mandatory_columns_non_null():
    loader = get_data_loader()
    df = loader.master_df
    mandatory = ["year", "category", "institution_uid", "institute_name_std", "state_std", "city_std"]
    for col in mandatory:
        assert df[col].isnull().sum() == 0, f"Mandatory column '{col}' has unexpected nulls"


def test_metric_bounds():
    loader = get_data_loader()
    df = loader.master_df
    metrics = ["score", "tlr", "rpc", "go", "oi", "perception"]
    for m in metrics:
        valid_vals = df[m].dropna()
        assert (valid_vals >= 0.0).all() and (valid_vals <= 100.0).all(), f"Values out of bounds in {m}"


def test_schema_validator_catches_corruption():
    loader = get_data_loader()
    corrupt_df = loader.master_df.copy()
    # Corrupt a mandatory column
    corrupt_df.loc[0, "year"] = 1990  # invalid year
    corrupt_df.loc[1, "institution_uid"] = None  # null primary key

    report = SchemaValidator.validate_dataset(corrupt_df)
    assert report.is_valid is False
    assert len(report.errors) >= 2

