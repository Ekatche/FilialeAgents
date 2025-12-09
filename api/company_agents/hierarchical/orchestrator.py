"""
Orchestrateur Hiérarchique

Coordonne l'exécution parallèle de l'architecture hiérarchique :
1. Phase 0 : Éclaireur identifie la société mère et le secteur
2. Phase 1 : Cartographe Minimal identifie jusqu'à 15 entités
3. Phase 2 : Extracteur Détaillé extrait les informations de chaque entité EN PARALLÈLE

Gestion :
- Exécution parallèle avec asyncio.gather
- Rate limiting avec asyncio.Semaphore
- Timeouts et gestion d'erreurs
- Consolidation des résultats
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from company_agents.common.models import (
    MinimalMappingReport,
    EntityRef,
    DetailedEntityInfo,
    SourceRef,
    EclaireurReport,
    ParentCompanyInfo
)
from company_agents.hierarchical.agents.eclaireur import run_eclaireur
from company_agents.hierarchical.agents.enrichisseur_societe_mere import run_enrichisseur_societe_mere
from company_agents.hierarchical.agents.cartographe_minimal import run_cartographe_minimal
from company_agents.hierarchical.agents.extracteur_detaille import run_extracteur_detaille
from company_agents.common.metrics import metrics_collector, MetricStatus
from status.models import AgentStatus

logger = logging.getLogger(__name__)


# ==========================================
#   CONFIGURATION
# ==========================================

# Rate limiting : nombre d'extractions parallèles max
MAX_PARALLEL_EXTRACTIONS = 10  # Optimisé pour extraction parallèle rapide

# Timeout par extraction (secondes)
EXTRACTION_TIMEOUT = 60  # 1 minute par entité

# Timeout global (secondes)
GLOBAL_TIMEOUT = 600  # 10 minutes total


# ==========================================
#   RAPPORT HIÉRARCHIQUE CONSOLIDÉ
# ==========================================

class HierarchicalExtractionReport:
    """Rapport consolidé de l'extraction hiérarchique"""

    def __init__(
        self,
        company_name: str,
        minimal_mapping: MinimalMappingReport,
        detailed_entities: List[DetailedEntityInfo],
        extraction_stats: Dict[str, Any],
        parent_company_info: Optional[ParentCompanyInfo] = None
    ):
        self.company_name = company_name
        self.minimal_mapping = minimal_mapping
        self.detailed_entities = detailed_entities
        self.extraction_stats = extraction_stats
        self.parent_company_info = parent_company_info
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le rapport en dictionnaire"""
        result = {
            "company_name": self.company_name,
            "timestamp": self.timestamp,
            "minimal_mapping": {
                "total_entities_identified": self.minimal_mapping.total_found,
                "entities": [entity.model_dump() for entity in self.minimal_mapping.entities_identified],
                "search_strategy": self.minimal_mapping.search_strategy,
                "methodology_notes": self.minimal_mapping.methodology_notes
            },
            "detailed_entities": [entity.model_dump() for entity in self.detailed_entities],
            "extraction_stats": self.extraction_stats
        }
        if self.parent_company_info:
            result["parent_company_info"] = self.parent_company_info.model_dump()
        return result

    def summary(self) -> str:
        """Résumé textuel du rapport"""
        success_count = sum(1 for e in self.detailed_entities if e.confidence > 0.5)
        return (
            f"📊 Extraction hiérarchique: {self.company_name}\n"
            f"   • Entités identifiées: {self.minimal_mapping.total_found}\n"
            f"   • Extractions réussies: {success_count}/{len(self.detailed_entities)}\n"
            f"   • Durée totale: {self.extraction_stats.get('total_duration_seconds', 0):.1f}s\n"
            f"   • Stratégie: {self.minimal_mapping.search_strategy}"
        )


# ==========================================
#   EXTRACTEUR PARALLÈLE AVEC RATE LIMITING
# ==========================================

async def extract_entity_with_timeout(
    entity_ref: EntityRef,
    parent_company: str,
    semaphore: asyncio.Semaphore,
    timeout: int = EXTRACTION_TIMEOUT,
    status_manager=None,  # NOUVEAU
    session_id: Optional[str] = None  # NOUVEAU
) -> Optional[DetailedEntityInfo]:
    """
    Extrait les détails d'une entité avec timeout et rate limiting.

    Args:
        entity_ref: Référence à l'entité
        parent_company: Nom de la société mère
        semaphore: Semaphore pour rate limiting
        timeout: Timeout en secondes

    Returns:
        DetailedEntityInfo ou None si erreur/timeout
    """
    async with semaphore:  # Rate limiting
        logger.info(f"🔬 Extraction parallèle: {entity_ref.legal_name}")

        try:
            # Exécution avec timeout
            detailed_entity = await asyncio.wait_for(
                run_extracteur_detaille(
                    entity_ref, 
                    parent_company,
                    status_manager=status_manager,  # NOUVEAU
                    session_id=session_id  # NOUVEAU
                ),
                timeout=timeout
            )
            logger.info(f"✅ Extraction terminée: {entity_ref.legal_name} (confiance: {detailed_entity.confidence})")
            return detailed_entity

        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout extraction: {entity_ref.legal_name} (>{timeout}s)")
            return None

        except Exception as e:
            logger.error(f"❌ Erreur extraction {entity_ref.legal_name}: {e}")
            return None


# ==========================================
#   ORCHESTRATEUR PRINCIPAL
# ==========================================

async def run_hierarchical_extraction(
    company_name: str,
    website: Optional[str] = None,
    sector: Optional[str] = None,
    context: Optional[str] = None,
    use_cache: bool = True,
    max_parallel: int = MAX_PARALLEL_EXTRACTIONS,
    status_manager=None,  # NOUVEAU
    session_id: Optional[str] = None  # NOUVEAU
) -> HierarchicalExtractionReport:
    """
    Orchestre l'extraction hiérarchique complète.

    Workflow:
    1. Cartographe Minimal : Identifie les entités (max 15)
    2. Extracteur Détaillé : Extrait en parallèle les infos de chaque entité
    3. Consolidation : Agrège tous les résultats

    Args:
        company_name: Nom de l'entreprise cible
        website: Site web officiel (optionnel)
        sector: Secteur d'activité (optionnel)
        context: Contexte additionnel (optionnel)
        use_cache: Utiliser le cache in-memory (défaut: True)
        max_parallel: Nombre d'extractions parallèles max (défaut: 5)

    Returns:
        HierarchicalExtractionReport avec tous les résultats
    """
    start_time = time.time()
    logger.info(f"🚀 Démarrage extraction hiérarchique: {company_name}")

    extraction_stats = {
        "company_name": company_name,
        "start_time": datetime.now().isoformat(),
        "phase_0_duration_seconds": 0,
        "phase_0_5_duration_seconds": 0,
        "phase_1_duration_seconds": 0,
        "phase_2_duration_seconds": 0,
        "total_duration_seconds": 0,
        "entities_identified": 0,
        "entities_extracted": 0,
        "extraction_success_count": 0,
        "extraction_error_count": 0,
        "cache_used": use_cache
    }

    # ==========================================
    # PHASE 0 : ÉCLAIREUR (IDENTIFICATION SOCIÉTÉ MÈRE)
    # ==========================================

    logger.info("🔍 Phase 0 : Éclaireur (identification société mère)")
    phase0_start = time.time()

    # Démarrer les métriques pour la Phase 0
    phase0_metrics = None
    phase0_step = None
    if status_manager and session_id:
        phase0_metrics = metrics_collector.start_agent("🔍 Éclaireur", session_id)
        phase0_step = phase0_metrics.add_step("Identification société mère")
        phase0_step.status = MetricStatus.RUNNING
        # Notifier le démarrage via WebSocket
        try:
            await status_manager.update_agent_status_detailed(
                session_id=session_id,
                agent_name="🔍 Éclaireur",
                status=AgentStatus.RUNNING,
                progress=0.0,
                message="Identification de la société mère...",
                current_step=1,
                total_steps=4,
                step_name="Phase 0 : Éclaireur"
            )
        except Exception as e:
            logger.warning(f"⚠️ Erreur notification WebSocket Phase 0: {e}")

    try:
        eclaireur_report = await run_eclaireur(
            company_name=company_name,
            website=website,
            status_manager=status_manager,  # NOUVEAU
            session_id=session_id  # NOUVEAU
        )

        extraction_stats["phase_0_duration_seconds"] = time.time() - phase0_start
        
        # Finaliser les métriques de la Phase 0
        if status_manager and session_id and phase0_metrics and phase0_step:
            phase0_step.finish(MetricStatus.COMPLETED, {
                "parent_company": eclaireur_report.parent_company_name,
                "confidence": eclaireur_report.confidence,
                "duration_seconds": extraction_stats["phase_0_duration_seconds"]
            })
            metrics_collector.finish_agent("🔍 Éclaireur", session_id, MetricStatus.COMPLETED)
            # Notifier la fin via WebSocket
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🔍 Éclaireur",
                    status=AgentStatus.COMPLETED,
                    progress=1.0,
                    message=f"Société mère identifiée: {eclaireur_report.parent_company_name}",
                    current_step=1,
                    total_steps=4,
                    step_name="Phase 0 : Éclaireur",
                    performance_metrics={
                        "duration_seconds": extraction_stats["phase_0_duration_seconds"],
                        "confidence": eclaireur_report.confidence
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket fin Phase 0: {e}")
        extraction_stats["parent_company_name"] = eclaireur_report.parent_company_name
        extraction_stats["parent_company_website"] = eclaireur_report.parent_website
        extraction_stats["is_parent_company"] = eclaireur_report.is_parent_company
        extraction_stats["eclaireur_confidence"] = eclaireur_report.confidence

        logger.info(
            f"✅ Phase 0 terminée: Société mère = {eclaireur_report.parent_company_name} "
            f"(confiance: {eclaireur_report.confidence:.2f}, "
            f"is_parent: {eclaireur_report.is_parent_company}) "
            f"({extraction_stats['phase_0_duration_seconds']:.1f}s)"
        )
        logger.info(
            f"🌐 URL société mère identifiée: {eclaireur_report.parent_website or 'Non trouvée'}"
        )
        # NOUVEAU : Logger le secteur extrait
        if eclaireur_report.sector:
            logger.info(
                f"🏭 Secteur d'activité identifié: {eclaireur_report.sector}"
        )

        # Utiliser les résultats de l'Éclaireur pour la Phase 1
        target_company_name = eclaireur_report.parent_company_name
        target_website = eclaireur_report.parent_website or website
        # NOUVEAU : Utiliser le secteur extrait par l'Éclaireur (priorité sur le secteur passé en paramètre)
        target_sector = eclaireur_report.sector or sector

        logger.info(
            f"🎯 Cible Phase 1: {target_company_name} | URL: {target_website or 'Non disponible'} | Secteur: {target_sector or 'Non spécifié'}"
        )

        # ==========================================
        # PHASE 0.5 : ENRICHISSEUR SOCIÉTÉ MÈRE
        # ==========================================

        logger.info("📊 Phase 0.5 : Enrichisseur Société Mère (enrichissement informations générales)")
        phase0_5_start = time.time()

        # Démarrer les métriques pour la Phase 0.5
        phase0_5_metrics = None
        phase0_5_step = None
        if status_manager and session_id:
            phase0_5_metrics = metrics_collector.start_agent("📊 Enrichisseur", session_id)
            phase0_5_step = phase0_5_metrics.add_step("Enrichissement informations générales")
            phase0_5_step.status = MetricStatus.RUNNING
            # Notifier le démarrage via WebSocket
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="📊 Enrichisseur Société Mère",
                    status=AgentStatus.RUNNING,
                    progress=0.0,
                    message="Enrichissement des informations générales...",
                    current_step=1,
                    total_steps=4,
                    step_name="Phase 0.5 : Enrichisseur Société Mère"
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket Phase 0.5: {e}")

        parent_company_info = None
        try:
            parent_company_info = await run_enrichisseur_societe_mere(
                company_name=target_company_name,
                website=target_website,
                status_manager=status_manager,
                session_id=session_id
            )

            extraction_stats["phase_0_5_duration_seconds"] = time.time() - phase0_5_start
            
            # Finaliser les métriques de la Phase 0.5
            if status_manager and session_id and phase0_5_metrics and phase0_5_step:
                phase0_5_step.finish(MetricStatus.COMPLETED, {
                    "revenue": parent_company_info.revenue,
                    "employees": parent_company_info.employees,
                    "founded_year": parent_company_info.founded_year,
                    "confidence": parent_company_info.confidence,
                    "duration_seconds": extraction_stats["phase_0_5_duration_seconds"]
                })
                metrics_collector.finish_agent("📊 Enrichisseur", session_id, MetricStatus.COMPLETED)
                # Notifier la fin via WebSocket
                try:
                    await status_manager.update_agent_status_detailed(
                        session_id=session_id,
                        agent_name="📊 Enrichisseur Société Mère",
                        status=AgentStatus.COMPLETED,
                        progress=1.0,
                        message=f"Informations générales enrichies (confiance: {parent_company_info.confidence:.2f})",
                        current_step=1,
                        total_steps=4,
                        step_name="Phase 0.5 : Enrichisseur Société Mère",
                        performance_metrics={
                            "duration_seconds": extraction_stats["phase_0_5_duration_seconds"],
                            "confidence": parent_company_info.confidence
                        }
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Erreur notification WebSocket fin Phase 0.5: {e}")

            logger.info(
                f"✅ Phase 0.5 terminée: Informations générales enrichies "
                f"(confiance: {parent_company_info.confidence:.2f}, "
                f"CA: {parent_company_info.revenue or 'N/A'}, "
                f"Effectifs: {parent_company_info.employees or 'N/A'}, "
                f"Année: {parent_company_info.founded_year or 'N/A'}) "
                f"({extraction_stats['phase_0_5_duration_seconds']:.1f}s)"
            )
        except Exception as e:
            logger.error(f"❌ Erreur Phase 0.5 (Enrichisseur): {e}")
            extraction_stats["phase_0_5_duration_seconds"] = time.time() - phase0_5_start
            extraction_stats["phase_0_5_error"] = str(e)
            
            # Finaliser les métriques en erreur
            if status_manager and session_id and phase0_5_metrics and phase0_5_step:
                phase0_5_step.finish(MetricStatus.ERROR, {"error": str(e)})
                metrics_collector.finish_agent("📊 Enrichisseur", session_id, MetricStatus.ERROR, str(e))
                # Notifier l'erreur via WebSocket
                try:
                    await status_manager.update_agent_status_detailed(
                        session_id=session_id,
                        agent_name="📊 Enrichisseur Société Mère",
                        status=AgentStatus.ERROR,
                        progress=0.0,
                        message=f"Erreur: {str(e)}",
                        current_step=1,
                        total_steps=4,
                        step_name="Phase 0.5 : Enrichisseur Société Mère"
                    )
                except Exception as ws_error:
                    logger.warning(f"⚠️ Erreur notification WebSocket erreur Phase 0.5: {ws_error}")

    except Exception as e:
        logger.error(f"❌ Erreur Phase 0 (Éclaireur): {e}")
        extraction_stats["phase_0_duration_seconds"] = time.time() - phase0_start
        extraction_stats["phase_0_error"] = str(e)
        
        # Finaliser les métriques en erreur
        if status_manager and session_id and phase0_metrics and phase0_step:
            phase0_step.finish(MetricStatus.ERROR, {"error": str(e)})
            metrics_collector.finish_agent("🔍 Éclaireur", session_id, MetricStatus.ERROR, str(e))
            # Notifier l'erreur via WebSocket
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🔍 Éclaireur",
                    status=AgentStatus.ERROR,
                    progress=0.0,
                    message=f"Erreur: {str(e)}",
                    current_step=1,
                    total_steps=4,
                    step_name="Phase 0 : Éclaireur"
                )
            except Exception as ws_error:
                logger.warning(f"⚠️ Erreur notification WebSocket erreur Phase 0: {ws_error}")
        
        # En cas d'erreur, utiliser l'input original
        target_company_name = company_name
        target_website = website
        target_sector = sector  # Utiliser le secteur passé en paramètre si erreur

    # ==========================================
    # PHASE 1 : CARTOGRAPHE MINIMAL
    # ==========================================

    logger.info(f"📍 Phase 1 : Cartographe Minimal (cible: {target_company_name})")
    phase1_start = time.time()

    # Démarrer les métriques pour la Phase 1
    phase1_metrics = None
    phase1_step = None
    if status_manager and session_id:
        phase1_metrics = metrics_collector.start_agent("📍 Cartographe Minimal", session_id)
        phase1_step = phase1_metrics.add_step("Identification des entités")
        phase1_step.status = MetricStatus.RUNNING
        # Notifier le démarrage via WebSocket
        try:
            await status_manager.update_agent_status_detailed(
                session_id=session_id,
                agent_name="📍 Cartographe Minimal",
                status="running",
                progress=0.0,
                message="Identification des entités liées...",
                current_step=2,
                total_steps=4,
                step_name="Phase 1 : Cartographe Minimal"
            )
        except Exception as e:
            logger.warning(f"⚠️ Erreur notification WebSocket Phase 1: {e}")

    try:
        minimal_mapping = await run_cartographe_minimal(
            company_name=target_company_name,
            website=target_website,
            sector=target_sector,  # NOUVEAU : Utiliser le secteur extrait par l'Éclaireur
            context=context,
            use_cache=use_cache,
            status_manager=status_manager,  # NOUVEAU
            session_id=session_id  # NOUVEAU
        )

        extraction_stats["phase_1_duration_seconds"] = time.time() - phase1_start
        
        # Finaliser les métriques de la Phase 1
        if status_manager and session_id and phase1_metrics and phase1_step:
            phase1_step.finish(MetricStatus.COMPLETED, {
                "entities_identified": minimal_mapping.total_found,
                "duration_seconds": extraction_stats["phase_1_duration_seconds"],
                "search_strategy": minimal_mapping.search_strategy
            })
            metrics_collector.finish_agent("📍 Cartographe Minimal", session_id, MetricStatus.COMPLETED)
            # Notifier la fin via WebSocket
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="📍 Cartographe Minimal",
                    status=AgentStatus.COMPLETED,
                    progress=1.0,
                    message=f"{minimal_mapping.total_found} entités identifiées",
                    current_step=2,
                    total_steps=4,
                    step_name="Phase 1 : Cartographe Minimal",
                    performance_metrics={
                        "duration_seconds": extraction_stats["phase_1_duration_seconds"],
                        "entities_identified": minimal_mapping.total_found
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket fin Phase 1: {e}")
        extraction_stats["entities_identified"] = minimal_mapping.total_found

        logger.info(
            f"✅ Phase 1 terminée: {minimal_mapping.total_found} entités identifiées "
            f"({extraction_stats['phase_1_duration_seconds']:.1f}s)"
        )

        # Vérification : au moins 1 entité trouvée
        if minimal_mapping.total_found == 0:
            logger.warning(f"⚠️ Aucune entité trouvée pour {company_name}")
            extraction_stats["total_duration_seconds"] = time.time() - start_time

            return HierarchicalExtractionReport(
                company_name=company_name,
                minimal_mapping=minimal_mapping,
                detailed_entities=[],
                extraction_stats=extraction_stats
            )

        # ==========================================
        # PHASE 2 : EXTRACTION DÉTAILLÉE PARALLÈLE
        # ==========================================

        logger.info(f"🔬 Phase 2 : Extraction parallèle ({len(minimal_mapping.entities_identified)} entités)")
        logger.info(f"⚙️ Rate limiting: {max_parallel} extractions simultanées max")
        phase2_start = time.time()

        # Démarrer les métriques pour la Phase 2
        phase2_metrics = None
        phase2_step = None
        if status_manager and session_id:
            phase2_metrics = metrics_collector.start_agent("🔬 Extracteur Détaillé", session_id)
            phase2_step = phase2_metrics.add_step(f"Extraction parallèle ({len(minimal_mapping.entities_identified)} entités)")
            phase2_step.status = MetricStatus.RUNNING
            # Notifier le démarrage via WebSocket
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🔬 Extracteur Détaillé",
                    status=AgentStatus.RUNNING,
                    progress=0.0,
                    message=f"Extraction en cours de {len(minimal_mapping.entities_identified)} entités...",
                    current_step=4,
                    total_steps=4,
                    step_name="Phase 2 : Extracteur Détaillé"
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket Phase 2: {e}")

        # Création du semaphore pour rate limiting
        semaphore = asyncio.Semaphore(max_parallel)

        # Lancement des extractions en parallèle
        extraction_tasks = [
            extract_entity_with_timeout(
                entity_ref=entity,
                parent_company=company_name,
                semaphore=semaphore,
                timeout=EXTRACTION_TIMEOUT,
                status_manager=status_manager,  # NOUVEAU
                session_id=session_id  # NOUVEAU
            )
            for entity in minimal_mapping.entities_identified
        ]

        # Exécution parallèle avec gather
        detailed_entities_raw = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Filtrage des résultats (None = erreur/timeout, Exception = erreur capturée)
        detailed_entities: List[DetailedEntityInfo] = []
        for i, entity in enumerate(detailed_entities_raw):
            if isinstance(entity, Exception):
                logger.error(f"❌ Exception lors de l'extraction de l'entité {i+1}: {entity}")
                continue
            if entity is not None and isinstance(entity, DetailedEntityInfo):
                detailed_entities.append(entity)
            else:
                logger.warning(f"⚠️ Résultat invalide pour l'entité {i+1}: {type(entity)}")

        extraction_stats["phase_2_duration_seconds"] = time.time() - phase2_start
        extraction_stats["entities_extracted"] = len(detailed_entities)
        
        # Compter les succès : confidence > 0.5 (succès partiel ou complet)
        # confidence <= 0.5 = échec ou données insuffisantes
        extraction_stats["extraction_success_count"] = sum(
            1 for e in detailed_entities if e.confidence > 0.5
        )
        extraction_stats["extraction_partial_count"] = sum(
            1 for e in detailed_entities if 0.3 < e.confidence <= 0.5
        )
        extraction_stats["extraction_failure_count"] = sum(
            1 for e in detailed_entities if e.confidence <= 0.3
        )
        extraction_stats["extraction_error_count"] = (
            len(minimal_mapping.entities_identified) - len(detailed_entities)
        )

        # Finaliser les métriques de la Phase 2
        if status_manager and session_id and phase2_metrics and phase2_step:
            phase2_step.finish(MetricStatus.COMPLETED, {
                "entities_extracted": len(detailed_entities),
                "entities_total": len(minimal_mapping.entities_identified),
                "success_count": extraction_stats["extraction_success_count"],
                "duration_seconds": extraction_stats["phase_2_duration_seconds"]
            })
            metrics_collector.finish_agent("🔬 Extracteur Détaillé", session_id, MetricStatus.COMPLETED)
            # Notifier la fin via WebSocket
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🔬 Extracteur Détaillé",
                    status=AgentStatus.COMPLETED,
                    progress=1.0,
                    message=f"{len(detailed_entities)}/{len(minimal_mapping.entities_identified)} extractions réussies",
                    current_step=4,
                    total_steps=4,
                    step_name="Phase 2 : Extracteur Détaillé",
                    performance_metrics={
                        "duration_seconds": extraction_stats["phase_2_duration_seconds"],
                        "entities_extracted": len(detailed_entities),
                        "success_count": extraction_stats["extraction_success_count"]
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket fin Phase 2: {e}")

        logger.info(
            f"✅ Phase 2 terminée: {len(detailed_entities)}/{len(minimal_mapping.entities_identified)} "
            f"extractions réussies ({extraction_stats['phase_2_duration_seconds']:.1f}s)"
        )

        # ==========================================
        # CONSOLIDATION
        # ==========================================

        extraction_stats["total_duration_seconds"] = time.time() - start_time

        report = HierarchicalExtractionReport(
            company_name=company_name,
            minimal_mapping=minimal_mapping,
            detailed_entities=detailed_entities,
            extraction_stats=extraction_stats,
            parent_company_info=parent_company_info
        )

        logger.info(f"🎉 Extraction hiérarchique terminée: {company_name}")
        logger.info(report.summary())

        return report

    except Exception as e:
        logger.error(f"❌ Erreur orchestration hiérarchique: {e}")
        extraction_stats["total_duration_seconds"] = time.time() - start_time
        extraction_stats["error"] = str(e)

        # Retour d'un rapport d'erreur
        return HierarchicalExtractionReport(
            company_name=company_name,
            minimal_mapping=MinimalMappingReport(
                entities_identified=[],
                total_found=0,
                search_strategy="gpt-4o-search",
                sources=[SourceRef(
                    title="Erreur d'extraction",
                    url="https://error.local",
                    accessibility="broken"
                )],
                methodology_notes=[f"❌ Erreur: {str(e)}"]
            ),
            detailed_entities=[],
            extraction_stats=extraction_stats,
            parent_company_info=None
        )


