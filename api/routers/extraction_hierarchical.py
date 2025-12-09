"""
Routes pour l'extraction hiérarchique

Architecture en 3 phases :
- Phase 0 : Éclaireur (gpt-4.1-mini) - Identification société mère et secteur
- Phase 1 : Cartographe Minimal (gpt-5.1) - Identification jusqu'à 15 entités
- Phase 2 : Extracteur Détaillé (gpt-4.1-mini) - Extraction parallèle des informations

Avantages :
- Exécution parallèle (5x plus rapide)
- Cache Redis
- Cost tracking hiérarchique précis
"""

import uuid
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from core.models import AsyncExtractionResponse
from services.validation_service import validate_extraction_input
from functions import validate_company_name, clean_company_name
from company_agents.hierarchical.orchestrator import run_hierarchical_extraction
from services.hierarchical_cost_tracking import HierarchicalCostTracker
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker
from company_agents.common.context import set_session_context, clear_session_context
from services.agent_tracking_service import agent_tracking_service
from status import status_manager
from dependencies.auth import get_optional_current_user, get_current_portal
from models.db_models import User, HubSpotPortal
from company_agents.common.metrics import metrics_collector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hierarchical", tags=["hierarchical-extraction"])


# ==========================================
#   HELPER : FILTRAGE DES CHAMPS VIDES
# ==========================================

def filter_empty_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supprime les champs None, listes vides, et valeurs "Non trouvé" de l'output.
    Préserve les champs requis comme legal_name, confidence, extraction_date.
    Note: entity_type a été retiré de EntityRef et n'est plus conservé.
    
    Args:
        data: Dictionnaire à nettoyer
        
    Returns:
        Dictionnaire nettoyé
    """
    if not isinstance(data, dict):
        return data
    
    # Champs toujours conservés (même si None ou vides)
    # Note: entity_type retiré car il n'est plus dans EntityRef
    # website est important pour la recherche détaillée, donc on le conserve même s'il est None
    # country est important car il est maintenant fourni par le Cartographe Minimal
    # extraction_date n'est plus conservé au niveau entité (une seule fois dans extraction_stats)
    required_fields = {"legal_name", "confidence", "website", "country", "sources"}
    
    filtered = {}
    for key, value in data.items():
        # Toujours conserver les champs requis
        if key in required_fields:
            filtered[key] = value
            continue
        
        # Ignorer les champs None (sauf les champs requis)
        # website est dans required_fields donc sera conservé même si None
        if value is None and key not in required_fields:
            continue
        
        # Ignorer les listes vides (sauf si c'est un champ requis)
        if isinstance(value, list) and len(value) == 0:
            continue
        
        # Ignorer les dictionnaires vides (sauf si c'est un champ requis comme headquarters)
        if isinstance(value, dict) and len(value) == 0:
            continue
        
        # Ignorer les strings "Non trouvé"
        if isinstance(value, str) and value.strip() == "Non trouvé":
            continue
        
        # Récursion pour les dictionnaires imbriqués
        if isinstance(value, dict):
            filtered_value = filter_empty_fields(value)
            # Pour headquarters, garder même si vide (structure requise)
            if key == "headquarters":
                filtered[key] = filtered_value
            elif filtered_value:  # Sinon, ne garder que si non vide
                filtered[key] = filtered_value
        elif isinstance(value, list):
            # Filtrer les éléments de la liste
            filtered_list = []
            for item in value:
                if isinstance(item, dict):
                    filtered_item = filter_empty_fields(item)
                    # Conserver l'item s'il contient des champs requis (même s'ils sont None)
                    # ou s'il a des valeurs non-None après filtrage
                    has_required_fields = any(key in required_fields for key in item.keys())
                    if filtered_item or has_required_fields:
                        # Si filtered_item est vide mais qu'on a des champs requis, utiliser l'item original
                        # mais en conservant uniquement les champs requis et les champs non-None
                        if not filtered_item and has_required_fields:
                            # Reconstruire l'item avec seulement les champs requis
                            preserved_item = {k: v for k, v in item.items() if k in required_fields}
                            filtered_list.append(preserved_item)
                        else:
                            filtered_list.append(filtered_item)
                elif item is not None and not (isinstance(item, str) and item.strip() == "Non trouvé"):
                    filtered_list.append(item)
            if filtered_list:
                filtered[key] = filtered_list
        else:
            filtered[key] = value
    
    return filtered


# ==========================================
#   MODÈLES DE REQUÊTE
# ==========================================

class HierarchicalExtractionRequest(BaseModel):
    """Requête pour extraction hiérarchique"""
    company_name: Optional[str] = None
    url: Optional[str] = None
    sector: Optional[str] = Field(None, description="Secteur d'activité (optionnel)")
    context: Optional[str] = Field(None, description="Contexte additionnel (optionnel)")
    use_cache: bool = Field(True, description="Utiliser le cache in-memory")
    max_parallel: int = Field(5, description="Nombre d'extractions parallèles max", ge=1, le=10)


class HierarchicalExtractionResponse(BaseModel):
    """Réponse d'extraction hiérarchique"""
    session_id: str
    extraction_id: str  # ID de l'entrée dans la DB
    company_name: str

    # Données
    minimal_mapping: dict
    detailed_entities: list
    extraction_stats: dict
    parent_company_info: Optional[dict] = None


# ==========================================
#   ENDPOINT : EXTRACTION HIÉRARCHIQUE
# ==========================================

@router.post("/extract", response_model=HierarchicalExtractionResponse)
async def extract_hierarchical(
    request: HierarchicalExtractionRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Extrait les informations d'entreprise avec l'architecture hiérarchique.

    **Workflow** :
    1. Phase 0 : Éclaireur identifie la société mère et le secteur
    2. Phase 1 : Cartographe Minimal identifie jusqu'à 15 entités
    3. Phase 2 : Extracteur Détaillé extrait en parallèle les informations de chaque entité
    4. Consolidation : Rapport hiérarchique complet

    **Avantages** :
    - Exécution parallèle (5x plus rapide)
    - Coûts optimisés (gpt-4.1-mini et gpt-5.1)
    - Cache in-memory (évite recherches redondantes)
    - Cost tracking hiérarchique précis (Phase → Agent → Tool → Entity)

    **Authentification** :
    - Si l'utilisateur est authentifié, utilise son portail HubSpot
    - Sinon, utilise le portail local par défaut

    Args:
        request: Requête avec company_name OU url
        current_user: Utilisateur authentifié (optionnel)
        portal: Portail HubSpot de l'utilisateur (optionnel)

    Returns:
        HierarchicalExtractionResponse avec tous les résultats
    """
    session_id = str(uuid.uuid4())

    try:
        # Validation : company_name OU url requis
        if not request.company_name and not request.url:
            raise HTTPException(
                status_code=400,
                detail="Vous devez fournir soit 'company_name' soit 'url'"
            )

        # Détermination de l'input
        if request.url:
            # Mode URL
            is_valid, cleaned_url, _ = validate_extraction_input(request.url)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"URL invalide: {request.url}")

            input_query = cleaned_url
            company_name = None  # Sera déterminé par le Cartographe
            website = cleaned_url

        else:
            # Mode nom d'entreprise
            if not validate_company_name(request.company_name):
                raise HTTPException(
                    status_code=400,
                    detail="Nom d'entreprise invalide"
                )

            company_name = clean_company_name(request.company_name)
            input_query = company_name
            website = None

        logger.info(
            f"🚀 Extraction hiérarchique: {input_query} [Session: {session_id}]"
        )

        # ==========================================
        # CRÉATION ENTRÉE DB (status=PENDING)
        # ==========================================
        from models.db_models import CompanyExtraction, ExtractionStatus, ExtractionType, HubSpotPortal
        from core.database import AsyncSessionLocal
        from core.config import settings
        from datetime import datetime
        from sqlalchemy import select

        extraction_id = None
        try:
            async with AsyncSessionLocal() as db:
                # Déterminer le portail à utiliser
                portal_uuid = None
                user_id = None
                
                # Si l'utilisateur est authentifié, utiliser son portail
                if current_user:
                    if current_user.hubspot_portal:
                        portal_uuid = current_user.hubspot_portal.id
                        user_id = current_user.id
                        logger.info(
                            f"✅ Utilisation du portail de l'utilisateur authentifié: "
                            f"user={current_user.email}, portal={portal_uuid} ({current_user.hubspot_portal.name})"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Utilisateur {current_user.email} authentifié mais sans portail, "
                            f"utilisation du portail local par défaut"
                        )
                        # Fallback sur le portail local par défaut si l'utilisateur n'a pas de portail
                        if settings.is_local:
                            portal_uuid = uuid.UUID(settings.LOCAL_DEFAULT_PORTAL_ID)
                            portal_res = await db.execute(select(HubSpotPortal).where(HubSpotPortal.id == portal_uuid))
                            if not portal_res.scalar_one_or_none():
                                logger.warning(f"⚠️ Portail local {portal_uuid} introuvable, création automatique...")
                                local_portal = HubSpotPortal(
                                    id=portal_uuid,
                                    hubspot_portal_id=0,
                                    name="Local Development",
                                    domain="localhost",
                                    is_active=True
                                )
                                db.add(local_portal)
                                await db.flush()
                            logger.info(f"✅ Utilisation du portail local par défaut: {portal_uuid}")
                        else:
                            raise HTTPException(
                                status_code=401,
                                detail="Utilisateur sans portail - authentification requise"
                            )
                else:
                    # Sinon, utiliser le portail local par défaut
                    if settings.is_local:
                        portal_uuid = uuid.UUID(settings.LOCAL_DEFAULT_PORTAL_ID)
                        # Vérifier si le portail existe
                        portal_res = await db.execute(select(HubSpotPortal).where(HubSpotPortal.id == portal_uuid))
                        if not portal_res.scalar_one_or_none():
                            logger.warning(f"⚠️ Portail local {portal_uuid} introuvable, création automatique...")
                            local_portal = HubSpotPortal(
                                id=portal_uuid,
                                hubspot_portal_id=0,
                                name="Local Development",
                                domain="localhost",
                                is_active=True
                            )
                            db.add(local_portal)
                            await db.flush() # Important pour s'assurer qu'il est dispo pour la clé étrangère
                        logger.info(f"✅ Utilisation du portail local par défaut: {portal_uuid}")
                    else:
                        raise HTTPException(
                            status_code=401,
                            detail="Authentification requise pour les extractions en mode production"
                        )

                # Créer l'entrée avec status=PENDING
                extraction_db = CompanyExtraction(
                    session_id=session_id,
                    company_name=input_query,
                    company_url=website,
                    extraction_type=ExtractionType.HIERARCHICAL.value, # Utiliser .value pour être sûr
                    status=ExtractionStatus.PENDING.value, # Utiliser .value pour être sûr
                    user_id=user_id,
                    hubspot_portal_id=portal_uuid,
                    created_at=datetime.now()
                )
                db.add(extraction_db)
                await db.commit()
                await db.refresh(extraction_db)
                extraction_id = str(extraction_db.id)
                logger.info(f"📝 Entrée DB créée: {extraction_id} (status=pending, portal={portal_uuid}, user={user_id})")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erreur création entrée DB: {e}", exc_info=True)
            # Continue quand même l'extraction, mais loggue l'erreur complète

        # ==========================================
        # EXÉCUTION DU SYSTÈME HIÉRARCHIQUE
        # ==========================================

        # Configuration du context (pour que les tools puissent récupérer le session_id)
        set_session_context(session_id)

        # NOUVEAU : Initialiser le tracking WebSocket
        try:
            await agent_tracking_service.start_extraction_tracking(session_id, input_query)
        except Exception as e:
            logger.warning(f"⚠️ Erreur démarrage tracking: {e}")

        # Initialisation des trackers
        cost_tracker = HierarchicalCostTracker.get_instance()
        cost_tracker.start_session(session_id, input_query)
        ToolTokensTracker.start_session(session_id)

        try:
            # Exécution avec status_manager
            hierarchical_report = await run_hierarchical_extraction(
                company_name=company_name or input_query,
                website=website,
                sector=request.sector,
                context=request.context,
                use_cache=request.use_cache,
                max_parallel=request.max_parallel,
                status_manager=status_manager,  # NOUVEAU
                session_id=session_id  # NOUVEAU
            )

            # Récupération des coûts
            cost_report = cost_tracker.end_session()
            
            # NOUVEAU : Finaliser le tracking
            try:
                await agent_tracking_service.complete_extraction_tracking(
                    session_id, 
                    {
                        "status": "completed", 
                        "entities": len(hierarchical_report.detailed_entities),
                        "entities_identified": hierarchical_report.minimal_mapping.total_found
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur finalisation tracking: {e}")
        except Exception as e:
            # NOUVEAU : Notifier l'erreur au tracking
            try:
                await agent_tracking_service.error_extraction_tracking(session_id, str(e))
            except Exception as tracking_error:
                logger.warning(f"⚠️ Erreur notification erreur tracking: {tracking_error}")
            raise
        finally:
            # Nettoyage du context
            clear_session_context()
            
            # NOUVEAU : Nettoyer les métriques
            try:
                metrics_collector.cleanup_session(session_id)
            except Exception as e:
                logger.warning(f"⚠️ Erreur nettoyage métriques: {e}")

        logger.info(
            f"✅ Extraction hiérarchique terminée: {input_query} "
            f"({hierarchical_report.extraction_stats['entities_extracted']}/{hierarchical_report.extraction_stats['entities_identified']} entités)"
        )

        # ==========================================
        # CONSTRUCTION DE LA RÉPONSE
        # ==========================================

        # Préparer extraction_stats avec toutes les stats consolidées
        extraction_stats = hierarchical_report.extraction_stats.copy()
        
        # Ajouter les coûts et tokens
        extraction_stats["total_cost_usd"] = cost_report.total_cost_usd if cost_report else 0.0
        extraction_stats["total_tokens"] = cost_report.total_tokens if cost_report else 0
        
        # Ajouter extraction_date une seule fois
        from datetime import datetime
        extraction_stats["extraction_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Retirer les durées de phase individuelles, garder seulement total_duration_seconds
        extraction_stats.pop("phase_0_duration_seconds", None)
        extraction_stats.pop("phase_0_5_duration_seconds", None)
        extraction_stats.pop("phase_1_duration_seconds", None)
        extraction_stats.pop("phase_2_duration_seconds", None)
        
        # Préparer parent_company_info si disponible
        parent_company_info_dict = None
        if hierarchical_report.parent_company_info:
            parent_company_info_dict = filter_empty_fields(hierarchical_report.parent_company_info.model_dump())
        
        # Filtrer les entités détaillées (extraction_date n'est plus dans le modèle)
        detailed_entities_filtered = []
        for entity in hierarchical_report.detailed_entities:
            entity_dict = filter_empty_fields(entity.model_dump())
            detailed_entities_filtered.append(entity_dict)

        # ==========================================
        # MISE À JOUR EN BASE DE DONNÉES
        # ==========================================
        try:
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                # Récupérer l'entrée existante
                if extraction_id:
                    result = await db.execute(
                        select(CompanyExtraction).where(CompanyExtraction.id == extraction_id)
                    )
                    extraction_db = result.scalar_one_or_none()

                    if extraction_db:
                        # Mettre à jour l'entrée existante
                        extraction_db.status = ExtractionStatus.COMPLETED.value # Utiliser .value
                        extraction_db.extraction_data = {
                            "minimal_mapping": filter_empty_fields(hierarchical_report.minimal_mapping.model_dump()),
                            "detailed_entities": detailed_entities_filtered,
                            "parent_company_info": parent_company_info_dict
                        }
                        extraction_db.subsidiaries_count = len(detailed_entities_filtered)
                        extraction_db.processing_time = extraction_stats.get("total_duration_seconds")
                        extraction_db.cost_usd = extraction_stats.get("total_cost_usd", 0.0)
                        extraction_db.cost_eur = extraction_stats.get("total_cost_usd", 0.0) * 0.92
                        extraction_db.total_tokens = extraction_stats.get("total_tokens", 0)
                        extraction_db.completed_at = datetime.now()

                        await db.commit()
                        logger.info(f"✅ Extraction mise à jour en DB: {extraction_id} (session: {session_id})")
                    else:
                        logger.warning(f"⚠️ Entrée DB introuvable pour mise à jour: {extraction_id}")
                else:
                    logger.warning(f"⚠️ Pas d'extraction_id pour mise à jour DB")

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour extraction en DB: {e}")
            # Ne pas bloquer la réponse si la mise à jour échoue

        response = HierarchicalExtractionResponse(
            session_id=session_id,
            extraction_id=extraction_id or session_id,  # Fallback sur session_id si pas d'ID
            company_name=hierarchical_report.company_name,
            minimal_mapping=filter_empty_fields(hierarchical_report.minimal_mapping.model_dump()),
            detailed_entities=detailed_entities_filtered,
            extraction_stats=extraction_stats,
            parent_company_info=parent_company_info_dict
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur extraction hiérarchique: {e}", exc_info=True)

        # Mettre à jour l'entrée DB avec status=ERROR
        if extraction_id:
            try:
                from sqlalchemy import select
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(CompanyExtraction).where(CompanyExtraction.id == extraction_id)
                    )
                    extraction_db = result.scalar_one_or_none()
                    if extraction_db:
                        extraction_db.status = ExtractionStatus.ERROR.value # Utiliser .value
                        extraction_db.error_message = str(e)
                        extraction_db.completed_at = datetime.now()
                        await db.commit()
                        logger.info(f"⚠️ Extraction marquée ERROR en DB: {extraction_id}")
            except Exception as db_error:
                logger.error(f"❌ Erreur mise à jour status ERROR: {db_error}")

        raise HTTPException(status_code=500, detail=str(e))
