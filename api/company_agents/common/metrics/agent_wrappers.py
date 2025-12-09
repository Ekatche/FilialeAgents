"""
Wrappers avec métriques pour tous les agents
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from agents import Runner
from agents.exceptions import OutputGuardrailTripwireTriggered

from .metrics_collector import metrics_collector, MetricStatus, AgentMetrics
from .real_time_tracker import RealTimeTracker
from .agent_hooks import RealtimeAgentHooks

logger = logging.getLogger(__name__)


async def run_agent_with_metrics(
    agent,
    agent_name: str,
    session_id: str,
    input_data: str,
    status_manager,
    max_turns: int = 3,
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Wrapper générique pour exécuter un agent avec métriques temps réel et retry.
    
    Args:
        agent: Agent à exécuter
        agent_name: Nom de l'agent pour les métriques
        session_id: ID de session
        input_data: Données d'entrée
        status_manager: Gestionnaire de statut pour WebSocket
        max_turns: Nombre maximum de tours
        max_retries: Nombre maximum de retries en cas de guardrail (default: 2)
        
    Returns:
        Dict avec résultat et métriques
    """
    # Démarrer les métriques
    agent_metrics = metrics_collector.start_agent(agent_name, session_id)
    real_time_tracker = RealTimeTracker(status_manager)
    
    # Attacher les hooks de cycle de vie pour notifier le WebSocket
    agent.hooks = RealtimeAgentHooks(status_manager, session_id, agent_name)
    
    # Démarrer le suivi temps réel en arrière-plan (ne sera jamais annulé jusqu'à la fin)
    tracking_task = asyncio.create_task(
        real_time_tracker.track_agent_realtime(agent_name, session_id, agent_metrics)
    )
    
    try:
        # Étape 1: Initialisation
        init_step = agent_metrics.add_step("Initialisation")
        init_step.finish(MetricStatus.COMPLETED)
        
        # Étape 2: Exécution de l'agent avec retry automatique
        exec_step = agent_metrics.add_step("Exécution")
        exec_step.status = MetricStatus.RUNNING
        
        result = None
        last_exception = None
        
        # Boucle de retry (max_retries + 1 tentatives)
        for attempt in range(max_retries + 1):
            try:
                # Préparer l'input avec correction si retry
                current_input = input_data
                
                if attempt > 0:
                    # Étape de retry
                    retry_step = agent_metrics.add_step(f"Correction/Retry-{attempt}")
                    retry_step.status = MetricStatus.RUNNING
                    
                    # Extraire les infos du guardrail précédent
                    guardrail_info = {}
                    dead_links = []
                    
                    if last_exception:
                        logger.info(f"🔍 [DEBUG] Exception type: {type(last_exception).__name__}")
                        
                        # L'exception OutputGuardrailTripwireTriggered a un attribut "guardrail_result"
                        if hasattr(last_exception, "guardrail_result"):
                            result = last_exception.guardrail_result
                            
                            # OutputGuardrailResult a un attribut "output" qui contient output_info
                            if hasattr(result, "output") and isinstance(result.output, dict):
                                guardrail_info = result.output
                                logger.info(f"✅ Guardrail output trouvé: {guardrail_info.keys()}")
                                dead_links = guardrail_info.get("removed_dead_links", [])
                                if dead_links:
                                    logger.info(f"✅ Dead links extracted: {dead_links}")
                                else:
                                    logger.warning(f"⚠️ Pas de removed_dead_links dans: {guardrail_info}")
                    
                    # Ajouter un hint de correction progressif avec URLs détaillées
                    if attempt == 1:
                        # Afficher TOUS les liens morts avec détails
                        if dead_links:
                            dead_links_details = "\n".join([f"  - {url}" for url in dead_links])
                            dead_hint = f"\n\n⚠️ URLs NON ACCESSIBLES détectées:\n{dead_links_details}\n\nRemplace chaque URL ci-dessus par une page on-domain accessible (contact/about/home)."
                        else:
                            dead_hint = ""
                        
                        correction_hint = (
                            f"\n\n[CORRECTION_HINT]: Corrige la sortie pour respecter: "
                            f"1) target_domain présent si détectable; 2) ≥1 source on-domain valide; "
                            f"3) exclure/remplacer toute URL morte par une page on-domain valide.{dead_hint}"
                        )
                    else:
                        # Deuxième tentative : rappel sans les URLs spécifiques
                        correction_hint = (
                            f"\n\n[CORRECTION_HINT_FINAL]: CRITIQUE - Vérifie l'accessibilité de TOUTES les URLs. "
                            f"Reste strictement on-domain. Si page légale 404, remplace par contact/about/home après vérification."
                        )
                    
                    current_input = f"{input_data}{correction_hint}"
                
                # Exécution de l'agent (le tracking continue en parallèle)
                result = await Runner.run(agent, input=current_input, max_turns=max_turns)

                # Capturer les tokens utilisés si disponibles (selon la doc OpenAI)
                if hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                    try:
                        usage = result.context_wrapper.usage

                        # Récupérer le nom du modèle (pas l'objet)
                        model_obj = getattr(agent, 'model', None)

                        # Essayer plusieurs méthodes pour extraire le nom du modèle
                        model_name = 'unknown'
                        if model_obj:
                            # Méthode 1 : Attribut 'name'
                            if hasattr(model_obj, 'name'):
                                model_name = model_obj.name
                            # Méthode 2 : Attribut 'model'
                            elif hasattr(model_obj, 'model'):
                                model_name = model_obj.model
                            # Méthode 3 : Attribut 'model_name'
                            elif hasattr(model_obj, 'model_name'):
                                model_name = model_obj.model_name
                            # Méthode 4 : Méthode get_model_name()
                            elif hasattr(model_obj, 'get_model_name'):
                                model_name = model_obj.get_model_name()
                            # Méthode 5 : Pour OpenAI models, chercher dans config
                            elif hasattr(model_obj, '_model'):
                                model_name = model_obj._model
                            # Méthode 6 : Convertir en string et extraire
                            else:
                                str_repr = str(model_obj)
                                logger.info(f"🔍 [DEBUG] Model string representation: {str_repr}")
                                # Si ça contient "model=" ou "name=", l'extraire
                                if 'model=' in str_repr:
                                    model_name = str_repr.split('model=')[1].split(',')[0].strip().strip("'\"")
                                else:
                                    model_name = str_repr

                        # Vérifier que usage existe et a les attributs nécessaires
                        if usage and hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                            token_info = {
                                "model": model_name,
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                                "total_tokens": getattr(usage, 'total_tokens', usage.input_tokens + usage.output_tokens)
                            }
                        else:
                            # Fallback si usage n'a pas les attributs attendus
                            token_info = {
                                "model": model_name,
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "total_tokens": 0
                            }

                        # Stocker dans les métriques de performance
                        agent_metrics.performance_metrics["tokens"] = token_info
                        
                        # Envoyer au ToolTokensTracker pour les coûts réels
                        try:
                            from .tool_tokens_tracker import ToolTokensTracker
                            ToolTokensTracker.add_tool_usage(
                                session_id=session_id,
                                tool_name=agent_name,
                                model=model_name,
                                input_tokens=token_info['input_tokens'],
                                output_tokens=token_info['output_tokens']
                            )
                            logger.info(f"🔧 Tokens envoyés au tracker pour {agent_name}")
                        except Exception as tracker_error:
                            logger.warning(f"⚠️ Erreur envoi tracker pour {agent_name}: {tracker_error}")

                        logger.info(
                            f"💰 Tokens capturés pour {agent_name}: "
                            f"{token_info['input_tokens']} in + {token_info['output_tokens']} out = "
                            f"{token_info['total_tokens']} total (modèle: {model_name})"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Impossible de capturer les tokens pour {agent_name}: {e}")
                else:
                    logger.warning(f"⚠️ Pas de données d'usage disponibles pour {agent_name}")

                # Si succès, sortir de la boucle
                if attempt > 0:
                    retry_step.finish(MetricStatus.COMPLETED, {"retry_success": True})
                break
                
            except OutputGuardrailTripwireTriggered as trip:
                last_exception = trip
                
                # Marquer l'étape en échec (sauf si dernière tentative)
                if attempt == 0:
                    exec_step.finish(MetricStatus.ERROR, {"error": "guardrail_tripwire", "attempt": attempt + 1})
                elif attempt < max_retries:
                    retry_step.finish(MetricStatus.ERROR, {"error": "guardrail_tripwire", "attempt": attempt + 1})
                else:
                    # Dernière tentative échouée
                    retry_step.finish(MetricStatus.ERROR, {"error": "guardrail_final_failure", "attempt": attempt + 1})
                    raise  # Remonter l'exception
                
                logger.warning(f"⚠️ Guardrail déclenché (tentative {attempt + 1}/{max_retries + 1}) pour {agent_name}")
        
        # Marquer l'exécution comme réussie si on est sorti de la boucle
        if attempt == 0:
            exec_step.finish(MetricStatus.COMPLETED)
        
        # Étape 3: Traitement des résultats
        process_step = agent_metrics.add_step("Traitement des résultats")
        process_step.status = MetricStatus.PROCESSING
        
        # Analyser les résultats
        if hasattr(result, 'final_output') and result.final_output:
            # Métriques de qualité basiques
            agent_metrics.quality_metrics = {
                "has_output": True,
                "output_type": type(result.final_output).__name__,
                "confidence_score": 0.8  # Score par défaut
            }
            
            # Métriques de performance (MISE À JOUR au lieu d'écrasement pour garder "tokens")
            agent_metrics.performance_metrics.update({
                "total_duration_ms": agent_metrics.total_duration_ms,
                "steps_completed": len(agent_metrics.steps),
                "success_rate": 1.0
            })
            
            process_step.finish(MetricStatus.COMPLETED, {
                "output_processed": True,
                "output_type": type(result.final_output).__name__
            })
            
            # Finalisation
            final_step = agent_metrics.add_step("Finalisation")
            final_step.finish(MetricStatus.COMPLETED)
            
            # Terminer les métriques
            agent_metrics.finish(MetricStatus.COMPLETED)
            
        else:
            process_step.finish(MetricStatus.ERROR, {"error": "Pas de résultat final"})
            agent_metrics.finish(MetricStatus.ERROR, "Pas de résultat final")
        
        # Annuler le suivi temps réel
        tracking_task.cancel()
        try:
            await tracking_task
        except asyncio.CancelledError:
            pass
        
        # Envoyer les métriques finales
        await real_time_tracker.send_final_metrics(agent_name, session_id, agent_metrics)
        
        return {
            "result": result,
            "status": "success" if agent_metrics.status == MetricStatus.COMPLETED else "error",
            "duration_ms": agent_metrics.total_duration_ms,
            "metrics": agent_metrics.to_dict()
        }
        
    except Exception as e:
        # Marquer l'étape en erreur
        current_step = agent_metrics.get_current_step()
        if current_step:
            current_step.finish(MetricStatus.ERROR, {"error": str(e)})
        
        agent_metrics.finish(MetricStatus.ERROR, str(e))
        
        # Annuler le suivi temps réel
        if 'tracking_task' in locals():
            tracking_task.cancel()
            try:
                await tracking_task
            except asyncio.CancelledError:
                pass
        
        # Envoyer les métriques finales
        await real_time_tracker.send_final_metrics(agent_name, session_id, agent_metrics)
        
        logger.error(f"❌ Erreur lors de l'exécution de {agent_name}: {str(e)}", exc_info=True)
        
        return {
            "result": None,
            "status": "error",
            "duration_ms": agent_metrics.total_duration_ms,
            "error": str(e),
            "metrics": agent_metrics.to_dict()
        }


# Les wrappers pour les agents legacy ont été supprimés car le code legacy a été retiré
# Ces fonctions ne sont plus nécessaires avec le système hiérarchique
