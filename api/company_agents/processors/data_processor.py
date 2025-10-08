"""
Data processing utilities for company information extraction.

This module handles data transformation, merging, and processing
for company information and subsidiaries.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractionState:
    """État d'extraction pour le traitement des données."""
    session_id: str
    raw_input: str
    include_subsidiaries: bool = True
    target_entity: Optional[str] = None
    info_card: Optional[Dict[str, Any]] = None
    info_raw: Optional[Dict[str, Any]] = None
    subs_report: Optional[Dict[str, Any]] = None
    subs_raw: Optional[Dict[str, Any]] = None
    analyzer_raw: Optional[Dict[str, Any]] = None
    meta_report: Optional[Dict[str, Any]] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def merge_sources(
    existing_sources: List[str], 
    new_sources: List[str], 
    max_sources: int = 7
) -> List[str]:
    """
    Fusionne deux listes de sources en évitant les doublons.
    
    Args:
        existing_sources: Sources existantes
        new_sources: Nouvelles sources à ajouter
        max_sources: Nombre maximum de sources
        
    Returns:
        Liste fusionnée des sources
    """
    seen: Set[str] = set()
    merged = []
    
    # Ajouter les sources existantes d'abord
    for source in existing_sources:
        if source and source not in seen and len(merged) < max_sources:
            seen.add(source)
            merged.append(source)
    
    # Ajouter les nouvelles sources
    for source in new_sources:
        if source and source not in seen and len(merged) < max_sources:
            seen.add(source)
            merged.append(source)
    
    return merged


def collect_sources(
    analyzer_data: Dict[str, Any], 
    subs_report: Optional[Dict[str, Any]]
) -> List[str]:
    """
    Collecte toutes les sources depuis les données d'analyse et de filiales.
    
    Args:
        analyzer_data: Données de l'analyseur d'entreprise
        subs_report: Rapport des filiales
        
    Returns:
        Liste des URLs sources collectées
    """
    sources = []
    
    # Sources de l'analyseur
    if analyzer_data and isinstance(analyzer_data, dict):
        analyzer_sources = analyzer_data.get("sources", [])
        if isinstance(analyzer_sources, list):
            for src in analyzer_sources:
                if isinstance(src, dict) and src.get("url"):
                    sources.append(src["url"])
                elif isinstance(src, str):
                    sources.append(src)
    
    # Sources des filiales
    if subs_report and isinstance(subs_report, dict):
        subsidiaries = subs_report.get("subsidiaries", [])
        if isinstance(subsidiaries, list):
            for sub in subsidiaries:
                if isinstance(sub, dict):
                    sub_sources = sub.get("sources", [])
                    if isinstance(sub_sources, list):
                        for src in sub_sources:
                            if isinstance(src, dict) and src.get("url"):
                                sources.append(src["url"])
                            elif isinstance(src, str):
                                sources.append(src)
    
    return sources


def process_subsidiary_data(
    subsidiary: Dict[str, Any],
    *,
    fallback_sources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Traite les données d'une filiale pour les normaliser.
    
    Args:
        subsidiary: Données brutes de la filiale
        fallback_sources: Sources de fallback si aucune source n'est trouvée
        
    Returns:
        Données de filiale traitées
    """
    if not isinstance(subsidiary, dict):
        return {}
    
    processed = {
        "subsidiary_name": subsidiary.get("legal_name", "Unknown"),
        "type": subsidiary.get("type", "subsidiary"),
        "activity": subsidiary.get("activity"),
        "confidence": subsidiary.get("confidence"),
    }
    
    # Traitement des sources
    sources = []
    if subsidiary.get("sources"):
        for src in subsidiary["sources"]:
            if isinstance(src, dict) and src.get("url"):
                sources.append(src["url"])
            elif isinstance(src, str):
                sources.append(src)
    
    # Utiliser les sources de fallback si nécessaire
    if not sources and fallback_sources:
        sources = fallback_sources[:2]  # Limiter à 2 sources max
    
    processed["sources"] = sources
    
    # Traitement du siège social
    headquarters = subsidiary.get("headquarters")
    if isinstance(headquarters, dict):
        processed["headquarters_site"] = headquarters
    else:
        processed["headquarters_site"] = headquarters  # Données brutes
    
    # Traitement des sites opérationnels
    sites = subsidiary.get("sites", [])
    if isinstance(sites, list):
        processed["operational_sites"] = sites
    else:
        processed["operational_sites"] = []
    
    return processed


def build_company_info(
    state: ExtractionState,
    analyzer_data: Dict[str, Any],
    info_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Construit l'objet CompanyInfo final à partir des données extraites.
    
    Args:
        state: État d'extraction
        analyzer_data: Données de l'analyseur
        info_data: Données d'information
        
    Returns:
        Objet CompanyInfo construit
    """
    company_info: Dict[str, Any] = {}

    # Nom de l'entreprise
    target = (
        state.target_entity or analyzer_data.get("entity_legal_name") or state.raw_input
    )
    company_info["company_name"] = target

    # L'agent restructurateur gère maintenant le mapping CompanyCard → CompanyInfo
    # On laisse les données brutes pour que l'agent restructurateur les traite
    company_info["headquarters_address"] = info_data.get("headquarters", "Unknown")
    company_info["headquarters_city"] = "Unknown"  # Sera normalisé par l'agent restructurateur
    company_info["headquarters_country"] = "Unknown"  # Sera normalisé par l'agent restructurateur

    # sector → industry_sector
    company_info["industry_sector"] = info_data.get("sector") or "Non spécifié"

    # activities → core_business (join des activités)
    activities = info_data.get("activities") or []
    company_info["core_business"] = (
        "; ".join(activities) if activities else "Non spécifié"
    )

    # revenue_recent → revenue
    company_info["revenue"] = info_data.get("revenue_recent")

    # employees → employee_count
    company_info["employee_count"] = info_data.get("employees")

    # founding_year (int) → founding_year (str)
    founding_year = info_data.get("founded_year")
    company_info["founding_year"] = str(founding_year) if founding_year else None

    # legal_status (pas dans CompanyCard, on met None)
    company_info["legal_status"] = None

    # confidence_score (pas dans CompanyCard, on met 0.8 par défaut)
    company_info["confidence_score"] = 0.8

    # sources (List[SourceRef dict]) → sources (List[str])
    sources_refs = info_data.get("sources") or []
    logger.info("🔍 DEBUG info_data sources_refs count: %d", len(sources_refs))
    company_info["sources"] = [
        src.get("url") if isinstance(src, dict) else src
        for src in sources_refs
        if (isinstance(src, dict) and src.get("url")) or isinstance(src, str)
    ]
    logger.info(
        "🔍 DEBUG company_info sources after info_data: %s", company_info["sources"]
    )

    # Gestion de la société mère
    relationship = analyzer_data.get("relationship")
    parent_company = analyzer_data.get("parent_company")
    if relationship == "subsidiary" and parent_company:
        company_info["parent_company"] = parent_company
    elif relationship in {"parent", "independent"}:
        # conserver valeur déjà présente le cas échéant
        company_info["parent_company"] = info_data.get("parent_company")

    # Collecter et fusionner les sources AVANT de merger les subsidiaires
    extra_sources = collect_sources(analyzer_data, state.subs_report)
    logger.info("🔍 DEBUG extra_sources collected: %s", extra_sources)
    company_info["sources"] = merge_sources(
        company_info.get("sources", []), extra_sources
    )
    logger.info(
        "🔍 DEBUG company_info sources after merge: %s", company_info["sources"]
    )

    # Traitement des filiales
    details = []
    if state.subs_report and state.subs_report.get("subsidiaries"):
        for sub in state.subs_report["subsidiaries"]:
            processed_sub = process_subsidiary_data(
                sub, fallback_sources=company_info.get("sources", [])
            )
            if processed_sub:
                details.append(processed_sub)
    
    company_info["subsidiaries_details"] = details
    company_info["total_subsidiaries"] = len(details)
    company_info["detailed_subsidiaries"] = len(details)

    # Traitement des métadonnées de validation
    if state.meta_report:
        scores = state.meta_report.get("section_scores") or {}
        coherence = {
            "geographic_score": scores.get("geographic"),
            "structure_score": scores.get("structure"),
            "sources_score": scores.get("sources"),
            "overall_score": scores.get("overall"),
            "conflicts": [
                c.get("description")
                for c in state.meta_report.get("conflicts", [])[:10]
                if isinstance(c, dict)
            ],
        }
        company_info["coherence_analysis"] = coherence
        if scores.get("overall") is not None:
            company_info["confidence_score"] = float(scores["overall"])

    # Traitement des avertissements
    if state.warnings:
        warning_label = "; ".join(state.warnings[:2])
        quality = list(company_info.get("quality_indicators", []))
        quality.append(
            {
                "indicator_name": "WorkflowWarnings",
                "score": 0.0,
                "description": warning_label,
            }
        )
        company_info["quality_indicators"] = quality

    return company_info
