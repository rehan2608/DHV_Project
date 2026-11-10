"""
General-Purpose Conversational Intent Classifier for NIRF Assistant.
Distinguishes Conversational (Capabilities, Limitations, Usage, Chit-Chat),
NIRF Knowledge (Methodology, Parameters, Rules), NIRF Analytics (Trends, Comparisons),
Out-of-Scope, and Ambiguous queries using structured Gemma reasoning and deterministic fast paths.
"""

from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import re
import logging
from pydantic import BaseModel, Field

from src.llm.gemma_client import GemmaClient, get_gemma_client, GemmaClientError
from src.conversational.capabilities import CapabilityRegistry, get_capability_registry

logger = logging.getLogger(__name__)


class IntentCategory(str, Enum):
    CONVERSATIONAL = "CONVERSATIONAL"
    NIRF_KNOWLEDGE = "NIRF_KNOWLEDGE"
    NIRF_ANALYTICAL = "NIRF_ANALYTICAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    AMBIGUOUS = "AMBIGUOUS"


class ConversationalSubintent(str, Enum):
    CAPABILITIES = "capabilities"
    LIMITATIONS = "limitations"
    USAGE_HELP = "usage_help"
    GRAPHS = "graphs"
    FUTURE_PREDICTION = "future_prediction"
    CHIT_CHAT = "chit_chat"


class IntentDecision(BaseModel):
    """Structured decision returned by the general intent classifier."""
    primary_intent: IntentCategory = Field(description="Primary category of the user query.")
    conversational_subintent: Optional[ConversationalSubintent] = Field(
        default=None,
        description="Specific subtype if primary_intent is CONVERSATIONAL."
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Helpful clarification question if primary_intent is AMBIGUOUS."
    )
    reasoning: str = Field(default="", description="Brief chain of thought explaining the classification.")


INTENT_CLASSIFIER_SYSTEM_PROMPT = """You are an expert intent understanding engine for the NIRF (National Institutional Ranking Framework) Conversational Assistant.

Your task is to classify the user's natural language question into exactly one primary_intent:

1. 'CONVERSATIONAL':
   - System capabilities: "what can you do?", "what are your features?", "what can you help me with?", "can you compare colleges?"
   - System limitations: "what u cannot do", "what can you not do?", "what are your limitations?", "what can't you answer?"
   - Graph/visualization meta-queries (ONLY general capability questions about whether charts are supported): "can you show graphs?", "do you have charts?", "can I see a plot?"
     CRITICAL: If the user asks to generate, show, or plot a graph, chart, or map for specific colleges, institutions, categories, or metrics (e.g. "generate map graph for top 10 colleges", "show graph of IIT Bombay", "plot distribution for engineering"), this is NIRF_ANALYTICAL, NOT CONVERSATIONAL!
   - Future prediction queries: "can you predict 2026 rankings?", "who will win next year?", "predict next year's score"
   - Usage help: "how do I use you?", "how should I ask questions?", "help"
   - Greetings, thanks, goodbyes, and pleasantries.

2. 'NIRF_KNOWLEDGE':
   - Explanations or definitions of NIRF methodology, metrics, parameters, scoring formulas, or ranking rules:
     "What is TLR?", "Explain RPC in simple words", "What does GO measure?", "How is NIRF ranking calculated?",
     "What is the difference between rank and composite score?", "Explain the five NIRF parameters".
   - Notice: The user is NOT asking to compute, filter, or rank specific institutional data, but rather to understand how the system or metrics work.

3. 'NIRF_ANALYTICAL':
   - The user is asking to perform calculations, filter rankings, look up institutions, track multi-year trends,
     compare colleges, examine category growth, analyze score distributions, outliers, state representation, or generate charts/maps for data:
     "generate map graph for top 10 colleges", "Compare IIT Bombay and IIT Madras in Engineering in 2025", "How the categories of colleges changed from 2017 to 2025?",
     "Show score distribution in Management in 2025", "Which colleges improved their rank the most?",
     "Which states have the most ranked colleges in 2025?".

4. 'OUT_OF_SCOPE':
   - The question is completely unrelated to Indian higher education institutions, NIRF rankings, or college analytics:
     "Who won the 2022 FIFA World Cup?", "Write python code to reverse a list", "How to make chicken curry?",
     "What is the capital of France?", "Write an essay on climate change".

5. 'AMBIGUOUS':
   - The query is an isolated keyword or fragmented phrase that lacks sufficient information to understand what is requested:
     "compare", "rankings", "colleges", "which is better".

Output valid JSON adhering strictly to the schema."""


class ConversationalIntentClassifier:
    """
    Two-stage intent classification engine:
    1. Instant deterministic fast path for obvious chit-chat and meta-queries.
    2. Gemma-powered structured understanding for semantic queries.
    """

    def __init__(
        self,
        client: Optional[GemmaClient] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
    ):
        self.client = client or get_gemma_client()
        self.capabilities = capability_registry or get_capability_registry()

    def classify_intent(
        self,
        query: str,
        context: Optional[Any] = None,
    ) -> IntentDecision:
        """
        Classifies user query into one of the 5 top-level intents with subintent mapping,
        taking into account conversation context for follow-up utterances.
        """
        q_raw = query.strip()
        q_clean = q_raw.lower()

        if not q_clean:
            return IntentDecision(
                primary_intent=IntentCategory.AMBIGUOUS,
                clarification_question="Please enter a question or explore our suggested queries.",
                reasoning="Empty input.",
            )

        # ---------------------------------------------------------------------
        # 1. Deterministic Fast Path: Obvious Greetings, Thanks, Goodbyes
        # ---------------------------------------------------------------------
        greeting_re = r"^(hi|hello|hey|namaste|greetings)(\s+there|\s+assistant|\s+all)?[\.!\?]*$"
        if re.search(greeting_re, q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.CONVERSATIONAL,
                conversational_subintent=ConversationalSubintent.CHIT_CHAT,
                reasoning="Standard greeting pattern match.",
            )

        thanks_re = r"^(thanks|thank\s+you|thx|many\s+thanks|much\s+appreciated)[\.!\?]*$"
        if re.search(thanks_re, q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.CONVERSATIONAL,
                conversational_subintent=ConversationalSubintent.CHIT_CHAT,
                reasoning="Standard thanks pattern match.",
            )

        goodbye_re = r"^(bye|goodbye|see\s+you|see\s+ya|farewell|take\s+care|good\s*night)[\.!\?]*$"
        if re.search(goodbye_re, q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.CONVERSATIONAL,
                conversational_subintent=ConversationalSubintent.CHIT_CHAT,
                reasoning="Standard goodbye pattern match.",
            )

        # ---------------------------------------------------------------------
        # 2. Fast Path: Common Meta / Capability Queries
        # ---------------------------------------------------------------------
        # Limitations (e.g. "what u cannot do", "what can you not do", "limitations")
        if re.search(r"\b(cannot\s+do|can'?t\s+do|can\s+not\s+do|limitations|what\s+can'?t\s+you|weaknesses)\b", q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.CONVERSATIONAL,
                conversational_subintent=ConversationalSubintent.LIMITATIONS,
                reasoning="Explicit limitations query.",
            )

        # Future prediction check (e.g. "can you predict 2026", "predict future rankings")
        if re.search(r"\b(predict|forecast|who\s+will\s+win|next\s+year)\b.*\b(2026|future|rankings?|scores?)\b", q_clean) or \
           re.search(r"\b(predict\s+next\s+year|forecast\s+rankings?)\b", q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.CONVERSATIONAL,
                conversational_subintent=ConversationalSubintent.FUTURE_PREDICTION,
                reasoning="Predictive modeling query (out of analytical scope).",
            )

        # Graph capability check (pure meta-question, e.g. "can you show graphs?", "do you support charts?")
        # Excludes actual analytical queries specifying entities, categories, or metrics (e.g. "generate map graph for top 10 colleges")
        has_analytical_targets = bool(re.search(
            r"\b(top\s+\d+|colleges?|institut\w+|universit\w+|engineering|management|pharmacy|medical|iit|nit|score|rank|tlr|rpc|go|oi|state|20\d\d)\b",
            q_clean
        ))
        if not has_analytical_targets:
            if re.search(r"^(can\s+you\s+(show|make|generate|produce|display)\s+(graphs?|charts?)|do\s+you\s+(support|have|make)\s+(graphs?|charts?)|can\s+i\s+see\s+(graphs?|charts?))[\.!\?]*$", q_clean) or \
               re.search(r"\b(graph|chart|visualization)\s+capabilities\b", q_clean):
                return IntentDecision(
                    primary_intent=IntentCategory.CONVERSATIONAL,
                    conversational_subintent=ConversationalSubintent.GRAPHS,
                    reasoning="Visualization capability query.",
                )

        # What can you do / capabilities
        if re.search(r"^(what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities|how\s+can\s+you\s+help|features|who\s+are\s+you)[\.!\?]*$", q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.CONVERSATIONAL,
                conversational_subintent=ConversationalSubintent.CAPABILITIES,
                reasoning="General capabilities inquiry.",
            )

        # Elliptical follow-up check when context is present
        if context and (getattr(context, "previous_category", None) or getattr(context, "previous_query_type", None)):
            if re.search(r"\b(now\s+do\s+the\s+same|same\s+for|what\s+about|now\s+include|also\s+add|include\s+also)\b", q_clean):
                return IntentDecision(
                    primary_intent=IntentCategory.NIRF_ANALYTICAL,
                    reasoning="Elliptical follow-up preserving previous context.",
                )

        # ---------------------------------------------------------------------
        # 3. Gemma-Powered Semantic Intent Understanding
        # ---------------------------------------------------------------------
        prompt_parts = []
        if context and (getattr(context, "previous_category", None) or getattr(context, "previous_query_type", None) or getattr(context, "previous_institution_names", None)):
            ctx_lines = ["PREVIOUS CONVERSATION CONTEXT:"]
            if getattr(context, "previous_query_type", None):
                ctx_lines.append(f"- Previous Analysis: {context.previous_query_type}")
            if getattr(context, "previous_category", None):
                ctx_lines.append(f"- Previous Category: {context.previous_category}")
            if getattr(context, "previous_institution_names", None):
                ctx_lines.append(f"- Previous Institutions: {', '.join(context.previous_institution_names)}")
            if getattr(context, "previous_year", None):
                ctx_lines.append(f"- Previous Year: {context.previous_year}")
            prompt_parts.append("\n".join(ctx_lines))

        prompt_parts.append(f"USER QUERY: {q_raw}")
        full_prompt = "\n\n".join(prompt_parts)

        try:
            raw_dict = self.client.generate_json(
                prompt=full_prompt,
                system_prompt=INTENT_CLASSIFIER_SYSTEM_PROMPT,
                schema=IntentDecision,
                temperature=0.0,
            )
            decision = IntentDecision.model_validate(raw_dict)
            return decision

        except GemmaClientError as ge:
            logger.warning("Gemma client failed during intent classification, using heuristic fallback: %s", ge)
            return self._heuristic_fallback(q_clean)
        except Exception as e:
            logger.warning("Unexpected error during intent classification, using heuristic fallback: %s", e)
            return self._heuristic_fallback(q_clean)

    def _heuristic_fallback(self, q_clean: str) -> IntentDecision:
        """Robust pattern fallback if LLM is unavailable."""
        # Knowledge patterns
        if re.search(r"\b(what\s+is\s+(tlr|rpc|go|oi|perception)|explain\s+(tlr|rpc|go|oi|perception)|methodology|formula)\b", q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.NIRF_KNOWLEDGE,
                reasoning="Heuristic match on methodology keywords.",
            )

        # Analytical patterns
        if re.search(r"\b(compare|trend|ranking|distribution|outlier|correlation|states?|top\s+\d+|20\d\d)\b", q_clean):
            return IntentDecision(
                primary_intent=IntentCategory.NIRF_ANALYTICAL,
                reasoning="Heuristic match on analytical keywords.",
            )

        # Default fallback
        return IntentDecision(
            primary_intent=IntentCategory.NIRF_ANALYTICAL,
            reasoning="Default heuristic fallback to analytical pipeline.",
        )

    def generate_conversational_response(self, decision: IntentDecision, query: str) -> str:
        """
        Generates dynamic, natural conversational responses in ChatGPT's conversational style,
        strictly grounded in actual system capabilities and empirical limitations.
        """
        system_prompt = (
            "You are a friendly, intelligent, and articulate conversational AI assistant specializing in India's National Institutional Ranking Framework (NIRF).\n"
            "Speak naturally, conversationally, and warmly, just like ChatGPT.\n\n"
            "CRITICAL OPERATIONAL RULES:\n"
            "1. Always be natural, helpful, engaging, and direct. Avoid sounding like a rigid template or reciting raw system error codes.\n"
            "2. Ground your knowledge strictly in the following verified boundaries:\n"
            f"- Available assessment years: {self.capabilities.start_year} to {self.capabilities.end_year}.\n"
            "- Core parameters: TLR (Teaching, Learning & Resources), RPC (Research and Professional Practice), GO (Graduation Outcomes), OI (Outreach and Inclusivity), Perception.\n"
            "- Supported analyses: compare institutions, multi-year ranking and score trends, score distributions, category evolution (2017–2025), outlier detection, and interactive Plotly graphs (including geographic India maps of institutions and states).\n"
            "- TRUE LIMITATIONS: You CANNOT predict future rankings (2026+). You have NO data on campus fees, hostel facilities, faculty salaries, or non-NIRF international rankings (QS/THE). Correlation does NOT imply causation. If data is unranked or missing, you never invent numbers.\n"
            "3. If the user asks an out-of-scope question, politely explain that you specialize in Indian institutional NIRF data and suggest relevant questions they can ask.\n"
            "4. If the query is ambiguous, ask a helpful, natural clarifying question without robotic jargon."
        )

        try:
            sub_label = decision.conversational_subintent.value if decision.conversational_subintent else "general"
            prompt = (
                f"User Intent: {decision.primary_intent.value} ({sub_label})\n"
                f"User Question: {query}\n\n"
                "Please provide a natural, articulate, ChatGPT-style response directly answering the user."
            )
            response = self.client.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.3)
            if response and response.strip():
                return response.strip()
        except Exception as e:
            logger.warning("Dynamic response generation failed, falling back to registry template: %s", e)

        # Robust fallback if LLM is unavailable
        if decision.primary_intent == IntentCategory.CONVERSATIONAL:
            sub = decision.conversational_subintent
            if sub == ConversationalSubintent.LIMITATIONS:
                return self.capabilities.get_limitations_response()
            elif sub == ConversationalSubintent.CAPABILITIES:
                return self.capabilities.get_capabilities_response()
            elif sub == ConversationalSubintent.GRAPHS:
                return self.capabilities.get_graphs_response()
            elif sub == ConversationalSubintent.FUTURE_PREDICTION:
                return self.capabilities.get_future_prediction_response()
            elif sub == ConversationalSubintent.USAGE_HELP:
                return self.capabilities.get_usage_guide()
            return self.capabilities.get_capabilities_response()

        elif decision.primary_intent == IntentCategory.OUT_OF_SCOPE:
            return self.capabilities.get_out_of_scope_response(query)

        elif decision.primary_intent == IntentCategory.AMBIGUOUS:
            return self.capabilities.get_ambiguous_response(query, decision.clarification_question)

        return self.capabilities.get_capabilities_response()


def get_intent_classifier() -> ConversationalIntentClassifier:
    """Returns singleton instance of ConversationalIntentClassifier."""
    return ConversationalIntentClassifier()

