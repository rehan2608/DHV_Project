"""
Unit tests for QueryRouter (Phase 4).
"""

import pytest
from src.execution.router import QueryRouter, get_query_router
from src.execution.exceptions import RouterError


def test_router_all_ten_functions_allowed():
    router = get_query_router()
    ten_functions = [
        "get_institution_trend",
        "get_rank_movement",
        "get_category_performance",
        "get_geographic_analysis",
        "get_parameter_correlation",
        "get_parameter_relationship",
        "get_multidimensional_performance",
        "get_score_distribution",
        "get_rank_transitions",
        "get_outlier_analysis",
    ]
    for fn in ten_functions:
        assert router.is_allowed(fn) is True
        callable_fn = router.resolve_function(fn)
        assert callable(callable_fn)


def test_router_rejects_unknown_function():
    router = get_query_router()
    with pytest.raises(RouterError):
        router.resolve_function("unauthorized_system_command")


def test_router_rejects_empty_function():
    router = get_query_router()
    with pytest.raises(RouterError):
        router.resolve_function("")

