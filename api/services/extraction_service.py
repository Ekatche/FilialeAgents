"""
Service d'extraction d'informations d'entreprise
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks
from company_agents.extraction_core import extract_company_data_unified
from status import status_manager
from functions import format_response_for_api
from .validation_service import validate_extraction_input

logger = logging.getLogger(__name__)


async def background_extraction_task_url(
    url: str,
    session_id: str,
    include_subsidiaries: bool = True,
    max_subsidiaries: int = 10
) -> None:
    """Tâche d'extraction en arrière-plan pour URL"""
    try:
        logger.info(f"🚀 Début extraction arrière-plan URL: {url} [Session: {session_id}]")

        result_dict = await extract_company_data_unified(
            url, session_id, include_subsidiaries, max_subsidiaries
        )

        await status_manager.store_extraction_results(session_id, result_dict)
        logger.info(f"✅ Extraction URL terminée: {session_id}")

    except Exception as e:
        logger.error(f"❌ Erreur extraction arrière-plan URL {url}: {e}")
        await status_manager.error_session(session_id, str(e))


async def background_extraction_task_company(
    company_name: str,
    session_id: str,
    include_subsidiaries: bool = True,
    max_subsidiaries: int = 50
) -> None:
    """Tâche d'extraction en arrière-plan pour nom d'entreprise"""
    try:
        logger.info(f"🚀 Début extraction arrière-plan entreprise: {company_name} [Session: {session_id}]")

        result_dict = await extract_company_data_unified(
            company_name, session_id, include_subsidiaries, max_subsidiaries
        )

        await status_manager.store_extraction_results(session_id, result_dict)
        logger.info(f"✅ Extraction entreprise terminée: {session_id}")

    except Exception as e:
        logger.error(f"❌ Erreur extraction arrière-plan entreprise {company_name}: {e}")
        await status_manager.error_session(session_id, str(e))


async def extract_company_sync(
    input_str: str,
    session_id: str,
    include_subsidiaries: bool = True,
    max_subsidiaries: int = 50
) -> Dict[str, Any]:
    """Extraction synchrone d'entreprise"""
    start_time = time.time()
    
    try:
        # Validation de l'input
        is_valid, cleaned_input, input_type = validate_extraction_input(input_str)
        if not is_valid:
            raise ValueError(f"Input invalide: {input_str}")

        logger.info(f"🔍 Début extraction synchrone: {cleaned_input} [Session: {session_id}]")

        # Créer la session de suivi d'état
        await status_manager.create_session(session_id, cleaned_input)

        # Extraction des données
        result_dict = await extract_company_data_unified(
            cleaned_input, session_id, include_subsidiaries, max_subsidiaries
        )

        # Calcul du temps de traitement
        processing_time = time.time() - start_time

        # Formatage de la réponse
        response = format_response_for_api(result_dict, processing_time, session_id)

        logger.info(f"✅ Extraction synchrone terminée: {cleaned_input} [Session: {session_id}]")
        return response

    except Exception as e:
        logger.error(f"❌ Erreur extraction synchrone {input_str}: {e}")
        if session_id:
            await status_manager.error_session(session_id, str(e))
        raise


async def extract_company_async(
    input_str: str,
    session_id: str,
    background_tasks: BackgroundTasks,
    include_subsidiaries: bool = True,
    max_subsidiaries: int = 50
) -> Dict[str, Any]:
    """Extraction asynchrone d'entreprise"""
    try:
        # Validation de l'input
        is_valid, cleaned_input, input_type = validate_extraction_input(input_str)
        if not is_valid:
            raise ValueError(f"Input invalide: {input_str}")

        logger.info(f"🔄 Début extraction asynchrone: {cleaned_input} [Session: {session_id}]")

        # Créer la session de suivi d'état
        await status_manager.create_session(session_id, cleaned_input)

        # Lancer la tâche en arrière-plan
        if input_type == "url":
            background_tasks.add_task(
                background_extraction_task_url,
                cleaned_input,
                session_id,
                include_subsidiaries,
                max_subsidiaries
            )
        else:
            background_tasks.add_task(
                background_extraction_task_company,
                cleaned_input,
                session_id,
                include_subsidiaries,
                max_subsidiaries
            )

        # Retourner la réponse immédiate
        return {
            "success": True,
            "session_id": session_id,
            "execution_mode": "async",
            "input_type": input_type,
            "message": "Extraction lancée en arrière-plan",
            "status_url": f"/session/{session_id}",
            "websocket_url": f"/ws/status/{session_id}",
            "results_url": f"/results/{session_id}"
        }

    except Exception as e:
        logger.error(f"❌ Erreur extraction asynchrone {input_str}: {e}")
        if session_id:
            await status_manager.error_session(session_id, str(e))
        raise
