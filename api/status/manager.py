"""
Gestionnaire principal des états des agents
Utilise PostgreSQL pour la persistance (remplace Redis)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from core.database import AsyncSessionLocal
from models.db_models import SessionState
from .models import AgentStatus, AgentState, ExtractionProgress

logger = logging.getLogger(__name__)

# TTL par défaut pour les sessions (2 heures)
DEFAULT_SESSION_TTL_HOURS = 2


class AgentStatusManager:
    """Gestionnaire des états des agents avec persistance PostgreSQL"""

    def __init__(self):
        # Cache local pour les abonnés WebSocket
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        # Sessions actives en mémoire (cache)
        self.active_sessions: Dict[str, ExtractionProgress] = {}
        # Timers pour les étapes
        self.step_timers: Dict[str, Dict[str, asyncio.Task]] = {}

    async def create_session(
        self, session_id: str, company_name: str
    ) -> ExtractionProgress:
        """Crée une nouvelle session d'extraction"""
        now = datetime.now()

        # Définir les agents impliqués dans l'extraction hiérarchique (ordre d'exécution réel)
        initial_agents = [
            AgentState(
                name="🔍 Éclaireur",
                status=AgentStatus.WAITING,
                progress=0.0,
                message="En attente de démarrage",
                started_at=now,
                updated_at=now,
            ),
            AgentState(
                name="📊 Enrichisseur",
                status=AgentStatus.WAITING,
                progress=0.0,
                message="En attente de démarrage",
                started_at=now,
                updated_at=now,
            ),
            AgentState(
                name="🗺️ Cartographe",
                status=AgentStatus.WAITING,
                progress=0.0,
                message="En attente de démarrage",
                started_at=now,
                updated_at=now,
            ),
            AgentState(
                name="🔬 Extracteur",
                status=AgentStatus.WAITING,
                progress=0.0,
                message="En attente de démarrage",
                started_at=now,
                updated_at=now,
            ),
        ]

        progress = ExtractionProgress(
            session_id=session_id,
            company_name=company_name,
            overall_status=AgentStatus.INITIALIZING,
            overall_progress=0.0,
            agents=initial_agents,
            started_at=now,
            updated_at=now,
        )

        # Sauvegarder en mémoire et PostgreSQL
        self.active_sessions[session_id] = progress
        await self._save_to_db(session_id, progress)

        logger.info(
            f"🚀 Session créée: {session_id} pour {company_name} avec {len(initial_agents)} agents"
        )
        await self._notify_subscribers(session_id, progress)

        return progress

    async def _save_to_db(
        self, session_id: str, progress: ExtractionProgress
    ) -> bool:
        """Sauvegarde les données en PostgreSQL"""
        try:
            async with AsyncSessionLocal() as db:
                # Chercher ou créer la session
                result = await db.execute(
                    select(SessionState).where(SessionState.session_id == session_id)
                )
                session_state = result.scalar_one_or_none()
                
                if not session_state:
                    session_state = SessionState(session_id=session_id)
                    db.add(session_state)
                
                # Mettre à jour les données
                session_state.progress_data = progress.to_dict()
                session_state.updated_at = datetime.now()
                session_state.expires_at = datetime.now() + timedelta(hours=DEFAULT_SESSION_TTL_HOURS)
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde PostgreSQL session {session_id}: {e}")
            return False

    async def _notify_subscribers(
        self, session_id: str, progress: ExtractionProgress
    ) -> None:
        """Notifie tous les abonnés WebSocket d'une mise à jour"""
        if session_id in self.subscribers:
            message = {
                "type": "progress_update",
                "session_id": session_id,
                "data": progress.to_dict(),
            }
            message_str = json.dumps(message, ensure_ascii=False)

            # Envoyer à toutes les connexions WebSocket
            disconnected_queues = []
            for queue in self.subscribers[session_id]:
                try:
                    await queue.put(message_str)
                except Exception as e:
                    logger.warning(f"⚠️ Queue WebSocket fermée: {e}")
                    disconnected_queues.append(queue)

            # Nettoyer les queues fermées
            for queue in disconnected_queues:
                self.subscribers[session_id].remove(queue)

    async def _get_session(self, session_id: str) -> Optional[ExtractionProgress]:
        """Récupère une session depuis PostgreSQL ou le cache local"""
        # D'abord vérifier le cache local
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Sinon, récupérer depuis PostgreSQL
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SessionState).where(SessionState.session_id == session_id)
                )
                session_state = result.scalar_one_or_none()
                
                if session_state:
                    # Vérifier si la session n'est pas expirée
                    if session_state.expires_at < datetime.now():
                        logger.warning(f"⚠️ Session {session_id} expirée, suppression...")
                        await db.delete(session_state)
                        await db.commit()
                        return None
                    
                    # Désérialiser les données
                    progress = ExtractionProgress.from_dict(session_state.progress_data)
                    self.active_sessions[session_id] = progress
                    return progress
        except Exception as e:
            logger.error(f"❌ Erreur récupération session {session_id} depuis PostgreSQL: {e}")
        
        return None

    async def _save_session(self, session_id: str, progress: ExtractionProgress) -> bool:
        """Sauvegarde une session en PostgreSQL"""
        return await self._save_to_db(session_id, progress)

    def _update_overall_progress(self, progress_session: ExtractionProgress):
        """Met à jour la progression globale basée sur les agents individuels"""
        # Calculer la progression moyenne
        total_progress = sum(agent.progress for agent in progress_session.agents)
        average_progress = total_progress / len(progress_session.agents)
        progress_session.overall_progress = average_progress

        # Déterminer le statut global
        agent_statuses = [agent.status for agent in progress_session.agents]

        if any(status == AgentStatus.ERROR for status in agent_statuses):
            progress_session.overall_status = AgentStatus.ERROR
        elif all(status == AgentStatus.COMPLETED for status in agent_statuses):
            progress_session.overall_status = AgentStatus.COMPLETED
        elif any(
            status
            in [AgentStatus.SEARCHING, AgentStatus.EXTRACTING, AgentStatus.ANALYZING]
            for status in agent_statuses
        ):
            progress_session.overall_status = AgentStatus.EXTRACTING
        elif any(status == AgentStatus.VALIDATING for status in agent_statuses):
            progress_session.overall_status = AgentStatus.VALIDATING
        else:
            progress_session.overall_status = AgentStatus.INITIALIZING

        progress_session.updated_at = datetime.now()

    def subscribe_to_session(self, session_id: str) -> asyncio.Queue:
        """S'abonne aux mises à jour d'une session"""
        if session_id not in self.subscribers:
            self.subscribers[session_id] = []

        queue = asyncio.Queue()
        self.subscribers[session_id].append(queue)

        logger.info(f"📡 Nouvel abonné pour la session: {session_id}")
        return queue

    def unsubscribe_from_session(self, session_id: str, queue: asyncio.Queue):
        """Se désabonne des mises à jour d'une session"""
        if session_id in self.subscribers and queue in self.subscribers[session_id]:
            self.subscribers[session_id].remove(queue)
            logger.info(f"📴 Abonné retiré de la session: {session_id}")

    async def get_session_progress(
        self, session_id: str
    ) -> Optional[ExtractionProgress]:
        """Récupère la progression d'une session"""
        return await self._get_session(session_id)

    async def complete_session(self, session_id: str):
        """Marque une session comme terminée"""
        progress = await self._get_session(session_id)
        if progress:
            progress.overall_status = AgentStatus.COMPLETED
            progress.overall_progress = 1.0
            progress.updated_at = datetime.now()

            # Mettre à jour tous les agents comme terminés
            for agent in progress.agents:
                if agent.status != AgentStatus.ERROR:
                    agent.status = AgentStatus.COMPLETED
                    agent.progress = 1.0
                    agent.updated_at = datetime.now()

            # Sauvegarder en PostgreSQL
            await self._save_session(session_id, progress)

            # Notifier une dernière fois
            await self._notify_subscribers(session_id, progress)

            logger.info(f"✅ Session terminée: {session_id}")

    async def store_extraction_results(self, session_id: str, extraction_data: dict):
        """Stocke les données d'extraction finales dans PostgreSQL"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SessionState).where(SessionState.session_id == session_id)
                )
                session_state = result.scalar_one_or_none()
                
                if not session_state:
                    session_state = SessionState(session_id=session_id)
                    db.add(session_state)
                
                session_state.results_data = extraction_data
                session_state.updated_at = datetime.now()
                # Résultats valides 24h
                session_state.expires_at = datetime.now() + timedelta(hours=24)
                
                await db.commit()
                logger.info(f"💾 Résultats stockés pour session: {session_id}")
        except Exception as e:
            logger.error(f"❌ Erreur stockage résultats session {session_id}: {e}")

    async def get_extraction_results(self, session_id: str) -> Optional[dict]:
        """Récupère les données d'extraction finales depuis PostgreSQL"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SessionState).where(SessionState.session_id == session_id)
                )
                session_state = result.scalar_one_or_none()
                
                if session_state and session_state.results_data:
                    return session_state.results_data
        except Exception as e:
            logger.error(f"❌ Erreur récupération résultats session {session_id}: {e}")
        return None

    async def error_session(self, session_id: str, error_message: str):
        """Marque une session en erreur"""
        progress = await self._get_session(session_id)
        if progress:
            progress.overall_status = AgentStatus.ERROR
            progress.updated_at = datetime.now()

            # Mettre à jour tous les agents en erreur
            for agent in progress.agents:
                if agent.status not in [AgentStatus.COMPLETED, AgentStatus.ERROR]:
                    agent.status = AgentStatus.ERROR
                    agent.message = f"Erreur: {error_message}"
                    agent.updated_at = datetime.now()

            # Sauvegarder en PostgreSQL
            await self._save_session(session_id, progress)

            # Notifier les abonnés
            await self._notify_subscribers(session_id, progress)

            logger.error(f"❌ Session en erreur: {session_id} - {error_message}")

    async def start_detailed_agent_progression(
        self,
        session_id: str,
        agent_name: str,
        callback: Optional[Callable] = None
    ) -> None:
        """Démarre la progression détaillée d'un agent"""

        # Définir les étapes selon l'agent
        agent_steps = {
            "🔍 Éclaireur": [
                {"name": "Reconnaissance du terrain", "duration": 1.5},
                {"name": "Analyse des sources disponibles", "duration": 2.0},
                {"name": "Identification du type d'entreprise", "duration": 1.8},
                {"name": "Préparation de la stratégie", "duration": 1.2}
            ],
            "⛏️ Mineur": [
                {"name": "Extraction des données de base", "duration": 2.5},
                {"name": "Collecte des informations financières", "duration": 3.0},
                {"name": "Recherche d'informations légales", "duration": 2.2},
                {"name": "Compilation des données", "duration": 1.8}
            ],
            "🔗 Vérificateur": [
                {"name": "Validation des sources", "duration": 1.8},
                {"name": "Vérification de cohérence", "duration": 2.2},
                {"name": "Contrôle qualité", "duration": 1.5},
                {"name": "Finalisation validation", "duration": 1.0}
            ],
            "🗺️ Cartographe": [
                {"name": "Exploration du réseau", "duration": 2.0},
                {"name": "Identification des filiales", "duration": 3.5},
                {"name": "Analyse géographique", "duration": 2.8},
                {"name": "Construction de la carte", "duration": 2.2}
            ],
            "⚖️ Superviseur": [
                {"name": "Révision générale", "duration": 2.0},
                {"name": "Calcul des scores", "duration": 1.5},
                {"name": "Validation finale", "duration": 1.8},
                {"name": "Rapport de qualité", "duration": 1.2}
            ]
        }

        steps = agent_steps.get(agent_name, [{"name": "Traitement", "duration": 2.0}])

        progress_session = await self._get_session(session_id)
        if not progress_session:
            logger.warning(f"Session inconnue: {session_id}")
            return

        # Trouver l'agent
        agent = next((a for a in progress_session.agents if a.name == agent_name), None)
        if not agent:
            logger.warning(f"Agent non trouvé: {agent_name}")
            return

        if not steps:
            logger.warning(f"Aucune étape définie pour {agent_name}")
            return

        # Initialiser l'agent avec les étapes
        agent.total_steps = len(steps)
        agent.current_step = 0

        # Démarrer la progression en arrière-plan
        task = asyncio.create_task(
            self._run_detailed_agent_progression(session_id, agent_name, steps, callback)
        )

        if session_id not in self.step_timers:
            self.step_timers[session_id] = {}
        self.step_timers[session_id][agent_name] = task

    async def _run_detailed_agent_progression(
        self,
        session_id: str,
        agent_name: str,
        steps: List[Dict[str, Any]],
        callback: Optional[Callable] = None,
    ) -> None:
        """Exécute la progression détaillée d'un agent"""
        start_time = datetime.now()
        total_duration = sum(step["duration"] for step in steps)

        for i, step in enumerate(steps):
            # Calculer la progression
            progress = (i + 1) / len(steps)

            # Calculer les métriques de performance
            elapsed = (datetime.now() - start_time).total_seconds()
            remaining_steps = len(steps) - i - 1

            performance_metrics = {
                "elapsed_time": elapsed,
                "steps_completed": i + 1,
                "steps_remaining": remaining_steps,
                "current_step_duration": step["duration"],
                "estimated_total_time": total_duration,
            }

            # Déterminer le statut selon la progression
            if progress >= 1.0:
                status = AgentStatus.COMPLETED
            elif progress >= 0.8:
                status = AgentStatus.VALIDATING
            elif progress >= 0.5:
                status = AgentStatus.ANALYZING
            elif progress >= 0.2:
                status = AgentStatus.EXTRACTING
            else:
                status = AgentStatus.SEARCHING

            # Mettre à jour l'agent avec tous les détails
            await self.update_agent_status_detailed(
                session_id=session_id,
                agent_name=agent_name,
                status=status,
                progress=progress,
                message=f"Étape {i + 1}/{len(steps)}: {step['name']}",
                current_step=i + 1,
                total_steps=len(steps),
                step_name=step['name'],
                performance_metrics=performance_metrics
            )

            # Notifier via callback si fourni
            if callback:
                progress_session = await self._get_session(session_id)
                if progress_session:
                    agent = next((a for a in progress_session.agents if a.name == agent_name), None)
                    if agent:
                        await callback(session_id, agent_name, agent)

            # Attendre la durée de l'étape
            await asyncio.sleep(step["duration"])

        # Marquer comme terminé
        await self.update_agent_status_detailed(
            session_id=session_id,
            agent_name=agent_name,
            status=AgentStatus.COMPLETED,
            progress=1.0,
            message="Terminé avec succès",
            current_step=len(steps),
            total_steps=len(steps),
            step_name="Terminé",
            performance_metrics={
                "elapsed_time": (datetime.now() - start_time).total_seconds(),
                "steps_completed": len(steps),
                "steps_remaining": 0,
            }
        )

    async def update_agent_status(
        self,
        session_id: str,
        agent_name: str,
        status: str,
        progress: float,
        message: str,
        error_message: Optional[str] = None,
    ):
        """
        Méthode wrapper simple pour update_agent_status_detailed
        Convertit le status string en AgentStatus enum et délègue à la méthode détaillée
        """
        # Convertir le string status en AgentStatus enum
        try:
            if status == "initializing":
                agent_status = AgentStatus.INITIALIZING
            elif status == "searching":
                agent_status = AgentStatus.SEARCHING
            elif status == "extracting":
                agent_status = AgentStatus.EXTRACTING
            elif status == "analyzing":
                agent_status = AgentStatus.ANALYZING
            elif status == "validating":
                agent_status = AgentStatus.VALIDATING
            elif status == "completed":
                agent_status = AgentStatus.COMPLETED
            elif status == "error":
                agent_status = AgentStatus.ERROR
            else:
                # Fallback - essayer de créer l'enum directement
                agent_status = AgentStatus(status.upper())
        except ValueError:
            # Si la conversion échoue, utiliser EXTRACTING par défaut
            logger.warning(f"Status inconnu '{status}', utilisation de EXTRACTING par défaut")
            agent_status = AgentStatus.EXTRACTING

        # Déléguer à la méthode détaillée
        await self.update_agent_status_detailed(
            session_id=session_id,
            agent_name=agent_name,
            status=agent_status,
            progress=progress,
            message=message,
            error_message=error_message,
        )

    async def update_agent_status_detailed(
        self,
        session_id: str,
        agent_name: str,
        status: AgentStatus,
        progress: float,
        message: str,
        current_step: int = 0,
        total_steps: int = 1,
        step_name: str = "",
        performance_metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """Met à jour l'état d'un agent avec tous les détails de progression"""
        progress_session = await self._get_session(session_id)
        if not progress_session:
            logger.debug(f"Session inconnue: {session_id}")
            return

        now = datetime.now()

        # Trouver l'agent et mettre à jour son état
        agent_found = False
        for agent in progress_session.agents:
            if agent.name == agent_name:
                agent.status = status
                agent.progress = progress
                agent.message = message
                agent.updated_at = now
                agent.error_message = error_message
                agent.current_step = current_step
                agent.total_steps = total_steps
                agent.step_name = step_name
                agent.performance_metrics = performance_metrics or {}
                agent_found = True
                break

        if not agent_found:
            logger.info(f"🆕 Nouvel agent détecté: {agent_name}")
            # Créer et ajouter le nouvel agent
            new_agent = AgentState(
                name=agent_name,
                status=status,
                progress=progress,
                message=message,
                started_at=now,
                updated_at=now,
                error_message=error_message,
                current_step=current_step,
                total_steps=total_steps,
                step_name=step_name,
                performance_metrics=performance_metrics or {}
            )
            progress_session.agents.append(new_agent)

        # Mettre à jour la progression globale
        self._update_overall_progress(progress_session)

        # Sauvegarder en PostgreSQL
        await self._save_session(session_id, progress_session)

        # Notifier les abonnés
        await self._notify_subscribers(session_id, progress_session)

        logger.info(
            f"🔄 Agent détaillé mis à jour: {agent_name} -> {status.value} ({progress:.1%}) - Étape {current_step}/{total_steps}: {step_name}"
        )

    async def cleanup_old_sessions(self, max_age_minutes: int = 60):
        """Nettoie les anciennes sessions expirées depuis PostgreSQL"""
        try:
            async with AsyncSessionLocal() as db:
                # Supprimer les sessions expirées
                cutoff_time = datetime.now()
                result = await db.execute(
                    delete(SessionState).where(SessionState.expires_at < cutoff_time)
                )
                deleted_count = result.rowcount
                
                await db.commit()
                
                # Nettoyer aussi le cache local et les abonnés pour les sessions expirées
                # Récupérer toutes les sessions valides depuis la DB
                valid_sessions_result = await db.execute(select(SessionState.session_id))
                valid_session_ids = {row[0] for row in valid_sessions_result.all()}
                
                # Supprimer du cache local les sessions qui ne sont plus valides
                expired_local_sessions = [
                    session_id for session_id in self.active_sessions.keys()
                    if session_id not in valid_session_ids
                ]
                
                for session_id in expired_local_sessions:
                    if session_id in self.active_sessions:
                        del self.active_sessions[session_id]
                    if session_id in self.subscribers:
                        del self.subscribers[session_id]

                if deleted_count > 0:
                    logger.info(f"🧹 {deleted_count} sessions expirées nettoyées de PostgreSQL")
                if expired_local_sessions:
                    logger.info(f"🧹 {len(expired_local_sessions)} sessions nettoyées du cache local")
        except Exception as e:
            logger.error(f"❌ Erreur lors du nettoyage: {e}")


# Instance globale
status_manager = AgentStatusManager()