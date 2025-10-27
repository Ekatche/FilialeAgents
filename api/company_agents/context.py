"""
Context variables for tracking session information across async calls.
"""

from contextvars import ContextVar
from typing import Optional

# ContextVar to store current session_id across all async calls
# This allows tools to access the session_id without passing it as parameter
current_session_id: ContextVar[Optional[str]] = ContextVar(
    'current_session_id',
    default=None
)


def set_session_context(session_id: str):
    """
    Set the session_id in the current async context.
    Should be called at the beginning of each extraction.

    Args:
        session_id: The session ID to use for this extraction
    """
    current_session_id.set(session_id)


def get_session_context() -> str:
    """
    Get the current session_id from context.

    Returns:
        The current session_id or 'default-session' if not set
    """
    session_id = current_session_id.get()
    return session_id if session_id else 'default-session'


def clear_session_context():
    """
    Clear the session context.
    Should be called after extraction completes or on error.
    """
    current_session_id.set(None)
