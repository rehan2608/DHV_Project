"""
Unit tests for QueryValidator (Phase 3).
"""

import pytest
from src.query_engine.schemas import (
    QueryPlan,
    AnalyticalOperation,
    VisualizationPreference,
)
from src.query_engine.validator import QueryValidator, get_query_validator


def test_validator_valid_rank_movement():
    validator = get_query_validator()
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
        original_question="Rank gainers in Karnataka Engineering",
        query_type="rank_movement",
        analytical_intent="Find rank movement",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is True
    assert result.status in ("VALID", "VALID_WITH_WARNINGS")
    assert len(result.errors) == 0
    assert "Karnataka" in result.resolved_entities["states"]


def test_validator_invalid_category():
    validator = get_query_validator()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="FictionalSpaceEngineering",
        year=2025,
    )
    plan = QueryPlan(
        original_question="Category performance in space engineering",
        query_type="category_performance",
        analytical_intent="Analyze category",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is False
    assert result.status == "INVALID"
    assert any("not a valid NIRF category" in e for e in result.errors)


def test_validator_comparability_research_institution_schema():
    validator = get_query_validator()
    # Research Institutions does not support TLR
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Research Institutions",
        year=2024,
        parameters=["tlr"],
    )
    plan = QueryPlan(
        original_question="TLR in research institutions",
        query_type="category_performance",
        analytical_intent="Analyze research institutions TLR",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is False
    assert any("Research Specific Schema" in e for e in result.errors)


def test_validator_rank_only_score_distribution_blocked():
    validator = get_query_validator()
    # Innovation is Rank-Only; score distribution must fail comparability
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_score_distribution",
        category="Innovation",
        year=2025,
        metric="score",
    )
    plan = QueryPlan(
        original_question="Score distribution in Innovation",
        query_type="score_distribution",
        analytical_intent="Distribute scores",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is False
    assert any("Rank-Order Only" in e or "score is NOT available" in e for e in result.errors)


def test_validator_logical_year_order_reversed():
    validator = get_query_validator()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2025,
        end_year=2020,  # Invalid: start > end
    )
    plan = QueryPlan(
        original_question="Backwards rank movement",
        query_type="rank_movement",
        analytical_intent="Backwards test",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is False
    assert any("cannot be greater than end year" in e for e in result.errors)


def test_validator_parameter_relationship_identical_params():
    validator = get_query_validator()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_parameter_relationship",
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="rpc",  # Invalid: identical
    )
    plan = QueryPlan(
        original_question="Relationship of rpc with rpc",
        query_type="parameter_relationship",
        analytical_intent="Self-relationship",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is False
    assert any("must be distinct" in e for e in result.errors)


def test_validator_missing_category_infers_or_defaults():
    validator = get_query_validator()
    # Missing category for institution trend should infer/default and pass validation
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_institution_trend",
        category=None,
        institution_names=["IIT Bombay"],
        start_year=2017,
        end_year=2025,
    )
    plan = QueryPlan(
        original_question="tell me about IIT bombay",
        query_type="institution_trend",
        analytical_intent="Track IIT Bombay",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is True
    assert op.category == "Overall"
    assert op.applied_defaults.get("category") == "Overall"


def test_validator_category_alias_research_to_research_institutions():
    validator = get_query_validator()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Research",
        year=2025,
    )
    plan = QueryPlan(
        original_question="how many reserach instituion in 2025",
        query_type="category_performance",
        analytical_intent="Count research institutions in 2025",
        operations=[op],
    )
    result = validator.validate(plan)
    assert result.is_valid is True
    assert op.category == "Research Institutions"
    assert op.applied_defaults.get("category") == "Research Institutions"



