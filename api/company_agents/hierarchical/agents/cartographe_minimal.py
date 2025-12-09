"""
Agent Cartographe Minimal (Phase 1)

Mission : Identifier UNIQUEMENT les entités liées à une entreprise (filiales, participations, holdings, etc.)
sans extraction détaillée. L'extraction détaillée sera faite par un agent dédié en Phase 2.

Modèle : gpt-5.1 + web_search
- Recherche web temps réel via tools
- Modèle reasoning avec capacités de recherche avancées
- $1.25/1M input, $10/1M output + $10/1K web_search calls
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from company_agents.common.models import MinimalMappingReport, EntityRef, SourceRef
from company_agents.common.metrics import metrics_collector, MetricStatus
from services.entity_cache_service import entity_cache
from company_agents.hierarchical.tools.minimal_subsidiary_search import minimal_subsidiary_search_gpt5
from status.models import AgentStatus

logger = logging.getLogger(__name__)


# ==========================================
#   FONCTION OUTIL : Recherche Web
# ==========================================

async def search_related_entities(
    company_name: str,
    website: Optional[str] = None,
    sector: Optional[str] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recherche les entités liées à une entreprise (filiales, participations, holdings, etc.).

    Utilise gpt-4o-mini-search-preview pour effectuer une recherche web temps réel
    et identifier les entités juridiques liées.

    Args:
        company_name: Nom de l'entreprise cible
        website: Site web officiel (optionnel, aide à la recherche)
        sector: Secteur d'activité (optionnel, contexte)
        context: Contexte additionnel (optionnel)

    Returns:
        Dict avec:
            - entities_found: Liste brute des entités trouvées
            - sources: URLs sources consultées
            - search_notes: Notes sur la recherche effectuée
            - status: "success" ou "error"
    """
    start_time = time.time()
    logger.info(f"🔍 Recherche d'entités liées pour: {company_name}")

    try:
        # Construction de la requête de recherche
        search_query = f"Liste des filiales et participations de {company_name}"

        if website:
            search_query += f" site:{website}"

        if sector:
            search_query += f" secteur {sector}"

        # Utilisation de la recherche minimale avec GPT-5 + web_search tools
        
        logger.info(f"📡 Recherche minimale GPT-5 avec web_search tools pour: {company_name}")

        # Appel de la fonction de recherche minimale avec GPT-5
        search_result = await minimal_subsidiary_search_gpt5(
            company_name=company_name,
            sector=sector,
            website=website
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Extraction des entités trouvées
        entities_found = []
        sources = []

        if "error" not in search_result:
            # Parser legal_subsidiaries
            for sub in search_result.get("legal_subsidiaries", []):
                # Nettoyer l'URL du website si présente
                website = sub.get("website")
                if website:
                    # Retirer les caractères parasites (parenthèses, espaces, guillemets)
                    website = website.strip().rstrip(')').rstrip('(').strip('"').strip("'").strip()
                    # Vérifier que c'est une URL valide
                    if not website.startswith(('http://', 'https://')):
                        website = None
                
                entities_found.append({
                    "legal_name": sub.get("legal_name") or sub.get("name"),
                    "country": sub.get("country"),
                    "city": sub.get("city"),
                    "activity": sub.get("activity"),
                    "website": website,
                    "source_url": sub.get("source_url"),  # Ajouter source_url pour validation
                    "source_title": sub.get("source_title")  # Ajouter source_title
                })

            # Extraire les sources depuis chaque entité (au lieu de search_result.get("source_url"))
            source_urls_set = set()
            for sub in search_result.get("legal_subsidiaries", []):
                source_url = sub.get("source_url")
                if source_url:
                    source_urls_set.add(source_url)
            
            # Ajouter les sources uniques
            sources = list(source_urls_set)

        return {
            "search_query": search_query,
            "entities_found": entities_found,
            "sources": sources,
            "search_notes": [
                f"Recherche minimale d'identification (GPT-5 + web_search tools)",
                f"Durée: {duration_ms}ms",
                f"{len(entities_found)} entités trouvées"
            ],
            "status": "success" if "error" not in search_result else "error",
            "duration_ms": duration_ms
        }

    except Exception as e:
        logger.error(f"❌ Erreur lors de la recherche d'entités: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "search_query": search_query if 'search_query' in locals() else "",
            "entities_found": [],
            "sources": [],
            "search_notes": [f"Erreur: {str(e)}"],
            "status": "error",
            "duration_ms": duration_ms,
            "error": str(e)
        }


# ==========================================
#   FONCTION PRINCIPALE : Cartographie Minimale
# ==========================================

async def run_cartographe_minimal(
    company_name: str,
    website: Optional[str] = None,
    sector: Optional[str] = None,
    context: Optional[str] = None,
    use_cache: bool = True,
    status_manager=None,  # NOUVEAU
    session_id: Optional[str] = None  # NOUVEAU
) -> MinimalMappingReport:
    """
    Exécute le Cartographe Minimal pour identifier les entités liées à une entreprise.

    Args:
        company_name: Nom de l'entreprise cible
        website: Site web officiel (optionnel)
        sector: Secteur d'activité (optionnel)
        context: Contexte additionnel (optionnel)
        use_cache: Utiliser le cache in-memory (défaut: True)
        status_manager: Gestionnaire de statut pour WebSocket (optionnel)
        session_id: ID de session pour le tracking (optionnel)

    Returns:
        MinimalMappingReport avec les entités identifiées
    """
    start_time = time.time()
    logger.info(f"🗺️ Démarrage Cartographe Minimal pour: {company_name}")
    
    # Notifier le démarrage via WebSocket si disponible
    if status_manager and session_id:
        try:
            await status_manager.update_agent_status_detailed(
                session_id=session_id,
                agent_name="🗺️ Cartographe",
                status=AgentStatus.RUNNING,
                progress=0.2,
                message="Recherche des entités liées en cours...",
                current_step=2,
                total_steps=3,
                step_name="Phase 1 : Cartographe Minimal"
            )
        except Exception as e:
            logger.warning(f"⚠️ Erreur notification WebSocket Cartographe: {e}")

    # Vérification du cache
    if use_cache:
        cached_data = await entity_cache.get(company_name)
        if cached_data:
            logger.info(f"✅ Cache HIT pour {company_name}")
            try:
                # Filtrer les métadonnées du cache (_cached_at, _ttl) qui ne font pas partie du modèle
                cache_metadata = {"_cached_at", "_ttl"}
                filtered_data = {k: v for k, v in cached_data.items() if k not in cache_metadata}
                
                # Reconstruction du MinimalMappingReport depuis le cache
                # Filtrer entity_type si présent (ancien format du cache)
                entities = []
                for entity in filtered_data.get("entities_identified", []):
                    # Filtrer entity_type si présent (migration depuis ancien format)
                    entity_clean = {k: v for k, v in entity.items() if k != "entity_type"}
                    try:
                        entities.append(EntityRef(**entity_clean))
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur reconstruction EntityRef depuis cache: {e}, skip")
                        continue
                sources = [SourceRef(**source) for source in filtered_data.get("sources", [])]

                cached_report = MinimalMappingReport(
                    entities_identified=entities,
                    total_found=filtered_data.get("total_found", len(entities)),
                    search_strategy=filtered_data.get("search_strategy", "gpt-4o-search"),
                    sources=sources,
                    methodology_notes=filtered_data.get("methodology_notes", []) + ["✅ Données du cache"]
                )
                
                # Notifier la fin via WebSocket si disponible (cache hit)
                if status_manager and session_id:
                    try:
                        await status_manager.update_agent_status_detailed(
                            session_id=session_id,
                            agent_name="🗺️ Cartographe",
                            status=AgentStatus.COMPLETED,
                            progress=1.0,
                            message=f"{cached_report.total_found} entités identifiées (cache)",
                            current_step=2,
                            total_steps=3,
                            step_name="Phase 1 : Cartographe Minimal",
                            performance_metrics={
                                "entities_identified": cached_report.total_found,
                                "cache_hit": True
                            }
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Erreur notification WebSocket cache Cartographe: {e}")
                
                return cached_report
            except Exception as e:
                logger.warning(f"⚠️ Erreur reconstruction cache: {e}, recherche normale")

    try:
        # Appel direct de l'outil de recherche (pas besoin d'agent pour éviter la latence)
        logger.info(f"🔍 Recherche d'entités pour {company_name}")

        tool_result = await search_related_entities(
            company_name=company_name,
            website=website,
            sector=sector,
            context=context
        )

        # Parse du résultat de l'outil
        duration_ms = int((time.time() - start_time) * 1000)

        entities_identified = []
        sources = []
        methodology_notes = [
            f"Recherche effectuée avec GPT-5 + web_search tools",
            f"Durée: {duration_ms}ms"
        ]

        # Extraire les entités du résultat de l'outil
        if tool_result and tool_result.get('status') == 'success' and tool_result.get('entities_found'):
            for entity_data in tool_result['entities_found'][:30]:  # Limite augmentée à 30
                legal_name = entity_data.get("legal_name", "")
                if not legal_name:
                    continue  # Skip si pas de nom

                # Nettoyer l'URL du website si présente
                website = entity_data.get("website")
                if website:
                    # Retirer les caractères parasites (parenthèses, espaces, guillemets)
                    website = website.strip().rstrip(')').rstrip('(').strip('"').strip("'").strip()
                    # Vérifier que c'est une URL valide
                    if not website.startswith(('http://', 'https://')):
                        website = None
                else:
                    website = None  # S'assurer que website est None si non présent

                # VALIDATION DE COHÉRENCE : Vérifier si le website correspond à l'entité
                if website:
                    from company_agents.hierarchical.tools.contact_finder import validate_entity_website_coherence
                    entity_country = entity_data.get("country")
                    
                    # Vérifier cohérence nom entité vs website
                    is_coherent, coherence_warning = validate_entity_website_coherence(legal_name, website)
                    
                    # Extraire le TLD du website pour validation supplémentaire
                    tld_to_country = {
                        '.fr': 'France', '.de': 'Germany', '.uk': 'UK', '.es': 'Spain',
                        '.it': 'Italy', '.nl': 'Netherlands', '.be': 'Belgium', '.ch': 'Switzerland',
                        '.ca': 'Canada', '.mx': 'Mexico', '.br': 'Brazil', '.ar': 'Argentina',
                        '.cl': 'Chile', '.us': 'USA',
                    }
                    website_country = None
                    for tld, country in tld_to_country.items():
                        if tld in website.lower():
                            website_country = country
                            break
                    
                    # Vérifier aussi cohérence pays vs website si pays disponible
                    if entity_country and website_country:
                        # Normaliser les noms de pays pour comparaison
                        country_normalized = entity_country.lower().strip()
                        website_country_normalized = website_country.lower().strip()
                        # Vérifier si les pays correspondent (tolérance pour variations)
                        if country_normalized not in website_country_normalized and website_country_normalized not in country_normalized:
                            # Incohérence : pays de l'entité ne correspond pas au TLD du website
                            logger.warning(
                                f"⚠️ [Cartographe Minimal] Website '{website}' ne correspond pas à l'entité '{legal_name}' "
                                f"(pays entité: {entity_country}, TLD website: {website_country}). Website ignoré."
                            )
                            website = None
                    
                    if not is_coherent:
                        # Incohérence détectée par le nom de l'entité
                        logger.warning(
                            f"⚠️ [Cartographe Minimal] {coherence_warning}. Website ignoré pour '{legal_name}'."
                        )
                        website = None

                # Logger pour debug
                logger.debug(f"📋 EntityRef créé: {legal_name}, website={website}, country={entity_data.get('country')}")

                # Créer l'EntityRef
                entity_ref = EntityRef(
                    legal_name=legal_name,
                    confidence=0.75,  # Confiance moyenne pour recherche web
                    country=entity_data.get("country"),
                    brief_context=entity_data.get("activity") or entity_data.get("brief_context"),
                    website=website
                )
                entities_identified.append(entity_ref)

            # Extraire les sources
            if tool_result.get('sources'):
                for source_url in tool_result['sources']:
                    if source_url:  # Skip empty sources
                        sources.append(SourceRef(
                            title=f"Source de recherche",
                            url=source_url,
                            accessibility="ok"
                        ))

            # Ajouter notes méthodologiques
            if tool_result.get('search_notes'):
                methodology_notes.extend(tool_result['search_notes'])

            logger.info(f"✅ Parsé {len(entities_identified)} entités depuis l'agent workflow")
        else:
            logger.warning("⚠️ Aucune entité trouvée ou erreur de recherche")
            # Ajouter une source par défaut
            if website:
                sources.append(SourceRef(
                    title="Site web de l'entreprise",
                    url=website,
                    accessibility="ok"
                ))

        # Construction du rapport minimal avec données réelles
        # Ne créer une source par défaut que si website est valide
        if not sources:
            if website:
                sources = [SourceRef(title="Site web de l'entreprise", url=website, accessibility="ok")]
            else:
                # Si pas de website, créer une source avec URL d'erreur valide
                sources = [SourceRef(title="Aucune source disponible", url="https://error.local", accessibility="broken")]
        
        report = MinimalMappingReport(
            entities_identified=entities_identified,
            total_found=len(entities_identified),
            search_strategy="gpt-5-web-search",
            sources=sources,
            methodology_notes=methodology_notes
        )

        # Mise en cache si activé
        if use_cache and report.total_found > 0:
            cache_data = {
                "entities_identified": [entity.model_dump() for entity in report.entities_identified],
                "total_found": report.total_found,
                "search_strategy": report.search_strategy,
                "sources": [source.model_dump() for source in report.sources],
                "methodology_notes": report.methodology_notes
            }
            await entity_cache.set(company_name, cache_data)
            logger.info(f"✅ Résultat mis en cache pour {company_name}")

        logger.info(f"✅ Cartographe Minimal terminé: {report.total_found} entités trouvées")
        
        # Notifier la fin via WebSocket si disponible
        if status_manager and session_id:
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🗺️ Cartographe",
                    status=AgentStatus.COMPLETED,
                    progress=1.0,
                    message=f"{report.total_found} entités identifiées",
                    current_step=2,
                    total_steps=3,
                    step_name="Phase 1 : Cartographe Minimal",
                    performance_metrics={
                        "entities_identified": report.total_found,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket fin Cartographe: {e}")
        
        return report
    except Exception as e:
        logger.error(f"❌ Erreur Cartographe Minimal: {e}")
        
        # Notifier l'erreur via WebSocket si disponible
        if status_manager and session_id:
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🗺️ Cartographe",
                    status=AgentStatus.ERROR,
                    progress=0.0,
                    message=f"Erreur: {str(e)}",
                    current_step=2,
                    total_steps=3,
                    step_name="Phase 1 : Cartographe Minimal"
                )
            except Exception as ws_error:
                logger.warning(f"⚠️ Erreur notification WebSocket erreur Cartographe: {ws_error}")

        # Retour d'un rapport d'erreur
        return MinimalMappingReport(
            entities_identified=[],
            total_found=0,
            search_strategy="gpt-4o-mini-search",
            sources=[
                SourceRef(
                    title="Erreur de cartographie",
                    url="https://error.local",
                    accessibility="broken"
                )
            ],
            methodology_notes=[
                f"❌ Erreur: {str(e)}",
                f"Entreprise: {company_name}"
            ]
        )
