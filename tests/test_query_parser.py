"""
Unit tests for QueryParser with mocked GemmaClient responses (Phase 3).
Tests parser workflow, prompt formatting, context inheritance, and error handling.
"""

import pytest
from unittest.mock import MagicMock
from src.query_engine.parser import QueryParser
from src.query_engine.schemas import (
    QueryPlan,
    ConversationContext,
    AnalyticalOperation,
)
from src.query_engine.exceptions import QueryParsingError


def test_parser_benchmark_1_intent_extraction_mocked():
    mock_client = MagicMock()
    mock_client.generate_json.return_value = {
        "original_question": "Which engineering colleges in Karnataka have improved their rankings the most since 2020?",
        "query_type": "rank_movement",
        "analytical_intent": "Identify engineering institutions in Karnataka with largest rank improvement between 2020 and 2025",
        "confidence_score": 0.98,
        "operations": [
            {
                "operation_id": "op_1",
                "function_name": "get_rank_movement",
                "category": "Engineering",
                "start_year": 2020,
                "end_year": 2025,
                "states": ["Karnataka"],
                "movement_type": "improvement",
                "top_n": 10,
            }
        ],
        "visualization": {
            "chart_requested": True,
            "preferred_chart_type": "horizontal_bar"
        }
    }

    parser = QueryParser(client=mock_client)
    plan = parser.parse("Which engineering colleges in Karnataka have improved their rankings the most since 2020?")

    assert plan.query_type == "rank_movement"
    assert len(plan.operations) == 1
    op = plan.operations[0]
    assert op.function_name == "get_rank_movement"
    assert op.category == "Engineering"
    assert op.start_year == 2020
    assert op.end_year == 2025
    assert "Karnataka" in op.states


def test_parser_benchmark_2_structured_query_mocked():
    mock_client = MagicMock()
    mock_client.generate_json.return_value = {
        "original_question": "Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025.",
        "query_type": "multidimensional_performance",
        "analytical_intent": "Compare research performance of IIT Bombay and IIT Madras in 2025 Engineering",
        "confidence_score": 0.99,
        "operations": [
            {
                "operation_id": "op_1",
                "function_name": "get_multidimensional_performance",
                "category": "Engineering",
                "year": 2025,
                "institution_names": ["IIT Bombay", "IIT Madras"],
                "parameters": ["rpc"],
            }
        ]
    }

    parser = QueryParser(client=mock_client)
    plan = parser.parse("Compare IIT Bombay and IIT Madras in research performance in Engineering in 2025.")

    assert plan.query_type == "multidimensional_performance"
    assert plan.operations[0].function_name == "get_multidimensional_performance"
    assert "IIT Bombay" in plan.operations[0].institution_names
    assert "IIT Madras" in plan.operations[0].institution_names
    assert "rpc" in plan.operations[0].parameters


def test_parser_follow_up_context_inheritance():
    mock_client = MagicMock()
    # In follow-up turn, user asks "Now compare them with Tamil Nadu"
    mock_client.generate_json.return_value = {
        "original_question": "Now compare them with Tamil Nadu.",
        "query_type": "geographic_analysis",
        "analytical_intent": "Compare Engineering performance of Karnataka and Tamil Nadu",
        "confidence_score": 0.95,
        "operations": [
            {
                "operation_id": "op_1",
                "function_name": "get_geographic_analysis",
                "category": "Engineering",
                "year": 2025,
                "states": ["Tamil Nadu"],  # Model returned new state
                "top_n": 10,
            }
        ]
    }

    parser = QueryParser(client=mock_client)
    prev_ctx = ConversationContext(
        previous_category="Engineering",
        previous_year=2025,
        previous_states=["Karnataka"],
        previous_top_n=10,
    )
    plan = parser.parse("Now compare them with Tamil Nadu.", conversation_context=prev_ctx)

    op = plan.operations[0]
    # Inheritance check: BOTH states must be present!
    assert "Karnataka" in op.states
    assert "Tamil Nadu" in op.states
    assert op.category == "Engineering"
    assert op.year == 2025


def test_parser_empty_question_raises():
    parser = QueryParser()
    with pytest.raises(QueryParsingError):
        parser.parse("   ")

