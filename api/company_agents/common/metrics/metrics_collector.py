"""
Collecteur de métriques unifié pour tous les agents
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MetricStatus(str, Enum):
    """États des agents pour les métriques"""
    STARTING = "starting"
    RUNNING = "running"
    TOOL_CALLING = "tool_calling"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StepMetrics:
    """Métriques d'une étape d'exécution"""
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[int] = None
    status: MetricStatus = MetricStatus.STARTING
    details: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, status: MetricStatus = MetricStatus.COMPLETED, details: Optional[Dict[str, Any]] = None):
        """Finalise l'étape avec les métriques"""
        self.end_time = time.time()
        self.duration_ms = int((self.end_time - self.start_time) * 1000)
        self.status = status
        if details:
            self.details.update(details)


@dataclass
class AgentMetrics:
    """Métriques complètes d'un agent"""
    agent_name: str
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration_ms: Optional[int] = None
    status: MetricStatus = MetricStatus.STARTING
    steps: List[StepMetrics] = field(default_factory=list)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    
    def add_step(self, step_name: str) -> StepMetrics:
        """Ajoute une nouvelle étape"""
        step = StepMetrics(
            step_name=step_name,
            start_time=time.time()
        )
        self.steps.append(step)
        return step
    
    def finish(self, status: MetricStatus = MetricStatus.COMPLETED, error_details: Optional[str] = None):
        """Finalise les métriques de l'agent"""
        self.end_time = time.time()
        self.total_duration_ms = int((self.end_time - self.start_time) * 1000)
        self.status = status
        if error_details:
            self.error_details = error_details
        
        # Finaliser toutes les étapes non terminées
        for step in self.steps:
            if step.end_time is None:
                step.finish(MetricStatus.COMPLETED)
    
    def get_current_step(self) -> Optional[StepMetrics]:
        """Retourne l'étape actuellement en cours"""
        for step in reversed(self.steps):
            if step.end_time is None:
                return step
        return None
    
    def get_progress_percentage(self) -> float:
        """Calcule le pourcentage de progression"""
        if not self.steps:
            return 0.0
        
        completed_steps = sum(1 for step in self.steps if step.end_time is not None)
        return completed_steps / len(self.steps)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour transmission"""
        return {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "status": self.status.value,
            "total_duration_ms": self.total_duration_ms,
            "progress_percentage": self.get_progress_percentage(),
            "current_step": self.get_current_step().step_name if self.get_current_step() else None,
            "total_steps": len(self.steps),
            "completed_steps": sum(1 for step in self.steps if step.end_time is not None),
            "quality_metrics": self.quality_metrics,
            "performance_metrics": self.performance_metrics,
            "error_details": self.error_details,
            "steps": [
                {
                    "name": step.step_name,
                    "duration_ms": step.duration_ms,
                    "status": step.status.value,
                    "details": step.details
                }
                for step in self.steps
            ]
        }


class MetricsCollector:
    """Collecteur centralisé de métriques pour tous les agents"""
    
    def __init__(self):
        self.active_metrics: Dict[str, AgentMetrics] = {}
    
    def start_agent(self, agent_name: str, session_id: str) -> AgentMetrics:
        """Démarre le suivi des métriques pour un agent"""
        metrics = AgentMetrics(
            agent_name=agent_name,
            session_id=session_id,
            start_time=time.time()
        )
        self.active_metrics[f"{session_id}:{agent_name}"] = metrics
        logger.info(f"📊 Métriques démarrées pour {agent_name} (session: {session_id})")
        return metrics
    
    def get_agent_metrics(self, agent_name: str, session_id: str) -> Optional[AgentMetrics]:
        """Récupère les métriques d'un agent"""
        return self.active_metrics.get(f"{session_id}:{agent_name}")
    
    def finish_agent(self, agent_name: str, session_id: str, status: MetricStatus = MetricStatus.COMPLETED, error_details: Optional[str] = None):
        """Finalise les métriques d'un agent"""
        key = f"{session_id}:{agent_name}"
        if key in self.active_metrics:
            self.active_metrics[key].finish(status, error_details)
            logger.info(f"📊 Métriques finalisées pour {agent_name}: {self.active_metrics[key].total_duration_ms}ms, status: {status.value}")
    
    def cleanup_session(self, session_id: str):
        """Nettoie les métriques d'une session"""
        keys_to_remove = [key for key in self.active_metrics.keys() if key.startswith(f"{session_id}:")]
        for key in keys_to_remove:
            del self.active_metrics[key]
        logger.info(f"🧹 Métriques nettoyées pour session: {session_id}")


# Instance globale du collecteur
metrics_collector = MetricsCollector()
