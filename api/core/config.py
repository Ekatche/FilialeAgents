"""
Configuration de l'application
"""

import os
from typing import List


class Settings:
    """Configuration de l'application"""
    
    # Informations de l'API
    API_TITLE: str = "Company Information Extraction API"
    API_DESCRIPTION: str = "API pour extraire les informations d'entreprise et leurs filiales en utilisant OpenAI Agents"
    API_VERSION: str = "1.0.0"
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    
    # Configuration CORS
    CORS_ORIGINS: List[str] = ["*"]  # En production, spécifiez les domaines autorisés
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Configuration OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Configuration de l'application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Configuration des limites
    MAX_EXTRACTION_TIME: int = int(os.getenv("MAX_EXTRACTION_TIME", "300"))  # 5 minutes
    MAX_SUBSIDIARIES: int = int(os.getenv("MAX_SUBSIDIARIES", "50"))
    
    # Configuration WebSocket
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_CONNECTION_TIMEOUT: int = int(os.getenv("WS_CONNECTION_TIMEOUT", "300"))

    # Configuration Redis (requis pour le suivi des agents WebSocket)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", "7200"))  # 2h par défaut


# Instance globale des paramètres
settings = Settings()
