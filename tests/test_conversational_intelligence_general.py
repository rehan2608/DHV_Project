"""
Comprehensive Verification Suite for General Conversational Intelligence (Pre-Phase 8).
Validates 60 distinct questions across 6 core intent groups:
1. 10 Capability Questions (including 'what u cannot do', graph queries, future predictions)
2. 10 NIRF Knowledge Questions (TLR, RPC, GO, formulas, rules)
3. 10 NIRF Analytical Questions (comparisons, trends, distributions, evolution)
4. 10 Greetings and General Conversational Questions (chit-chat, thanks, goodbyes)
5. 10 Out-of-Scope Questions (general knowledge, coding, recipes)
6. 10 Context-Switching and Follow-up Questions (context isolation & additive follow-ups)
"""

import pytest

from src.conversational.capabilities import get_capability_registry
from src.conversational.intent_classifier import (
    get_intent_classifier,
    IntentCategory,
    ConversationalSubintent,
)
from src.query_engine.intent_router import get_intent_router
from src.query_engine.parser import get_query_parser
from src.query_engine.schemas import ConversationContext


# =============================================================================
# GROUP 1: 10 CAPABILITY QUESTIONS
# =============================================================================

CAPABILITY_TEST_CASES = [
    ("what u cannot do", ConversationalSubintent.LIMITATIONS),
    ("What can you do?", ConversationalSubintent.CAPABILITIES),
    ("What are your limitations?", ConversationalSubintent.LIMITATIONS),
    ("Tell me your features.", ConversationalSubintent.CAPABILITIES),
    ("Can you compare colleges?", ConversationalSubintent.CAPABILITIES),
    ("Can you show graphs?", ConversationalSubintent.GRAPHS),
    ("What can't you answer?", ConversationalSubintent.LIMITATIONS),
    ("Can you predict next year's rankings?", ConversationalSubintent.FUTURE_PREDICTION),
    ("How should I use you?", ConversationalSubintent.USAGE_HELP),
    ("What are your supported capabilities?", ConversationalSubintent.CAPABILITIES),
]

class TestCapabilityUnderstanding:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = get_intent_classifier()
        self.router = get_intent_router()
        self.capabilities = get_capability_registry()

    @pytest.mark.parametrize("query,expected_subintent", CAPABILITY_TEST_CASES)
    def test_capability_queries_classification_and_response(self, query, expected_subintent):
        decision = self.classifier.classify_intent(query)
        assert decision.primary_intent == IntentCategory.CONVERSATIONAL
        assert decision.conversational_subintent == expected_subintent

        resp_text = self.classifier.generate_conversational_response(decision, query)
        assert len(resp_text) > 50
        # Must not leak developer jargon
        assert "UNSUPPORTED" not in resp_text
        assert "CLARIFICATION_REQUIRED" not in resp_text
        assert "QueryPlan" not in resp_text

        # Verify specific content requirements
        if expected_subintent == ConversationalSubintent.LIMITATIONS:
            assert any(k in resp_text.lower() for k in ["cannot", "can't", "limitations", "limit"])
            assert "predict" in resp_text.lower()
        elif expected_subintent == ConversationalSubintent.GRAPHS:
            assert "graph" in resp_text.lower() or "chart" in resp_text.lower()
        elif expected_subintent == ConversationalSubintent.FUTURE_PREDICTION:
            assert ("predict" in resp_text.lower() or "forecast" in resp_text.lower()) and any(
                neg in resp_text.lower() for neg in ["cannot", "can't", "unable", "don't", "not able", "won't", "wish i could"]
            )

    def test_capabilities_derived_from_actual_engine(self):
        supported_ops = self.capabilities.get_supported_analytical_operations()
        assert len(supported_ops) >= 11
        assert "get_institution_trend" in supported_ops
        assert "get_category_evolution" in supported_ops


# =============================================================================
# GROUP 2: 10 NIRF KNOWLEDGE QUESTIONS
# =============================================================================

KNOWLEDGE_TEST_CASES = [
    "What is TLR?",
    "What does RPC measure?",
    "How is NIRF ranking calculated?",
    "What is the difference between rank and score?",
    "Explain GO parameter in simple words.",
    "What does Outreach and Inclusivity (OI) evaluate?",
    "How is Peer Perception measured in NIRF?",
    "What are the five main NIRF parameters?",
    "What is the formula for calculating TLR score?",
    "Why do some categories only have rank and no scores?",
]

class TestKnowledgeUnderstanding:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = get_intent_classifier()
        self.router = get_intent_router()

    @pytest.mark.parametrize("query", KNOWLEDGE_TEST_CASES)
    def test_knowledge_queries_routed_correctly(self, query):
        decision = self.classifier.classify_intent(query)
        assert decision.primary_intent == IntentCategory.NIRF_KNOWLEDGE

        route_res = self.router.route_intent(query)
        assert route_res.intent == "DOCUMENTATION_QUERY"
        assert route_res.is_conversational is False


# =============================================================================
# GROUP 3: 10 NIRF ANALYTICAL QUESTIONS
# =============================================================================

ANALYTICAL_TEST_CASES = [
    "Compare IIT Bombay and IIT Madras in Engineering in 2025.",
    "How has IIT Delhi performed in Engineering from 2017 to 2025?",
    "Which colleges performed best in Management in 2025?",
    "Which states have the most ranked Engineering colleges in 2025?",
    "Show score distribution for Engineering in 2025.",
    "How have NIRF institutional categories evolved since 2017?",
    "Which institutions improved their Engineering rankings the most between 2020 and 2025?",
    "Is there a correlation between TLR and RPC in Engineering for 2025?",
    "Identify statistical outliers in Engineering scores for 2025.",
    "How did institutions move between ranking tiers from 2020 to 2025?",
]

class TestAnalyticalUnderstanding:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = get_intent_classifier()
        self.router = get_intent_router()

    @pytest.mark.parametrize("query", ANALYTICAL_TEST_CASES)
    def test_analytical_queries_routed_to_pipeline(self, query):
        decision = self.classifier.classify_intent(query)
        assert decision.primary_intent == IntentCategory.NIRF_ANALYTICAL

        route_res = self.router.route_intent(query)
        assert route_res.intent == "ANALYTICAL_QUERY"
        assert route_res.is_conversational is False


# =============================================================================
# GROUP 4: 10 GREETINGS & CONVERSATIONAL QUESTIONS
# =============================================================================

CONVERSATIONAL_TEST_CASES = [
    "hi",
    "hello there",
    "good morning",
    "namaste",
    "thanks",
    "thank you so much",
    "bye",
    "see you later",
    "how are you today?",
    "nice to meet you",
]

class TestConversationalUnderstanding:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.router = get_intent_router()

    @pytest.mark.parametrize("query", CONVERSATIONAL_TEST_CASES)
    def test_conversational_queries_routed_without_analytics(self, query):
        route_res = self.router.route_intent(query)
        assert route_res.is_conversational is True
        assert route_res.response_text is not None
        assert len(route_res.response_text) > 10


# =============================================================================
# GROUP 5: 10 OUT-OF-SCOPE QUESTIONS
# =============================================================================

OUT_OF_SCOPE_TEST_CASES = [
    "Who won the 2022 FIFA World Cup?",
    "Write a python function to reverse a string.",
    "What is the recipe for chicken tikka masala?",
    "What is the capital of France?",
    "Can you write an essay about Shakespeare?",
    "What is the current stock price of Apple?",
    "Explain the theory of general relativity.",
    "How do I fix a leaking bathroom faucet?",
    "Who was the first president of the United States?",
    "Can you book a flight ticket to Mumbai for me?",
]

class TestOutOfScopeUnderstanding:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.classifier = get_intent_classifier()
        self.router = get_intent_router()

    @pytest.mark.parametrize("query", OUT_OF_SCOPE_TEST_CASES)
    def test_out_of_scope_queries_polite_redirection(self, query):
        decision = self.classifier.classify_intent(query)
        assert decision.primary_intent == IntentCategory.OUT_OF_SCOPE

        route_res = self.router.route_intent(query)
        assert route_res.intent == "UNSUPPORTED_QUERY"
        assert route_res.is_conversational is True
        assert "NIRF" in route_res.response_text
        assert "higher education" in route_res.response_text.lower() or "ranking" in route_res.response_text.lower()


# =============================================================================
# GROUP 6: 10 CONTEXT-SWITCHING & FOLLOW-UP SCENARIOS
# =============================================================================

class TestContextSwitchingScenarios:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parser = get_query_parser()
        self.router = get_intent_router()

    def test_scenario_1_additive_institution_preserves_context(self):
        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_institution_names=["IIT Bombay", "IIT Madras"],
            previous_query_type="multidimensional_performance",
        )
        plan = self.parser.parse("Now include IIT Delhi.", conversation_context=ctx)
        assert "IIT Delhi" in plan.operations[0].institution_names
        assert "IIT Bombay" in plan.operations[0].institution_names
        assert "IIT Madras" in plan.operations[0].institution_names
        assert plan.operations[0].category == "Engineering"

    def test_scenario_2_year_shift_preserves_category(self):
        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_query_type="score_distribution",
        )
        plan = self.parser.parse("Now do the same for 2024.", conversation_context=ctx)
        assert plan.operations[0].category == "Engineering"
        assert plan.operations[0].year == 2024

    def test_scenario_3_capability_after_analytical_cleans_context(self):
        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_institution_names=["IIT Bombay", "IIT Madras"],
        )
        res = self.router.route_intent("What can you do?", context=ctx)
        assert res.is_conversational is True
        assert any(term in res.response_text.lower() for term in ["trend", "compare", "ranking", "visualiz"])

    def test_scenario_4_limitations_after_analytical_cleans_context(self):
        ctx = ConversationContext(previous_category="Engineering", previous_year=2025)
        res = self.router.route_intent("what u cannot do", context=ctx)
        assert res.is_conversational is True
        assert "predict" in res.response_text.lower()
        assert "Engineering" not in res.response_text

    def test_scenario_5_knowledge_after_analytical_does_not_inherit_filters(self):
        ctx = ConversationContext(
            previous_category="College",
            previous_start_year=2017,
            previous_end_year=2025,
            previous_query_type="rank_transitions",
        )
        res = self.router.route_intent("What is TLR?", context=ctx)
        assert res.intent == "DOCUMENTATION_QUERY"
        assert res.is_conversational is False

    def test_scenario_6_analytical_after_knowledge(self):
        ctx = ConversationContext(previous_query_type="methodology_explanation")
        res = self.router.route_intent("Compare IIT Madras and IIT Delhi in Engineering in 2025.", context=ctx)
        assert res.intent == "ANALYTICAL_QUERY"

    def test_scenario_7_greeting_after_analytical(self):
        ctx = ConversationContext(previous_category="Management", previous_year=2025)
        res = self.router.route_intent("hi", context=ctx)
        assert res.intent == "GREETING"
        assert res.is_conversational is True
        assert "Management" not in res.response_text

    def test_scenario_8_out_of_scope_after_analytical(self):
        ctx = ConversationContext(previous_category="Pharmacy", previous_year=2023)
        res = self.router.route_intent("What is the capital of France?", context=ctx)
        assert res.intent == "UNSUPPORTED_QUERY"
        assert res.is_conversational is True
        assert "NIRF" in res.response_text

    def test_scenario_9_independent_category_evolution_after_institution_comparison(self):
        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_institution_names=["IIT Bombay", "IIT Madras"],
        )
        plan = self.parser.parse("How have NIRF institutional categories evolved since 2017?", conversation_context=ctx)
        assert plan.query_type == "category_evolution"
        assert plan.operations[0].category is None
        assert plan.operations[0].institution_names == []

    def test_scenario_10_institution_trend_after_category_evolution(self):
        ctx = ConversationContext(previous_query_type="category_evolution")
        plan = self.parser.parse("How has IIT Madras performed in Engineering from 2017 to 2025?", conversation_context=ctx)
        assert plan.query_type == "institution_trend"
        assert plan.operations[0].category == "Engineering"
        assert "IIT Madras" in plan.operations[0].institution_names

