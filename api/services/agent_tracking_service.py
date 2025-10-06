"""
Service de suivi en temps réel des agents
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

# Import conditionnel pour éviter l'erreur agents
try:
    from company_agents.extraction_manager import (
        get_all_tools_names,
        get_agent_info,
        get_extraction_steps,
        get_sub_agents_info,
    )
except ImportError:
    # Fallback si le module agents n'est pas disponible
    def get_all_tools_names():
        return [
            "run_analyze_and_info",
            "information_extractor",
            "subsidiary_extractor",
            "meta_validator",
        ]

    def get_agent_info():
        return {
            "name": "Extraction Orchestrator",
            "model": "gpt-4o-mini",
            "tools_count": 4,
            "max_turns": 8,
        }

    def get_extraction_steps():
        return [
            {
                "name": "Identification de l'entité légale",
                "agent": "🔍 Éclaireur",
                "duration": 6,
            },
            {
                "name": "Consolidation des informations clés",
                "agent": "⛏️ Mineur",
                "duration": 10,
                "conditional": True,
            },
            {
                "name": "Extraction des filiales",
                "agent": "🗺️ Cartographe",
                "duration": 12,
            },
            {
                "name": "Validation de cohérence",
                "agent": "⚖️ Superviseur",
                "duration": 4,
                "conditional": True,
            },
        ]

    def get_sub_agents_info():
        return {
            "company_analyzer": {"max_turns": 2},
            "information_extractor": {"max_turns": 2},
            "subsidiary_extractor": {"max_turns": 3},
            "meta_validator": {"max_turns": 1},
        }


from status import status_manager
from status.models import AgentStatus

logger = logging.getLogger(__name__)

# Mapping des noms de fonctions vers des messages conviviaux
FUNCTION_TO_FRIENDLY_MESSAGE = {
    "run_analyze_and_info": "Identification de l'entité légale",
    "run_extract_subsidiaries_details": "Extraction des filiales",
    "run_validate_data_coherence": "Validation de cohérence",
    "choose_target_entity": "Sélection de la cible",
}


def _get_friendly_message(message: str) -> str:
    """Convertit un message technique en message convivial"""
    if not message:
        return message

    # Chercher si le message contient un nom de fonction
    for func_name, friendly_name in FUNCTION_TO_FRIENDLY_MESSAGE.items():
        if func_name in message:
            # Remplacer le nom de fonction par le message convivial
            return message.replace(func_name, friendly_name)

    # Si c'est un message de type "Terminé: run_xxx", le simplifier
    if message.startswith("Terminé: "):
        func_name = message.replace("Terminé: ", "")
        friendly_name = FUNCTION_TO_FRIENDLY_MESSAGE.get(func_name, func_name)
        return f"Terminé: {friendly_name}"

    return message


class AgentTrackingService:
    """Service de suivi des agents en temps réel"""

    def __init__(self):
        self.active_tracking: Dict[str, Dict[str, Any]] = {}

    async def start_extraction_tracking(
        self, session_id: str, input_query: str
    ) -> Dict[str, Any]:
        """Démarre le suivi d'une extraction"""
        try:
            # Créer la session de suivi
            await status_manager.create_session(session_id, input_query)

            # Initialiser les agents
            agent_info = get_agent_info()
            extraction_steps = get_extraction_steps()
            sub_agents = get_sub_agents_info()

            # Créer le tracking info
            tracking_info = {
                "session_id": session_id,
                "input_query": input_query,
                "started_at": datetime.now().isoformat(),
                "agent_info": agent_info,
                "extraction_steps": extraction_steps,
                "sub_agents": sub_agents,
                "current_step": 0,
                "total_steps": len(extraction_steps),
                "status": "initializing",
            }

            self.active_tracking[session_id] = tracking_info

            # Initialiser les agents dans le status manager
            for step in extraction_steps:
                await status_manager.update_agent_status(
                    session_id=session_id,
                    agent_name=step["agent"],
                    status="initializing",
                    progress=0.0,
                    message=f"En attente: {step['name']}",
                )

            logger.info(f"🚀 Suivi démarré pour la session: {session_id}")
            return tracking_info

        except Exception as e:
            logger.error(f"❌ Erreur démarrage suivi {session_id}: {e}")
            await status_manager.error_session(session_id, str(e))
            raise

    async def update_step_progress(
        self,
        session_id: str,
        step_name: str,
        progress: float,
        message: str = "",
        performance_metrics: Optional[Dict[str, Any]] = None,
        step_label: Optional[str] = None,
    ):
        """Met à jour la progression d'une étape"""
        try:
            if session_id not in self.active_tracking:
                logger.warning(f"Session de tracking inconnue: {session_id}")
                return

            tracking = self.active_tracking[session_id]

            # Trouver l'étape par nom d'agent
            step_index = next(
                (
                    i
                    for i, step in enumerate(tracking["extraction_steps"])
                    if step["agent"] == step_name
                ),
                None,
            )

            if step_index is not None:
                tracking["current_step"] = step_index + 1
                step = tracking["extraction_steps"][step_index]

                # Nettoyer le message pour le rendre plus convivial
                friendly_message = _get_friendly_message(
                    message or f"Étape {step_index + 1}: {step['name']}"
                )
                friendly_step_name = _get_friendly_message(step_label or step["name"])

                # Mettre à jour le status manager (détaillé avec métriques)
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name=step["agent"],
                    status=(
                        AgentStatus.EXTRACTING
                        if progress < 1.0
                        else AgentStatus.COMPLETED
                    ),
                    progress=progress,
                    message=friendly_message,
                    current_step=step_index + 1,
                    total_steps=tracking["total_steps"],
                    step_name=friendly_step_name,
                    performance_metrics=(performance_metrics or {}),
                )

                # Calculer la progression globale
                overall_progress = (step_index + progress) / tracking["total_steps"]

                # Mettre à jour le statut global
                # (sans appeler complete_session ici)
                if overall_progress >= 1.0:
                    # Pas "completed" car on attend la vraie fin
                    tracking["status"] = "finalizing"
                elif overall_progress >= 0.8:
                    tracking["status"] = "validating"
                elif overall_progress >= 0.5:
                    tracking["status"] = "extracting"
                else:
                    tracking["status"] = "analyzing"

                logger.info(
                    (
                        "📊 Progression %s: %s = %.1f%%"
                        % (
                            session_id,
                            step_name,
                            (progress * 100.0),
                        )
                    )
                )

        except Exception as e:
            logger.error(
                "❌ Erreur mise à jour progression %s: %s"
                % (
                    session_id,
                    e,
                )
            )

    async def complete_extraction_tracking(
        self, session_id: str, result: Dict[str, Any]
    ):
        """Termine le suivi d'une extraction"""
        try:
            if session_id in self.active_tracking:
                tracking = self.active_tracking[session_id]
                tracking["status"] = "completed"
                tracking["completed_at"] = datetime.now().isoformat()
                tracking["result"] = result

                # Marquer tous les agents comme terminés
                for step in tracking["extraction_steps"]:
                    await status_manager.update_agent_status(
                        session_id=session_id,
                        agent_name=step["agent"],
                        status="completed",
                        progress=1.0,
                        message="Terminé avec succès",
                    )

                await status_manager.complete_session(session_id)
                logger.info("✅ Suivi terminé pour la session: %s" % session_id)

        except Exception as e:
            logger.error("❌ Erreur fin suivi %s: %s" % (session_id, e))

    async def error_extraction_tracking(
        self,
        session_id: str,
        error_message: str,
    ):
        """Marque une extraction en erreur"""
        try:
            if session_id in self.active_tracking:
                tracking = self.active_tracking[session_id]
                tracking["status"] = "error"
                tracking["error_message"] = error_message
                tracking["failed_at"] = datetime.now().isoformat()

            await status_manager.error_session(session_id, error_message)
            logger.error(
                "❌ Erreur extraction %s: %s"
                % (
                    session_id,
                    error_message,
                )
            )

        except Exception as e:
            logger.error("❌ Erreur gestion erreur %s: %s" % (session_id, e))

    def get_tracking_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations de suivi d'une session"""
        return self.active_tracking.get(session_id)

    def cleanup_tracking(self, session_id: str):
        """Nettoie les informations de suivi d'une session"""
        if session_id in self.active_tracking:
            del self.active_tracking[session_id]
            logger.info("🧹 Nettoyage suivi pour la session: %s" % session_id)


# Instance globale du service de suivi
agent_tracking_service = AgentTrackingService()
