"""
Gestionnaire de cycle de vie de l'application
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from functions import setup_logging, get_version, check_openai_agents_availability
from .config import settings


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

    yield

    # Arrêt
    logger.info("🛑 Arrêt de l'API Company Information Extraction")
