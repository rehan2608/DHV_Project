"""
SQLite Persistence Store for Conversation Memory (Phase 8).
Provides ACID-compliant, persistent relational storage for conversation sessions,
turn trajectories, verification audits, and active filter contexts.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import sqlite3
import json
import uuid
import logging
from datetime import datetime, timezone

from src.conversation.models import ConversationTurnRecord, SessionSummary
from src.query_engine.schemas import ConversationContext

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "conversations.db"


class SQLiteConversationStore:
    """
    Relational SQLite persistence store for NIRF conversational memory.
    Manages session lifecycle, turn recording, and context snapshots across app restarts.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._ensure_db_dir()
        self._init_tables()

    def _ensure_db_dir(self) -> None:
        """Ensures the parent directory for the database exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a SQLite connection with foreign keys and WAL mode enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_tables(self) -> None:
        """Initializes relational tables if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    user_query TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    query_type TEXT,
                    plan_json TEXT,
                    execution_summary_json TEXT,
                    claims_json TEXT,
                    verification_status TEXT,
                    context_snapshot_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_turns_session_idx 
                ON turns(session_id, turn_index);

                CREATE TABLE IF NOT EXISTS context_state (
                    session_id TEXT PRIMARY KEY,
                    previous_category TEXT,
                    previous_year INTEGER,
                    previous_start_year INTEGER,
                    previous_end_year INTEGER,
                    previous_states TEXT,
                    previous_institution_names TEXT,
                    previous_institution_uids TEXT,
                    previous_parameters TEXT,
                    previous_top_n INTEGER,
                    previous_query_type TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)
            conn.commit()

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Retrieves existing session ID or creates a new persistent session record.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            if session_id:
                row = conn.execute(
                    "SELECT session_id FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if row:
                    return row["session_id"]

            sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
            stitle = title or "New Conversation"
            meta_str = json.dumps(metadata or {})
            conn.execute(
                """
                INSERT INTO sessions (session_id, title, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, stitle, now, now, meta_str),
            )
            # Initialize empty context state for new session
            conn.execute(
                """
                INSERT INTO context_state (session_id, updated_at)
                VALUES (?, ?)
                """,
                (sid, now),
            )
            conn.commit()
            return sid

    def save_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        intent: str = "ANALYTICAL_QUERY",
        query_type: Optional[str] = None,
        plan_dict: Optional[Dict[str, Any]] = None,
        execution_summary: Optional[Dict[str, Any]] = None,
        claims: Optional[List[Dict[str, Any]]] = None,
        verification_status: Optional[str] = None,
        context: Optional[ConversationContext] = None,
    ) -> ConversationTurnRecord:
        """
        Persists a completed conversational turn into the SQLite store
        and updates the active conversation context.
        """
        now = datetime.now(timezone.utc).isoformat()
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"

        # Ensure session exists
        self.get_or_create_session(session_id)

        with self._get_connection() as conn:
            # Determine next turn index
            row = conn.execute(
                "SELECT COALESCE(MAX(turn_index), 0) + 1 AS next_idx FROM turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            turn_index = row["next_idx"] if row else 1

            plan_str = json.dumps(plan_dict) if plan_dict else None
            exec_str = json.dumps(execution_summary) if execution_summary else None
            claims_str = json.dumps(claims) if claims else None
            ctx_snapshot = context or self.get_context(session_id)
            ctx_str = ctx_snapshot.model_dump_json() if ctx_snapshot else None

            conn.execute(
                """
                INSERT INTO turns (
                    turn_id, session_id, turn_index, user_query, assistant_response,
                    intent, query_type, plan_json, execution_summary_json, claims_json,
                    verification_status, context_snapshot_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_id, session_id, turn_index, user_query, assistant_response,
                    intent, query_type, plan_str, exec_str, claims_str,
                    verification_status, ctx_str, now
                ),
            )

            # Update session title from first user query if still default
            sess = conn.execute("SELECT title FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if sess and sess["title"] == "New Conversation":
                clean_title = (user_query[:35] + "...") if len(user_query) > 35 else user_query
                conn.execute(
                    "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                    (clean_title, now, session_id),
                )
            else:
                conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))

            conn.commit()

        # Update persisted context state
        if context:
            self.save_context(session_id, context)

        return ConversationTurnRecord(
            turn_id=turn_id,
            session_id=session_id,
            turn_index=turn_index,
            user_query=user_query,
            assistant_response=assistant_response,
            intent=intent,
            query_type=query_type,
            plan_json=plan_str,
            execution_summary_json=exec_str,
            claims_json=claims_str,
            verification_status=verification_status,
            context_snapshot=ctx_snapshot,
            created_at=now,
        )

    def get_context(self, session_id: str) -> ConversationContext:
        """
        Retrieves the active ConversationContext for a session.
        Returns empty ConversationContext if session is new or context has been reset.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM context_state WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return ConversationContext()

            states = json.loads(row["previous_states"]) if row["previous_states"] else []
            inst_names = json.loads(row["previous_institution_names"]) if row["previous_institution_names"] else []
            inst_uids = json.loads(row["previous_institution_uids"]) if row["previous_institution_uids"] else []
            params = json.loads(row["previous_parameters"]) if row["previous_parameters"] else []

            return ConversationContext(
                previous_category=row["previous_category"],
                previous_year=row["previous_year"],
                previous_start_year=row["previous_start_year"],
                previous_end_year=row["previous_end_year"],
                previous_states=states,
                previous_institution_names=inst_names,
                previous_institution_uids=inst_uids,
                previous_parameters=params,
                previous_top_n=row["previous_top_n"],
                previous_query_type=row["previous_query_type"],
            )

    def save_context(self, session_id: str, context: ConversationContext) -> None:
        """
        Persists updated ConversationContext for the session.
        """
        now = datetime.now(timezone.utc).isoformat()
        states_str = json.dumps(context.previous_states or [])
        names_str = json.dumps(context.previous_institution_names or [])
        uids_str = json.dumps(context.previous_institution_uids or [])
        params_str = json.dumps(context.previous_parameters or [])

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO context_state (
                    session_id, previous_category, previous_year, previous_start_year,
                    previous_end_year, previous_states, previous_institution_names,
                    previous_institution_uids, previous_parameters, previous_top_n,
                    previous_query_type, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    previous_category=excluded.previous_category,
                    previous_year=excluded.previous_year,
                    previous_start_year=excluded.previous_start_year,
                    previous_end_year=excluded.previous_end_year,
                    previous_states=excluded.previous_states,
                    previous_institution_names=excluded.previous_institution_names,
                    previous_institution_uids=excluded.previous_institution_uids,
                    previous_parameters=excluded.previous_parameters,
                    previous_top_n=excluded.previous_top_n,
                    previous_query_type=excluded.previous_query_type,
                    updated_at=excluded.updated_at
                """,
                (
                    session_id, context.previous_category, context.previous_year,
                    context.previous_start_year, context.previous_end_year,
                    states_str, names_str, uids_str, params_str, context.previous_top_n,
                    context.previous_query_type, now
                ),
            )
            conn.commit()

    def reset_context(self, session_id: str) -> None:
        """
        Clears inherited context filters for a session while preserving message history.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE context_state SET
                    previous_category=NULL, previous_year=NULL, previous_start_year=NULL,
                    previous_end_year=NULL, previous_states=NULL, previous_institution_names=NULL,
                    previous_institution_uids=NULL, previous_parameters=NULL, previous_top_n=NULL,
                    previous_query_type=NULL, updated_at=?
                WHERE session_id=?
                """,
                (now, session_id),
            )
            conn.commit()

    def get_turns(self, session_id: str, limit: int = 50) -> List[ConversationTurnRecord]:
        """
        Retrieves ordered turn records for a session.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM turns 
                WHERE session_id = ? 
                ORDER BY turn_index ASC 
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

            turns = []
            for r in rows:
                ctx_snap = None
                if r["context_snapshot_json"]:
                    try:
                        ctx_snap = ConversationContext.model_validate_json(r["context_snapshot_json"])
                    except Exception:
                        pass

                turns.append(ConversationTurnRecord(
                    turn_id=r["turn_id"],
                    session_id=r["session_id"],
                    turn_index=r["turn_index"],
                    user_query=r["user_query"],
                    assistant_response=r["assistant_response"],
                    intent=r["intent"],
                    query_type=r["query_type"],
                    plan_json=r["plan_json"],
                    execution_summary_json=r["execution_summary_json"],
                    claims_json=r["claims_json"],
                    verification_status=r["verification_status"],
                    context_snapshot=ctx_snap,
                    created_at=r["created_at"],
                ))
            return turns

    def list_sessions(self, limit: int = 30) -> List[SessionSummary]:
        """
        Lists all conversation sessions ordered by most recently updated.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT 
                    s.session_id, s.title, s.created_at, s.updated_at, s.metadata_json,
                    COUNT(t.turn_id) AS turn_count,
                    (SELECT user_query FROM turns WHERE session_id = s.session_id ORDER BY turn_index DESC LIMIT 1) AS last_query
                FROM sessions s
                LEFT JOIN turns t ON s.session_id = t.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            summaries = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                summaries.append(SessionSummary(
                    session_id=r["session_id"],
                    title=r["title"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    turn_count=r["turn_count"],
                    last_query=r["last_query"],
                    metadata=meta,
                ))
            return summaries

    def delete_session(self, session_id: str) -> bool:
        """Deletes a conversation session and all its associated turns and context."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_session(self, session_id: str) -> bool:
        """Clears all turns and resets context for a session while keeping the session record."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
            self.reset_context(session_id)
            conn.commit()
            return True
