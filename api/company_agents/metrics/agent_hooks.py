"""
Hooks de cycle de vie pour les agents avec suivi WebSocket
"""

import logging
from typing import Any, Optional
from agents import AgentHooks

logger = logging.getLogger(__name__)


class RealtimeAgentHooks(AgentHooks):
    """
    Hooks personnalisés pour notifier le suivi temps réel des événements guardrail.
    """
    
    def __init__(self, status_manager, session_id: str, agent_name: str):
        """
        Args:
            status_manager: Gestionnaire de statut WebSocket
            session_id: ID de session
            agent_name: Nom de l'agent
        """
        self.status_manager = status_manager
        self.session_id = session_id
        self.agent_name = agent_name
    
    async def on_output_guardrail_tripwire_triggered(self, context: Any, guardrail_result: Any) -> None:
        """
        Appelé quand un guardrail déclenche un tripwire.
        
        Notifie le frontend via WebSocket pour afficher l'état de retry.
        """
        try:
            # Extraire les infos du guardrail
            output_info = getattr(guardrail_result, "output_info", {})
            violations = output_info.get("violations", [])
            
            logger.warning(
                f"🚨 Guardrail tripwire pour {self.agent_name} (session: {self.session_id}): {violations}"
            )
            
            # Notifier via WebSocket
            await self.status_manager.update_agent_status_detailed(
                session_id=self.session_id,
                agent_name=self.agent_name,
                status="running",  # Reste en "running" pendant le retry
                progress=0.5,  # Progression intermédiaire
                message=f"⚠️ Validation échouée - Retry en cours...",
                current_step=None,
                total_steps=None,
                performance_metrics={
                    "guardrail_triggered": True,
                    "violations": violations[:3],  # Limiter à 3 pour le frontend
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur dans hook guardrail: {e}", exc_info=True)
    
    async def on_agent_start(self, context: Any) -> None:
        """Appelé au démarrage de l'agent."""
        try:
            await self.status_manager.update_agent_status_detailed(
                session_id=self.session_id,
                agent_name=self.agent_name,
                status="initializing",
                progress=0.0,
                message="Démarrage de l'agent...",
            )
        except Exception as e:
            logger.error(f"❌ Erreur dans hook start: {e}")
    
    async def on_agent_end(self, context: Any, result: Any) -> None:
        """Appelé à la fin de l'agent."""
        try:
            await self.status_manager.update_agent_status_detailed(
                session_id=self.session_id,
                agent_name=self.agent_name,
                status="completed",
                progress=1.0,
                message="Agent terminé avec succès",
            )
        except Exception as e:
            logger.error(f"❌ Erreur dans hook end: {e}")

