"""
Router pour le suivi en temps réel des agents
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging

from services.agent_tracking_service import agent_tracking_service
from company_agents.extraction_manager import (
    get_all_tools_names,
    get_agent_info,
    get_extraction_steps,
    get_sub_agents_info,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/agent-info")
async def get_agent_tracking_info() -> Dict[str, Any]:
    """Récupère les informations de suivi des agents"""
    try:
        return {
            "agent_info": get_agent_info(),
            "tools": get_all_tools_names(),
            "extraction_steps": get_extraction_steps(),
            "sub_agents": get_sub_agents_info(),
        }
    except Exception as e:
        logger.error(f"❌ Erreur récupération info agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_tracking(session_id: str) -> Dict[str, Any]:
    """Récupère les informations de suivi d'une session"""
    try:
        tracking_info = agent_tracking_service.get_tracking_info(session_id)
        if not tracking_info:
            raise HTTPException(status_code=404, detail="Session non trouvée")

        return tracking_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération suivi session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def cleanup_session_tracking(session_id: str) -> Dict[str, str]:
    """Nettoie les informations de suivi d'une session"""
    try:
        agent_tracking_service.cleanup_tracking(session_id)
        return {"message": f"Suivi nettoyé pour la session {session_id}"}
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage suivi {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def tracking_health_check() -> Dict[str, str]:
    """Vérification de santé du système de suivi"""
    try:
        # Vérifier que les méthodes existent
        tools = get_all_tools_names()
        info = get_agent_info()
        steps = get_extraction_steps()

        return {
            "status": "healthy",
            "tools_count": str(len(tools)),
            "steps_count": str(len(steps)),
            "agent_name": info["name"],
        }
    except Exception as e:
        logger.error(f"❌ Erreur health check suivi: {e}")
        raise HTTPException(status_code=500, detail=str(e))
