"""
Configuration constants for the extraction pipeline.

This module contains all the configuration settings for URL validation,
timeouts, headers, and feature flags.
"""

from typing import Dict, Set

# Configuration pour la validation des URLs
_URL_STATUS_CACHE: Dict[str, bool] = {}  # Cache d'accessibilité des URLs
URL_TIMEOUT_S = 5.0  # Timeout pour les requêtes HTTP
URL_ALLOWED_STATUSES: Set[int] = {
    403
}  # Codes de statut acceptés (403 = accès restreint mais valide)

URL_REQUEST_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
}

# Feature flags: activer/désactiver les filtres post-extraction (accessibilité & fraîcheur)
ENABLE_URL_FILTERING = True
ENABLE_FRESHNESS_FILTERING = True

# Configuration des tours maximum (sera resserrée côté orchestrateur)
MAX_TURNS = {"analyze": 2, "info": 2, "subs": 3, "meta": 1}

# Cache d'accessibilité des URLs (accessible globalement)
def get_url_cache() -> Dict[str, bool]:
    """Retourne le cache d'accessibilité des URLs."""
    return _URL_STATUS_CACHE

def clear_url_cache() -> None:
    """Vide le cache d'accessibilité des URLs."""
    _URL_STATUS_CACHE.clear()

def set_url_cache_status(url: str, is_accessible: bool) -> None:
    """Met à jour le statut d'accessibilité d'une URL dans le cache."""
    _URL_STATUS_CACHE[url] = is_accessible

def get_url_cache_status(url: str) -> bool:
    """Récupère le statut d'accessibilité d'une URL depuis le cache."""
    return _URL_STATUS_CACHE.get(url, False)
