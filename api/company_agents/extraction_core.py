"""
Point d'entrée principal de l'API d'extraction d'informations d'entreprise.

Ce module orchestre le processus complet d'extraction en coordonnant :
- Le tracking des sessions
- L'orchestration des agents
- La gestion des erreurs
- Le stockage des résultats
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid
import logging
import time

from status import status_manager
from services.agent_tracking_service import agent_tracking_service

from .extraction_manager import orchestrate_extraction

logger = logging.getLogger(__name__)


async def extract_company_data(
    input_query: str,
    *,
    session_id: Optional[str] = None,
    include_subsidiaries: bool = True,
    force_company_profile: Optional[str] = None,
    max_turns: int = 4,
    deep_search: bool = False,
) -> Dict[str, Any]:
    """
    Point d'entrée principal pour l'extraction d'informations d'entreprise.

    Args:
        input_query: Nom d'entreprise ou URL à analyser
        session_id: ID de session pour le tracking (généré si None)
        include_subsidiaries: Inclure l'extraction des filiales
        force_company_profile: Forcer un profil d'entreprise spécifique
        max_turns: Nombre maximum de tours pour les agents
        deep_search: Mode de recherche approfondie (Perplexity) vs simple (GPT-4o-search)

    Returns:
        Dict contenant les informations d'entreprise extraites
    """
    sid = session_id or str(uuid.uuid4())
    start_time = time.perf_counter()

    # Démarrage du tracking de session
    await agent_tracking_service.start_extraction_tracking(sid, input_query)

    try:
        # Orchestration des agents spécialisés
        result = await orchestrate_extraction(
            input_query,
            session_id=sid,
            include_subsidiaries=include_subsidiaries,
            deep_search=deep_search,
        )

        # Ajout des métadonnées d'extraction
        # Préparer / compléter les métadonnées d'extraction
        metadata = result.get("extraction_metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        metadata.setdefault(
            "input_type",
            "url" if input_query.startswith("http") else "name",
        )
        metadata["session_id"] = sid
        metadata["processing_time"] = int(
            (time.perf_counter() - start_time) * 1000
        )
        result["extraction_metadata"] = metadata

        result["extraction_date"] = datetime.now(timezone.utc).isoformat()

        # Stockage des résultats et finalisation du tracking
        await status_manager.store_extraction_results(sid, result)
        await agent_tracking_service.complete_extraction_tracking(sid, result)
        return result
    except Exception as exc:
        logger.exception("❌ Échec extraction [Session: %s]", sid)
        await agent_tracking_service.error_extraction_tracking(sid, str(exc))
        raise
