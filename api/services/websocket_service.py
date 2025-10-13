"""
Service de gestion WebSocket
"""

import json
import asyncio
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from status import status_manager

logger = logging.getLogger(__name__)


async def handle_websocket_connection(websocket: WebSocket, session_id: str) -> None:
    """
    Gère une connexion WebSocket pour le suivi d'état en temps réel
    """
    logger.info(f"🔌 Tentative de connexion WebSocket pour session: {session_id}")
    await websocket.accept()
    logger.info(f"✅ Connexion WebSocket acceptée pour session: {session_id}")

    # Vérifier si c'est une session temporaire
    if session_id.startswith("temp-"):
        logger.info(f"📡 Connexion WebSocket pour session temporaire: {session_id}")
        # Pour les sessions temporaires, on attend que la vraie session soit créée
        await websocket.send_text(
            json.dumps(
                {
                    "type": "waiting",
                    "message": "En attente de l'initialisation de la session...",
                    "session_id": session_id,
                }
            )
        )
    else:
        logger.info(f"📡 Connexion WebSocket établie pour la session: {session_id}")

    # S'abonner aux mises à jour de la session
    queue = status_manager.subscribe_to_session(session_id)

    try:
        # Envoyer l'état initial s'il existe
        progress = await status_manager.get_session_progress(session_id)
        if progress:
            initial_state = json.dumps(progress.to_dict())
            await websocket.send_text(initial_state)

        # Boucle d'écoute des mises à jour avec heartbeat amélioré
        last_ping = datetime.now()
        while True:
            try:
                # Attendre une mise à jour avec timeout de 25s (< 30s pour envoyer ping avant timeout Nginx)
                update = await asyncio.wait_for(queue.get(), timeout=25.0)
                await websocket.send_text(update)
            except asyncio.TimeoutError:
                # Envoyer un ping pour maintenir la connexion (toutes les 25s si pas d'activité)
                now = datetime.now()
                if (now - last_ping).total_seconds() >= 25:
                    ping_message = json.dumps(
                        {"type": "ping", "timestamp": now.isoformat()}
                    )
                    await websocket.send_text(ping_message)
                    last_ping = now
                    logger.debug(f"🏓 Ping envoyé pour session: {session_id}")

    except WebSocketDisconnect:
        if session_id.startswith("temp-"):
            logger.info(
                f"📴 Connexion WebSocket fermée pour session temporaire: {session_id}"
            )
        else:
            logger.info(f"📴 Connexion WebSocket fermée pour la session: {session_id}")
    except Exception as e:
        if session_id.startswith("temp-"):
            logger.info(f"📴 Fermeture normale de session temporaire: {session_id}")
        else:
            logger.error(f"❌ Erreur WebSocket pour la session {session_id}: {e}")
    finally:
        # Se désabonner
        status_manager.unsubscribe_from_session(session_id, queue)


async def get_session_status(session_id: str) -> dict:
    """
    Récupère l'état actuel d'une session d'extraction
    """
    progress = await status_manager.get_session_progress(session_id)
    if not progress:
        raise ValueError(f"Session {session_id} non trouvée")

    return progress.to_dict()


async def get_extraction_results(session_id: str) -> dict:
    """
    Récupère les données d'extraction finales d'une session terminée
    """
    extraction_data = await status_manager.get_extraction_results(session_id)
    if not extraction_data:
        raise ValueError(
            f"Aucune donnée d'extraction trouvée pour la session {session_id}"
        )

    return extraction_data


async def list_active_sessions() -> list:
    """
    Liste toutes les sessions actives
    """
    sessions = []
    for session_id, progress in status_manager.active_sessions.items():
        sessions.append(
            {
                "session_id": session_id,
                "status": progress.overall_status.value,
                "progress": progress.overall_progress,
                "created_at": progress.started_at.isoformat(),
                "updated_at": progress.updated_at.isoformat(),
                "company_name": progress.company_name,
            }
        )

    return sessions
