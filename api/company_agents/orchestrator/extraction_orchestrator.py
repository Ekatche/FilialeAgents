"""
Main orchestration logic for company information extraction.

This module contains the core orchestration logic that coordinates
the execution of all agents in the extraction pipeline.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import ValidationError

from ..models import CompanyInfo
from ..processors.data_processor import ExtractionState
from .agent_caller import (
    call_company_analyzer,
    call_information_extractor,
    call_subsidiary_extractor,
    call_meta_validator,
    call_data_restructurer,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractionState:
    """État d'extraction pour l'orchestrateur."""
    session_id: str
    raw_input: str
    include_subsidiaries: bool = True
    deep_search: bool = False
    target_entity: Optional[str] = None
    info_card: Optional[Dict[str, Any]] = None
    info_raw: Optional[Dict[str, Any]] = None
    subs_report: Optional[Dict[str, Any]] = None
    subs_raw: Optional[Dict[str, Any]] = None
    analyzer_raw: Optional[Dict[str, Any]] = None
    meta_report: Optional[Dict[str, Any]] = None
    warnings: list = field(default_factory=list)

    def log(self, step: str, payload: Any) -> None:
        """Log une étape de l'extraction."""
        logger.debug("[state:%s] %s → %s", self.session_id, step, payload)


def _resolve_target_entity(raw_input: str, analyzer_data: Dict[str, Any]) -> str:
    """
    Résout l'entité cible à partir des données d'analyse.
    
    Logique de sélection :
    1. Si l'entreprise est une filiale (relationship="subsidiary") ET qu'une parent_company est identifiée
       → Utiliser la parent_company comme target_entity
    2. Sinon, utiliser l'entité légale identifiée par l'Éclaireur
    3. Fallback sur l'entrée brute si aucune donnée d'analyse
    
    Args:
        raw_input: Entrée brute de l'utilisateur
        analyzer_data: Données de l'analyseur d'entreprise
        
    Returns:
        Nom de l'entité cible résolue
    """
    if not analyzer_data:
        return raw_input
    
    # Vérifier si c'est une filiale avec une société mère identifiée
    relationship = analyzer_data.get("relationship")
    parent_company = analyzer_data.get("parent_company")
    
    if relationship == "subsidiary" and parent_company:
        logger.info(
            "🎯 Entité filiale détectée: %s → Cible changée vers société mère: %s",
            analyzer_data.get("entity_legal_name", raw_input),
            parent_company
        )
        return parent_company
    
    # Priorité aux données d'analyse (entité légale)
    entity_name = analyzer_data.get("entity_legal_name")
    if entity_name:
        logger.info("🎯 Entité cible résolue: %s", entity_name)
        return entity_name
    
    # Fallback sur l'entrée brute
    logger.info("🎯 Fallback sur entrée brute: %s", raw_input)
    return raw_input


def _should_run_meta_validation(state: ExtractionState) -> bool:
    """
    Détermine si la validation méta doit être exécutée.
    
    Args:
        state: État d'extraction
        
    Returns:
        True si la validation méta doit être exécutée
    """
    # Exécuter la validation méta si on a un rapport de filiales (même vide)
    if not state.subs_report:
        return False
    
    # Si c'est une chaîne, la parser
    if isinstance(state.subs_report, str):
        try:
            import json
            state.subs_report = json.loads(state.subs_report)
        except (json.JSONDecodeError, TypeError):
            return False
    
    # Vérifier si on a un rapport de filiales valide (même avec liste vide)
    # Le Superviseur doit valider la cohérence même quand il n'y a pas de filiales
    return isinstance(state.subs_report, dict) and "subsidiaries" in state.subs_report


async def orchestrate_extraction(
    raw_input: str,
    *,
    session_id: str,
    include_subsidiaries: bool = True,
    deep_search: bool = False,
) -> Dict[str, Any]:
    """
    Orchestrateur principal du pipeline d'extraction multi-agents.

    Séquence d'exécution :
    1. 🔍 Company Analyzer : Identification de l'entité légale
    2. ⛏️ Information Extractor : Consolidation des informations clés
    3. 🗺️ Subsidiary Extractor : Extraction des filiales (si demandé)
    4. ⚖️ Meta Validator : Validation de cohérence (si nécessaire)
    5. 🔄 Data Restructurer : Normalisation finale

    Args:
        raw_input: Entrée brute de l'utilisateur
        session_id: ID de session unique
        include_subsidiaries: Inclure l'extraction des filiales
        deep_search: Mode de recherche approfondie (Perplexity) vs simple (GPT-4o-search)

    Returns:
        Données d'entreprise extraites et validées
    """
    logger.info("🚀 Démarrage de l'orchestration d'extraction pour session=%s (deep_search=%s)", session_id, deep_search)

    state = ExtractionState(
        session_id=session_id,
        raw_input=raw_input,
        include_subsidiaries=include_subsidiaries,
        deep_search=deep_search,
    )

    try:
        # Étape 1: Identification de l'entité légale
        logger.info("🔍 Étape 1: Identification de l'entité légale")
        analyzer_data = await call_company_analyzer(state)
        state.target_entity = _resolve_target_entity(raw_input, analyzer_data)
        state.log("analyzer", analyzer_data)

        # Étape 2: Consolidation des informations clés
        logger.info("⛏️ Étape 2: Consolidation des informations clés")
        info_data = await call_information_extractor(state)
        state.log("information_extractor", info_data)

        # Étape 3: Extraction des filiales (conditionnelle)
        if state.include_subsidiaries:
            logger.info("🗺️ Étape 3: Extraction des filiales")
            await call_subsidiary_extractor(state)
            state.log("subsidiary_extractor", state.subs_report)

        # Étape 4: Validation de cohérence (conditionnelle)
        if _should_run_meta_validation(state):
            logger.info("⚖️ Étape 4: Validation de cohérence")
            await call_meta_validator(state)
            state.log("meta_validator", state.meta_report)

        # Étape 5: Restructuration des données pour garantir la qualité
        logger.info("🔄 Étape 5: Restructuration des données")
        restructured_company_info = await call_data_restructurer(state)

        if restructured_company_info:
            # Utiliser les données restructurées directement
            try:
                validated_model = CompanyInfo.model_validate(
                    restructured_company_info
                )

                # Enrichir les métadonnées avant de retourner
                from ..models import ExtractionMetadata
                
                metadata_dict = (
                    validated_model.extraction_metadata.model_dump()
                    if validated_model.extraction_metadata
                    else {}
                )
                metadata_dict.setdefault("session_id", session_id)
                
                # Créer un objet ExtractionMetadata valide
                validated_model.extraction_metadata = ExtractionMetadata(**metadata_dict)

                if not validated_model.extraction_date:
                    validated_model.extraction_date = datetime.now(timezone.utc).isoformat()

                logger.info("✅ Extraction terminée avec succès pour session=%s", session_id)
                return validated_model.model_dump()
            except ValidationError as exc:
                logger.error(
                    "❌ Erreur de validation CompanyInfo pour session=%s: %s",
                    session_id,
                    exc,
                )
                # Fallback sur les données brutes
                return restructured_company_info
        else:
            logger.warning("⚠️ Aucune donnée restructurée disponible pour session=%s", session_id)
            return {}

    except Exception as exc:
        logger.error(
            "❌ Erreur lors de l'orchestration pour session=%s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        # Retourner un résultat d'erreur structuré
        return {
            "error": "Extraction failed",
            "message": str(exc),
            "session_id": session_id,
            "raw_input": raw_input,
        }
