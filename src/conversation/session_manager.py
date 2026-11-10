"""
High-Level Session and Memory Management Service (Phase 8).
Coordinates conversation sessions, turn recording, context inheritance derivation,
and SQLite persistence for both conversational interfaces and automated pipelines.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from src.conversation.models import ConversationTurnRecord, SessionSummary
from src.conversation.sqlite_store import SQLiteConversationStore, DEFAULT_DB_PATH
from src.query_engine.schemas import ConversationContext, QueryPlan
from src.execution.result_schema import ExecutionResult
from src.response.result_schema import GeneratedResponse

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Central manager for multi-turn conversation sessions.
    Handles context preservation, follow-up query enrichment, and state persistence.
    """

    def __init__(self, store: Optional[SQLiteConversationStore] = None):
        self.store = store or SQLiteConversationStore()

    def start_new_session(
        self,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Initializes a new persistent conversation session."""
        return self.store.get_or_create_session(
            session_id=session_id,
            title=title,
            metadata=metadata,
        )

    def get_active_context(self, session_id: str) -> ConversationContext:
        """Retrieves active conversation context with inherited filters."""
        return self.store.get_context(session_id)

    def record_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        intent: str,
        query_plan: Optional[QueryPlan] = None,
        execution_result: Optional[ExecutionResult] = None,
        generated_response: Optional[GeneratedResponse] = None,
    ) -> ConversationTurnRecord:
        """
        Records a completed conversation turn and automatically updates
        the persisted conversation context based on analytical operations executed.
        """
        # Ensure session exists
        self.store.get_or_create_session(session_id)

        # Retrieve current context
        current_ctx = self.store.get_context(session_id)

        # Derive updated context if analytical operation succeeded
        updated_ctx = self._derive_updated_context(
            current_ctx=current_ctx,
            plan=query_plan,
            exec_res=execution_result,
        )

        plan_dict = query_plan.model_dump() if query_plan else None
        exec_summary = None
        if execution_result:
            exec_summary = {
                "execution_id": execution_result.execution_id,
                "status": execution_result.status,
                "operations_count": len(execution_result.operations),
                "warnings": execution_result.warnings,
            }

        claims_list = None
        ver_status = None
        if generated_response:
            ver_status = getattr(generated_response, "response_status", "VERIFIED")
            if hasattr(ver_status, "value"):
                ver_status = ver_status.value
            elif not isinstance(ver_status, str):
                ver_status = str(ver_status)
            if generated_response.numerical_claims:
                claims_list = [c.model_dump() for c in generated_response.numerical_claims]

        query_type = query_plan.query_type if query_plan else None

        record = self.store.save_turn(
            session_id=session_id,
            user_query=user_query,
            assistant_response=assistant_response,
            intent=intent,
            query_type=query_type,
            plan_dict=plan_dict,
            execution_summary=exec_summary,
            claims=claims_list,
            verification_status=ver_status,
            context=updated_ctx,
        )

        return record

    def _derive_updated_context(
        self,
        current_ctx: ConversationContext,
        plan: Optional[QueryPlan],
        exec_res: Optional[ExecutionResult],
    ) -> ConversationContext:
        """
        Derives updated conversation context from execution.
        Follows strict inheritance boundaries:
        - Cross-category evolution queries do NOT overwrite specific discipline filters.
        - Additive entity lists (institutions/states) are appended without data loss.
        """
        if not plan or not plan.operations:
            return current_ctx

        # Do not inherit or update filters for meta/evolution queries
        if plan.query_type == "category_evolution":
            return current_ctx

        # Check if execution succeeded
        if exec_res and exec_res.status not in ["SUCCESS", "PARTIAL_SUCCESS"]:
            return current_ctx

        op0 = plan.operations[0]

        # Merge institutions (preserve order and uniqueness)
        merged_institutions = list(current_ctx.previous_institution_names or [])
        if op0.institution_names:
            for inst in op0.institution_names:
                if inst not in merged_institutions:
                    merged_institutions.append(inst)

        # Merge states
        merged_states = list(current_ctx.previous_states or [])
        if op0.states:
            for st in op0.states:
                if st not in merged_states:
                    merged_states.append(st)

        # Update parameters
        merged_params = op0.parameters if op0.parameters else current_ctx.previous_parameters

        updated = ConversationContext(
            previous_category=op0.category or current_ctx.previous_category,
            previous_year=op0.year or current_ctx.previous_year,
            previous_start_year=op0.start_year or current_ctx.previous_start_year,
            previous_end_year=op0.end_year or current_ctx.previous_end_year,
            previous_states=merged_states if merged_states else None,
            previous_institution_names=merged_institutions if merged_institutions else None,
            previous_institution_uids=op0.institution_uids if op0.institution_uids else current_ctx.previous_institution_uids,
            previous_parameters=merged_params,
            previous_top_n=op0.top_n or current_ctx.previous_top_n,
            previous_query_type=plan.query_type,
        )

        return updated

    def reset_context(self, session_id: str) -> None:
        """Resets active context for session while preserving turn history."""
        self.store.reset_context(session_id)

    def get_history(self, session_id: str, limit: int = 50) -> List[ConversationTurnRecord]:
        """Retrieves conversational turn history."""
        return self.store.get_turns(session_id, limit=limit)

    def list_all_sessions(self, limit: int = 30) -> List[SessionSummary]:
        """Lists existing persistent sessions."""
        return self.store.list_sessions(limit=limit)

    def delete_session(self, session_id: str) -> bool:
        """Deletes session."""
        return self.store.delete_session(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clears session messages and resets context."""
        return self.store.clear_session(session_id)


_SESSION_MANAGER_INSTANCE: Optional[SessionManager] = None


def get_session_manager(db_path: Optional[Path | str] = None) -> SessionManager:
    """Returns singleton SessionManager instance."""
    global _SESSION_MANAGER_INSTANCE
    if _SESSION_MANAGER_INSTANCE is None or db_path is not None:
        store = SQLiteConversationStore(db_path=db_path)
        _SESSION_MANAGER_INSTANCE = SessionManager(store=store)
    return _SESSION_MANAGER_INSTANCE

