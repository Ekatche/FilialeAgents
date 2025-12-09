"""
Configuration for agents and extraction steps.

This module contains metadata about agents, extraction steps, and tool names.
"""

from typing import Dict, List, Any, Callable
import importlib
from .extraction_config import MAX_TURNS

# Noms des outils disponibles
DEFAULT_TOOL_NAMES: List[str] = [
    "run_analyze_and_info",
    "information_extractor",
    "subsidiary_extractor",
    "meta_validator",
    "data_restructurer",
]

# Étapes d'extraction avec leurs agents
DEFAULT_EXTRACTION_STEPS: List[Dict[str, Any]] = [
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
    {
        "name": "Restructuration des données",
        "agent": "🔄 Restructurateur",
        "duration": 3,
        "conditional": True,
    },
]

# Configuration des sous-agents
DEFAULT_SUB_AGENTS: Dict[str, Dict[str, Any]] = {
    "company_analyzer": {"max_turns": MAX_TURNS["analyze"]},
    "information_extractor": {"max_turns": MAX_TURNS["info"]},
    "subsidiary_extractor": {"max_turns": MAX_TURNS["subs"]},
    "meta_validator": {"max_turns": MAX_TURNS["meta"]},
    "data_restructurer": {"max_turns": 3},
}

# Guardrails dynamiques (module:function)
DEFAULT_AGENT_GUARDRAILS: Dict[str, List[str]] = {
    # Ex: pour l'Éclaireur (company_analyzer), on active un guardrail d'URLs on-domain
    "company_analyzer": [
        "company_agents.guardrails.eclaireur:eclaireur_output_guardrail",
    ],
}


def load_guardrails(agent_key: str) -> List[Callable]:
    """Charge dynamiquement les guardrails déclarés pour un agent.

    Chaque entrée est du type "module.sub:callable". Si un import échoue, on l'ignore.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    guardrails: List[Callable] = []
    entries = DEFAULT_AGENT_GUARDRAILS.get(agent_key, [])
    for entry in entries:
        try:
            module_name, func_name = entry.split(":", 1)
            mod = importlib.import_module(module_name)
            func = getattr(mod, func_name, None)
            
            # Le decorator @output_guardrail retourne un objet OutputGuardrail
            # qui peut ne pas être directement callable, mais est utilisable par l'Agent
            if func is not None:
                guardrails.append(func)
                logger.info(f"✅ Guardrail chargé: {entry}")
            else:
                logger.warning(f"⚠️ {func_name} non trouvé dans {module_name}")
        except Exception as e:
            logger.error(f"❌ Impossible de charger le guardrail {entry}: {e}")
            continue
    
    if not guardrails and entries:
        logger.warning(f"⚠️ Aucun guardrail chargé pour {agent_key} (configurés: {entries})")
    
    return guardrails


def get_all_tools_names() -> List[str]:
    """Retourne la liste des noms d'outils disponibles"""
    return [
        "run_analyze_and_info",
        "information_extractor",
        "subsidiary_extractor",
        "meta_validator",
        "data_restructurer",
    ]


def get_agent_info() -> Dict[str, Any]:
    """Retourne les informations sur l'orchestrateur principal"""
    return {
        "name": "Extraction Orchestrator",
        "model": "gpt-4o-mini",
        "tools_count": len(get_all_tools_names()),
        "max_turns": 8,
    }


def get_extraction_steps() -> List[Dict[str, Any]]:
    """Retourne les étapes d'extraction avec leurs agents"""
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
        {
            "name": "Restructuration des données",
            "agent": "🔄 Restructurateur",
            "duration": 3,
            "conditional": True,
        },
    ]


def get_sub_agents_info() -> Dict[str, Dict[str, Any]]:
    """Retourne les informations sur les sous-agents"""
    return {
        "company_analyzer": {"max_turns": 2, "model": "gpt-4.1-mini"},
        "information_extractor": {"max_turns": 2, "model": "gpt-5-nano"},
        "subsidiary_extractor": {"max_turns": 3, "model": "sonar"},
        "meta_validator": {"max_turns": 1, "model": "gpt-4o-mini"},
        "data_restructurer": {"max_turns": 1, "model": "gpt-4.1-mini"},
    }
