"""
Tracker global pour les tokens utilisés par les tools.
Utilise contextvars pour associer les tokens au session_id.
"""

from contextvars import ContextVar
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# ContextVar pour stocker les tokens des tools par session
_tool_tokens_store: ContextVar[Dict[str, List[Dict[str, Any]]]] = ContextVar(
    'tool_tokens_store',
    default={}
)


class ToolTokensTracker:
    """Tracker global pour les tokens des tools."""

    @staticmethod
    def start_session(session_id: str):
        """Démarre le tracking pour une nouvelle session."""
        store = _tool_tokens_store.get().copy()
        store[session_id] = []
        _tool_tokens_store.set(store)
        logger.info(f"🔧 [ToolTracker] Session démarrée: {session_id}")

    @staticmethod
    def add_tool_usage(
        session_id: str,
        tool_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ):
        """Ajoute l'usage d'un tool."""
        store = _tool_tokens_store.get().copy()

        if session_id not in store:
            store[session_id] = []

        usage = {
            "tool": tool_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }

        store[session_id].append(usage)
        _tool_tokens_store.set(store)

        logger.info(
            f"🔧 [ToolTracker] Token ajouté pour {session_id}/{tool_name}: "
            f"{input_tokens} in + {output_tokens} out = {input_tokens + output_tokens} total"
        )

    @staticmethod
    def get_session_tools(session_id: str) -> List[Dict[str, Any]]:
        """Récupère tous les tokens des tools pour une session."""
        store = _tool_tokens_store.get()
        tools = store.get(session_id, [])
        logger.info(f"🔧 [ToolTracker] Récupération de {len(tools)} tools pour session {session_id}")
        return tools

    @staticmethod
    def clear_session(session_id: str):
        """Nettoie les données d'une session."""
        store = _tool_tokens_store.get().copy()
        if session_id in store:
            del store[session_id]
            _tool_tokens_store.set(store)
            logger.info(f"🔧 [ToolTracker] Session nettoyée: {session_id}")


# Instance globale
tool_tokens_tracker = ToolTokensTracker()
