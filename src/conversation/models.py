"""
Pydantic Data Models for Conversation Memory and Multi-Turn Sessions (Phase 8).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from src.query_engine.schemas import ConversationContext


class ConversationTurnRecord(BaseModel):
    """Immutable record of a single conversational turn stored in SQLite."""
    model_config = ConfigDict(extra="ignore")

    turn_id: str = Field(description="Unique identifier for the turn.")
    session_id: str = Field(description="Foreign key session identifier.")
    turn_index: int = Field(description="Sequential turn index (1-based) within session.")
    user_query: str = Field(description="The user's original query text.")
    assistant_response: str = Field(description="The verified natural-language answer or conversational text.")
    intent: str = Field(default="ANALYTICAL_QUERY", description="Classified intent.")
    query_type: Optional[str] = Field(default=None, description="Analytical query type if applicable.")
    plan_json: Optional[str] = Field(default=None, description="Serialized QueryPlan JSON.")
    execution_summary_json: Optional[str] = Field(default=None, description="Serialized execution summary.")
    claims_json: Optional[str] = Field(default=None, description="Serialized verified claims JSON.")
    verification_status: Optional[str] = Field(default=None, description="Response verification standing.")
    context_snapshot: Optional[ConversationContext] = Field(
        default=None,
        description="Snapshot of active ConversationContext at end of turn."
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp."
    )


class SessionSummary(BaseModel):
    """Metadata summary of a conversation session."""
    model_config = ConfigDict(extra="ignore")

    session_id: str = Field(description="Unique session identifier.")
    title: str = Field(default="New Conversation", description="User-facing conversation title.")
    created_at: str = Field(description="ISO 8601 creation timestamp.")
    updated_at: str = Field(description="ISO 8601 last activity timestamp.")
    turn_count: int = Field(default=0, description="Total number of conversational turns recorded.")
    last_query: Optional[str] = Field(default=None, description="Most recent user query in session.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags.")
