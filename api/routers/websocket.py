"""
Routes WebSocket pour le suivi en temps réel
"""

import logging
from fastapi import APIRouter, WebSocket, HTTPException
from services.websocket_service import (
    handle_websocket_connection,
    get_session_status,
    get_extraction_results,
    list_active_sessions,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/status/{session_id}")
async def websocket_status(websocket: WebSocket, session_id: str):
    """
    WebSocket pour recevoir les mises à jour d'état en temps réel
    """
    await handle_websocket_connection(websocket, session_id)


@router.get("/status/{session_id}")
async def get_session_status_endpoint(session_id: str):
    """
    Récupère l'état actuel d'une session d'extraction
    """
    try:
        return await get_session_status(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/results/{session_id}")
async def get_extraction_results_endpoint(session_id: str):
    """
    Récupère les données d'extraction finales d'une session terminée
    """
    try:
        return await get_extraction_results(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions")
async def list_active_sessions_endpoint():
    """
    Liste toutes les sessions actives
    """
    return await list_active_sessions()
