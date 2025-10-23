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
    meta_validator,
)
from ..subs_agents.data_validator import data_restructurer
from ..subs_agents.subsidiary_extractor import run_cartographe_with_metrics
from ..config.extraction_config import MAX_TURNS
from ..processors.data_processor import ExtractionState
from services.agent_tracking_service import agent_tracking_service
from status import status_manager
from ..metrics import (
    metrics_collector, 
    MetricStatus, 
    RealTimeTracker,
    run_company_analyzer_with_metrics,
    run_information_extractor_with_metrics,
    run_meta_validator_with_metrics,
    run_data_restructurer_with_metrics
)

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


def _to_dict(obj: Any) -> Any:
    """
    Convertit un objet en dictionnaire, gérant les objets Pydantic.
    
    Args:
        obj: Objet à convertir
        
    Returns:
        Dictionnaire ou valeur primitive
    """
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    return obj


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
        
        # Détecter si le JSON est tronqué (ne se termine pas par })
        if not cleaned_json.endswith('}'):
            # Essayer de trouver la fin du JSON en cherchant le dernier } valide
            last_brace = cleaned_json.rfind('}')
            if last_brace > 0:
                cleaned_json = cleaned_json[:last_brace + 1]
            else:
                logger.warning("JSON tronqué sans accolade fermante")
                return None
        
        # Nettoyer les caractères de contrôle dans les chaînes
        import re
        # Remplacer les caractères de contrôle par des espaces
        cleaned_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned_json)
        
        return json.loads(cleaned_json)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Erreur de parsing JSON: %s", exc)
        logger.warning("JSON problématique (premiers 200 chars): %s", json_str[:200])
        logger.warning("JSON problématique (derniers 200 chars): %s", json_str[-200:])
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
    Met à jour le tracking de manière sécurisée via le status manager.
    
    Args:
        session_id: ID de session
        step_name: Nom de l'étape
        message: Message de statut
        progress: Progression (0.0 à 1.0)
        metrics: Métriques supplémentaires
    """
    try:
        # Utiliser directement le status manager pour les mises à jour WebSocket
        from status.manager import status_manager
        from status.models import MetricStatus
        
        # Convertir le progress en pourcentage
        progress_percent = progress * 100
        
        # Déterminer le statut basé sur la progression et le contexte
        if progress == 0.0:
            status = MetricStatus.INITIALIZING
        elif progress == 1.0:
            status = MetricStatus.COMPLETED
        elif progress >= 0.9:
            status = MetricStatus.FINALIZING
        else:
            status = MetricStatus.RUNNING
        
        # Extraire les métriques de performance
        performance_metrics = {}
        if metrics:
            performance_metrics = {
                "elapsed_time": metrics.get("elapsed_ms", 0),
                "steps_completed": metrics.get("current_step", 0),
                "steps_remaining": metrics.get("total_steps", 0) - metrics.get("current_step", 0),
            }
        
        # Mettre à jour via le status manager (qui notifie via WebSocket)
        await status_manager.update_agent_status_detailed(
            session_id=session_id,
            agent_name=step_name,
            status=status,
            progress=progress,
            message=message,
            current_step=metrics.get("current_step", 0) if metrics else 0,
            total_steps=metrics.get("total_steps", 1) if metrics else 1,
            step_name=metrics.get("step_name", "") if metrics else "",
            performance_metrics=performance_metrics,
        )
        
        logger.debug(f"✅ Tracking mis à jour: {step_name} -> {progress:.1%} - {message}")
        
    except Exception as e:
        logger.debug(f"❌ Tracking update failed: {e}", exc_info=True)


async def _progressive_tracking(
    session_id: str,
    agent_name: str,
    steps: list,
    current_step: int = 0,
    step_duration: float = 0.5,
) -> None:
    """
    Met à jour la progression de manière progressive pour simuler un traitement granulaire.
    
    Args:
        session_id: ID de session
        agent_name: Nom de l'agent
        steps: Liste des étapes avec leurs messages
        current_step: Étape actuelle (0-based)
        step_duration: Durée de chaque étape en secondes
    """
    total_steps = len(steps)
    
    # Mise à jour de l'étape actuelle
    if current_step < total_steps:
        step_info = steps[current_step]
        progress = (current_step + 1) / total_steps
        
        await _safe_tracking(
            session_id=session_id,
            step_name=agent_name,
            message=step_info["message"],
            progress=progress,
            metrics={
                "current_step": current_step + 1,
                "total_steps": total_steps,
                "step_name": step_info.get("step_name", f"Étape {current_step + 1}"),
                "elapsed_time": step_info.get("elapsed_time", 0),
            },
        )
        
        # Attendre avant la prochaine étape
        if step_duration > 0:
            await asyncio.sleep(step_duration)


async def _simulate_progressive_tracking(
    session_id: str,
    agent_name: str,
    steps: list,
    step_duration: float = 0.5,
) -> None:
    """
    Simule la progression granulaire en arrière-plan pendant l'exécution de l'agent.
    S'adapte au temps réel de l'agent pour éviter les décalages.
    
    Args:
        session_id: ID de session
        agent_name: Nom de l'agent
        steps: Liste des étapes avec leurs messages
        step_duration: Durée de chaque étape en secondes
    """
    total_steps = len(steps)
    start_time = time.perf_counter()
    
    for i, step in enumerate(steps):
        step_info = step
        progress = (i + 1) / total_steps
        
        # Calculer le temps écoulé réel
        elapsed_time = int((time.perf_counter() - start_time) * 1000)
        
        await _safe_tracking(
            session_id=session_id,
            step_name=agent_name,
            message=step_info["message"],
            progress=progress,
            metrics={
                "current_step": i + 1,
                "total_steps": total_steps,
                "step_name": step_info.get("step_name", f"Étape {i + 1}"),
                "elapsed_time": elapsed_time,
            },
        )
        
        # Attendre avant la prochaine étape, mais pas pour la dernière
        if step_duration > 0 and i < total_steps - 1:
            await asyncio.sleep(step_duration)


async def call_company_analyzer(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Company Analyzer avec métriques temps réel.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données d'analyse de l'entreprise
    """
    logger.info("🔍 Appel de l'agent éclaireur pour: %s", state.raw_input)
    
    try:
        # Exécuter l'agent avec métriques temps réel
        result_data = await run_company_analyzer_with_metrics(
            company_name=state.raw_input,
            session_id=state.session_id,
            status_manager=status_manager,
            max_turns=3
        )
        
        if result_data["status"] != "success":
            logger.error("❌ Erreur lors de l'analyse: %s", result_data.get("error", "Erreur inconnue"))
            return {}
        
        # Extraire les données du résultat
        result = result_data["result"]
        if hasattr(result, "final_output") and result.final_output:
            raw_output = result.final_output
            # Si c'est un objet Pydantic, le convertir en dict
            if hasattr(raw_output, "model_dump"):
                analyzer_data = raw_output.model_dump()
            else:
                analyzer_data = _safe_json_loads(raw_output)
        else:
            logger.warning("JSON Company Analyzer invalide ou vide.")
            analyzer_data = {}

        state.analyzer_raw = analyzer_data
        state.log("company_analyzer", analyzer_data)
        return analyzer_data
        
    except Exception as e:
        logger.error("❌ Erreur lors de l'analyse: %s", str(e))
        state.analyzer_raw = {}
        return {}


async def call_information_extractor(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Information Extractor avec métriques temps réel.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données d'information de l'entreprise
    """
    logger.info("⛏️ Appel de l'agent mineur pour: %s", state.target_entity)
    
    # Préparer l'entrée avec les données précédentes
    input_data = json.dumps({
        "target_entity": state.target_entity,
        "analyzer_data": state.analyzer_raw,
    }, ensure_ascii=False)
    
    try:
        # Exécuter l'agent avec métriques temps réel
        result_data = await run_information_extractor_with_metrics(
            input_data=input_data,
            session_id=state.session_id,
            status_manager=status_manager,
            max_turns=3
        )
        
        if result_data["status"] != "success":
            logger.error("❌ Erreur lors de l'extraction: %s", result_data.get("error", "Erreur inconnue"))
            return {}
        
        # Extraire les données du résultat
        result = result_data["result"]
        if hasattr(result, "final_output") and result.final_output:
            raw_output = result.final_output
            # Si c'est un objet Pydantic, le convertir en dict
            if hasattr(raw_output, "model_dump"):
                info_data = raw_output.model_dump()
            else:
                info_data = _safe_json_loads(raw_output)
        else:
            logger.warning("JSON Information Extractor invalide ou vide.")
            info_data = {}

        state.info_card = info_data
        state.info_raw = info_data
        state.log("information_extractor", info_data)
        return info_data
        
    except Exception as e:
        logger.error("❌ Erreur lors de l'extraction: %s", str(e))
        state.info_card = {}
        state.info_raw = {}
        return {}


async def call_subsidiary_extractor(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Subsidiary Extractor avec métriques temps réel.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données des filiales
    """
    try:
        # Préparer le contexte avec les données du Mineur
        analyzer_data = state.analyzer_raw if isinstance(state.analyzer_raw, dict) else {}
        info_card = state.info_card if isinstance(state.info_card, dict) else {}

        target_domain = analyzer_data.get("target_domain")

        website = None
        # Chercher une URL on-domain dans les sources du Mineur
        for source in info_card.get("sources", []) or []:
            url = source.get("url")
            if url and target_domain and target_domain in url:
                website = url
                break
        # Si aucune source n'a fourni d'URL exploitable, construire à partir du domaine
        if not website and target_domain:
            website = f"https://{target_domain.strip('/')}/"

        company_context = {
            "company_name": state.target_entity,
            "sector": info_card.get("sector") if info_card else None,
            "activities": info_card.get("activities") if info_card else None,
            "context": info_card.get("context") if info_card else None,
            "target_domain": target_domain,
            "website": website,
        }
        
        # Exécuter l'agent avec métriques détaillées (gère ses propres métriques)
        cartographe_result = await run_cartographe_with_metrics(
            company_context,
            state.session_id,
            deep_search=state.deep_search
        )
        
    except Exception as e:
        logger.error("❌ Erreur lors de la cartographie: %s", str(e))
        return {}
    
    # Extraire les données du résultat
    if cartographe_result and isinstance(cartographe_result, dict) and cartographe_result.get("result"):
        # Le résultat est déjà un dictionnaire depuis run_cartographe_with_metrics
        subsidiary_report = cartographe_result.get("result", {})

        # Convertir en dict si c'est une chaîne JSON ou un objet Pydantic
        if isinstance(subsidiary_report, str):
            try:
                subsidiary_report = json.loads(subsidiary_report)
            except json.JSONDecodeError:
                logger.error("❌ Impossible de parser le JSON du cartographe")
                subsidiary_report = {}
        elif (
            isinstance(subsidiary_report, dict)
            and "content" in subsidiary_report
            and isinstance(subsidiary_report["content"], str)
        ):
            try:
                subsidiary_report = json.loads(subsidiary_report["content"])
            except json.JSONDecodeError:
                logger.error("❌ Impossible de parser le champ content du cartographe")
                subsidiary_report = {}
        elif hasattr(subsidiary_report, "model_dump"):
            subsidiary_report = subsidiary_report.model_dump()
        
        state.subs_report = subsidiary_report
        state.subs_raw = subsidiary_report
        state.log("subsidiary_extractor", subsidiary_report)
        return subsidiary_report
    else:
        logger.warning("❌ Pas de résultat du cartographe ou format invalide: %s", type(cartographe_result))
        state.subs_report = {}
        state.subs_raw = {}
        return {}


async def call_meta_validator(state: ExtractionState) -> Dict[str, Any]:
    """
    Appelle l'agent Meta Validator avec métriques temps réel.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données de validation méta
    """
    logger.info("⚖️ Appel de l'agent superviseur")
    
    # Préparer l'entrée avec toutes les données
    input_data = json.dumps({
        "company_info": state.info_card,
        "subsidiaries": state.subs_report,
        "analyzer_data": state.analyzer_raw,
    }, ensure_ascii=False)
    
    try:
        # Exécuter l'agent avec métriques temps réel
        result_data = await run_meta_validator_with_metrics(
            input_data=input_data,
            session_id=state.session_id,
            status_manager=status_manager,
            max_turns=3
        )
        
        if result_data["status"] != "success":
            logger.error("❌ Erreur lors de la validation: %s", result_data.get("error", "Erreur inconnue"))
            return {}
        
        # Extraire les données du résultat
        result = result_data["result"]
        if hasattr(result, "final_output") and result.final_output:
            raw_output = result.final_output
            # Si c'est un objet Pydantic, le convertir en dict
            if hasattr(raw_output, "model_dump"):
                meta_data = raw_output.model_dump()
            else:
                meta_data = _safe_json_loads(raw_output)
        else:
            logger.warning("JSON Meta Validator invalide ou vide.")
            meta_data = {}

        state.meta_report = meta_data
        state.log("meta_validator", meta_data)
        return meta_data
        
    except Exception as e:
        logger.error("❌ Erreur lors de la validation: %s", str(e))
        return {}


async def call_data_restructurer(state: ExtractionState) -> Optional[Dict[str, Any]]:
    """
    Appelle l'agent Data Restructurer avec métriques temps réel.
    
    Args:
        state: État d'extraction
        
    Returns:
        Données restructurées
    """
    logger.info("🔄 Appel de l'agent restructurateur")
    
    # Préparer les données à restructurer (éviter les doublons)
    # Convertir les objets Pydantic en dictionnaires
    input_data = json.dumps({
        "company_info": _to_dict(state.info_card),
        "subsidiaries": _to_dict(state.subs_report),
        "analyzer_data": _to_dict(state.analyzer_raw),
        "meta_validation": _to_dict(state.meta_report),
    }, ensure_ascii=False)
    
    try:
        # Exécuter l'agent avec métriques temps réel
        result_data = await run_data_restructurer_with_metrics(
            input_data=input_data,
            session_id=state.session_id,
            status_manager=status_manager,
            max_turns=3
        )
        
        if result_data["status"] != "success":
            logger.error("❌ Erreur lors de la restructuration: %s", result_data.get("error", "Erreur inconnue"))
            return None
        
        # Extraire les données du résultat
        result = result_data["result"]
        if hasattr(result, "final_output") and result.final_output:
            raw_output = result.final_output
            # Si c'est un objet Pydantic, le convertir en dict
            if hasattr(raw_output, "model_dump"):
                company_info = raw_output.model_dump()
            else:
                company_info = _safe_json_loads(raw_output)
        else:
            logger.warning("JSON Data Restructurer invalide ou vide.")
            company_info = {}

        state.log("data_restructurer", company_info)
        return company_info
        
    except Exception as e:
        logger.error("❌ Erreur lors de la restructuration: %s", str(e))
        return None
