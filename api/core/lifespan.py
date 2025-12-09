"""
Gestionnaire de cycle de vie de l'application
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from functions import setup_logging, get_version, check_openai_agents_availability
from core.config import settings
from core.database import init_db, close_db
from status import status_manager
from services.entity_cache_service import entity_cache

logger = logging.getLogger(__name__)


async def ensure_local_portal():
    """Crée le portail local par défaut s'il n'existe pas (mode local uniquement)"""
    from core.database import AsyncSessionLocal
    from models.db_models import HubSpotPortal
    from sqlalchemy import select
    import uuid

    try:
        portal_uuid = uuid.UUID(settings.LOCAL_DEFAULT_PORTAL_ID)

        # Créer une session async
        async with AsyncSessionLocal() as session:
            try:
                # Vérifier si le portail existe
                stmt = select(HubSpotPortal).where(HubSpotPortal.id == portal_uuid)
                result = await session.execute(stmt)
                portal = result.scalar_one_or_none()

                if not portal:
                    # Créer le portail local
                    portal = HubSpotPortal(
                        id=portal_uuid,
                        hubspot_portal_id=0,  # ID fictif pour mode local
                        name="Local Development",
                        domain="localhost",
                        is_active=True
                    )
                    session.add(portal)
                    await session.commit()
                    logger.info(f"✅ Portail local créé: {settings.LOCAL_DEFAULT_PORTAL_ID}")
                else:
                    logger.info(f"✅ Portail local existant: {settings.LOCAL_DEFAULT_PORTAL_ID}")

            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Erreur lors de la création du portail local: {e}", exc_info=True)
                raise

    except Exception as e:
        logger.error(f"❌ Erreur dans ensure_local_portal: {e}", exc_info=True)


async def background_cleanup_task():
    """Tâche de nettoyage périodique en arrière-plan"""
    # Intervalle adapté à l'environnement (production = moins fréquent)
    cleanup_interval = 900 if settings.is_production else 300  # 15min prod, 5min dev

    while True:
        try:
            # Attendre l'intervalle configuré
            await asyncio.sleep(cleanup_interval)

            # Nettoyer les sessions expirées (extraction sessions)
            await status_manager.cleanup_old_sessions(max_age_minutes=60)

            # Nettoyer les sessions utilisateur expirées
            from services.session_service import session_service
            await session_service.cleanup_expired_sessions()

            # Nettoyer le cache d'entités expirées
            await entity_cache.cleanup_expired()

            logger.debug(f"✅ Nettoyage périodique effectué (intervalle: {cleanup_interval}s)")

        except asyncio.CancelledError:
            logger.info("🛑 Tâche de nettoyage annulée")
            break
        except Exception as e:
            logger.error(f"❌ Erreur dans la tâche de nettoyage: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Démarrage
    logger.info("🚀 Démarrage de l'API Company Information Extraction")
    logger.info(f"📋 Version: {get_version()} | Environment: {settings.ENVIRONMENT}")

    # Vérifier la clé API OpenAI (sans appel réseau inutile)
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

    # Créer le portail local par défaut si en mode local
    if settings.is_local:
        logger.info("🏠 Mode local détecté - Initialisation du portail par défaut...")
        await ensure_local_portal()

    # Vérifier la configuration HubSpot OAuth
    if settings.HUBSPOT_CLIENT_ID and settings.HUBSPOT_CLIENT_SECRET:
        logger.info("✅ HubSpot OAuth configuré")
    else:
        logger.warning("⚠️ HubSpot OAuth non configuré - l'authentification ne fonctionnera pas")

    # Démarrer la tâche de nettoyage en arrière-plan
    cleanup_task = asyncio.create_task(background_cleanup_task())
    logger.info("✅ Tâche de nettoyage périodique démarrée")

    yield

    # Arrêt
    logger.info("🛑 Arrêt de l'API Company Information Extraction")

    # Arrêter la tâche de nettoyage
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Tâche de nettoyage arrêtée")

    # Fermer le cache d'entités
    try:
        await entity_cache.close()
    except Exception as e:
        logger.error(f"❌ Erreur lors de la fermeture du cache: {e}")

    # Fermer les connexions à la base de données
    try:
        logger.info("🗄️  Fermeture des connexions à la base de données...")
        await close_db()
        logger.info("✅ Connexions fermées")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la fermeture de la base de données: {e}")
