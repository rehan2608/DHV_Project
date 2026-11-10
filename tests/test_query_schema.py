"""
Unit tests for Pydantic Query Plan Schemas (Phase 3).
"""

import pytest
from pydantic import ValidationError
from src.query_engine.schemas import (
    QueryPlan,
    AnalyticalOperation,
    ConversationContext,
    VisualizationPreference,
)


def test_valid_query_plan_instantiation():
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2020,
        end_year=2025,
        states=["Karnataka"],
        top_n=10,
    )
    plan = QueryPlan(
        original_question="Which engineering colleges in Karnataka improved most since 2020?",
        query_type="rank_movement",
        analytical_intent="Find top rank gainers in Karnataka Engineering",
        operations=[op],
    )
    assert plan.query_type == "rank_movement"
    assert len(plan.operations) == 1
    assert plan.operations[0].function_name == "get_rank_movement"
    assert plan.operations[0].category == "Engineering"


def test_invalid_function_name_raises():
    with pytest.raises(ValidationError):
        AnalyticalOperation(
            operation_id="op_1",
            function_name="arbitrary_unsupported_function",  # Not in allowed literal
        )


def test_invalid_query_type_raises():
    with pytest.raises(ValidationError):
        QueryPlan(
            original_question="Test question",
            query_type="invalid_unknown_query_type",  # Not in allowed literal
            analytical_intent="Test intent",
        )


def test_multi_operation_plan():
    op1 = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        parameters=["rpc"],
        top_n=10,
    )
    op2 = AnalyticalOperation(
        operation_id="op_2",
        function_name="get_parameter_relationship",
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="tlr",
        depends_on="op_1",
    )
    plan = QueryPlan(
        original_question="Find top 10 engineering institutions by research, then analyze relationship between research and teaching.",
        query_type="multi_operation",
        analytical_intent="Top research institutions and RPC-TLR bivariate relationship",
        operations=[op1, op2],
    )
    assert plan.query_type == "multi_operation"
    assert len(plan.operations) == 2
    assert plan.operations[1].depends_on == "op_1"


def test_conversation_context_serialization():
    ctx = ConversationContext(
        previous_category="Engineering",
        previous_year=2025,
        previous_states=["Karnataka"],
        previous_top_n=10,
        inherited_fields=["category", "year"],
        modified_fields=["states"],
    )
    dumped = ctx.model_dump()
    assert dumped["previous_category"] == "Engineering"
    assert "Karnataka" in dumped["previous_states"]
    loaded = ConversationContext.model_validate(dumped)
    assert loaded.previous_year == 2025

