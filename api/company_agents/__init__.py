"""
Package company_agents - Orchestration multi-agents pour l'extraction d'informations d'entreprise.

Architecture :
- models.py : Modèles Pydantic pour la validation des données
- extraction_core.py : Point d'entrée principal de l'API
- extraction_manager.py : Orchestrateur des agents spécialisés
- subs_agents/ : Agents spécialisés (analyzer, extractor, validator)
"""

# Modèles Pydantic pour la validation des données
from .models import (
    CompanyInfo,        # Modèle final de sortie API
    SubsidiaryReport,   # Rapport des filiales
    CompanyCard,        # Fiche d'identité entreprise
    Subsidiary,         # Modèle filiale
    SubsidiaryDetail,   # Détails d'une filiale
    ExtractionMetadata, # Métadonnées d'extraction
    SourceRef,          # Référence source unifiée
)

# Point d'entrée principal de l'API
from .extraction_core import extract_company_data


__all__ = [
    # Models
    "CompanyInfo",
    "SubsidiaryReport",
    "CompanyCard",
    "Subsidiary",
    "SubsidiaryDetail",
    "ExtractionMetadata",
    "SourceRef",
    # Core Extraction
    "extract_company_data",
]
