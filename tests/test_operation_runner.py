"""
Unit tests for OperationRunner (Phase 4).
"""

import pytest
from src.query_engine.schemas import AnalyticalOperation
from src.execution.operation_runner import OperationRunner, get_operation_runner


def test_operation_runner_single_operation_success():
    runner = get_operation_runner()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2024,
        end_year=2025,
        states=["Karnataka"],
        top_n=3,
    )
    res = runner.run_operation(op)
    assert res.operation_id == "op_1"
    assert res.function_name == "get_rank_movement"
    assert res.status == "SUCCESS"
    assert res.data is not None
    assert "gainers" in res.data
    assert res.execution_duration_seconds > 0.0


def test_operation_runner_with_overrides():
    runner = get_operation_runner()
    # Predecessor provides institution_uids override
    op = AnalyticalOperation(
        operation_id="op_2",
        function_name="get_parameter_relationship",
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="tlr",
    )
    # Target IIT Madras (U-456), IIT Bombay (U-306), and IIT Delhi (I-1074)
    overrides = {"institution_uids": ["U-456", "U-306", "I-1074"]}
    res = runner.run_operation(op, overrides=overrides)
    assert res.status == "SUCCESS"
    assert res.data["sample_size"] == 3


def test_operation_runner_handles_failure_cleanly():
    runner = get_operation_runner()
    op = AnalyticalOperation(
        operation_id="op_fail",
        function_name="get_category_performance",
        category=None,  # Missing mandatory category causes clean ArgumentMappingError
        year=2025,
    )
    res = runner.run_operation(op)
    assert res.status == "FAILED"
    assert "category" in res.error_message.lower()
