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

    # Détection d'environnement
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")  # local, staging, production

    @property
    def is_local(self) -> bool:
        """Check if running in local environment"""
        return self.ENVIRONMENT == "local"

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    # Configuration du portail local par défaut
    LOCAL_DEFAULT_PORTAL_ID: str = "00000000-0000-0000-0000-000000000001"  # UUID fixe pour mode local

    # Configuration des limites
    MAX_EXTRACTION_TIME: int = int(os.getenv("MAX_EXTRACTION_TIME", "300"))  # 5 minutes
    MAX_SUBSIDIARIES: int = int(os.getenv("MAX_SUBSIDIARIES", "50"))
    
    # Configuration WebSocket
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_CONNECTION_TIMEOUT: int = int(os.getenv("WS_CONNECTION_TIMEOUT", "300"))

    # Configuration Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/filialeagents"
    )

    # Database Connection Pool Settings (optimized for Supabase)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour

    # Configuration OAuth HubSpot
    HUBSPOT_CLIENT_ID: str = os.getenv("HUBSPOT_CLIENT_ID", "")
    HUBSPOT_CLIENT_SECRET: str = os.getenv("HUBSPOT_CLIENT_SECRET", "")
    HUBSPOT_REDIRECT_URI: str = os.getenv(
        "HUBSPOT_REDIRECT_URI",
        "http://localhost:8012/auth/hubspot/callback"
    )
    HUBSPOT_SCOPES: List[str] = [
        "oauth",
        "crm.objects.contacts.read",
        "crm.objects.companies.read",
        "crm.objects.companies.write",
    ]

    # Configuration JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# Instance globale des paramètres
settings = Settings()
