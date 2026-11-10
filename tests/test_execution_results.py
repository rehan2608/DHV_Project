"""
Unit tests for Result Schema and JSON Serialization (Phase 4).
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import pytest

from src.execution.result_schema import (
    clean_for_json,
    ExecutionResult,
    OperationResult,
    ExecutionMetadata,
)


def test_clean_for_json_nan_and_inf():
    dirty = {
        "nan_val": float("nan"),
        "inf_val": float("inf"),
        "neg_inf": float("-inf"),
        "np_nan": np.nan,
        "valid_float": 42.5,
    }
    cleaned = clean_for_json(dirty)
    assert cleaned["nan_val"] is None
    assert cleaned["inf_val"] is None
    assert cleaned["neg_inf"] is None
    assert cleaned["np_nan"] is None
    assert cleaned["valid_float"] == 42.5

    # Assert strict JSON encoding does not crash on allow_nan=False
    serialized = json.dumps(cleaned, allow_nan=False)
    assert "null" in serialized


def test_clean_for_json_numpy_primitives():
    dirty = {
        "np_int": np.int64(100),
        "np_float": np.float64(3.14159),
        "np_bool": np.bool_(True),
        "np_arr": np.array([1, 2, 3]),
    }
    cleaned = clean_for_json(dirty)
    assert isinstance(cleaned["np_int"], int)
    assert isinstance(cleaned["np_float"], float)
    assert isinstance(cleaned["np_bool"], bool)
    assert cleaned["np_arr"] == [1, 2, 3]


def test_clean_for_json_dataframe_and_series():
    df = pd.DataFrame({
        "rank": [1, 2],
        "score": [85.5, np.nan],
    })
    cleaned_df = clean_for_json(df)
    assert isinstance(cleaned_df, list)
    assert len(cleaned_df) == 2
    assert cleaned_df[1]["score"] is None

    s = pd.Series([10, 20], index=["a", "b"])
    cleaned_s = clean_for_json(s)
    assert cleaned_s == {"a": 10, "b": 20}


def test_execution_result_to_json():
    op_res = OperationResult(
        operation_id="op_1",
        function_name="get_category_performance",
        status="SUCCESS",
        data={"mean_score": 62.4, "nan_test": float("nan")},
        execution_duration_seconds=0.045,
    )
    exec_res = ExecutionResult(
        execution_id="exec_test_123",
        query_id="qp_test_123",
        original_question="Test query",
        status="SUCCESS",
        query_type="category_performance",
        operations=[op_res],
        validation_status="VALID",
        metadata=ExecutionMetadata(category="Engineering", year=2025),
    )
    json_str = exec_res.to_json(indent=2)
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["execution_id"] == "exec_test_123"
    assert parsed["operations"][0]["data"]["nan_test"] is None

