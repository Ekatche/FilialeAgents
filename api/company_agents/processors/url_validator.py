"""
URL validation and accessibility checking utilities.

This module handles URL validation, caching, and accessibility checks
for the extraction pipeline.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import httpx

from ..config.extraction_config import (
    URL_TIMEOUT_S,
    URL_ALLOWED_STATUSES,
    URL_REQUEST_HEADERS,
    get_url_cache,
    set_url_cache_status,
    get_url_cache_status,
)

logger = logging.getLogger(__name__)


async def is_url_accessible(url: str) -> bool:
    """
    Vérifie si une URL est accessible.
    
    Args:
        url: L'URL à vérifier
        
    Returns:
        True si l'URL est accessible, False sinon
    """
    if not url:
        return False
        
    # Vérifier le cache d'abord
    cached = get_url_cache_status(url)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(
            timeout=URL_TIMEOUT_S,
            follow_redirects=True,
            headers=URL_REQUEST_HEADERS,
        ) as client:
            response = await client.head(url)
            if (
                response.status_code >= 400
                and response.status_code not in URL_ALLOWED_STATUSES
            ):
                response = await client.get(url)
                
        is_accessible = (
            response.status_code < 400 
            or response.status_code in URL_ALLOWED_STATUSES
        )
    except Exception:
        logger.debug("URL accessibility check failed for %s", url, exc_info=True)
        is_accessible = False

    # Mettre en cache le résultat
    set_url_cache_status(url, is_accessible)
    return is_accessible


async def validate_urls_accessibility(
    urls: List[str], 
    *,
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None
) -> Tuple[List[str], List[str]]:
    """
    Valide l'accessibilité d'une liste d'URLs.
    
    Args:
        urls: Liste des URLs à valider
        session_id: ID de session pour le logging
        agent_name: Nom de l'agent pour le logging
        
    Returns:
        Tuple (urls_accessibles, urls_inaccessibles)
    """
    accessible_urls = []
    inaccessible_urls = []
    
    for url in urls:
        if await is_url_accessible(url):
            accessible_urls.append(url)
        else:
            inaccessible_urls.append(url)
            logger.info(
                "URL exclue (inaccessible) pour session=%s agent=%s : %s",
                session_id or "unknown",
                agent_name or "unknown", 
                url,
            )
    
    return accessible_urls, inaccessible_urls


async def filter_sources_by_accessibility(
    sources: Optional[List[Any]],
    *,
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None
) -> Tuple[List[Any], List[str]]:
    """
    Filtre une liste de sources en fonction de l'accessibilité de leurs URLs.
    
    Args:
        sources: Liste des sources à filtrer
        session_id: ID de session pour le logging
        agent_name: Nom de l'agent pour le logging
        
    Returns:
        Tuple (sources_filtrées, urls_supprimées)
    """
    filtered_sources = []
    removed_urls = []

    if not sources:
        return filtered_sources, removed_urls

    for entry in sources:
        if isinstance(entry, dict):
            url = entry.get("url")
        elif isinstance(entry, str):
            url = entry
        else:
            url = None

        if not url:
            filtered_sources.append(entry)
            continue

        if await is_url_accessible(url):
            filtered_sources.append(entry)
        else:
            removed_urls.append(url)
            logger.info(
                "Source exclue (URL inaccessible) pour session=%s agent=%s : %s",
                session_id or "unknown",
                agent_name or "unknown",
                url,
            )

    return filtered_sources, removed_urls


def get_url_cache_status(url: str) -> bool:
    """Récupère le statut d'accessibilité d'une URL depuis le cache."""
    from ..config.extraction_config import get_url_cache_status as _get_cache_status
    return _get_cache_status(url)


def set_url_cache_status(url: str, is_accessible: bool) -> None:
    """Met à jour le statut d'accessibilité d'une URL dans le cache."""
    from ..config.extraction_config import set_url_cache_status as _set_cache_status
    _set_cache_status(url, is_accessible)


def clear_url_cache() -> None:
    """Vide le cache d'accessibilité des URLs."""
    from ..config.extraction_config import clear_url_cache
    clear_url_cache()
