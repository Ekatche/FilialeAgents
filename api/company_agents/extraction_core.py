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

        # Ajouter le type de recherche dans les métadonnées
        metadata["search_type"] = "advanced" if deep_search else "simple"
        result["extraction_metadata"] = metadata

        result["extraction_date"] = datetime.now(timezone.utc).isoformat()

        # Calculer les coûts si les données de tokens sont disponibles
        if "models_usage_raw" in result and result["models_usage_raw"]:
            try:
                from services.cost_tracking_service import cost_tracking_service

                # Calculer les coûts totaux
                cost_data = cost_tracking_service.calculate_extraction_cost(
                    result["models_usage_raw"]
                )

                # Ajouter les coûts des tools (temps réel si disponible, sinon estimation)
                real_time_tools_data = result.get("tools_usage_real_time")
                tools_cost = cost_tracking_service.calculate_tools_cost(
                    result["models_usage_raw"],
                    metadata["search_type"],
                    real_time_tools_data,
                    session_id=sid
                )

                # Coût total sans marge de sécurité
                total_cost_usd = cost_data["total_cost_usd"] + tools_cost["total_cost_usd"]
                total_cost_eur = cost_data["total_cost_eur"] + tools_cost["total_cost_eur"]

                # Ajouter les coûts au résultat
                result["extraction_costs"] = {
                    "cost_usd": total_cost_usd,
                    "cost_eur": total_cost_eur,
                    "total_tokens": cost_data["total_tokens"] + tools_cost["total_tokens"],
                    "input_tokens": cost_data["total_input_tokens"] + tools_cost["total_input_tokens"],
                    "output_tokens": cost_data["total_output_tokens"] + tools_cost["total_output_tokens"],
                    "models_breakdown": cost_data["models_breakdown"] + tools_cost["tools_breakdown"],
                    "search_type": metadata["search_type"],
                    "exchange_rate": cost_data["exchange_rate"],
                    "base_cost_usd": cost_data["total_cost_usd"],  # Coût des agents principaux
                    "base_cost_eur": cost_data["total_cost_eur"],  # Coût des agents principaux
                    "tools_cost_usd": tools_cost["total_cost_usd"],  # Coût des tools
                    "tools_cost_eur": tools_cost["total_cost_eur"]  # Coût des tools
                }

                logger.info(
                    f"💰 Coûts calculés pour session {sid}: "
                    f"{total_cost_eur:.4f}€ (agents: {cost_data['total_cost_eur']:.4f}€ + tools: {tools_cost['total_cost_eur']:.4f}€) "
                    f"({cost_data['total_tokens'] + tools_cost['total_tokens']} tokens, type: {metadata['search_type']})"
                )
            except Exception as e:
                logger.error(f"❌ Erreur lors du calcul des coûts pour session {sid}: {e}")
                # Ne pas bloquer l'extraction si le calcul des coûts échoue
        else:
            logger.warning(f"⚠️ Aucune donnée de tokens disponible pour session {sid}")

        # Stockage des résultats et finalisation du tracking
        await status_manager.store_extraction_results(sid, result)
        await agent_tracking_service.complete_extraction_tracking(sid, result)
        
        # Nettoyer le tracker de tokens APRÈS le calcul des coûts
        try:
            from .metrics.tool_tokens_tracker import ToolTokensTracker
            ToolTokensTracker.clear_session(sid)
            logger.info(f"🧹 ToolTokensTracker nettoyé pour session: {sid}")
        except Exception as e:
            logger.warning(f"⚠️ Impossible de nettoyer ToolTokensTracker: {e}")
        
        return result
    except Exception as exc:
        logger.exception("❌ Échec extraction [Session: %s]", sid)
        await agent_tracking_service.error_extraction_tracking(sid, str(exc))
        raise
