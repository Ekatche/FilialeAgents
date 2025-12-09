"""
Service de Tracking des Coûts Hiérarchique (Phase 7)

Permet de tracker les coûts de manière hiérarchique :
- Phase → Agent → Tool → Entity

Utilise des context managers async pour un tracking automatique et transparent.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ==========================================
#   MODÈLES DE COÛTS HIÉRARCHIQUES
# ==========================================

class TokenUsage(BaseModel):
    """Usage de tokens pour un appel"""
    model_config = ConfigDict(extra="forbid")

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class EntityCost(BaseModel):
    """Coûts pour une entité spécifique"""
    model_config = ConfigDict(extra="forbid")

    entity_name: str
    tool_calls: List[TokenUsage] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    extraction_duration_seconds: float = 0.0


class AgentCost(BaseModel):
    """Coûts pour un agent"""
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    model: str
    entities: List[EntityCost] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    execution_duration_seconds: float = 0.0


class PhaseCost(BaseModel):
    """Coûts pour une phase"""
    model_config = ConfigDict(extra="forbid")

    phase_name: str
    agents: List[AgentCost] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    execution_duration_seconds: float = 0.0


class HierarchicalExtractionCosts(BaseModel):
    """Coûts hiérarchiques complets pour une extraction"""
    model_config = ConfigDict(extra="forbid")

    session_id: str
    company_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Hiérarchie des coûts
    phases: List[PhaseCost] = Field(default_factory=list)

    # Totaux globaux
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_duration_seconds: float = 0.0

    # Statistiques
    entities_identified: int = 0
    entities_extracted: int = 0
    cache_hits: int = 0
    cache_savings_usd: float = 0.0

    def add_phase(self, phase: PhaseCost):
        """Ajoute une phase et recalcule les totaux"""
        self.phases.append(phase)
        self._recalculate_totals()

    def _recalculate_totals(self):
        """Recalcule les totaux globaux"""
        self.total_cost_usd = sum(phase.total_cost_usd for phase in self.phases)

        # Calcul des tokens totaux
        total_input = 0
        total_output = 0
        for phase in self.phases:
            for agent in phase.agents:
                for entity in agent.entities:
                    for tool_call in entity.tool_calls:
                        total_input += tool_call.input_tokens
                        total_output += tool_call.output_tokens

        self.total_input_tokens = total_input
        self.total_output_tokens = total_output
        self.total_tokens = total_input + total_output

    def summary(self) -> str:
        """Résumé textuel des coûts"""
        return f"""
💰 Coûts Hiérarchiques - {self.company_name}

TOTAUX:
  • Coût total: ${self.total_cost_usd:.4f}
  • Tokens: {self.total_tokens:,} ({self.total_input_tokens:,} in / {self.total_output_tokens:,} out)
  • Durée: {self.total_duration_seconds:.1f}s
  • Entités: {self.entities_extracted}/{self.entities_identified}

PAR PHASE:
{self._format_phases()}

CACHE:
  • Hits: {self.cache_hits}
  • Économies: ${self.cache_savings_usd:.4f}
"""

    def _format_phases(self) -> str:
        """Formate les coûts par phase"""
        lines = []
        for phase in self.phases:
            lines.append(f"  [{phase.phase_name}] ${phase.total_cost_usd:.4f} ({phase.execution_duration_seconds:.1f}s)")
            for agent in phase.agents:
                lines.append(f"    → {agent.agent_name}: ${agent.total_cost_usd:.4f}")
        return "\n".join(lines)


# ==========================================
#   CONTEXT MANAGER : COST CONTEXT
# ==========================================

class CostContext:
    """
    Context manager async pour tracker automatiquement les coûts.

    Usage:
        async with CostContext("phase_1", "cartographe_minimal") as ctx:
            # Faire l'extraction
            ctx.add_token_usage(model="gpt-4o-mini", input=100, output=50)
    """

    def __init__(
        self,
        phase_name: str,
        agent_name: str,
        entity_name: Optional[str] = None,
        tracker: Optional['HierarchicalCostTracker'] = None
    ):
        self.phase_name = phase_name
        self.agent_name = agent_name
        self.entity_name = entity_name
        self.tracker = tracker or HierarchicalCostTracker.get_instance()

        self.start_time: Optional[float] = None
        self.token_usages: List[TokenUsage] = []

    async def __aenter__(self):
        """Entrée dans le contexte"""
        self.start_time = asyncio.get_event_loop().time()
        logger.debug(f"📊 CostContext start: {self.phase_name}/{self.agent_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Sortie du contexte"""
        duration = asyncio.get_event_loop().time() - self.start_time

        # Enregistrement dans le tracker
        self.tracker.record_cost(
            phase_name=self.phase_name,
            agent_name=self.agent_name,
            entity_name=self.entity_name,
            token_usages=self.token_usages,
            duration_seconds=duration
        )

        logger.debug(
            f"📊 CostContext end: {self.phase_name}/{self.agent_name} "
            f"({len(self.token_usages)} calls, {duration:.2f}s)"
        )
        return False  # Ne pas supprimer les exceptions

    def add_token_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float] = None
    ):
        """
        Ajoute un usage de tokens au contexte.

        Args:
            model: Nom du modèle
            input_tokens: Tokens en entrée
            output_tokens: Tokens en sortie
            cost_usd: Coût en USD (calculé automatiquement si None)
        """
        if cost_usd is None:
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

        usage = TokenUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd
        )
        self.token_usages.append(usage)

    @staticmethod
    def _get_model_pricing(model: str) -> Dict[str, Any]:
        """
        Retourne la configuration de prix pour un modèle.

        Prix (au 02/12/2024):
        - gpt-4o-mini-search-preview: $0.15/1M input, $0.60/1M output + $25/1K calls (preview non-reasoning)
        - gpt-4o-search-preview: $2.50/1M input, $10/1M output + $30/1K calls (preview reasoning)
        - gpt-5_1: $1.25/1M input, $10/1M output + $10/1K calls (reasoning model avec web_search)
        - gpt-5: $1.25/1M input, $10/1M output + $10/1K calls (reasoning model avec web_search)
        - gpt-5-mini: $0.25/1M input, $2.00/1M output + $25/1K calls (non-reasoning model avec web_search)
        - gpt-4.1: $2.00/1M input, $8.00/1M output + $10/1K calls (web_search tool)
        - gpt-4.1-mini: $0.40/1M input, $1.60/1M output + ~$20/1K web_search (observé en production, varie $5.70-$33.20)
        - gpt-4o-mini: $0.15/1M input, $0.60/1M output
        - gpt-4o: $2.50/1M input, $10/1M output

        Web Search costs:
        - Tool calls: $30/1K calls (gpt-4o-search-preview) or $25/1K calls (gpt-4o-mini-search-preview)
        - Search content tokens: Already included in input_tokens (billed at model rate)
        """
        pricing = {
            "gpt-4o-mini-search-preview": {
                "input": 0.15 / 1_000_000,
                "output": 0.60 / 1_000_000,
                "call_cost": 25.00 / 1_000  # Non-reasoning model preview
            },
            "gpt-4o-search-preview": {
                "input": 2.50 / 1_000_000,
                "output": 10.00 / 1_000_000,
                "call_cost": 30.00 / 1_000  # Reasoning model preview ($30/1K calls min)
            },
            "gpt-5_1": {
                "input": 1.25 / 1_000_000,  # Corrigé: $1.25 au lieu de $2.50
                "output": 10.00 / 1_000_000,
                "call_cost": 10.00 / 1_000  # Reasoning model avec web_search
            },
            "gpt-5.1": {  # Alias avec point (format utilisé par l'API)
                "input": 1.25 / 1_000_000,  # Corrigé: $1.25 au lieu de $2.50
                "output": 10.00 / 1_000_000,
                "call_cost": 10.00 / 1_000  # Reasoning model avec web_search
            },
            "gpt-5": {
                "input": 1.25 / 1_000_000,  # Corrigé: $1.25 au lieu de $2.50
                "output": 10.00 / 1_000_000,
                "call_cost": 10.00 / 1_000  # Reasoning model avec web_search
            },
            "gpt-5-mini": {
                "input": 0.25 / 1_000_000,  # Corrigé: $0.25 au lieu de $0.15
                "output": 2.00 / 1_000_000,  # Corrigé: $2.00 au lieu de $0.60
                "call_cost": 25.00 / 1_000  # Non-reasoning model avec web_search
            },
            "gpt-4o-mini": {
                "input": 0.15 / 1_000_000,
                "output": 0.60 / 1_000_000,
                "call_cost": 0.0  # No web search
            },
            "gpt-4o": {
                "input": 2.50 / 1_000_000,
                "output": 10.00 / 1_000_000,
                "call_cost": 0.0  # No web search
            },
            "gpt-4.1": {
                "input": 2.00 / 1_000_000,
                "output": 8.00 / 1_000_000,
                "call_cost": 10.00 / 1_000  # Web search tool calls ($10/1K)
            },
            "gpt-4_1": {  # Alias avec underscore (format normalisé)
                "input": 2.00 / 1_000_000,
                "output": 8.00 / 1_000_000,
                "call_cost": 10.00 / 1_000  # Web search tool calls ($10/1K)
            },
            "gpt-4_1": {  # Alias avec underscore (format normalisé)
                "input": 2.00 / 1_000_000,
                "output": 8.00 / 1_000_000,
                "call_cost": 10.00 / 1_000  # Web search tool calls ($10/1K)
            },
            "gpt-4.1-mini": {
                "input": 0.40 / 1_000_000,
                "output": 1.60 / 1_000_000,
                "call_cost": 25.00 / 1_000,  # web_search_preview: $25/1K (tool call fee) + search content tokens GRATUITS
                # Référence doc OpenAI: https://platform.openai.com/docs/guides/function-calling#web-search
                # web_search_preview (non-reasoning): $25/1K + search tokens gratuits
                # web_search (non-preview): $2.50/1K + 8,000 tokens fixes ($5.70/1K total pour gpt-4.1-mini)
                "search_content_tokens": 0  # Gratuits pour web_search_preview
            },
            "gpt-4_1-mini": {  # Alias avec underscore (format normalisé)
                "input": 0.40 / 1_000_000,
                "output": 1.60 / 1_000_000,
                "call_cost": 25.00 / 1_000,  # web_search_preview: $25/1K (tool call fee) + search content tokens GRATUITS
                # Référence doc OpenAI: https://platform.openai.com/docs/guides/function-calling#web-search
                # web_search_preview (non-reasoning): $25/1K + search tokens gratuits
                # web_search (non-preview): $2.50/1K + 8,000 tokens fixes ($5.70/1K total pour gpt-4.1-mini)
                "search_content_tokens": 0  # Gratuits pour web_search_preview
            },
        }
        return pricing.get(model, {"input": 0.0, "output": 0.0, "call_cost": 0.0})

    @staticmethod
    def _calculate_cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
        """
        Calcule le coût en USD basé sur le modèle et les tokens UNIQUEMENT.
        
        NOTE: Les coûts des web_search tool calls sont calculés séparément
        dans end_session() pour éviter de les compter plusieurs fois.
        
        Args:
            model: Nom du modèle
            input_tokens: Nombre de tokens en entrée (total, inclut cached)
            output_tokens: Nombre de tokens en sortie
            cached_tokens: Nombre de tokens mis en cache (facturés à 50% du prix input)
            
        Returns:
            Coût en USD (tokens uniquement, sans les appels web_search)
        """
        model_pricing = CostContext._get_model_pricing(model)

        # Calculer les coûts avec prise en compte des cached tokens
        # Les cached tokens sont facturés à 50% du prix input
        non_cached_input = input_tokens - cached_tokens
        input_cost = (non_cached_input * model_pricing["input"]) + (cached_tokens * model_pricing["input"] * 0.5)
        output_cost = output_tokens * model_pricing["output"]
        
        token_cost = input_cost + output_cost

        return token_cost


# ==========================================
#   TRACKER HIÉRARCHIQUE (SINGLETON)
# ==========================================

class HierarchicalCostTracker:
    """
    Tracker hiérarchique des coûts (Singleton).

    Consolide tous les coûts de manière hiérarchique et génère le rapport final.
    """

    _instance: Optional['HierarchicalCostTracker'] = None

    def __init__(self):
        self.sessions: Dict[str, HierarchicalExtractionCosts] = {}
        self.current_session_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> 'HierarchicalCostTracker':
        """Récupère l'instance singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_session(self, session_id: str, company_name: str):
        """Démarre une nouvelle session de tracking"""
        self.current_session_id = session_id
        self.sessions[session_id] = HierarchicalExtractionCosts(
            session_id=session_id,
            company_name=company_name
        )
        logger.info(f"📊 Session tracking démarrée: {session_id} ({company_name})")

    def record_cost(
        self,
        phase_name: str,
        agent_name: str,
        entity_name: Optional[str],
        token_usages: List[TokenUsage],
        duration_seconds: float
    ):
        """
        Enregistre un coût dans la hiérarchie.

        Args:
            phase_name: Nom de la phase
            agent_name: Nom de l'agent
            entity_name: Nom de l'entité (optionnel)
            token_usages: Liste des usages de tokens
            duration_seconds: Durée d'exécution
        """
        if not self.current_session_id:
            logger.warning("⚠️ Aucune session active, coûts non trackés")
            return

        session = self.sessions[self.current_session_id]

        # Trouver ou créer la phase
        phase = next((p for p in session.phases if p.phase_name == phase_name), None)
        if not phase:
            phase = PhaseCost(phase_name=phase_name)
            session.phases.append(phase)

        # Trouver ou créer l'agent
        agent = next((a for a in phase.agents if a.agent_name == agent_name), None)
        if not agent:
            # Déterminer le modèle depuis les token_usages
            model = token_usages[0].model if token_usages else "unknown"
            agent = AgentCost(agent_name=agent_name, model=model)
            phase.agents.append(agent)

        # Ajouter l'entité (toujours créer une entité pour tracker les tokens)
        effective_entity_name = entity_name or f"{agent_name}_global"
        entity = EntityCost(
            entity_name=effective_entity_name,
            tool_calls=token_usages,
            total_cost_usd=sum(t.cost_usd for t in token_usages),
            extraction_duration_seconds=duration_seconds
        )
        agent.entities.append(entity)

        # Recalcul des totaux
        agent.total_cost_usd = sum(e.total_cost_usd for e in agent.entities)
        agent.execution_duration_seconds += duration_seconds

        phase.total_cost_usd = sum(a.total_cost_usd for a in phase.agents)
        phase.execution_duration_seconds = max(
            phase.execution_duration_seconds,
            duration_seconds
        )

        session._recalculate_totals()

    def get_session_costs(self, session_id: Optional[str] = None) -> Optional[HierarchicalExtractionCosts]:
        """Récupère les coûts d'une session"""
        sid = session_id or self.current_session_id
        return self.sessions.get(sid)

    def end_session(self) -> Optional[HierarchicalExtractionCosts]:
        """Termine la session courante et retourne le rapport final"""
        if not self.current_session_id:
            return None

        session = self.sessions[self.current_session_id]

        # Récupération des tokens depuis le ToolTokensTracker
        try:
            from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker

            tool_tokens = ToolTokensTracker.get_session_tools(self.current_session_id)

            if tool_tokens:
                logger.info(f"📊 Récupération de {len(tool_tokens)} appels tools depuis ToolTokensTracker")

                # Compter les appels web_search séparément
                web_search_calls = 0
                web_search_models = []  # Pour déterminer le coût par appel

                # Grouper les tools par phase
                for tool_usage in tool_tokens:
                    tool_name = tool_usage.get("tool", "unknown")
                    model = tool_usage.get("model", "unknown")
                    input_tokens = tool_usage.get("input_tokens", 0)
                    output_tokens = tool_usage.get("output_tokens", 0)
                    cached_tokens = tool_usage.get("cached_tokens", 0)
                    
                    # Utiliser le nombre réel de web_search calls si disponible, sinon détecter
                    tool_web_search_calls = tool_usage.get("web_search_calls", 0)
                    
                    if tool_web_search_calls > 0:
                        # Utiliser le nombre réel tracké
                        web_search_calls += tool_web_search_calls
                        # Normaliser le modèle pour la recherche de prix
                        normalized_model = model.replace(".", "_") if "." in model else model
                        # Ajouter le modèle pour chaque appel (pour déterminer le coût)
                        for _ in range(tool_web_search_calls):
                            web_search_models.append(normalized_model)
                        logger.info(
                            f"🔍 [CostTracking] {tool_name} ({model}) a {tool_web_search_calls} web_search call(s) tracké(s) → Total cumulé: {web_search_calls}"
                        )
                    else:
                        # Fallback: Détecter les appels web_search basé sur le modèle (ancienne méthode)
                        # Normaliser le nom du modèle (gpt-5.1 -> gpt-5_1 pour la détection)
                        normalized_model = model.replace(".", "_") if "." in model else model
                        is_web_search = (
                            "web_search" in tool_name.lower() or
                            model.endswith("-search-preview") or
                            normalized_model.endswith("-search-preview") or
                            "gpt-5" in model.lower() or
                            normalized_model in ["gpt-5_1", "gpt-5", "gpt-5-mini"]
                        )

                        if is_web_search:
                            # Estimation: 1 appel par tool (ancienne méthode)
                            web_search_calls += 1
                            # Normaliser le modèle pour la recherche de prix
                            normalized_model = model.replace(".", "_") if "." in model else model
                            web_search_models.append(normalized_model)
                            logger.debug(
                                f"🔍 [CostTracking] {tool_name} détecté comme web_search (estimation: 1 appel)"
                            )

                    # Déterminer la phase selon le nom du tool
                    if "eclaireur" in tool_name.lower():
                        phase_name = "phase_0"
                        agent_name = "eclaireur"
                    elif "enrichisseur" in tool_name.lower() or "financial_data" in tool_name.lower() or "headquarters" in tool_name.lower():
                        # Phase 0.5 : Enrichisseur Société Mère
                        phase_name = "phase_0_5"
                        agent_name = "enrichisseur_societe_mere"
                    elif "filiales" in tool_name.lower() or "subsidiary" in tool_name.lower() or "minimal_subsidiary" in tool_name.lower() or "cartographe" in tool_name.lower():
                        phase_name = "phase_1"
                        agent_name = "cartographe_minimal"
                    elif "web_search" in tool_name.lower() or "address" in tool_name.lower() or "contact" in tool_name.lower() or "extracteur" in tool_name.lower():
                        phase_name = "phase_2"
                        agent_name = "extracteur_detaille"
                    else:
                        phase_name = "unknown_phase"
                        agent_name = "unknown_agent"

                    # Normaliser le nom du modèle pour le calcul (gpt-5.1 -> gpt-5_1)
                    normalized_model = model.replace(".", "_") if "." in model else model
                    
                    # Calculer le coût (tokens uniquement, sans call_cost, avec prise en compte des cached tokens)
                    cost_usd = CostContext._calculate_cost(normalized_model, input_tokens, output_tokens, cached_tokens)
                    
                    # Logger le calcul détaillé pour debug
                    model_pricing = CostContext._get_model_pricing(normalized_model)
                    non_cached_input = input_tokens - cached_tokens
                    input_cost = (non_cached_input * model_pricing["input"]) + (cached_tokens * model_pricing["input"] * 0.5)
                    output_cost = output_tokens * model_pricing["output"]
                    logger.info(
                        f"💰 [CostTracking] {tool_name} ({normalized_model}): "
                        f"{input_tokens} in ({non_cached_input} non-cached + {cached_tokens} cached) + "
                        f"{output_tokens} out = ${cost_usd:.6f} "
                        f"(input: ${input_cost:.6f}, output: ${output_cost:.6f})"
                    )
                    
                    if cached_tokens > 0:
                        logger.info(
                            f"💾 [CostTracking] {tool_name}: {cached_tokens} cached tokens "
                            f"(coût réduit à 50%: ${cached_tokens * model_pricing['input'] * 0.5:.6f})"
                        )

                    # Créer TokenUsage
                    token_usage = TokenUsage(
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        cost_usd=cost_usd
                    )

                    # Enregistrer le coût
                    self.record_cost(
                        phase_name=phase_name,
                        agent_name=agent_name,
                        entity_name=None,  # Pas d'entité spécifique pour les tools globaux
                        token_usages=[token_usage],
                        duration_seconds=0  # Pas de durée spécifique
                    )

                # Ajouter le coût des appels web_search séparément
                if web_search_calls > 0:
                    # Déterminer le coût par appel selon le modèle utilisé
                    # Par défaut, utiliser $10/1K = $0.01 par appel pour reasoning models
                    # ou $25/1K = $0.025 par appel pour non-reasoning models
                    call_cost_per_call = 0.01  # Par défaut pour reasoning models
                    
                    # Chercher le premier modèle avec un call_cost défini
                    for model in web_search_models:
                        model_pricing = CostContext._get_model_pricing(model)
                        if model_pricing.get("call_cost", 0) > 0:
                            call_cost_per_call = model_pricing["call_cost"]
                            break
                    
                    # Calcul du coût des web_search calls
                    # Pour gpt-4.1-mini: call_cost ($2.50/1K) + search_content_tokens (8,000 tokens/call × $0.4/1M)
                    web_search_calls_cost = web_search_calls * call_cost_per_call

                    # Ajouter le coût des search_content_tokens si le modèle les utilise
                    model_pricing = CostContext._get_model_pricing(model)
                    if "search_content_tokens" in model_pricing:
                        search_content_tokens_per_call = model_pricing["search_content_tokens"]
                        total_search_content_tokens = web_search_calls * search_content_tokens_per_call
                        search_content_tokens_cost = total_search_content_tokens * model_pricing["input"]
                        web_search_calls_cost += search_content_tokens_cost
                        logger.info(
                            f"💰 [CostTracking] Search content tokens pour {model}: "
                            f"{web_search_calls} calls × {search_content_tokens_per_call} tokens = {total_search_content_tokens:,} tokens "
                            f"(${search_content_tokens_cost:.6f})"
                        )
                    
                    # Déterminer la phase appropriée selon les modèles utilisés
                    # Les web_search calls peuvent être dans phase_0 (Éclaireur) ou phase_1 (Cartographe Minimal)
                    target_phase = None
                    target_phase_name = "phase_1"  # Par défaut
                    
                    # TOUJOURS répartir les appels web_search entre phase_0, phase_0_5, phase_1 et phase_2
                    # en utilisant le nombre réel tracké pour chaque tool
                    phase_0_calls = 0
                    phase_0_5_calls = 0
                    phase_1_calls = 0
                    phase_2_calls = 0
                    
                    logger.info(f"🔍 [CostTracking] Répartition des {web_search_calls} web_search calls par phase...")
                    
                    for tool_usage in tool_tokens:
                        tool_name = tool_usage.get("tool", "").lower()
                        model = tool_usage.get("model", "")
                        tool_web_search_calls = tool_usage.get("web_search_calls", 0)
                        
                        # IMPORTANT: Ne compter QUE les appels réellement trackés (web_search_calls > 0)
                        # Ne PAS utiliser la détection automatique pour éviter de surcompter
                        
                        if tool_web_search_calls > 0:
                            if "eclaireur" in tool_name:
                                phase_0_calls += tool_web_search_calls
                                logger.info(f"🔍 [CostTracking] Phase 0: {tool_usage.get('tool', 'unknown')} ({model}) a {tool_web_search_calls} web_search call(s) → Total phase_0: {phase_0_calls}")
                            elif "enrichisseur" in tool_name or "financial_data" in tool_name or "headquarters" in tool_name:
                                # Phase 0.5 : Enrichisseur Société Mère
                                phase_0_5_calls += tool_web_search_calls
                                logger.info(f"🔍 [CostTracking] Phase 0.5: {tool_usage.get('tool', 'unknown')} ({model}) a {tool_web_search_calls} web_search call(s) → Total phase_0_5: {phase_0_5_calls}")
                            elif "minimal_subsidiary" in tool_name or "cartographe" in tool_name:
                                phase_1_calls += tool_web_search_calls
                                logger.info(f"🔍 [CostTracking] Phase 1: {tool_usage.get('tool', 'unknown')} ({model}) a {tool_web_search_calls} web_search call(s) → Total phase_1: {phase_1_calls}")
                            elif "contact" in tool_name or "extracteur" in tool_name:
                                phase_2_calls += tool_web_search_calls
                                logger.info(f"🔍 [CostTracking] Phase 2: {tool_usage.get('tool', 'unknown')} ({model}) a {tool_web_search_calls} web_search call(s) → Total phase_2: {phase_2_calls}")
                        else:
                            # Logger pour debug si un tool avec web_search n'a pas de web_search_calls tracké
                            normalized_model = model.replace(".", "_") if "." in model else model
                            is_web_search_model = (
                                model.endswith("-search-preview") or
                                normalized_model.endswith("-search-preview") or
                                "gpt-5" in model.lower() or
                                normalized_model in ["gpt-5_1", "gpt-5", "gpt-5-mini"]
                            )
                            if is_web_search_model:
                                logger.warning(f"⚠️ [CostTracking] {tool_usage.get('tool', 'unknown')} ({model}) n'a pas de web_search_calls tracké (peut être normal si aucun appel n'a été fait, ou problème de détection)")
                    
                    # Vérifier que la somme correspond
                    total_phased_calls = phase_0_calls + phase_0_5_calls + phase_1_calls + phase_2_calls
                    if total_phased_calls != web_search_calls:
                        logger.warning(
                            f"⚠️ [CostTracking] Incohérence: web_search_calls total={web_search_calls}, "
                            f"mais phase_0={phase_0_calls} + phase_0_5={phase_0_5_calls} + phase_1={phase_1_calls} + phase_2={phase_2_calls} = {total_phased_calls}"
                        )
                    
                    # Utiliser les appels répartis par phase au lieu du total
                    # IMPORTANT: Calculer le coût par phase en utilisant le bon tarif pour chaque modèle
                    if phase_0_calls > 0 or phase_0_5_calls > 0 or phase_1_calls > 0 or phase_2_calls > 0:
                        
                        # Trouver le modèle utilisé dans chaque phase pour appliquer le bon tarif
                        phase_0_model = None
                        phase_0_5_model = None
                        phase_1_model = None
                        phase_2_model = None
                        
                        for tool_usage in tool_tokens:
                            tool_name = tool_usage.get("tool", "").lower()
                            model = tool_usage.get("model", "")
                            tool_web_search_calls = tool_usage.get("web_search_calls", 0)
                            
                            if tool_web_search_calls > 0:
                                normalized_model = model.replace(".", "_") if "." in model else model
                                if "eclaireur" in tool_name and phase_0_model is None:
                                    phase_0_model = normalized_model
                                elif ("enrichisseur" in tool_name or "financial_data" in tool_name or "headquarters" in tool_name) and phase_0_5_model is None:
                                    phase_0_5_model = normalized_model
                                elif ("minimal_subsidiary" in tool_name or "cartographe" in tool_name) and phase_1_model is None:
                                    phase_1_model = normalized_model
                                elif ("contact" in tool_name or "extracteur" in tool_name) and phase_2_model is None:
                                    phase_2_model = normalized_model
                        
                        # Calculer les coûts par phase avec le bon tarif
                        if phase_0_5_calls > 0:
                            phase_0_5 = next((p for p in session.phases if p.phase_name == "phase_0_5"), None)
                            if phase_0_5:
                                # Utiliser le tarif du modèle de phase_0_5
                                phase_0_5_pricing = CostContext._get_model_pricing(phase_0_5_model or "gpt-4_1-mini")
                                phase_0_5_call_cost = phase_0_5_pricing.get("call_cost", 0.025)
                                phase_0_5_cost = phase_0_5_calls * phase_0_5_call_cost
                                phase_0_5.total_cost_usd += phase_0_5_cost
                                logger.info(
                                    f"📊 Coût des appels web_search phase_0_5: {phase_0_5_calls} appels × ${phase_0_5_call_cost:.4f} ({phase_0_5_model}) = ${phase_0_5_cost:.4f}"
                                )
                            else:
                                # Si phase_0_5 n'existe pas, créer une phase pour les web_search calls
                                phase_0_5 = PhaseCost(phase_name="phase_0_5")
                                phase_0_5_pricing = CostContext._get_model_pricing(phase_0_5_model or "gpt-4_1-mini")
                                phase_0_5_call_cost = phase_0_5_pricing.get("call_cost", 0.025)
                                phase_0_5.total_cost_usd = phase_0_5_calls * phase_0_5_call_cost
                                session.phases.append(phase_0_5)
                                logger.info(
                                    f"📊 Coût des appels web_search phase_0_5: {phase_0_5_calls} appels × ${phase_0_5_call_cost:.4f} ({phase_0_5_model}) = ${phase_0_5.total_cost_usd:.4f} (nouvelle phase_0_5 créée)"
                                )
                        
                        if phase_0_calls > 0:
                            phase_0 = next((p for p in session.phases if p.phase_name == "phase_0"), None)
                            if phase_0:
                                # Utiliser le tarif du modèle de phase_0
                                phase_0_pricing = CostContext._get_model_pricing(phase_0_model or "gpt-4o-search-preview")
                                phase_0_call_cost = phase_0_pricing.get("call_cost", 0.01)
                                phase_0_cost = phase_0_calls * phase_0_call_cost
                                phase_0.total_cost_usd += phase_0_cost
                                logger.info(
                                    f"📊 Coût des appels web_search phase_0: {phase_0_calls} appels × ${phase_0_call_cost:.4f} ({phase_0_model}) = ${phase_0_cost:.4f}"
                                )
                        
                        if phase_1_calls > 0:
                            phase_1 = next((p for p in session.phases if p.phase_name == "phase_1"), None)
                            if phase_1:
                                # Utiliser le tarif du modèle de phase_1
                                phase_1_pricing = CostContext._get_model_pricing(phase_1_model or "gpt-5_1")
                                phase_1_call_cost = phase_1_pricing.get("call_cost", 0.01)
                                phase_1_cost = phase_1_calls * phase_1_call_cost
                                phase_1.total_cost_usd += phase_1_cost
                                logger.info(
                                    f"📊 Coût des appels web_search phase_1: {phase_1_calls} appels × ${phase_1_call_cost:.4f} ({phase_1_model}) = ${phase_1_cost:.4f}"
                                )
                            else:
                                # Si phase_1 n'existe pas, créer une phase pour les web_search calls
                                phase_1 = PhaseCost(phase_name="phase_1")
                                phase_1_pricing = CostContext._get_model_pricing(phase_1_model or "gpt-5_1")
                                phase_1_call_cost = phase_1_pricing.get("call_cost", 0.01)
                                phase_1.total_cost_usd = phase_1_calls * phase_1_call_cost
                                session.phases.append(phase_1)
                                logger.info(
                                    f"📊 Coût des appels web_search phase_1: {phase_1_calls} appels × ${phase_1_call_cost:.4f} ({phase_1_model}) = ${phase_1.total_cost_usd:.4f} (nouvelle phase_1 créée)"
                                )
                        
                        if phase_2_calls > 0:
                            phase_2 = next((p for p in session.phases if p.phase_name == "phase_2"), None)
                            if phase_2:
                                # Utiliser le tarif du modèle de phase_2
                                phase_2_pricing = CostContext._get_model_pricing(phase_2_model or "gpt-4o-search-preview")
                                phase_2_call_cost = phase_2_pricing.get("call_cost", 0.01)
                                phase_2_cost = phase_2_calls * phase_2_call_cost
                                phase_2.total_cost_usd += phase_2_cost
                                logger.info(
                                    f"📊 Coût des appels web_search phase_2: {phase_2_calls} appels × ${phase_2_call_cost:.4f} ({phase_2_model}) = ${phase_2_cost:.4f}"
                                )
                    # La répartition par phase est maintenant toujours faite ci-dessus
                    # Cette section else n'est plus nécessaire car on répartit toujours
                    
                    # Recalculer les totaux pour inclure le coût des web_search calls
                    session._recalculate_totals()

                # Nettoyer les données du ToolTokensTracker
                ToolTokensTracker.clear_session(self.current_session_id)
                logger.info(f"📊 {len(tool_tokens)} appels tools intégrés au rapport hiérarchique")

        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la récupération des tokens tools: {e}")

        logger.info(f"📊 Session terminée: {self.current_session_id}")

        # Logger le détail des coûts pour debug
        total_phases_cost = sum(phase.total_cost_usd for phase in session.phases)
        logger.info(f"💰 [CostTracking] Détail des coûts:")
        logger.info(f"   - Total phases: ${total_phases_cost:.6f}")
        for phase in session.phases:
            logger.info(f"   - {phase.phase_name}: ${phase.total_cost_usd:.6f}")
        logger.info(f"   - Total session: ${session.total_cost_usd:.6f}")

        # Logger le détail par modèle
        logger.info(f"💰 [CostTracking] Détail par modèle:")
        model_costs = {}
        for phase in session.phases:
            for agent in phase.agents:
                model = agent.model
                if model not in model_costs:
                    model_costs[model] = {"cost": 0, "input": 0, "output": 0}
                model_costs[model]["cost"] += agent.total_cost_usd
                for entity in agent.entities:
                    for tool_call in entity.tool_calls:
                        model_costs[model]["input"] += tool_call.input_tokens
                        model_costs[model]["output"] += tool_call.output_tokens

        for model, stats in sorted(model_costs.items()):
            logger.info(
                f"   - {model}: ${stats['cost']:.6f} "
                f"({stats['input']:,} in + {stats['output']:,} out)"
            )

        logger.info(session.summary())

        self.current_session_id = None
        return session


# ==========================================
#   HELPER : CONTEXT MANAGER FACTORY
# ==========================================

@asynccontextmanager
async def track_cost(
    phase_name: str,
    agent_name: str,
    entity_name: Optional[str] = None
):
    """
    Factory pour créer un CostContext facilement.

    Usage:
        async with track_cost("phase_1", "cartographe_minimal") as ctx:
            result = await some_api_call()
            ctx.add_token_usage("gpt-4o-mini", 100, 50)
    """
    ctx = CostContext(phase_name, agent_name, entity_name)
    async with ctx:
        yield ctx
