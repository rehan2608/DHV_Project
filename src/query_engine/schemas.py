"""
Standardized Pydantic Schemas for NIRF Natural-Language Query Plans (Phase 3).
Defines machine-readable, strictly-typed schemas for query intents, analytical operations,
entities, filters, context inheritance, and validation results.
"""

from typing import List, Dict, Any, Optional, Literal, Union
import uuid
from pydantic import BaseModel, Field, ConfigDict


QueryType = Literal[
    "institution_trend",
    "rank_movement",
    "category_performance",
    "geographic_analysis",
    "parameter_correlation",
    "parameter_relationship",
    "multidimensional_performance",
    "score_distribution",
    "rank_transitions",
    "outlier_analysis",
    "category_evolution",
    "multi_operation",
    "clarification_required",
    "unsupported",
]

AnalyticalFunctionName = Literal[
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
    "get_category_evolution",
]

ValidationStatus = Literal[
    "VALID",
    "VALID_WITH_WARNINGS",
    "CLARIFICATION_REQUIRED",
    "INVALID",
    "UNSUPPORTED",
]


class VisualizationPreference(BaseModel):
    """User preferences for response formatting and visualization."""
    chart_requested: bool = Field(default=False, description="Whether the user explicitly or implicitly asks for a chart.")
    preferred_chart_type: Optional[str] = Field(
        default=None,
        description="Suggested chart type: 'bar', 'horizontal_bar', 'line', 'scatter', 'histogram', 'table', etc."
    )
    comparison_requested: bool = Field(default=False, description="Whether comparative presentation is requested.")
    explanation_requested: bool = Field(default=False, description="Whether explanatory text is requested.")


class ConversationContext(BaseModel):
    """Context state for tracking follow-up questions and inherited constraints."""
    previous_category: Optional[str] = None
    previous_year: Optional[int] = None
    previous_start_year: Optional[int] = None
    previous_end_year: Optional[int] = None
    previous_states: Optional[List[str]] = Field(default_factory=list)
    previous_institution_names: Optional[List[str]] = Field(default_factory=list)
    previous_institution_uids: Optional[List[str]] = Field(default_factory=list)
    previous_parameters: Optional[List[str]] = Field(default_factory=list)
    previous_top_n: Optional[int] = None
    previous_query_type: Optional[str] = None
    inherited_fields: List[str] = Field(default_factory=list, description="Fields inherited from previous turn.")
    modified_fields: List[str] = Field(default_factory=list, description="Fields explicitly modified in this turn.")


class AnalyticalOperation(BaseModel):
    """Specification of a single Phase 2 analytical function invocation."""
    operation_id: str = Field(default="op_1", description="Unique operation identifier in the plan.")
    function_name: AnalyticalFunctionName = Field(description="Exact public API function name in Phase 2.")
    description: str = Field(default="", description="Human-readable summary of this operation.")
    category: Optional[str] = Field(default=None, description="Standardized category (e.g. 'Engineering').")
    year: Optional[int] = Field(default=None, description="Single edition year (e.g. 2025).")
    start_year: Optional[int] = Field(default=None, description="Starting edition year for multi-year tracking.")
    end_year: Optional[int] = Field(default=None, description="Ending edition year for multi-year tracking.")
    states: List[str] = Field(default_factory=list, description="List of target states (supports multiple states).")
    institution_names: List[str] = Field(default_factory=list, description="Target institution names or acronyms.")
    institution_uids: List[str] = Field(default_factory=list, description="Target standardized institution UIDs.")
    parameters: List[str] = Field(default_factory=list, description="Specific parameters requested (e.g. ['rpc', 'tlr']).")
    metric: Optional[str] = Field(default=None, description="Target metric for distribution/outliers (e.g. 'score', 'rpc').")
    param_x: Optional[str] = Field(default=None, description="Independent parameter for bivariate relationship.")
    param_y: Optional[str] = Field(default=None, description="Dependent parameter for bivariate relationship.")
    top_n: Optional[int] = Field(default=None, description="Limit on top institutions.")
    movement_type: Optional[str] = Field(default="both", description="'both', 'improvement', or 'decline'.")
    correlation_method: Optional[str] = Field(default="both", description="'both', 'pearson', or 'spearman'.")
    outlier_method: Optional[str] = Field(default="iqr", description="'iqr' or 'z_score'.")
    outlier_threshold: Optional[float] = Field(default=1.5, description="Threshold multiplier for outlier detection.")
    lookback_years: Optional[List[int]] = Field(default=None, description="Years for rank volatility analysis.")
    bins_count: Optional[int] = Field(default=10, description="Bin count for histograms.")
    multi_year_trend: Optional[bool] = Field(default=False, description="Whether to aggregate across all years.")
    custom_bands: Optional[List[Any]] = Field(default=None, description="Custom ranking bands.")
    applied_defaults: Dict[str, Any] = Field(default_factory=dict, description="Audit record of inferred default values.")
    depends_on: Optional[str] = Field(default=None, description="Operation ID that must execute before this one.")


class QueryPlan(BaseModel):
    """Top-level standardized query plan generated by Gemma and validated by QueryValidator."""
    model_config = ConfigDict(extra="ignore")

    query_id: str = Field(default_factory=lambda: f"qp_{uuid.uuid4().hex[:8]}")
    original_question: str = Field(description="The exact user question.")
    query_type: QueryType = Field(description="Classified analytical intent or query category.")
    analytical_intent: str = Field(description="Concise description of the user's analytical goal.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in plan extraction.")
    operations: List[AnalyticalOperation] = Field(default_factory=list, description="Ordered list of analytical operations.")
    conversation_context: Optional[ConversationContext] = Field(default=None, description="Inherited follow-up context.")
    visualization: VisualizationPreference = Field(default_factory=VisualizationPreference)
    clarification_message: Optional[str] = Field(default=None, description="Message to user if clarification is needed.")
    unsupported_reason: Optional[str] = Field(default=None, description="Reason why the query cannot be handled.")
    semantic_retrieval_needed: bool = Field(default=False, description="True if methodology / definitions are asked.")


class QueryValidationResult(BaseModel):
    """Result produced by the independent QueryValidator."""
    is_valid: bool = Field(description="True if the plan is executable by the analytical engine.")
    status: ValidationStatus = Field(description="Validation standing.")
    errors: List[str] = Field(default_factory=list, description="Fatal blocking issues.")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or cautionary notes.")
    comparability_notes: List[str] = Field(default_factory=list, description="Official NIRF comparability rules notes.")
    resolved_entities: Dict[str, Any] = Field(default_factory=dict, description="Standardized names, UIDs, and states.")
    validated_plan: Optional[QueryPlan] = Field(default=None, description="The validated (and sanitized) QueryPlan.")

    def summary(self) -> str:
        lines = [f"Query Plan Validation: {self.status} (Valid: {self.is_valid})"]
        if self.errors:
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  [ERROR] {e}")
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  [WARNING] {w}")
        if self.comparability_notes:
            lines.append("Comparability Notes:")
            for n in self.comparability_notes:
                lines.append(f"  [NOTE] {n}")
        return "\n".join(lines)

