"""
Integration and End-to-End tests for QueryExecutor (Phase 4).
Tests revalidation, multi-operation sequencing, dependency passing, error isolation,
and end-to-end execution of the four benchmark query plans.
"""

import pytest
from src.query_engine.schemas import QueryPlan, AnalyticalOperation
from src.execution.executor import QueryExecutor, get_query_executor


def test_executor_single_operation_success():
    executor = get_query_executor()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2020,
        end_year=2025,
        states=["Karnataka"],
        top_n=5,
    )
    plan = QueryPlan(
        original_question="Engineering rank gainers in Karnataka",
        query_type="rank_movement",
        analytical_intent="Identify rank gainers",
        operations=[op],
    )
    result = executor.execute(plan)

    assert result.status == "SUCCESS"
    assert len(result.operations) == 1
    assert result.operations[0].status == "SUCCESS"
    assert result.combined_result is not None
    assert "gainers" in result.combined_result
    assert result.metadata.total_duration_seconds > 0.0


def test_executor_revalidation_rejects_invalid_plan():
    executor = get_query_executor()
    op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="NonExistentCategoryXYZ",  # Invalid
        year=2025,
    )
    plan = QueryPlan(
        original_question="Invalid category test",
        query_type="category_performance",
        analytical_intent="Test rejection",
        operations=[op],
    )
    result = executor.execute(plan)

    assert result.status == "REJECTED"
    assert result.validation_status == "INVALID"
    assert len(result.errors) > 0
    assert len(result.operations) == 0  # Analytics was never invoked!


def test_executor_multi_operation_dependency_passing():
    executor = get_query_executor()
    # Op 1: Get top 5 engineering institutions by research in 2025
    op1 = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        parameters=["rpc"],
        top_n=5,
    )
    # Op 2: Analyze RPC vs TLR relationship specifically for the top 5 from Op 1
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
        original_question="Find top 5 engineering institutions, then analyze their RPC vs TLR relationship.",
        query_type="multi_operation",
        analytical_intent="Top research cohort and its parameter relationship",
        operations=[op1, op2],
    )
    result = executor.execute(plan)

    assert result.status == "SUCCESS"
    assert len(result.operations) == 2
    op1_res = result.operations[0]
    op2_res = result.operations[1]

    assert op1_res.status == "SUCCESS"
    assert op2_res.status == "SUCCESS"

    # Op 2 must have received the 5 institutions passed from Op 1!
    assert op2_res.data["sample_size"] == 5


def test_executor_circular_dependency_detected():
    executor = get_query_executor()
    op1 = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        depends_on="op_2",  # Cycle
    )
    op2 = AnalyticalOperation(
        operation_id="op_2",
        function_name="get_score_distribution",
        category="Engineering",
        year=2025,
        depends_on="op_1",  # Cycle
    )
    plan = QueryPlan(
        original_question="Circular test",
        query_type="multi_operation",
        analytical_intent="Cycle",
        operations=[op1, op2],
    )
    result = executor.execute(plan)

    assert result.status == "FAILED"
    assert any("circular" in err.lower() for err in result.errors)


def test_executor_skipped_dependency_when_predecessor_fails():
    executor = get_query_executor()
    # Op 1 fails comparability check
    op1 = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Research Institutions",
        year=2024,
        parameters=["tlr"],  # Invalid parameter for research institutions
    )
    op2 = AnalyticalOperation(
        operation_id="op_2",
        function_name="get_parameter_relationship",
        category="Research Institutions",
        year=2024,
        param_x="research_sfc",
        param_y="research_qnr",
        depends_on="op_1",
    )
    plan = QueryPlan(
        original_question="Failing dependency test",
        query_type="multi_operation",
        analytical_intent="Fail and skip",
        operations=[op1, op2],
    )
    result = executor.execute(plan)

    # Revalidation catches the TLR on research institutions immediately
    assert result.status == "REJECTED"


def test_executor_end_to_end_benchmarks():
    executor = get_query_executor()

    # Benchmark 1: Karnataka Engineering rank movement
    b1_op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_rank_movement",
        category="Engineering",
        start_year=2020,
        end_year=2025,
        states=["Karnataka"],
        top_n=10,
        movement_type="improvement",
    )
    b1_plan = QueryPlan(
        original_question="Which engineering colleges in Karnataka have improved their rankings the most since 2020?",
        query_type="rank_movement",
        analytical_intent="Find top rank gainers in Karnataka Engineering",
        operations=[b1_op],
    )
    b1_res = executor.execute(b1_plan)
    assert b1_res.status == "SUCCESS"
    assert len(b1_res.operations[0].data["gainers"]) > 0

    # Benchmark 2: Compare IIT Bombay and IIT Madras in Engineering 2025
    b2_op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_multidimensional_performance",
        category="Engineering",
        year=2025,
        institution_names=["IIT Bombay", "IIT Madras"],
        parameters=["rpc", "tlr"],
    )
    b2_plan = QueryPlan(
        original_question="Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025.",
        query_type="multidimensional_performance",
        analytical_intent="Compare IIT Bombay and IIT Madras",
        operations=[b2_op],
    )
    b2_res = executor.execute(b2_plan)
    assert b2_res.status == "SUCCESS"
    assert len(b2_res.operations[0].data["profiles"]) == 2

    # Benchmark 3: Top 10 Engineering by research + relationship between RPC and TLR
    b3_op1 = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_category_performance",
        category="Engineering",
        year=2025,
        parameters=["rpc"],
        top_n=10,
    )
    b3_op2 = AnalyticalOperation(
        operation_id="op_2",
        function_name="get_parameter_relationship",
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="tlr",
        depends_on="op_1",
    )
    b3_plan = QueryPlan(
        original_question="Find top 10 engineering institutions, then examine research vs teaching relationship.",
        query_type="multi_operation",
        analytical_intent="Multi-operation benchmark",
        operations=[b3_op1, b3_op2],
    )
    b3_res = executor.execute(b3_plan)
    assert b3_res.status == "SUCCESS"
    assert len(b3_res.operations) == 2

    # Benchmark 4: Multi-state comparison (Karnataka & Tamil Nadu)
    b4_op = AnalyticalOperation(
        operation_id="op_1",
        function_name="get_geographic_analysis",
        category="Engineering",
        year=2025,
        states=["Karnataka", "Tamil Nadu"],
    )
    b4_plan = QueryPlan(
        original_question="Compare Karnataka and Tamil Nadu engineering institutions in 2025.",
        query_type="geographic_analysis",
        analytical_intent="Compare states",
        operations=[b4_op],
    )
    b4_res = executor.execute(b4_plan)
    assert b4_res.status == "SUCCESS"
    assert b4_res.operations[0].data["head_to_head_comparison"] is not None

