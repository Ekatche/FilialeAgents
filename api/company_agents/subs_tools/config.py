"""
Configuration simple et centralisée pour aiohttp
Basée sur les recommandations de la documentation aiohttp
"""

import aiohttp
from typing import Dict, Any


class AiohttpConfig:
    """Configuration simple et réutilisable pour aiohttp"""

    @staticmethod
    def fast_validation() -> Dict[str, Any]:
        return {
            "connector": aiohttp.TCPConnector(
                limit=10,
                limit_per_host=3,
                ttl_dns_cache=300,
                use_dns_cache=True,
            ),
            "timeout": aiohttp.ClientTimeout(total=3, connect=2, sock_read=2),
            "headers": {
                "User-Agent": "URLValidator/1.0",
                "Accept": "text/html,application/xhtml+xml",
                "Connection": "keep-alive",
            },
        }

    @staticmethod
    def detailed_validation() -> Dict[str, Any]:
        return {
            "connector": aiohttp.TCPConnector(
                limit=30,
                limit_per_host=8,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
            ),
            "timeout": aiohttp.ClientTimeout(total=5, connect=3, sock_read=2),
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
            },
        }

    @staticmethod
    def default() -> Dict[str, Any]:
        return {
            "connector": aiohttp.TCPConnector(
                limit=20,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            ),
            "timeout": aiohttp.ClientTimeout(total=10, connect=5, sock_read=3),
            "headers": {
                "User-Agent": "CompanyAnalysis/1.0",
                "Accept": "application/json,text/html,*/*",
                "Connection": "keep-alive",
            },
        }


def get_aiohttp_config(config_type: str = "default") -> Dict[str, Any]:
    """
    Récupère la configuration aiohttp selon le type

    Args:
        config_type: Type de configuration ("fast", "detailed", "default")

    Returns:
        Configuration aiohttp prête à utiliser
    """
    builders = {
        "fast": AiohttpConfig.fast_validation,
        "detailed": AiohttpConfig.detailed_validation,
        "default": AiohttpConfig.default,
    }

    builder = builders.get(config_type, AiohttpConfig.default)
    return builder()


def create_session(config_type: str = "default") -> aiohttp.ClientSession:
    """
    Crée une session aiohttp avec la configuration appropriée

    Args:
        config_type: Type de configuration à utiliser

    Returns:
        Session aiohttp configurée
    """
    config = get_aiohttp_config(config_type)
    # On passe une copie pour éviter toute mutation accidentelle
    return aiohttp.ClientSession(
        connector=config.get("connector"),
        timeout=config.get("timeout"),
        headers=config.get("headers"),
    )
