"""
Routes pour l'extraction d'informations d'entreprise
"""

import uuid
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from core.models import (
    CompanyExtractionRequest,
    URLExtractionRequest,
    AsyncExtractionResponse,
)
from company_agents.models import CompanyInfo
from company_agents.extraction_core import extract_company_data
from services.validation_service import validate_extraction_input
from services.agent_tracking_service import agent_tracking_service
from functions import validate_company_name, clean_company_name


logger = logging.getLogger(__name__)
router = APIRouter()


# Fonction utilitaire pour exécuter l'extraction en arrière-plan
async def _run_extraction_background(
    session_id: str,
    input_query: str,
    include_subsidiaries: bool = True,
    deep_search: bool = False,
):
    """
    Exécute l'extraction en arrière-plan et gère le tracking
    """
    try:
        logger.info("🚀 Démarrage extraction background: %s (deep_search=%s)", session_id, deep_search)

        result = await extract_company_data(
            input_query,
            session_id=session_id,
            include_subsidiaries=include_subsidiaries,
            deep_search=deep_search,
        )

        # Sauvegarder les coûts dans la base de données
        try:
            from core.database import AsyncSessionLocal
            from models.db_models import CompanyExtraction, ExtractionType, ExtractionStatus

            # Extraire les données de coût du résultat
            extraction_costs = result.get("extraction_costs", {})

            if extraction_costs:
                async with AsyncSessionLocal() as db:
                    # Vérifier si une extraction existe déjà pour ce session_id
                    from sqlalchemy import select
                    stmt = select(CompanyExtraction).where(CompanyExtraction.session_id == session_id)
                    db_result = await db.execute(stmt)
                    existing_extraction = db_result.scalar_one_or_none()

                    if existing_extraction:
                        # Mettre à jour l'extraction existante
                        existing_extraction.cost_usd = extraction_costs.get("cost_usd")
                        existing_extraction.cost_eur = extraction_costs.get("cost_eur")
                        existing_extraction.total_tokens = extraction_costs.get("total_tokens")
                        existing_extraction.input_tokens = extraction_costs.get("input_tokens")
                        existing_extraction.output_tokens = extraction_costs.get("output_tokens")
                        existing_extraction.models_usage = {
                            "models_breakdown": extraction_costs.get("models_breakdown", []),
                            "total_cost_usd": extraction_costs.get("cost_usd"),
                            "total_cost_eur": extraction_costs.get("cost_eur"),
                            "total_tokens": extraction_costs.get("total_tokens"),
                            "exchange_rate": extraction_costs.get("exchange_rate", 0.92)
                        }
                        existing_extraction.status = ExtractionStatus.COMPLETED
                        existing_extraction.processing_time = result.get("extraction_metadata", {}).get("processing_time", 0) / 1000  # Convert ms to seconds

                        await db.commit()
                        logger.info(f"💾 Coûts mis à jour dans DB pour session {session_id}: {extraction_costs.get('cost_eur'):.4f}€")
                    else:
                        logger.warning(f"⚠️ Aucune extraction trouvée pour session {session_id}")

        except Exception as cost_error:
            logger.error(f"❌ Erreur lors de la sauvegarde des coûts pour {session_id}: {cost_error}", exc_info=True)

        logger.info("✅ Extraction background terminée: %s", session_id)
        return result

    except Exception as e:
        logger.error(
            "❌ Erreur extraction background %s: %s",
            session_id,
            e,
        )
        await agent_tracking_service.error_extraction_tracking(
            session_id,
            str(e),
        )
        raise


@router.post("/extract", response_model=CompanyInfo)
async def extract_company_info(request: CompanyExtractionRequest):
    """
    Extrait les informations d'entreprise et de ses filiales

    Args:
        request: Requête contenant le nom de l'entreprise

    Returns:
        CompanyInfo: Informations d'entreprise structurées
    """
    session_id = str(uuid.uuid4())

    try:
        # Validation du nom d'entreprise
        if not validate_company_name(request.company_name):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Nom d'entreprise invalide. " "Veuillez fournir un nom valide."
                ),
            )

        # Nettoyage du nom
        company_name = clean_company_name(request.company_name)

        logger.info(
            "🔍 Début de l'extraction pour: %s [Session: %s] (deep_search=%s)",
            company_name,
            session_id,
            request.deep_search,
        )

        # Extraction des données
        result_dict = await extract_company_data(
            company_name,
            session_id=session_id,
            include_subsidiaries=True,
            deep_search=request.deep_search or False,
        )

        logger.info(
            "✅ Extraction terminée pour: %s [Session: %s]",
            company_name,
            session_id,
        )
        return CompanyInfo(**result_dict)

    except Exception as e:
        logger.error(
            "❌ Erreur lors de l'extraction pour %s: %s",
            request.company_name,
            e,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-from-url", response_model=CompanyInfo)
async def extract_company_from_url(request: URLExtractionRequest):
    """
    Extrait les informations d'entreprise à partir d'une URL

    Args:
        request: Requête contenant l'URL de l'entreprise

    Returns:
        CompanyInfo: Informations d'entreprise structurées
    """
    session_id = str(uuid.uuid4())

    try:
        # Validation de l'URL
        is_valid, cleaned_url, _ = validate_extraction_input(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"URL invalide: {request.url}",
            )

        logger.info(
            "🔍 Début de l'extraction depuis URL: %s [Session: %s] (deep_search=%s)",
            cleaned_url,
            session_id,
            request.deep_search,
        )

        # Extraction des données
        result_dict = await extract_company_data(
            cleaned_url,
            session_id=session_id,
            include_subsidiaries=request.include_subsidiaries,
            deep_search=request.deep_search or False,
        )

        logger.info(
            "✅ Extraction depuis URL terminée: %s [Session: %s]",
            cleaned_url,
            session_id,
        )
        return CompanyInfo(**result_dict)

    except Exception as e:
        logger.error(
            "❌ Erreur lors de l'extraction depuis URL %s: %s",
            request.url,
            e,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-async", response_model=AsyncExtractionResponse)
async def extract_company_info_async(request: CompanyExtractionRequest):
    """
    Démarre l'extraction d'informations d'entreprise en mode asynchrone

    Retourne immédiatement le session_id pour suivre la progression via WebSocket

    Args:
        request: Requête contenant le nom de l'entreprise

    Returns:
        AsyncExtractionResponse: Session ID et statut de démarrage
    """
    session_id = str(uuid.uuid4())

    try:
        # Validation du nom d'entreprise
        if not validate_company_name(request.company_name):
            raise HTTPException(
                status_code=400,
                detail="Nom d'entreprise invalide. Veuillez fournir un nom valide.",
            )

        # Nettoyage du nom
        company_name = clean_company_name(request.company_name)

        logger.info(
            "🚀 Démarrage extraction async pour: %s [Session: %s]",
            company_name,
            session_id,
        )

        # Démarrer l'extraction en arrière-plan
        asyncio.create_task(
            _run_extraction_background(
                session_id=session_id,
                input_query=company_name,
                include_subsidiaries=True,
                deep_search=request.deep_search or False,
            )
        )

        # 202 Accepted + Location pour suivi
        payload = AsyncExtractionResponse(
            session_id=session_id,
            status="started",
            message=f"Extraction démarrée pour {company_name}",
        )
        return JSONResponse(
            status_code=202,
            content=payload.model_dump(),
            headers={"Location": f"/status/{session_id}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur démarrage extraction async: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-from-url-async", response_model=AsyncExtractionResponse)
async def extract_company_from_url_async(request: URLExtractionRequest):
    """
    Démarre l'extraction d'informations d'entreprise depuis URL en mode asynchrone

    Retourne immédiatement le session_id pour suivre la progression via WebSocket

    Args:
        request: Requête contenant l'URL de l'entreprise

    Returns:
        AsyncExtractionResponse: Session ID et statut de démarrage
    """
    session_id = str(uuid.uuid4())

    try:
        # Validation de l'URL
        is_valid, cleaned_url, _ = validate_extraction_input(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"URL invalide: {request.url}",
            )

        logger.info(
            "🚀 Démarrage extraction async depuis URL: %s [Session: %s]",
            cleaned_url,
            session_id,
        )

        # Démarrer l'extraction en arrière-plan
        asyncio.create_task(
            _run_extraction_background(
                session_id=session_id,
                input_query=cleaned_url,
                include_subsidiaries=request.include_subsidiaries or True,
                deep_search=request.deep_search or False,
            )
        )

        # 202 Accepted + Location pour suivi
        payload = AsyncExtractionResponse(
            session_id=session_id,
            status="started",
            message="Extraction démarrée depuis URL",
        )
        return JSONResponse(
            status_code=202,
            content=payload.model_dump(),
            headers={"Location": f"/status/{session_id}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur démarrage extraction async depuis URL: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
