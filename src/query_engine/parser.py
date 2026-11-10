"""
Natural Language Query Parser for NIRF Dashboard (Phase 3).
Converts natural-language queries and follow-ups into structured QueryPlans using Gemma 4 31B Cloud.
"""

from typing import Optional, Dict, Any
import logging
import uuid
import re

from src.llm.gemma_client import GemmaClient, get_gemma_client, GemmaClientError
from src.query_engine.schemas import (
    QueryPlan,
    ConversationContext,
    AnalyticalOperation,
    VisualizationPreference,
)
from src.query_engine.prompts import (
    QUERY_PARSER_SYSTEM_PROMPT,
    build_parser_user_prompt,
)
from src.query_engine.intent_router import get_intent_router, IntentRouter
from src.query_engine.exceptions import QueryParsingError

logger = logging.getLogger(__name__)


class QueryParser:
    """
    Parses natural language NIRF questions into standardized QueryPlan objects
    using Gemma 4 31B Cloud via the Ollama client, with pre-routed conversational intent handling.
    """

    def __init__(self, client: Optional[GemmaClient] = None) -> None:
        self.client = client or get_gemma_client()
        self.intent_router = get_intent_router()

    def parse(
        self,
        question: str,
        conversation_context: Optional[ConversationContext] = None,
    ) -> QueryPlan:
        """
        Converts a user question into a validated Pydantic QueryPlan.

        Args:
            question: User's natural language question.
            conversation_context: Optional context from preceding turns for follow-ups.

        Returns:
            Validated QueryPlan object.
        """
        q_clean = question.strip()
        if not q_clean:
            raise QueryParsingError("User question cannot be empty.")

        # Conversational Pre-Routing
        intent_res = self.intent_router.route_intent(q_clean, conversation_context)
        if intent_res.is_conversational:
            logger.info("Conversational intent '%s' routed deterministically.", intent_res.intent)
            return QueryPlan(
                query_id=f"qp_{uuid.uuid4().hex[:8]}",
                original_question=q_clean,
                query_type="unsupported" if intent_res.intent == "UNSUPPORTED_QUERY" else "clarification_required",
                analytical_intent=f"Conversational {intent_res.intent.lower()}",
                explanation=intent_res.response_text or "",
                clarification_message=intent_res.response_text,
                operations=[],
                semantic_retrieval_needed=False,
                conversation_context=ConversationContext(),
            )

        prompt = build_parser_user_prompt(q_clean, conversation_context)

        logger.debug("Parsing query with Gemma: '%s'", q_clean)
        try:
            raw_dict = self.client.generate_json(
                prompt=prompt,
                system_prompt=QUERY_PARSER_SYSTEM_PROMPT,
                schema=QueryPlan,
                temperature=0.0,
            )

            # Ensure original question is preserved exactly
            raw_dict["original_question"] = q_clean

            # Instantiate QueryPlan
            plan = QueryPlan.model_validate(raw_dict)

            # Context inheritance post-processing
            if conversation_context is not None:
                self._apply_context_inheritance(plan, conversation_context)

            return plan

        except GemmaClientError as ge:
            logger.error("Gemma client failed during query parsing: %s", ge)
            raise QueryParsingError(f"Failed to generate structured query plan from Gemma: {ge}") from ge
        except Exception as e:
            logger.error("Unexpected error during query parsing: %s", e)
            raise QueryParsingError(f"Query parsing error: {e}") from e

    def _apply_context_inheritance(
        self,
        plan: QueryPlan,
        context: ConversationContext,
    ) -> None:
        """Ensures inherited constraints from previous turn are preserved in the plan."""
        if not plan.conversation_context:
            plan.conversation_context = context

        # Do not inherit context if query is category evolution (aggregate cross-category analysis)
        if plan.query_type == "category_evolution":
            plan.conversation_context.inherited_fields = []
            plan.conversation_context.modified_fields = []
            return

        inherited = []
        modified = []
        q_lower = plan.original_question.lower()

        # Check each operation
        for op in plan.operations:
            fn = op.function_name

            # Skip category evolution operations from inheriting institution or category filters
            if fn == "get_category_evolution":
                continue

            # 1. Category: inherit if omitted in op, or if passed via context without user restating it
            if not op.category and context.previous_category:
                op.category = context.previous_category
                inherited.append("category")
            elif op.category and context.previous_category:
                if op.category.lower() == context.previous_category.lower() and op.category.lower() not in q_lower:
                    inherited.append("category")
                elif op.category.lower() != context.previous_category.lower():
                    modified.append("category")

            # 2. Year: inherit if omitted in op
            if not op.year and not op.start_year and context.previous_year:
                op.year = context.previous_year
                inherited.append("year")
            elif op.year and context.previous_year and op.year != context.previous_year:
                modified.append("year")

            # 3. Additive Institution inheritance ("Now include IIT Delhi", "also add...", "along with...")
            is_additive_inst = bool(re.search(r"\b(include|also\s+include|add|also\s+add|along\s+with|and\s+also)\b", q_lower))
            if context.previous_institution_names:
                existing_inst_lower = [n.lower() for n in op.institution_names]
                if is_additive_inst:
                    for prev_inst in context.previous_institution_names:
                        if prev_inst.lower() not in existing_inst_lower:
                            op.institution_names.append(prev_inst)
                    inherited.append("institution_names")
                    modified.append("institution_names")
                elif any(p.lower() in existing_inst_lower for p in context.previous_institution_names) and len(op.institution_names) > len(context.previous_institution_names):
                    inherited.append("institution_names")

            # 4. States: if follow-up asked to add another state, merge previous states
            if context.previous_states:
                existing_lower = [s.lower() for s in op.states]
                for prev_s in context.previous_states:
                    if prev_s.lower() not in existing_lower:
                        op.states.append(prev_s)
                        inherited.append("states")

            # 5. Top N
            if op.top_n is None and context.previous_top_n is not None:
                op.top_n = context.previous_top_n
                inherited.append("top_n")
            elif op.top_n is not None and context.previous_top_n is not None and op.top_n != context.previous_top_n:
                modified.append("top_n")

        plan.conversation_context.inherited_fields = list(set(inherited))
        plan.conversation_context.modified_fields = list(set(modified))


def get_query_parser(client: Optional[GemmaClient] = None) -> QueryParser:
    """Returns a QueryParser instance."""
    return QueryParser(client=client)

