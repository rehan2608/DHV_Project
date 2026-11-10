"""
Conversation Memory & Session Management Package (Phase 8).
Provides persistent SQLite storage and session state management for multi-turn
conversational context, follow-up query resolution, and historical trajectory audit.
"""

from src.conversation.models import ConversationTurnRecord, SessionSummary
from src.conversation.sqlite_store import SQLiteConversationStore
from src.conversation.session_manager import SessionManager, get_session_manager

__all__ = [
    "ConversationTurnRecord",
    "SessionSummary",
    "SQLiteConversationStore",
    "SessionManager",
    "get_session_manager",
]

