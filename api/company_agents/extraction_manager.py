"""
Orchestrateur multi-agents pour l'extraction d'informations d'entreprise.

Ce module coordonne l'exécution séquentielle des agents spécialisés :
1. 🔍 Company Analyzer : Identification de l'entité légale
2. ⛏️ Information Extractor : Consolidation des informations clés
3. 🗺️ Subsidiary Extractor : Extraction des filiales
4. ⚖️ Meta Validator : Validation de cohérence
5. 🔄 Data Restructurer : Normalisation finale

Fonctionnalités :
- Gestion des sessions et tracking en temps réel
- Validation et filtrage des sources
- Gestion des erreurs et retry automatique
- Cache d'accessibilité des URLs
"""

# flake8: noqa
from __future__ import annotations
from typing import Any, Dict

# Import des modules refactorisés
from .orchestrator import orchestrate_extraction
from .config import (
    get_all_tools_names,
    get_agent_info,
    get_extraction_steps,
    get_sub_agents_info,
)

# Import pour la compatibilité avec l'API existante - supprimé pour éviter la dépendance circulaire

# Exposition de l'API publique
__all__ = [
    "orchestrate_extraction",
    "get_all_tools_names",
    "get_agent_info", 
    "get_extraction_steps",
    "get_sub_agents_info",
]


# =======================================================
# 🔧 Fonctions pour le webhook de suivi en temps réel
# =======================================================

def get_all_tools_names() -> list[str]:
    """Retourne la liste des noms d'outils disponibles"""
    return get_all_tools_names()


def get_agent_info() -> Dict[str, Any]:
    """Retourne les informations sur l'orchestrateur principal"""
    return get_agent_info()


def get_extraction_steps() -> list[Dict[str, Any]]:
    """Retourne les étapes d'extraction avec leurs agents"""
    return get_extraction_steps()


def get_sub_agents_info() -> Dict[str, Dict[str, Any]]:
    """Retourne les informations sur les sous-agents"""
    return get_sub_agents_info()
