"""
Agent Extracteur Détaillé (Phase 2)

Mission : Extraire les informations essentielles d'une entité identifiée par le Cartographe Minimal.
Utilise l'outil contact_finder pour extraire téléphone et email.

Modèle : gpt-4.1-mini
- Version optimisée pour extraction précise
- Excellent rapport qualité/prix
- $0.40/1M input, $1.60/1M output + $25/1K web_search calls
- Le pays est fourni par le Cartographe Minimal (pas besoin d'extraire)
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from agents import Agent, function_tool, Runner
from openai import AsyncOpenAI, OpenAI
import asyncio

from company_agents.common.models import DetailedEntityInfo, EntityRef, SourceRef
from company_agents.common.metrics import metrics_collector, MetricStatus
from company_agents.common.tools.json_parser_helper import parse_json_response
from company_agents.common.context import get_session_context
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker
from company_agents.hierarchical.tools.contact_finder import contact_finder

logger = logging.getLogger(__name__)

# Client OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("⚠️ OPENAI_API_KEY non définie")
    client = None
else:
    client = AsyncOpenAI(api_key=api_key)


# ==========================================
#   PROMPT SYSTÈME DE L'EXTRACTEUR DÉTAILLÉ
# ==========================================


EXTRACTEUR_DETAILLE_SYSTEM_PROMPT = """
Tu es un expert en extraction d'informations détaillées sur les entités corporatives.

**MISSION** :
Extraire les informations essentielles d'une entité (filiale, participation, holding)
en utilisant les outils spécialisés à ta disposition.

**OUTILS DISPONIBLES** :
1. **contact_finder** : Trouver téléphone, email (le site web et le pays sont déjà fournis par le Cartographe Minimal)

**WORKFLOW RECOMMANDÉ** :
1. Tour 1 : Utiliser contact_finder pour extraire téléphone et email
2. Tour final : Consolider toutes les informations et terminer

**IMPORTANT** : 
- Le pays est DÉJÀ fourni par le Cartographe Minimal, tu n'as PAS besoin de le rechercher
- Utilise uniquement contact_finder pour extraire les coordonnées de contact
- ⚠️ VALIDATION DE COHÉRENCE : Si un site web est fourni mais ne correspond pas à l'entité (ex: entité chilienne avec site français), 
  NE PAS utiliser ce site web. Cherche directement l'entité par son nom dans les registres du pays concerné.

**RÈGLES STRICTES** :
- ✅ Utiliser l'outil contact_finder disponible
- ✅ Vérifier la cohérence entre le nom de l'entité et le website fourni avant utilisation
- ✅ Si incohérence détectée, chercher directement l'entité par son nom (pas via le website)
- ✅ Croiser les sources pour confirmer les informations
- ✅ Fournir un score de confiance (0-1) basé sur la qualité des sources
- ✅ Lister TOUTES les sources consultées
- ❌ NE JAMAIS inventer d'informations
- ❌ NE JAMAIS construire d'URLs par déduction
- ❌ NE JAMAIS utiliser un website qui ne correspond pas à l'entité recherchée
- ❌ Marquer "Non trouvé" plutôt que deviner
- ❌ NE PAS chercher le pays (déjà fourni)

**SOURCES PRIORITAIRES** :
- Site officiel de l'entité
- Registres officiels (Companies House, INPI, etc.)
- Rapports annuels du groupe
- Base de données corporatives (LinkedIn, Bloomberg)
- Articles de presse fiables

**CONFIANCE** :
- 0.9-1.0 : Trouvé sur site officiel ou registre
- 0.7-0.89 : Trouvé dans rapport annuel ou base de données fiable
- 0.5-0.69 : Trouvé dans presse ou source secondaire
- <0.5 : Information incertaine (à marquer comme telle)

**FORMAT DE SORTIE JSON STRICT - OBLIGATOIRE** :
⚠️ TU DOIS RETOURNER UNIQUEMENT UN OBJET JSON VALIDE, JAMAIS DE TEXTE FORMATÉ.

**RÈGLE ABSOLUE** :
- ✅ Retourne UNIQUEMENT du JSON brut, sans texte avant ou après
- ❌ JAMAIS de texte formaté avec des tirets, des titres, des sections
- ❌ JAMAIS de format markdown ou texte libre
- ❌ JAMAIS de format comme "### Coordonnées de Contact" ou "- **Longitude**: ..."

**Format JSON exact à retourner** :
{
  "phone": "Téléphone ou null",
  "email": "Email ou null",
  "legal_status": "Active|Dissolved|Liquidation|Unknown|null",
  "confidence": 0.7,
  "sources": ["URL1", "URL2"]
}

**EXEMPLES À ÉVITER (FORMAT TEXTE)** :
❌ "### Coordonnées de Contact\n- **Téléphone**: ..."
❌ "- **Email**: contact@example.com"
❌ "### Confiance et Sources\n- **Confiance**: 0.7"

**EXEMPLE CORRECT (JSON BRUT)** :
✅ {"phone": "+33 1 23 45 67 89", "email": "contact@example.com", "legal_status": "Active", "confidence": 0.8, "sources": ["https://example.com/contact"]}

Si tu ne trouves pas une information, utilise `null` dans le JSON, pas "Non trouvé" en texte.
"""


# ==========================================
#   OUTILS : IMPORTÉS DEPUIS tools/
# ==========================================
# Les outils sont maintenant dans api/company_agents/hierarchical/tools/
# contact_finder est importé en haut du fichier


# ==========================================
#   FONCTION PRINCIPALE : EXTRACTION DÉTAILLÉE
# ==========================================

async def run_extracteur_detaille(
    entity_ref: EntityRef,
    parent_company: Optional[str] = None,
    status_manager=None,  # NOUVEAU
    session_id: Optional[str] = None  # NOUVEAU
) -> DetailedEntityInfo:
    """
    Exécute l'Extracteur Détaillé pour une entité.

    Args:
        entity_ref: Référence à l'entité (depuis Cartographe Minimal)
        parent_company: Nom de la société mère (optionnel)
        status_manager: Gestionnaire de statut pour WebSocket (optionnel)
        session_id: ID de session pour le tracking (optionnel)

    Returns:
        DetailedEntityInfo avec toutes les informations extraites
    """
    logger.info(f"🔬 Démarrage Extracteur Détaillé: {entity_ref.legal_name}")

    # Création de l'agent avec contact_finder uniquement
    extracteur = Agent(
        name="Extracteur Détaillé",
        instructions=EXTRACTEUR_DETAILLE_SYSTEM_PROMPT,
        model="gpt-4.1-mini",  # Version optimisée (80% moins cher que gpt-4o)
        tools=[
            contact_finder,
        ],
    )

    # VALIDATION DE COHÉRENCE : Vérifier si le website correspond à l'entité
    from company_agents.hierarchical.tools.contact_finder import validate_entity_website_coherence
    
    validated_website = entity_ref.website
    if entity_ref.website:
        is_coherent, coherence_warning = validate_entity_website_coherence(
            entity_ref.legal_name, 
            entity_ref.website
        )
        if not is_coherent:
            logger.warning(f"⚠️ [Extracteur Détaillé] {coherence_warning}")
            logger.warning(f"   Website '{entity_ref.website}' ignoré pour {entity_ref.legal_name}")
            validated_website = None  # Ne pas utiliser le website si incohérent
    
    # Préparation de la requête
    user_query = f"Extrais TOUTES les informations détaillées de {entity_ref.legal_name}"
    if entity_ref.country:
        user_query += f" ({entity_ref.country})"
    if parent_company:
        user_query += f", filiale de {parent_company}"
    if validated_website:
        user_query += f". Site web connu: {validated_website} - utilise-le PRIORITAIREMENT pour tes recherches."
    elif entity_ref.website and not validated_website:
        user_query += f". ⚠️ ATTENTION: Le site web fourni ({entity_ref.website}) ne correspond probablement pas à cette entité spécifique. Cherche directement l'entité par son nom."

    user_query += ". Utilise les outils disponibles pour extraire les informations essentielles."

    try:
        # Exécution de l'agent avec run_agent_with_metrics pour activer hooks et métriques
        logger.info(f"🤖 Exécution extracteur pour {entity_ref.legal_name}")

        # NOUVEAU : Utiliser run_agent_with_metrics au lieu de Runner.run
        if status_manager and session_id:
            from company_agents.common.metrics.agent_wrappers import run_agent_with_metrics
            
            agent_result = await run_agent_with_metrics(
                agent=extracteur,
                agent_name=f"🔬 Extracteur Détaillé ({entity_ref.legal_name})",
                session_id=session_id,
                input_data=user_query,
                status_manager=status_manager,
                max_turns=3,
                max_retries=2
            )
            result = agent_result["result"]
        else:
            # Fallback si pas de status_manager (compatibilité)
            result = await Runner.run(
                extracteur,
                input=user_query,
                max_turns=3  # Réduit car seulement 1 outil maintenant (contact_finder)
            )
        
        # Debug: inspecter la structure du résultat (seulement en mode DEBUG)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"🔍 Type du résultat: {type(result).__name__}")

            # Vérifier les attributs principaux
            if hasattr(result, 'context_wrapper'):
                logger.debug(f"🔍 context_wrapper disponible")
                if hasattr(result.context_wrapper, 'context') and hasattr(result.context_wrapper.context, 'messages'):
                    msg_count = len(result.context_wrapper.context.messages)
                    logger.debug(f"🔍 {msg_count} message(s) dans le contexte")

            if hasattr(result, 'final_output') and result.final_output:
                logger.debug(f"🔍 final_output disponible ({len(result.final_output)} chars)")
        
        # Tracking des tokens de l'agent principal
        try:
            session_id = get_session_context()

            if hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                usage = result.context_wrapper.usage
                model_name = "gpt-4.1-mini"  # Modèle de l'agent extracteur

                # Compter les web_search calls de l'agent principal (si présents)
                web_search_calls = 0
                web_search_items_seen = set()

                # Vérifier dans result.output si disponible (format Responses API)
                if hasattr(result, 'output') and result.output:
                    for item in result.output:
                        item_id = id(item)
                        is_web_search = False

                        if hasattr(item, 'type'):
                            if item.type == 'web_search' or 'web_search' in str(item.type).lower():
                                is_web_search = True

                        if not is_web_search:
                            item_type_name = type(item).__name__.lower()
                            if 'web_search' in item_type_name or 'websearch' in item_type_name:
                                is_web_search = True

                        if is_web_search and item_id not in web_search_items_seen:
                            web_search_calls += 1
                            web_search_items_seen.add(item_id)

                # Fallback: vérifier dans context_wrapper.context.messages (format Agents SDK)
                elif hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'context'):
                    ctx = result.context_wrapper.context
                    if hasattr(ctx, 'messages'):
                        for msg in ctx.messages:
                            msg_id = id(msg)
                            if hasattr(msg, 'type') and 'web_search' in str(msg.type).lower():
                                if msg_id not in web_search_items_seen:
                                    web_search_calls += 1
                                    web_search_items_seen.add(msg_id)

                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name="extracteur_detaille",
                    model=model_name,
                    input_tokens=getattr(usage, 'input_tokens', 0),
                    output_tokens=getattr(usage, 'output_tokens', 0),
                    web_search_calls=web_search_calls  # ✅ Ajout du comptage
                )

                if web_search_calls > 0:
                    logger.info(f"🔍 [extracteur_detaille] {web_search_calls} web_search call(s) détecté(s) pour {entity_ref.legal_name}")
                logger.debug(f"💰 Tokens trackés pour extracteur_detaille principal")
        except Exception as e:
            logger.warning(f"⚠️ Erreur tracking tokens extracteur_detaille: {e}")

        # Parser le résultat final aggregé par le modèle
        # address_data = {}  # SUPPRIMÉ : Le pays vient de entity_ref.country
        contact_data = {}
        status_data = {}
        all_sources = []

        # NOUVELLE APPROCHE: Parser result.final_output directement
        # Le modèle agrège tous les résultats des tools dans sa réponse finale
        if hasattr(result, 'final_output') and result.final_output:
            logger.info(f"✅ [EXTRACTION] Parsing final_output pour {entity_ref.legal_name}")

            # Logger le contenu brut pour debug si nécessaire
            if len(result.final_output) > 1000:
                logger.debug(f"📋 [EXTRACTION] final_output (premiers 500 caractères): {result.final_output[:500]}")
            else:
                logger.debug(f"📋 [EXTRACTION] final_output complet: {result.final_output}")

            # Parser le JSON depuis final_output (peut contenir des markdown blocks ou texte formaté)
            parsed_data = parse_json_response(result.final_output, "extracteur_detaille_final")
            
            # Si le parsing a échoué mais qu'on a extrait des données depuis le texte, logger un warning
            if "error" in parsed_data and "raw_content" in parsed_data:
                logger.warning(
                    f"⚠️ [EXTRACTION] Le modèle a retourné du texte formaté au lieu de JSON pour {entity_ref.legal_name}. "
                    f"Données extraites depuis texte: {list(parsed_data.keys())}"
                )

            if parsed_data and 'error' not in parsed_data:
                logger.info(f"✅ [EXTRACTION] Données extraites: {list(parsed_data.keys())}")

                # Extraire les données de contact (peut être 'contact', 'contact_info', ou flat)
                if 'contact' in parsed_data and isinstance(parsed_data['contact'], dict):
                    # Format nested avec 'contact'
                    contact_data = parsed_data['contact']
                    logger.info(f"📞 [CONTACT] Contact extrait (nested): phone={contact_data.get('phone', 'N/A')}")
                elif 'contact_info' in parsed_data and isinstance(parsed_data['contact_info'], dict):
                    # Format nested avec 'contact_info'
                    contact_data = parsed_data['contact_info']
                    logger.info(f"📞 [CONTACT] Contact extrait (nested): phone={contact_data.get('phone', 'N/A')}")
                else:
                    # Format flat - extraire directement depuis parsed_data
                    if 'phone' in parsed_data or 'email' in parsed_data:
                        contact_data = {
                            'phone': parsed_data.get('phone'),
                            'email': parsed_data.get('email')
                        }
                        logger.info(f"📞 [CONTACT] Contact extrait (flat): phone={contact_data.get('phone', 'N/A')}")

                # Extraire les sources
                if 'sources' in parsed_data and isinstance(parsed_data['sources'], list):
                    all_sources = parsed_data['sources']
                    logger.info(f"🔗 [SOURCES] {len(all_sources)} sources trouvées")

                # Utiliser le confidence score du modèle si disponible
                if 'confidence_score' in parsed_data:
                    confidence_override = parsed_data['confidence_score']
                    logger.info(f"🎯 [CONFIDENCE] Score du modèle: {confidence_override}")
            else:
                logger.warning(f"⚠️ [EXTRACTION] Échec du parsing de final_output pour {entity_ref.legal_name}")
        else:
            logger.warning(f"⚠️ [EXTRACTION] Pas de final_output disponible pour {entity_ref.legal_name}")
        
        # Log des données extraites pour debug
        if contact_data:
            logger.info(f"📞 Contacts extraits: phone={contact_data.get('phone', 'N/A')}, email={contact_data.get('email', 'N/A')}")
        else:
            logger.warning(f"⚠️ Aucune donnée de contact extraite pour {entity_ref.legal_name}")

        # Calculer le score de confiance basé sur la quantité de données trouvées
        data_quality_score = 0
        has_any_data = False
        
        # Le pays est déjà fourni par le Cartographe Minimal, pas besoin de le vérifier
        has_country = entity_ref.country is not None
        if has_country:
            # Le pays est fourni, on ne compte pas ça dans le score car c'est déjà acquis
            has_any_data = True
        
        # Vérifier les données de contact
        has_contact = contact_data.get("phone") or contact_data.get("email")
        if has_contact:
            data_quality_score += 0.5  # Augmenté car c'est maintenant le seul critère d'extraction
            has_any_data = True
        
        # Vérifier le statut légal
        has_status = status_data.get("legal_status") and status_data["legal_status"] != "Unknown"
        if has_status:
            data_quality_score += 0.3
            has_any_data = True
        
        # Vérifier les sources
        unique_sources = list(set(all_sources))
        has_sources = len(unique_sources) > 0
        if has_sources:
            data_quality_score += 0.2
            has_any_data = True

        # Calculer la confiance : si aucune donnée n'est trouvée, confidence = 0.3 (échec)
        # Si des données sont trouvées, utiliser le score calculé (min 0.5, max 1.0)
        if not has_any_data:
            # Aucune donnée trouvée = échec d'extraction
            confidence = 0.3
            logger.warning(f"⚠️ Aucune donnée extraite pour {entity_ref.legal_name}, confidence = 0.3")
        else:
            # Des données ont été trouvées, utiliser le score (min 0.5 pour refléter un succès partiel)
            confidence = max(0.5, min(1.0, data_quality_score))
            logger.info(f"✅ Données extraites pour {entity_ref.legal_name}, confidence = {confidence:.2f}")

        # Utiliser directement le pays du Cartographe Minimal (pas besoin d'extraire)
        country = entity_ref.country if entity_ref.country else None

        # Convertir sources en SourceRef objects (dédupliquer) - seulement si des sources valides existent
        source_refs = []
        if has_sources:
            source_refs = [
                SourceRef(title="Source de recherche", url=url, accessibility="ok") 
                for url in unique_sources[:10] 
                if url and url != "N/A" and url != "https://error.local"
            ]

        # Construire DetailedEntityInfo avec données réelles - ne pas inclure les champs vides
        # Note: entity_type a une valeur par défaut "subsidiary" dans le modèle
        # Le website vient du Cartographe Minimal (entity_ref.website), utiliser validated_website si validation effectuée
        website_to_use = validated_website if 'validated_website' in locals() else entity_ref.website
        
        detailed_info = DetailedEntityInfo(
            legal_name=entity_ref.legal_name,
            entity_type="subsidiary",  # Valeur par défaut, peut être omis car défini dans le modèle
            website=website_to_use,  # Website du Cartographe Minimal (validé si validation effectuée)
            country=country,  # Uniquement le pays, pas d'adresse complète
            legal_status=status_data.get("legal_status") if has_status else None,
            sector=None,  # Non extrait (secteur de la société mère suffit)
            activities=None,  # Non extrait (secteur de la société mère suffit)
            employees=None,  # Pas extrait par les outils actuels
            revenue=None,  # Pas extrait par les outils actuels
            ownership_details=None,  # Non extrait (le fait qu'elle soit filiale suffit)
            phone=contact_data.get("phone") if contact_data.get("phone") else None,
            email=contact_data.get("email") if contact_data.get("email") else None,
            confidence=confidence,
            sources=source_refs  # Liste vide si aucune source, pas de source d'erreur
            # Note: extraction_date retiré - une seule date dans extraction_stats au niveau global
        )

        logger.info(f"✅ Extraction détaillée terminée: {entity_ref.legal_name}")
        return detailed_info

    except Exception as e:
        logger.error(f"❌ Erreur Extracteur Détaillé: {e}")

        # Retour d'une entité minimale en cas d'erreur
        return DetailedEntityInfo(
            legal_name=entity_ref.legal_name,
            entity_type="subsidiary",  # Valeur par défaut, peut être omis car défini dans le modèle
            website=entity_ref.website,  # Conserver le website même en cas d'erreur
            country=entity_ref.country if entity_ref.country else None,  # Uniquement le pays
            confidence=0.0,
            sources=[]  # Liste vide, sera filtrée dans la réponse
            # Note: extraction_date retiré - une seule date dans extraction_stats au niveau global
        )
