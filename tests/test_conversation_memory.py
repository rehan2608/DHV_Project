"""
Unit Tests for Phase 8: Conversation Memory & SQLite Persistence.
Validates session state lifecycle, SQLite persistence across reloads,
multi-turn context inheritance, and follow-up query enrichment.
"""

import pytest
import tempfile
from pathlib import Path

from src.conversation.sqlite_store import SQLiteConversationStore
from src.conversation.session_manager import SessionManager
from src.query_engine.schemas import ConversationContext, QueryPlan, AnalyticalOperation
from src.execution.result_schema import ExecutionResult, OperationResult


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated temporary SQLite database for testing."""
    db_file = tmp_path / "test_conversations.db"
    return db_file


@pytest.fixture
def session_mgr(temp_db):
    """Provides a fresh SessionManager connected to the temporary database."""
    store = SQLiteConversationStore(db_path=temp_db)
    return SessionManager(store=store)


class TestSQLiteStoreLifecycle:
    """Verifies low-level SQLite store operations."""

    def test_session_creation_and_listing(self, temp_db):
        store = SQLiteConversationStore(db_path=temp_db)
        sid = store.get_or_create_session(title="Engineering Comparison")
        assert sid.startswith("sess_")

        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == sid
        assert sessions[0].title == "Engineering Comparison"
        assert sessions[0].turn_count == 0

    def test_turn_recording_and_context_persistence(self, temp_db):
        store = SQLiteConversationStore(db_path=temp_db)
        sid = store.get_or_create_session()

        ctx = ConversationContext(
            previous_category="Engineering",
            previous_year=2025,
            previous_institution_names=["IIT Madras", "IIT Bombay"],
        )

        turn = store.save_turn(
            session_id=sid,
            user_query="Compare IIT Bombay and IIT Madras in Engineering in 2025.",
            assistant_response="IIT Madras ranks 1st while IIT Bombay ranks 3rd.",
            intent="ANALYTICAL_QUERY",
            query_type="institution_comparison",
            context=ctx,
        )

        assert turn.turn_index == 1
        assert turn.user_query == "Compare IIT Bombay and IIT Madras in Engineering in 2025."

        # Verify context retrieved from SQLite matches persisted snapshot
        loaded_ctx = store.get_context(sid)
        assert loaded_ctx.previous_category == "Engineering"
        assert loaded_ctx.previous_year == 2025
        assert "IIT Madras" in loaded_ctx.previous_institution_names
        assert "IIT Bombay" in loaded_ctx.previous_institution_names

    def test_persistence_across_reloads(self, temp_db):
        """Simulates restarting the application by opening a new SQLiteStore connection."""
        store1 = SQLiteConversationStore(db_path=temp_db)
        sid = store1.get_or_create_session(title="Trend Session")
        store1.save_turn(
            session_id=sid,
            user_query="Show IIT Delhi trend from 2020 to 2025",
            assistant_response="IIT Delhi remained steadily in top 3.",
            intent="ANALYTICAL_QUERY",
            context=ConversationContext(previous_category="Engineering", previous_year=2025),
        )

        # Open completely fresh store instance pointing to same file
        store2 = SQLiteConversationStore(db_path=temp_db)
        turns = store2.get_turns(sid)
        assert len(turns) == 1
        assert turns[0].user_query == "Show IIT Delhi trend from 2020 to 2025"

        ctx2 = store2.get_context(sid)
        assert ctx2.previous_category == "Engineering"


class TestMultiTurnFollowUpMemory:
    """Verifies that multi-turn follow-up queries retain and evolve context correctly."""

    def test_multi_turn_additive_follow_up(self, session_mgr):
        sid = session_mgr.start_new_session(title="Additive Test")

        # Turn 1: Base Comparison
        op1 = AnalyticalOperation(
            operation_id="op_1",
            function_name="get_category_performance",
            category="Engineering",
            year=2025,
            institution_names=["IIT Bombay", "IIT Madras"],
        )
        plan1 = QueryPlan(
            original_question="Compare IIT Bombay and IIT Madras in Engineering for 2025",
            query_type="category_performance",
            analytical_intent="Compare two colleges",
            operations=[op1],
        )
        exec1 = ExecutionResult(
            query_id="q_1",
            query_type="category_performance",
            validation_status="VALID",
            original_question=plan1.original_question,
            execution_id="exec_1",
            status="SUCCESS",
            operations=[OperationResult(operation_id="op_1", function_name="get_category_performance", status="SUCCESS")],
        )

        session_mgr.record_turn(
            session_id=sid,
            user_query="Compare IIT Bombay and IIT Madras in Engineering for 2025",
            assistant_response="Comparison generated.",
            intent="ANALYTICAL_QUERY",
            query_plan=plan1,
            execution_result=exec1,
        )

        ctx_after_turn1 = session_mgr.get_active_context(sid)
        assert ctx_after_turn1.previous_category == "Engineering"
        assert ctx_after_turn1.previous_year == 2025
        assert set(ctx_after_turn1.previous_institution_names) == {"IIT Bombay", "IIT Madras"}

        # Turn 2: Follow-up adding third institution
        op2 = AnalyticalOperation(
            operation_id="op_2",
            function_name="get_category_performance",
            category="Engineering",
            year=2025,
            institution_names=["IIT Delhi"],
        )
        plan2 = QueryPlan(
            original_question="Now include IIT Delhi.",
            query_type="category_performance",
            analytical_intent="Add IIT Delhi to comparison",
            operations=[op2],
        )
        exec2 = ExecutionResult(
            query_id="q_2",
            query_type="category_performance",
            validation_status="VALID",
            original_question=plan2.original_question,
            execution_id="exec_2",
            status="SUCCESS",
            operations=[OperationResult(operation_id="op_2", function_name="get_category_performance", status="SUCCESS")],
        )

        session_mgr.record_turn(
            session_id=sid,
            user_query="Now include IIT Delhi.",
            assistant_response="IIT Delhi added to comparison.",
            intent="ANALYTICAL_QUERY",
            query_plan=plan2,
            execution_result=exec2,
        )

        # Context should now contain all 3 institutions seamlessly
        ctx_after_turn2 = session_mgr.get_active_context(sid)
        assert set(ctx_after_turn2.previous_institution_names) == {"IIT Bombay", "IIT Madras", "IIT Delhi"}
        assert ctx_after_turn2.previous_category == "Engineering"

    def test_year_shift_preserves_institutions_and_category(self, session_mgr):
        sid = session_mgr.start_new_session()

        # Turn 1
        op1 = AnalyticalOperation(
            operation_id="op_1",
            function_name="get_category_performance",
            category="Management",
            year=2025,
            institution_names=["IIM Ahmedabad", "IIM Bangalore"],
        )
        plan1 = QueryPlan(
            original_question="Compare IIM Ahmedabad and IIM Bangalore in Management in 2025",
            query_type="category_performance",
            analytical_intent="Compare IIMs",
            operations=[op1],
        )
        session_mgr.record_turn(
            session_id=sid,
            user_query=plan1.original_question,
            assistant_response="IIM Ahmedabad ranks 1st.",
            intent="ANALYTICAL_QUERY",
            query_plan=plan1,
            execution_result=ExecutionResult(query_id="q1", query_type="category_performance", validation_status="VALID", original_question=plan1.original_question, execution_id="e1", status="SUCCESS", operations=[]),
        )

        # Turn 2: Shift year to 2024
        op2 = AnalyticalOperation(
            operation_id="op_2",
            function_name="get_category_performance",
            category="Management",
            year=2024,
            institution_names=[],
        )
        plan2 = QueryPlan(
            original_question="What about 2024?",
            query_type="category_performance",
            analytical_intent="Shift year to 2024",
            operations=[op2],
        )
        session_mgr.record_turn(
            session_id=sid,
            user_query="What about 2024?",
            assistant_response="In 2024, IIM Ahmedabad was also 1st.",
            intent="ANALYTICAL_QUERY",
            query_plan=plan2,
            execution_result=ExecutionResult(query_id="q2", query_type="category_performance", validation_status="VALID", original_question=plan2.original_question, execution_id="e2", status="SUCCESS", operations=[]),
        )

        ctx2 = session_mgr.get_active_context(sid)
        assert ctx2.previous_year == 2024
        assert ctx2.previous_category == "Management"
        assert "IIM Ahmedabad" in ctx2.previous_institution_names

    def test_context_reset_preserves_turn_history(self, session_mgr):
        sid = session_mgr.start_new_session()
        session_mgr.record_turn(
            session_id=sid,
            user_query="Show top 5 colleges in 2025",
            assistant_response="Top 5 colleges listed.",
            intent="ANALYTICAL_QUERY",
            query_plan=QueryPlan(
                original_question="Show top 5 colleges in 2025",
                query_type="category_performance",
                analytical_intent="Top colleges",
                operations=[AnalyticalOperation(operation_id="op1", function_name="get_category_performance", category="College", year=2025)],
            ),
            execution_result=ExecutionResult(query_id="q3", query_type="category_performance", validation_status="VALID", original_question="q", execution_id="e", status="SUCCESS", operations=[]),
        )

        # Reset active context
        session_mgr.reset_context(sid)
        ctx = session_mgr.get_active_context(sid)
        assert ctx.previous_category is None
        assert ctx.previous_year is None

        # Turns should still be preserved
        history = session_mgr.get_history(sid)
        assert len(history) == 1
        assert history[0].user_query == "Show top 5 colleges in 2025"
