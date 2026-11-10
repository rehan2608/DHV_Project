"""
Unit tests for ArgumentMapper (Phase 4).
"""

import pytest
from src.query_engine.schemas import AnalyticalOperation
from src.execution.argument_mapper import ArgumentMapper, get_argument_mapper
from src.execution.exceptions import ArgumentMappingError


def test_mapper_rank_movement():
    mapper = get_argument_mapper()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2020,
        end_year=2025,
        states=["Karnataka"],
        top_n=5,
        movement_type="improvement",
    )
    kwargs = mapper.map_arguments(op)
    assert kwargs["category"] == "Engineering"
    assert kwargs["start_year"] == 2020
    assert kwargs["end_year"] == 2025
    assert kwargs["state"] == "Karnataka"
    assert kwargs["top_n"] == 5
    assert kwargs["movement_type"] == "improvement"


def test_mapper_multidimensional_performance():
    mapper = get_argument_mapper()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_multidimensional_performance",
        category="Engineering",
        year=2025,
        institution_names=["IIT Madras", "IIT Bombay"],
        parameters=["rpc", "tlr"],
        top_n=2,
    )
    kwargs = mapper.map_arguments(op)
    assert kwargs["category"] == "Engineering"
    assert kwargs["year"] == 2025
    assert kwargs["institution_names"] == ["IIT Madras", "IIT Bombay"]
    assert kwargs["parameters"] == ["rpc", "tlr"]
    assert kwargs["top_n"] == 2


def test_mapper_parameter_relationship_param_fallback():
    mapper = get_argument_mapper()
    # parameters list should fallback into param_x and param_y
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_parameter_relationship",
        category="Engineering",
        year=2025,
        parameters=["rpc", "tlr"],
    )
    kwargs = mapper.map_arguments(op)
    assert kwargs["param_x"] == "rpc"
    assert kwargs["param_y"] == "tlr"


def test_mapper_missing_category_raises():
    mapper = get_argument_mapper()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        year=2025,
        category=None,
    )
    with pytest.raises(ArgumentMappingError):
        mapper.map_arguments(op)

