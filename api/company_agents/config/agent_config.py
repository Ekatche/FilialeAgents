"""
Configuration for agents and extraction steps.

This module contains metadata about agents, extraction steps, and tool names.
"""

from typing import Dict, List, Any
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
