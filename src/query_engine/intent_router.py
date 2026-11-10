"""
Conversational Intent Router for NIRF Assistant.
Determines query intent (Greeting, Thanks, Goodbye, Capabilities, Limitations,
NIRF Knowledge, NIRF Analytics, Out of Scope, and Ambiguous)
before analytical query parsing and execution, preventing unnecessary analytical execution,
empty visualizations, or context contamination.
"""

from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
import re
import logging

from src.query_engine.schemas import ConversationContext
from src.conversational.intent_classifier import (
    ConversationalIntentClassifier,
    get_intent_classifier,
    IntentCategory,
    ConversationalSubintent,
    IntentDecision,
)
from src.conversational.capabilities import get_capability_registry

logger = logging.getLogger(__name__)


ConversationalIntent = Literal[
    "GREETING",
    "GOODBYE",
    "THANKS",
    "GENERAL_CONVERSATION",
    "ANALYTICAL_QUERY",
    "DOCUMENTATION_QUERY",
    "CLARIFICATION_REQUIRED",
    "UNSUPPORTED_QUERY",
]


@dataclass
class IntentRoutingResult:
    """Structured result of intent classification."""
    intent: ConversationalIntent
    is_conversational: bool
    response_text: Optional[str] = None
    sub_intent: Optional[str] = None
    confidence: float = 1.0
    matched_pattern: Optional[str] = None
    decision: Optional[IntentDecision] = None


class IntentRouter:
    """
    Intelligent intent router combining instant deterministic matching for chit-chat
    with Gemma semantic understanding for general conversational, capability,
    knowledge, and analytical queries.
    """

    def __init__(self, classifier: Optional[ConversationalIntentClassifier] = None):
        self.classifier = classifier or get_intent_classifier()
        self.capabilities = get_capability_registry()

    def route_intent(
        self,
        query: str,
        context: Optional[ConversationContext] = None,
    ) -> IntentRoutingResult:
        """
        Classifies user query into a ConversationalIntent with appropriate response text.
        """
        q_raw = query.strip()
        q_clean = q_raw.lower()

        if not q_clean:
            return IntentRoutingResult(
                intent="CLARIFICATION_REQUIRED",
                is_conversational=True,
                response_text="Please enter a question or explore our suggested queries.",
                confidence=1.0,
            )

        # 1. Deterministic Fast-Path for obvious greetings, thanks, goodbyes
        greeting_patterns = [
            r"^(hi|hello|hey|namaste|greetings)(\s+there|\s+assistant|\s+all)?[\.!\?]*$",
            r"^(good\s+(morning|afternoon|evening|day))[\.!\?]*$",
            r"^(what'?s\s+up|sup|yo)[\.!\?]*$",
            r"^howdy[\.!\?]*$",
        ]
        for pat in greeting_patterns:
            if re.search(pat, q_clean):
                return IntentRoutingResult(
                    intent="GREETING",
                    is_conversational=True,
                    response_text=(
                        "Hello! I am your NIRF Conversational Analytical Assistant. "
                        "I can help you explore rankings, compare institutions, analyze multi-year trends, "
                        "and understand NIRF methodology. What would you like to explore?"
                    ),
                    matched_pattern=pat,
                )

        thanks_patterns = [
            r"^(thanks|thank\s+you|thx|many\s+thanks|much\s+appreciated)[\.!\?]*$",
            r"^(thank\s+you\s+(so\s+much|very\s+much|a\s+lot))[\.!\?]*$",
            r"^(appreciate\s+it|i\s+appreciate\s+it|great,\s*thanks)[\.!\?]*$",
        ]
        for pat in thanks_patterns:
            if re.search(pat, q_clean):
                return IntentRoutingResult(
                    intent="THANKS",
                    is_conversational=True,
                    response_text="You're welcome! Let me know if you would like to explore anything else in the NIRF data.",
                    matched_pattern=pat,
                )

        goodbye_patterns = [
            r"^(bye|goodbye|see\s+you|see\s+ya|farewell|take\s+care|good\s*night)[\.!\?]*$",
            r"^(have\s+a\s+good\s+(day|evening|night)|good\s*night)[\.!\?]*$",
            r"^(bye\s+bye|cya)[\.!\?]*$",
        ]
        for pat in goodbye_patterns:
            if re.search(pat, q_clean):
                return IntentRoutingResult(
                    intent="GOODBYE",
                    is_conversational=True,
                    response_text="Goodbye! Feel free to return whenever you want to explore India's institutional rankings data.",
                    matched_pattern=pat,
                )

        # 2. Semantic Intent Classification via ConversationalIntentClassifier
        decision = self.classifier.classify_intent(q_raw, context=context)

        if decision.primary_intent == IntentCategory.CONVERSATIONAL:
            sub = decision.conversational_subintent.value if decision.conversational_subintent else "general"
            response_text = self.classifier.generate_conversational_response(decision, q_raw)
            return IntentRoutingResult(
                intent="GENERAL_CONVERSATION",
                is_conversational=True,
                response_text=response_text,
                sub_intent=sub,
                confidence=1.0,
                decision=decision,
            )

        elif decision.primary_intent == IntentCategory.OUT_OF_SCOPE:
            response_text = self.classifier.generate_conversational_response(decision, q_raw)
            return IntentRoutingResult(
                intent="UNSUPPORTED_QUERY",
                is_conversational=True,
                response_text=response_text,
                sub_intent="out_of_scope",
                confidence=1.0,
                decision=decision,
            )

        elif decision.primary_intent == IntentCategory.AMBIGUOUS:
            response_text = self.classifier.generate_conversational_response(decision, q_raw)
            return IntentRoutingResult(
                intent="CLARIFICATION_REQUIRED",
                is_conversational=True,
                response_text=response_text,
                sub_intent="ambiguous",
                confidence=0.9,
                decision=decision,
            )

        elif decision.primary_intent == IntentCategory.NIRF_KNOWLEDGE:
            return IntentRoutingResult(
                intent="DOCUMENTATION_QUERY",
                is_conversational=False,
                sub_intent="methodology_explanation",
                confidence=0.95,
                decision=decision,
            )

        else:  # NIRF_ANALYTICAL
            # Check if specifically category evolution
            sub = "category_evolution" if "category" in q_clean and ("change" in q_clean or "evolv" in q_clean or "count" in q_clean or "how many" in q_clean) else "standard_analytical"
            return IntentRoutingResult(
                intent="ANALYTICAL_QUERY",
                is_conversational=False,
                sub_intent=sub,
                confidence=0.95,
                decision=decision,
            )


def get_intent_router() -> IntentRouter:
    """Returns singleton IntentRouter instance."""
    return IntentRouter()
