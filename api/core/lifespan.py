"""
Gestionnaire de cycle de vie de l'application
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from functions import setup_logging, get_version, check_openai_agents_availability
from core.config import settings
from core.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Démarrage
    logger.info("🚀 Démarrage de l'API Company Information Extraction")
    logger.info(f"📋 Version: {get_version()}")
    logger.info(f"🔧 OpenAI Agents disponible: {check_openai_agents_availability()}")

    # Vérifier la clé API OpenAI
    if not settings.OPENAI_API_KEY:
        logger.warning(
            "⚠️ OPENAI_API_KEY non définie dans les variables d'environnement"
        )
    else:
        logger.info("✅ OPENAI_API_KEY configurée")

    # Initialiser la base de données
    try:
        logger.info("🗄️  Initialisation de la base de données...")
        await init_db()
        logger.info("✅ Base de données initialisée")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation de la base de données: {e}")

    # Vérifier la configuration HubSpot OAuth
    if settings.HUBSPOT_CLIENT_ID and settings.HUBSPOT_CLIENT_SECRET:
        logger.info("✅ HubSpot OAuth configuré")
    else:
        logger.warning("⚠️ HubSpot OAuth non configuré - l'authentification ne fonctionnera pas")

    yield

    # Arrêt
    logger.info("🛑 Arrêt de l'API Company Information Extraction")

    # Fermer les connexions à la base de données
    try:
        logger.info("🗄️  Fermeture des connexions à la base de données...")
        await close_db()
        logger.info("✅ Connexions fermées")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la fermeture de la base de données: {e}")
