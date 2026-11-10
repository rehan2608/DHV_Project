"""
Comprehensive test suite for Conversational Intent Routing, Category Evolution Analysis,
and Context Inheritance Corrections (Pre-Phase 8).
"""

import pytest
from unittest.mock import MagicMock

from src.analytics.categories import get_category_evolution
from src.analytics.engine import NIRFAnalyticsEngine, get_analytics_engine
from src.execution.router import get_query_router
from src.execution.argument_mapper import get_argument_mapper
from src.execution.result_schema import OperationResult
from src.query_engine.intent_router import get_intent_router
from src.query_engine.parser import QueryParser
from src.query_engine.validator import get_query_validator
from src.query_engine.schemas import (
    ConversationContext,
    AnalyticalOperation,
    QueryPlan,
)
from src.visualization.chart_planner import get_chart_planner
from src.visualization.plotly_renderer import get_plotly_renderer


# =============================================================================
# 1. Conversational Intent Routing Tests
# =============================================================================

class TestConversationalRouting:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.router = get_intent_router()

    @pytest.mark.parametrize("greeting", [
        "hi", "hello", "hey", "good morning", "good afternoon", "namaste", "what's up?", "yo"
    ])
    def test_greetings_routed_conversationally(self, greeting):
        res = self.router.route_intent(greeting)
        assert res.intent == "GREETING"
        assert res.is_conversational is True
        assert res.response_text is not None
        assert "NIRF" in res.response_text

    @pytest.mark.parametrize("thanks", [
        "thanks", "thank you", "thank you so much", "thx", "much appreciated", "appreciate it"
    ])
    def test_thanks_routed_conversationally(self, thanks):
        res = self.router.route_intent(thanks)
        assert res.intent == "THANKS"
        assert res.is_conversational is True
        assert "welcome" in res.response_text.lower()

    @pytest.mark.parametrize("goodbye", [
        "bye", "goodbye", "see you", "see ya", "farewell", "take care", "good night"
    ])
    def test_goodbye_routed_conversationally(self, goodbye):
        res = self.router.route_intent(goodbye)
        assert res.intent == "GOODBYE"
        assert res.is_conversational is True
        assert "goodbye" in res.response_text.lower() or "feel free" in res.response_text.lower()

    @pytest.mark.parametrize("cap_query", [
        "what can you do?", "what are your capabilities?", "help", "who are you?", "how can you help me?"
    ])
    def test_capabilities_routed_conversationally(self, cap_query):
        res = self.router.route_intent(cap_query)
        assert res.intent == "GENERAL_CONVERSATION"
        assert res.is_conversational is True
        assert "Institution Trend Tracking" in res.response_text or "NIRF" in res.response_text

    def test_parser_intercepts_greetings_without_llm(self):
        # Mock LLM to prove it is NEVER invoked for greetings
        mock_llm = MagicMock()
        parser = QueryParser(client=mock_llm)

        plan = parser.parse("hi")
        mock_llm.generate_json.assert_not_called()
        assert plan.query_type == "clarification_required"
        assert plan.operations == []
        assert "NIRF" in plan.clarification_message


# =============================================================================
# 2. Category Evolution Analytics Tests (Real Clean Dataset)
# =============================================================================

class TestCategoryEvolutionAnalytics:
    def test_category_counts_and_boundaries(self):
        res = get_category_evolution(start_year=2017, end_year=2025)
        assert res["success"] is True

        yearly = {ym["year"]: ym for ym in res["yearly_metrics"]}

        # 2017: exactly 6 categories
        assert yearly[2017]["category_count"] == 6
        assert sorted(yearly[2017]["categories"]) == [
            "College", "Engineering", "Management", "Overall", "Pharmacy", "University"
        ]

        # 2018: 10 categories (+4)
        assert yearly[2018]["category_count"] == 10
        assert set(yearly[2018]["new_categories"]) == {
            "Architecture & Planning", "Law", "Medical", "Special Mention (2018)"
        }

        # 2019: 9 categories (Special Mention discontinued)
        assert yearly[2019]["category_count"] == 9
        assert "Special Mention (2018)" in yearly[2019]["discontinued_categories"]

        # 2020: 10 categories (+ Dental)
        assert yearly[2020]["category_count"] == 10
        assert yearly[2020]["new_categories"] == ["Dental"]

        # 2021: 11 categories (+ Research Institutions)
        assert yearly[2021]["category_count"] == 11
        assert yearly[2021]["new_categories"] == ["Research Institutions"]

        # 2022: 11 categories
        assert yearly[2022]["category_count"] == 11
        assert yearly[2022]["new_categories"] == []

        # 2023: 13 categories (+ Agriculture & Innovation)
        assert yearly[2023]["category_count"] == 13
        assert set(yearly[2023]["new_categories"]) == {"Agriculture & Allied Sectors", "Innovation"}

        # 2024: 16 categories (+ Open University, Skill University, State Public University)
        assert yearly[2024]["category_count"] == 16
        assert set(yearly[2024]["new_categories"]) == {
            "Open University", "Skill University", "State Public University"
        }

        # 2025: 17 categories (+ SDG)
        assert yearly[2025]["category_count"] == 17
        assert yearly[2025]["new_categories"] == ["Sustainable Development Goals (SDG)"]

    def test_persistent_and_discontinued_categories(self):
        res = get_category_evolution(start_year=2017, end_year=2025)
        # Exactly 6 persistent categories throughout 2017-2025
        assert res["persistent_categories"] == [
            "College", "Engineering", "Management", "Overall", "Pharmacy", "University"
        ]
        # Discontinued in dataset
        assert "Special Mention (2018)" in res["discontinued_categories"]

    def test_dataset_first_observed_provenance(self):
        res = get_category_evolution(start_year=2017, end_year=2025)
        details = res["category_details"]

        assert details["Engineering"]["first_observed_year"] == 2017
        assert details["Medical"]["first_observed_year"] == 2018
        assert details["Dental"]["first_observed_year"] == 2020
        assert details["Research Institutions"]["first_observed_year"] == 2021
        assert details["Agriculture & Allied Sectors"]["first_observed_year"] == 2023
        assert details["State Public University"]["first_observed_year"] == 2024
        assert details["Sustainable Development Goals (SDG)"]["first_observed_year"] == 2025

        # Metadata warning distinguishing first appearance from official introduction
        warnings = res["metadata"]["warnings"]
        assert any("first appearance" in w.lower() for w in warnings)

    def test_invalid_temporal_bounds(self):
        res = get_category_evolution(start_year=2025, end_year=2020)
        assert res["success"] is False
        assert "cannot be greater than" in res["error"]


# =============================================================================
# 3. Router and Argument Mapper Registration Tests
# =============================================================================

class TestRouterAndMapperIntegration:
    def test_router_allowlist_contains_category_evolution(self):
        router = get_query_router()
        assert router.is_allowed("get_category_evolution")
        fn = router.resolve_function("get_category_evolution")
        assert callable(fn)

    def test_argument_mapper_for_category_evolution(self):
        mapper = get_argument_mapper()
        op = AnalyticalOperation(
            function_name="get_category_evolution",
            start_year=2018,
            end_year=2024,
            category=None,
        )
        kwargs = mapper.map_arguments(op)
        assert kwargs["start_year"] == 2018
        assert kwargs["end_year"] == 2024
        assert kwargs["category"] is None

    def test_argument_mapper_defaults(self):
        mapper = get_argument_mapper()
        op = AnalyticalOperation(
            function_name="get_category_evolution",
        )
        kwargs = mapper.map_arguments(op)
        assert kwargs["start_year"] == 2017
        assert kwargs["end_year"] == 2025


# =============================================================================
# 4. Context Inheritance Tests
# =============================================================================

class TestContextInheritance:
    def test_additive_institution_inheritance(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "original_question": "Now include IIT Delhi.",
            "query_type": "multidimensional_performance",
            "analytical_intent": "Compare multidimensional performance",
            "confidence_score": 1.0,
            "operations": [
                {
                    "operation_id": "op_1",
                    "function_name": "get_multidimensional_performance",
                    "category": None,
                    "year": None,
                    "institution_names": ["IIT Delhi"],
                }
            ],
            "conversation_context": None,
        }
        parser = QueryParser(client=mock_llm)

        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_institution_names=["IIT Bombay", "IIT Madras"],
            previous_query_type="multidimensional_performance",
        )

        plan = parser.parse("Now include IIT Delhi.", conversation_context=ctx)
        op = plan.operations[0]

        # Verify previous institutions were merged
        assert "IIT Bombay" in op.institution_names
        assert "IIT Madras" in op.institution_names
        assert "IIT Delhi" in op.institution_names
        # Verify category and year were inherited
        assert op.category == "Engineering"
        assert op.year == 2025
        assert "institution_names" in plan.conversation_context.inherited_fields
        assert "category" in plan.conversation_context.inherited_fields

    def test_year_change_inheritance(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "original_question": "Now do the same for 2024.",
            "query_type": "score_distribution",
            "analytical_intent": "Score distribution for 2024",
            "confidence_score": 1.0,
            "operations": [
                {
                    "operation_id": "op_1",
                    "function_name": "get_score_distribution",
                    "category": None,
                    "year": 2024,
                }
            ],
            "conversation_context": None,
        }
        parser = QueryParser(client=mock_llm)

        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_query_type="score_distribution",
        )

        plan = parser.parse("Now do the same for 2024.", conversation_context=ctx)
        op = plan.operations[0]

        assert op.category == "Engineering"
        assert op.year == 2024
        assert "category" in plan.conversation_context.inherited_fields
        assert "year" in plan.conversation_context.modified_fields

    def test_independent_category_evolution_does_not_inherit_filters(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "original_question": "How have NIRF institutional categories evolved since 2017?",
            "query_type": "category_evolution",
            "analytical_intent": "Category evolution analysis",
            "confidence_score": 1.0,
            "operations": [
                {
                    "operation_id": "op_1",
                    "function_name": "get_category_evolution",
                    "category": None,
                    "start_year": 2017,
                    "end_year": 2025,
                    "institution_names": [],
                }
            ],
            "conversation_context": None,
        }
        parser = QueryParser(client=mock_llm)

        # Context from a completely different prior query
        ctx = ConversationContext(
            previous_category="Management",
            previous_year=2024,
            previous_institution_names=["IIM Ahmedabad", "IIM Bangalore"],
            previous_query_type="multidimensional_performance",
        )

        plan = parser.parse("How have NIRF institutional categories evolved since 2017?", conversation_context=ctx)
        op = plan.operations[0]

        # Crucial: category evolution MUST NOT inherit prior Management or IIM filters
        assert op.category is None
        assert op.institution_names == []
        assert plan.conversation_context.inherited_fields == []


# =============================================================================
# 5. Visualization Integration Tests for Category Evolution
# =============================================================================

class TestCategoryEvolutionVisualization:
    def test_chart_planner_produces_bar_spec(self):
        res = get_category_evolution(start_year=2017, end_year=2025)
        op_res = OperationResult(
            operation_id="op_1",
            function_name="get_category_evolution",
            status="SUCCESS",
            data=res,
            warnings=res["metadata"]["warnings"],
        )
        planner = get_chart_planner()
        spec = planner.plan_chart(op_res)

        assert spec.chart_type == "bar"
        assert spec.x_field == "year"
        assert spec.y_field == "category_count"
        assert len(spec.data) == 9
        assert "2017–2025" in spec.title

    def test_chart_planner_table_request(self):
        res = get_category_evolution(start_year=2017, end_year=2025)
        op_res = OperationResult(
            operation_id="op_1",
            function_name="get_category_evolution",
            status="SUCCESS",
            data=res,
            warnings=res["metadata"]["warnings"],
        )
        planner = get_chart_planner()
        spec = planner.plan_chart(op_res, explicit_chart_type="table")

        assert spec.chart_type == "table"
        assert len(spec.data) == 9
        assert "Total Categories" in spec.data[0]

    def test_plotly_renderer_renders_category_chart(self):
        res = get_category_evolution(start_year=2017, end_year=2025)
        op_res = OperationResult(
            operation_id="op_1",
            function_name="get_category_evolution",
            status="SUCCESS",
            data=res,
            warnings=res["metadata"]["warnings"],
        )
        planner = get_chart_planner()
        spec = planner.plan_chart(op_res)

        renderer = get_plotly_renderer()
        fig = renderer.render(spec)

        assert fig is not None
        assert len(fig.data) == 1
        assert list(fig.data[0].x) == [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        assert list(fig.data[0].y) == [6, 10, 9, 10, 11, 11, 13, 16, 17]
