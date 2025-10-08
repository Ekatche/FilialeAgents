"""
Agent calling utilities for company information extraction.

This module handles individual agent calls, error handling, and retry logic.
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional

from agents import Runner
from ..subs_agents import (
    company_analyzer,
    information_extractor,
    meta_validator,
    subsidiary_extractor,
)
from ..subs_agents.data_validator import data_restructurer
from ..config.extraction_config import MAX_TURNS
from ..processors.data_processor import ExtractionState
from services.agent_tracking_service import agent_tracking_service

logger = logging.getLogger(__name__)


async def _run_agent_with_retry(
    agent: Any,
    input: str,
    max_turns: int = 3,
    max_retries: int = 2,
) -> Any:
    """
    Exécute un agent avec retry automatique en cas d'erreur.
    
    Args:
        agent: Agent à exécuter
        input: Entrée pour l'agent
        max_turns: Nombre maximum de tours
        max_retries: Nombre maximum de tentatives
        
    Returns:
        Résultat de l'agent
    """
    for attempt in range(max_retries + 1):
        try:
            result = await Runner.run(agent, input=input, max_turns=max_turns)
            return result
        except Exception as exc:
            logger.warning(
                "Tentative %d/%d échouée pour agent %s: %s",
                attempt + 1,
                max_retries + 1,
                agent.name,
                exc,
            )
            if attempt == max_retries:
                logger.error(
                    "Toutes les tentatives échouées pour agent %s",
                    agent.name,
                )
                raise
            # Attendre avant de réessayer
            await asyncio.sleep(1 * (attempt + 1))


def _final_json(result: Any) -> str:
    """
    Extrait le JSON final du résultat d'un agent.
    
    Args:
        result: Résultat brut de l'agent
        
    Returns:
        JSON final sous forme de string
    """
    # Priorité 1: final_output (nouveau format OpenAI Agents)
    if hasattr(result, "final_output") and result.final_output:
        # Si c'est un objet Pydantic, le convertir en dict puis en JSON
        if hasattr(result.final_output, "model_dump"):
            return json.dumps(result.final_output.model_dump(), ensure_ascii=False)
        # Si c'est déjà un dict, le convertir en JSON
        elif isinstance(result.final_output, dict):
            return json.dumps(result.final_output, ensure_ascii=False)
        # Sinon, conversion en string
        else:
            return str(result.final_output)
    
    # Priorité 2: messages (ancien format)
    if hasattr(result, "messages") and result.messages:
        last_message = result.messages[-1]
        if hasattr(last_message, "content"):
            return last_message.content
    
    # Fallback: conversion en string
    return str(result)


def _safe_json_loads(json_str: str) -> Optional[Dict[str, Any]]:
    """
    Charge un JSON de manière sécurisée.
    
    Args:
        json_str: String JSON à parser
        
    Returns:
        Dictionnaire parsé ou None en cas d'erreur
    """
    try:
        # Nettoyer la chaîne JSON des caractères de contrôle
        cleaned_json = json_str.strip()
        # Supprimer les caractères de tabulation répétés à la fin
        cleaned_json = cleaned_json.rstrip('\t\n\r ')
        
        return json.loads(cleaned_json)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Erreur de parsing JSON: %s", exc)
        logger.warning("JSON problématique (premiers 200 chars): %s", json_str[:200])
        return None


async def _safe_tracking(
    session_id: str,
    step_name: str,
    *,
    message: str,
    progress: float,
    metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Met à jour le tracking de manière sécurisée.
    
    Args:
        session_id: ID de session
        step_name: Nom de l'étape
        message: Message de statut
        progress: Progression (0.0 à 1.0)
        metrics: Métriques supplémentaires
    """
    try:
        await agent_tracking_service.update_tracking(
            session_id=session_id,
            step_name=step_name,
            message=message,
            progress=progress,
            metrics=metrics or {},
        )
    except Exception:
        logger.debug("Tracking update failed", exc_info=True)


async def call_company_analyzer(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Company Analyzer.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données d'analyse de l'entreprise
    """
    t0 = time.perf_counter()
    
    result = await _run_agent_with_retry(
        company_analyzer,
        input=state.raw_input,
        max_turns=MAX_TURNS["analyze"],
    )
    
    raw_output = _final_json(result)
    analyzer_data = _safe_json_loads(raw_output)
    
    if not analyzer_data:
        logger.warning("JSON Company Analyzer invalide: %s", raw_output)
        analyzer_data = {}
    
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "🔍 Éclaireur",
        message="Entité légale identifiée",
        progress=0.2,
        metrics={"elapsed_ms": elapsed_ms},
    )
    
    state.analyzer_raw = analyzer_data
    state.log("company_analyzer", analyzer_data)
    return analyzer_data


async def call_information_extractor(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Information Extractor.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données d'information de l'entreprise
    """
    t0 = time.perf_counter()
    
    # Préparer l'entrée avec les données d'analyse
    input_data = {
        "target_entity": state.target_entity,
        "analyzer_data": state.analyzer_raw,
        "raw_input": state.raw_input,
    }
    
    result = await _run_agent_with_retry(
        information_extractor,
        input=json.dumps(input_data, ensure_ascii=False),
        max_turns=MAX_TURNS["info"],
    )
    
    raw_output = _final_json(result)
    info_data = _safe_json_loads(raw_output)
    
    if not info_data:
        logger.warning("JSON Information Extractor invalide: %s", raw_output)
        info_data = {}
    
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "⛏️ Mineur",
        message="Informations clés consolidées",
        progress=0.4,
        metrics={"elapsed_ms": elapsed_ms},
    )
    
    state.info_card = info_data
    state.info_raw = info_data
    state.log("information_extractor", info_data)
    return info_data


async def call_subsidiary_extractor(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Subsidiary Extractor.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données des filiales
    """
    t0 = time.perf_counter()
    
    # Préparer l'entrée avec les données précédentes
    input_data = {
        "target_entity": state.target_entity,
        "company_info": state.info_card,
        "analyzer_data": state.analyzer_raw,
    }
    
    result = await _run_agent_with_retry(
        subsidiary_extractor,
        input=json.dumps(input_data, ensure_ascii=False),
        max_turns=MAX_TURNS["subs"],
    )
    
    raw_output = _final_json(result)
    subs_data = _safe_json_loads(raw_output)
    
    if not subs_data:
        logger.warning("JSON Subsidiary Extractor invalide: %s", raw_output)
        subs_data = {}
    
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "🗺️ Cartographe",
        message="Filiales extraites",
        progress=0.7,
        metrics={"elapsed_ms": elapsed_ms},
    )
    
    state.subs_report = subs_data
    state.subs_raw = subs_data
    state.log("subsidiary_extractor", subs_data)
    return subs_data


async def call_meta_validator(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Meta Validator.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données de validation méta
    """
    t0 = time.perf_counter()
    
    # Préparer l'entrée avec toutes les données
    input_data = {
        "company_info": state.info_card,
        "subsidiaries": state.subs_report,
        "analyzer_data": state.analyzer_raw,
    }
    
    result = await _run_agent_with_retry(
        meta_validator,
        input=json.dumps(input_data, ensure_ascii=False),
        max_turns=MAX_TURNS["meta"],
    )
    
    raw_output = _final_json(result)
    meta_data = _safe_json_loads(raw_output)
    
    if not meta_data:
        logger.warning("JSON Meta Validator invalide: %s", raw_output)
        meta_data = {}
    
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "⚖️ Superviseur",
        message="Cohérence validée",
        progress=0.9,
        metrics={"elapsed_ms": elapsed_ms},
    )
    
    state.meta_report = meta_data
    state.log("meta_validator", meta_data)
    return meta_data


async def call_data_restructurer(state: ExtractionState) -> Optional[Dict[str, Any]]:
    """
    Appelle l'agent Data Restructurer.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données restructurées
    """
    # L'agent restructurateur peut fonctionner même sans filiales
    # Il restructure les données de l'entreprise principale
    
    t0 = time.perf_counter()
    
    # Préparer les données à restructurer
    data_to_restructure = {
        "company_info": state.info_card,
        "company_info_raw": state.info_raw,
        "subsidiaries": state.subs_report,
        "subsidiaries_raw": state.subs_raw,
        "analyzer_raw": state.analyzer_raw,
        "meta_validation": state.meta_report,
    }
    
    logger.info("🔄 Appel de l'agent restructurateur avec %d filiales", 
                len(state.subs_report) if state.subs_report else 0)
    
    result = await _run_agent_with_retry(
        data_restructurer,
        input=json.dumps(data_to_restructure, ensure_ascii=False),
        max_turns=3,  # Limite pour éviter les boucles infinies
    )
    
    # Extraire les données directement du final_output
    if hasattr(result, "final_output") and result.final_output:
        raw_output = result.final_output
        # Si c'est un objet Pydantic, le convertir en dict
        if hasattr(raw_output, "model_dump"):
            company_info = raw_output.model_dump()
        # Si c'est déjà un dict, l'utiliser directement
        elif isinstance(raw_output, dict):
            company_info = raw_output
        else:
            # Fallback: essayer de parser comme JSON
            company_info = _safe_json_loads(str(raw_output))
    else:
        # Fallback: utiliser l'ancienne méthode
        raw_output = _final_json(result)
        company_info = _safe_json_loads(raw_output)
    
    logger.info("🔄 Réponse brute de l'agent restructurateur: %s", str(company_info)[:200] + "..." if len(str(company_info)) > 200 else str(company_info))
    
    if not company_info:
        logger.warning("JSON restructurer invalid: %s", raw_output)
        return None
    
    # Vérifier que company_info est un dictionnaire
    if not isinstance(company_info, dict):
        logger.warning("Restructurer output is not a dict: %s", type(company_info))
        return None
    
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "🔄 Restructurateur",
        message="Données restructurées et normalisées",
        progress=1.0,
        metrics={"elapsed_ms": elapsed_ms},
    )
    
    state.log("restructurer", company_info)
    return company_info
