"""
Suivi en temps réel des métriques via WebSocket
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from .metrics_collector import AgentMetrics, MetricStatus, metrics_collector

logger = logging.getLogger(__name__)


class RealTimeTracker:
    """Gestionnaire de suivi en temps réel des métriques"""
    
    def __init__(self, status_manager):
        self.status_manager = status_manager
        self.update_interval = 1.0  # Mise à jour toutes les secondes
    
    async def track_agent_realtime(self, agent_name: str, session_id: str, agent_metrics: AgentMetrics):
        """Suivi en temps réel d'un agent avec métriques détaillées"""
        try:
            while agent_metrics.status not in [MetricStatus.COMPLETED, MetricStatus.ERROR]:
                # Mettre à jour le statut via WebSocket
                await self._send_metrics_update(agent_name, session_id, agent_metrics)
                
                # Attendre avant la prochaine mise à jour
                await asyncio.sleep(self.update_interval)
                
                # Vérifier si l'agent est toujours actif
                current_metrics = metrics_collector.get_agent_metrics(agent_name, session_id)
                if not current_metrics:
                    break
                agent_metrics = current_metrics
            
            # Envoi final
            await self._send_metrics_update(agent_name, session_id, agent_metrics)
            
        except Exception as e:
            logger.error(f"❌ Erreur suivi temps réel {agent_name}: {e}")
    
    async def _send_metrics_update(self, agent_name: str, session_id: str, agent_metrics: AgentMetrics):
        """Envoie une mise à jour des métriques via WebSocket"""
        try:
            # Préparer les métriques pour le frontend
            frontend_metrics = {
                "current_step": agent_metrics.get_current_step().step_name if agent_metrics.get_current_step() else "Finalisation",
                "total_steps": len(agent_metrics.steps),
                "completed_steps": sum(1 for step in agent_metrics.steps if step.end_time is not None),
                "progress_percentage": agent_metrics.get_progress_percentage(),
                "elapsed_time": agent_metrics.total_duration_ms or int((time.time() - agent_metrics.start_time) * 1000),
                "quality_metrics": agent_metrics.quality_metrics,
                "performance_metrics": agent_metrics.performance_metrics,
                "status": agent_metrics.status.value
            }
            
            # Envoyer via le status manager
            await self.status_manager.update_agent_status_detailed(
                session_id=session_id,
                agent_name=agent_name,
                status=agent_metrics.status,
                progress=agent_metrics.get_progress_percentage(),
                message=f"{agent_metrics.get_current_step().step_name if agent_metrics.get_current_step() else 'Finalisation'}",
                current_step=frontend_metrics["completed_steps"],
                total_steps=frontend_metrics["total_steps"],
                performance_metrics=frontend_metrics
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi métriques {agent_name}: {e}")
    
    async def send_final_metrics(self, agent_name: str, session_id: str, agent_metrics: AgentMetrics):
        """Envoie les métriques finales d'un agent"""
        try:
            # Métriques finales complètes
            final_metrics = agent_metrics.to_dict()
            
            await self.status_manager.update_agent_status_detailed(
                session_id=session_id,
                agent_name=agent_name,
                status=agent_metrics.status,
                progress=1.0 if agent_metrics.status == MetricStatus.COMPLETED else 0.0,
                message=f"Terminé - {agent_metrics.total_duration_ms}ms" if agent_metrics.status == MetricStatus.COMPLETED else f"Erreur: {agent_metrics.error_details}",
                current_step=len(agent_metrics.steps),
                total_steps=len(agent_metrics.steps),
                performance_metrics={
                    "elapsed_time": agent_metrics.total_duration_ms,
                    "quality_score": agent_metrics.quality_metrics.get("confidence_score", 0),
                    "items_processed": agent_metrics.quality_metrics.get("items_count", 0),
                    "error_rate": 1.0 if agent_metrics.status == MetricStatus.ERROR else 0.0,
                    "final_status": agent_metrics.status.value
                }
            )
            
            logger.info(f"📊 Métriques finales envoyées pour {agent_name}: {final_metrics}")
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi métriques finales {agent_name}: {e}")


# Import time pour les calculs
import time
