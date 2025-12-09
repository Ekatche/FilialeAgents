"""
Source filtering utilities for company information extraction.

This module handles filtering of sources based on accessibility,
freshness, and deduplication.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta

from .url_validator import filter_sources_by_accessibility

logger = logging.getLogger(__name__)


def filter_fresh_sources(
    sources: List[Dict[str, Any]], 
    max_age_months: int = 24
) -> List[Dict[str, Any]]:
    """
    Filtre les sources en fonction de leur fraîcheur.
    
    Args:
        sources: Liste des sources à filtrer
        max_age_months: Âge maximum en mois
        
    Returns:
        Sources filtrées par fraîcheur
    """
    if not sources:
        return []
    
    cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)
    fresh_sources = []
    
    for source in sources:
        if not isinstance(source, dict):
            fresh_sources.append(source)
            continue
            
        published_date = source.get("published_date")
        if not published_date:
            # Si pas de date, on garde la source
            fresh_sources.append(source)
            continue
            
        try:
            # Parser la date (format YYYY-MM-DD)
            if isinstance(published_date, str):
                source_date = datetime.strptime(published_date, "%Y-%m-%d")
            else:
                fresh_sources.append(source)
                continue
                
            if source_date >= cutoff_date:
                fresh_sources.append(source)
            else:
                logger.debug(
                    "Source filtrée (trop ancienne): %s (date: %s)",
                    source.get("url", "unknown"),
                    published_date
                )
        except ValueError:
            # Date invalide, on garde la source
            fresh_sources.append(source)
    
    return fresh_sources


def dedupe_sites(
    sites: List[Dict[str, Any]], 
    max_items: int = 7
) -> List[Dict[str, Any]]:
    """
    Déduplique les sites en fonction de leurs caractéristiques.
    
    Args:
        sites: Liste des sites à dédupliquer
        max_items: Nombre maximum d'éléments à conserver
        
    Returns:
        Sites dédupliqués
    """
    if not sites:
        return []
    
    deduped = []
    seen: Set[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]] = set()
    
    for site in sites:
        if not isinstance(site, dict):
            continue
            
        # Créer une clé unique basée sur les caractéristiques principales
        key = (
            site.get("label"),
            site.get("line1"),
            site.get("city"),
            site.get("country"),
        )
        
        if key in seen:
            continue
            
        seen.add(key)
        deduped.append(site)
        
        if len(deduped) >= max_items:
            break
    
    return deduped


def extract_sources_from_subsidiary(subsidiary: Dict[str, Any]) -> List[str]:
    """
    Extrait les URLs sources d'une filiale.
    
    Args:
        subsidiary: Données de la filiale
        
    Returns:
        Liste des URLs sources
    """
    if not isinstance(subsidiary, dict):
        return []
    
    sources = []
    subsidiary_sources = subsidiary.get("sources", [])
    
    if isinstance(subsidiary_sources, list):
        for src in subsidiary_sources:
            if isinstance(src, dict) and src.get("url"):
                sources.append(src["url"])
            elif isinstance(src, str):
                sources.append(src)
    
    return sources


async def filter_sources_comprehensive(
    sources: List[Any],
    *,
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    max_age_months: int = 24,
    max_sources: int = 7
) -> Tuple[List[Any], List[str]]:
    """
    Filtre les sources de manière complète (accessibilité + fraîcheur).
    
    Args:
        sources: Liste des sources à filtrer
        session_id: ID de session pour le logging
        agent_name: Nom de l'agent pour le logging
        max_age_months: Âge maximum en mois
        max_sources: Nombre maximum de sources
        
    Returns:
        Tuple (sources_filtrées, urls_supprimées)
    """
    if not sources:
        return [], []
    
    # Étape 1: Filtrage par accessibilité
    accessible_sources, inaccessible_urls = await filter_sources_by_accessibility(
        sources, session_id=session_id, agent_name=agent_name
    )
    
    # Étape 2: Filtrage par fraîcheur (si activé)
    fresh_sources = filter_fresh_sources(accessible_sources, max_age_months)
    
    # Étape 3: Limitation du nombre de sources
    final_sources = fresh_sources[:max_sources]
    
    total_removed = len(sources) - len(final_sources)
    if total_removed > 0:
        logger.info(
            "Filtrage des sources: %d sources supprimées (inaccessibles: %d, autres: %d)",
            total_removed,
            len(inaccessible_urls),
            total_removed - len(inaccessible_urls)
        )
    
    return final_sources, inaccessible_urls


def validate_source_quality(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valide la qualité d'une source et retourne des métadonnées.
    
    Args:
        source: Source à valider
        
    Returns:
        Métadonnées de qualité de la source
    """
    if not isinstance(source, dict):
        return {"quality_score": 0.0, "issues": ["Invalid source format"]}
    
    issues = []
    quality_score = 1.0
    
    # Vérifier l'URL
    url = source.get("url")
    if not url:
        issues.append("Missing URL")
        quality_score -= 0.5
    elif not url.startswith(("http://", "https://")):
        issues.append("Invalid URL format")
        quality_score -= 0.3
    
    # Vérifier le titre
    title = source.get("title")
    if not title:
        issues.append("Missing title")
        quality_score -= 0.2
    
    # Vérifier le tier
    tier = source.get("tier")
    if not tier:
        issues.append("Missing tier")
        quality_score -= 0.1
    elif tier not in ["official", "financial_media", "pro_db", "other"]:
        issues.append("Invalid tier")
        quality_score -= 0.1
    
    # Vérifier la date
    published_date = source.get("published_date")
    if not published_date:
        issues.append("Missing publication date")
        quality_score -= 0.1
    
    return {
        "quality_score": max(0.0, quality_score),
        "issues": issues,
        "is_high_quality": quality_score >= 0.8
    }
