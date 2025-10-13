"""
Modèles de données pour le système de suivi des agents
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass


class AgentStatus(str, Enum):
    """États possibles d'un agent"""

    WAITING = "waiting"           # En attente de démarrage
    INITIALIZING = "initializing" # Initialisation
    RUNNING = "running"           # En cours d'exécution
    FINALIZING = "finalizing"     # Finalisation
    COMPLETED = "completed"       # Terminé
    ERROR = "error"              # Erreur
    
    # États dépréciés (pour compatibilité)
    IDLE = "idle"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    VALIDATING = "validating"


class DetailedAgentStatus(str, Enum):
    """États détaillés d'un agent avec sous-étapes"""

    # Analyseur d'Entreprise
    ANALYZING_BASIC_INFO = "analyzing_basic_info"
    VALIDATING_COMPANY_NAME = "validating_company_name"
    RESEARCHING_COMPANY_HISTORY = "researching_company_history"
    IDENTIFYING_BUSINESS_MODEL = "identifying_business_model"

    # Extracteur d'Informations
    SEARCHING_WEB_SOURCES = "searching_web_sources"
    EXTRACTING_COMPANY_DATA = "extracting_company_data"
    PROCESSING_SUBSIDIARIES = "processing_subsidiaries"
    ANALYZING_FINANCIAL_DATA = "analyzing_financial_data"
    GATHERING_EMPLOYEE_INFO = "gathering_employee_info"
    COLLATING_SOURCES = "collating_sources"

    # Validateur de Données
    VALIDATING_DATA_QUALITY = "validating_data_quality"
    CROSS_REFERENCING_SOURCES = "cross_referencing_sources"
    CHECKING_CONSISTENCY = "checking_consistency"
    FINALIZING_VALIDATION = "finalizing_validation"


@dataclass
class AgentState:
    """État d'un agent individuel"""

    name: str
    status: AgentStatus
    progress: float  # 0.0 to 1.0
    message: str
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    # Nouveaux champs pour la progression détaillée
    current_step: int = 0
    total_steps: int = 1
    step_name: str = ""
    performance_metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire"""
        return {
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "started_at": (self.started_at.isoformat() if self.started_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
            "error_message": self.error_message,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_name": self.step_name,
            "performance_metrics": self.performance_metrics or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Crée un AgentState depuis un dictionnaire"""
        return cls(
            name=data["name"],
            status=AgentStatus(data["status"]),
            progress=data["progress"],
            message=data["message"],
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else None
            ),
            error_message=data.get("error_message"),
            current_step=data.get("current_step", 0),
            total_steps=data.get("total_steps", 1),
            step_name=data.get("step_name", ""),
            performance_metrics=data.get("performance_metrics"),
        )


@dataclass
class ExtractionProgress:
    """Progression globale de l'extraction"""

    session_id: str
    company_name: str
    overall_status: AgentStatus
    overall_progress: float
    agents: List[AgentState]
    started_at: datetime
    updated_at: datetime
    global_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la progression en dictionnaire"""
        return {
            "session_id": self.session_id,
            "company_name": self.company_name,
            "overall_status": self.overall_status.value,
            "overall_progress": self.overall_progress,
            "agents": [agent.to_dict() for agent in self.agents],
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "global_message": self.global_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionProgress':
        """Crée un ExtractionProgress depuis un dictionnaire"""
        agents = []
        for agent_data in data["agents"]:
            agent = AgentState.from_dict(agent_data)
            agents.append(agent)

        return cls(
            session_id=data["session_id"],
            company_name=data["company_name"],
            overall_status=AgentStatus(data["overall_status"]),
            overall_progress=data["overall_progress"],
            agents=agents,
            started_at=datetime.fromisoformat(data["started_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            global_message=data.get("global_message"),
        )