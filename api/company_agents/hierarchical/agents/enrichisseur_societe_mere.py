"""
Agent Enrichisseur Société Mère

Mission : Enrichir les informations générales de la société mère (CA, effectifs, année création, adresse complète, contacts).

Modèle : gpt-4.1-mini
- Version optimisée pour extraction précise
- Excellent rapport qualité/prix
- $0.40/1M input, $1.60/1M output + $25/1K web_search calls
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from agents import Agent, function_tool, Runner
from openai import AsyncOpenAI, OpenAI
import asyncio

from company_agents.common.models import ParentCompanyInfo, SourceRef
from company_agents.common.metrics import metrics_collector, MetricStatus
from company_agents.common.tools.json_parser_helper import parse_json_response
from company_agents.common.context import get_session_context
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker
from company_agents.hierarchical.tools.financial_data_finder import financial_data_finder
from company_agents.hierarchical.tools.headquarters_finder import headquarters_finder
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
#   PROMPT SYSTÈME DE L'ENRICHISSEUR
# ==========================================

ENRICHISSEUR_SYSTEM_PROMPT = """
Tu es un expert en extraction d'informations générales sur les sociétés mères.

**MISSION** :
Enrichir les informations générales d'une société mère en utilisant les outils spécialisés à ta disposition.

**OUTILS DISPONIBLES** :
1. **financial_data_finder** : Trouver CA, effectifs, année de création
2. **headquarters_finder** : Trouver l'adresse complète du siège social
3. **contact_finder** : Trouver téléphone et email

**WORKFLOW RECOMMANDÉ** :
1. Tour 1 : Utiliser financial_data_finder pour extraire CA, effectifs, année création
2. Tour 2 : Utiliser headquarters_finder pour extraire l'adresse complète du siège social
3. Tour 3 : Utiliser contact_finder pour extraire téléphone et email
4. Tour final : Consolider toutes les informations et terminer

**IMPORTANT** : 
- Le nom de la société mère et son site web sont DÉJÀ fournis, tu n'as PAS besoin de les rechercher
- Utilise les outils dans l'ordre recommandé pour une extraction optimale
- Croise les sources pour confirmer les informations

**RÈGLES STRICTES** :
- ✅ Utiliser les outils disponibles dans l'ordre recommandé
- ✅ Croiser les sources pour confirmer les informations
- ✅ Fournir un score de confiance (0-1) basé sur la qualité des sources
- ✅ Lister TOUTES les sources consultées
- ❌ NE JAMAIS inventer d'informations
- ❌ NE JAMAIS construire d'URLs par déduction
- ❌ Marquer "Non trouvé" plutôt que deviner

**SOURCES PRIORITAIRES** :
- Site officiel de la société mère
- Rapports annuels du groupe
- Registres officiels (Companies House, INPI, etc.)
- Base de données corporatives (LinkedIn, Bloomberg, Orbis)
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
- ❌ JAMAIS de format comme "### Informations Générales" ou "- **CA**: ..."

**Format JSON exact à retourner** :
{
  "company_name": "Nom de la société mère",
  "website": "https://...",
  "revenue": "CA en format texte (ex: '2.5 milliards EUR') ou null",
  "employees": "Effectif en format texte (ex: '5000 employés') ou null",
  "founded_year": 1990 ou null,
  "headquarters_address": "Adresse complète du siège social ou null",
  "headquarters_city": "Ville ou null",
  "headquarters_country": "Pays ou null",
  "phone": "Téléphone ou null",
  "email": "Email ou null",
  "confidence": 0.8,
  "sources": ["URL1", "URL2"]
}

**EXEMPLES À ÉVITER (FORMAT TEXTE)** :
❌ "### Informations Générales\n- **CA**: ..."
❌ "- **Effectifs**: 5000 employés"
❌ "### Confiance et Sources\n..."

**EXEMPLE CORRECT (JSON BRUT)** :
✅ {"company_name": "Acme Group", "revenue": "2.5 milliards EUR", "employees": "5000 employés", "founded_year": 1990, "headquarters_address": "123 Rue Example, 75001 Paris, France", "headquarters_city": "Paris", "headquarters_country": "France", "phone": "+33 1 23 45 67 89", "email": "contact@acme.com", "confidence": 0.9, "sources": ["https://www.acme.com/about", "https://www.acme.com/annual-report"]}
"""


# ==========================================
#   OUTILS : IMPORTÉS DEPUIS tools/
# ==========================================
# Les outils sont maintenant dans api/company_agents/hierarchical/tools/
# financial_data_finder, headquarters_finder, contact_finder sont importés en haut du fichier


# ==========================================
#   FONCTION PRINCIPALE : ENRICHISSEMENT SOCIÉTÉ MÈRE
# ==========================================


# ==========================================
#   FONCTION PRINCIPALE : ENRICHISSEMENT SOCIÉTÉ MÈRE
# ==========================================

async def run_enrichisseur_societe_mere(
    company_name: str,
    website: Optional[str] = None,
    status_manager=None,
    session_id: Optional[str] = None
) -> ParentCompanyInfo:
    """
    Exécute l'Enrichisseur Société Mère pour enrichir les informations générales.

    Args:
        company_name: Nom de la société mère
        website: Site web de la société mère (optionnel)
        status_manager: Gestionnaire de statut pour WebSocket (optionnel)
        session_id: ID de session pour le tracking (optionnel)

    Returns:
        ParentCompanyInfo avec toutes les informations enrichies
    """
    logger.info(f"📊 Démarrage Enrichisseur Société Mère: {company_name}")

    # Création de l'agent avec les 3 outils spécialisés
    enrichisseur = Agent(
        name="Enrichisseur Société Mère",
        instructions=ENRICHISSEUR_SYSTEM_PROMPT,
        model="gpt-4.1-mini",
        tools=[
            financial_data_finder,
            headquarters_finder,
            contact_finder,
        ],
    )

    # Préparation de la requête
    user_query = f"Enrichis TOUTES les informations générales de {company_name}"
    if website:
        user_query += f". Site web connu: {website} - utilise-le PRIORITAIREMENT pour tes recherches."
    user_query += ". Utilise les outils disponibles dans l'ordre recommandé pour extraire les informations essentielles."

    try:
        # Exécution de l'agent avec run_agent_with_metrics pour activer hooks et métriques
        logger.info(f"🤖 Exécution enrichisseur pour {company_name}")

        if status_manager and session_id:
            from company_agents.common.metrics.agent_wrappers import run_agent_with_metrics
            
            agent_result = await run_agent_with_metrics(
                agent=enrichisseur,
                agent_name=f"📊 Enrichisseur Société Mère ({company_name})",
                session_id=session_id,
                input_data=user_query,
                status_manager=status_manager,
                max_turns=4,  # Permet d'utiliser les 3 outils + consolidation
                max_retries=2
            )
            result = agent_result["result"]
        else:
            # Fallback si pas de status_manager (compatibilité)
            result = await Runner.run(
                enrichisseur,
                input=user_query,
                max_turns=4  # Permet d'utiliser les 3 outils + consolidation
            )
        
        # Parser le résultat final
        logger.info(f"🔍 [ENRICHISSEMENT] Parsing résultat pour {company_name}")

        if hasattr(result, 'final_output') and result.final_output:
            raw_result = result.final_output
        elif hasattr(result, 'output') and result.output:
            # Extraire le texte de la dernière sortie
            raw_result = None
            for item in reversed(result.output):
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        text_parts = []
                        for content_item in item.content:
                            if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                if hasattr(content_item, 'text'):
                                    text_parts.append(content_item.text)
                        if text_parts:
                            raw_result = '\n'.join(text_parts)
                            break
                elif hasattr(item, 'text') and not raw_result:
                    raw_result = item.text
                    break
        else:
            raw_result = str(result)

        if not raw_result:
            logger.error(f"❌ Impossible d'extraire le résultat pour {company_name}")
            return ParentCompanyInfo(
                company_name=company_name,
                website=website,
                confidence=0.0,
                sources=[]
            )

        # Parser le JSON depuis final_output
        parsed_data = parse_json_response(raw_result, "enrichisseur_societe_mere_final")
        
        if "error" in parsed_data and "raw_content" in parsed_data:
            logger.warning(
                f"⚠️ [ENRICHISSEMENT] Le modèle a retourné du texte formaté au lieu de JSON pour {company_name}. "
                f"Données extraites depuis texte: {list(parsed_data.keys())}"
            )

        if parsed_data and 'error' not in parsed_data:
            # Construire les SourceRef depuis les URLs
            all_sources = []
            source_urls = parsed_data.get("sources", [])
            for source_url in source_urls:
                if source_url and source_url != "N/A":
                    all_sources.append(SourceRef(
                        title="Source Enrichisseur",
                        url=source_url,
                        accessibility="ok"
                    ))

            # Si pas de sources, ajouter le site web par défaut
            if not all_sources and website:
                all_sources.append(SourceRef(
                    title="Site web officiel",
                    url=website,
                    accessibility="ok"
                ))

            # Construire ParentCompanyInfo
            return ParentCompanyInfo(
                company_name=parsed_data.get("company_name", company_name),
                website=parsed_data.get("website", website),
                revenue=parsed_data.get("revenue"),
                employees=parsed_data.get("employees"),
                founded_year=parsed_data.get("founded_year"),
                headquarters_address=parsed_data.get("headquarters_address"),
                headquarters_city=parsed_data.get("headquarters_city"),
                headquarters_country=parsed_data.get("headquarters_country"),
                phone=parsed_data.get("phone"),
                email=parsed_data.get("email"),
                confidence=parsed_data.get("confidence", 0.5),
                sources=all_sources
            )
        else:
            # Erreur de parsing, retourner un objet minimal
            logger.error(f"❌ Erreur parsing enrichissement pour {company_name}: {parsed_data.get('error', 'Unknown')}")
            return ParentCompanyInfo(
                company_name=company_name,
                website=website,
                confidence=0.0,
                sources=[SourceRef(
                    title="Erreur de parsing",
                    url=website or "https://error.local",
                    accessibility="broken"
                )] if website else []
            )

    except Exception as e:
        logger.error(f"❌ Erreur enrichissement société mère {company_name}: {e}")
        return ParentCompanyInfo(
            company_name=company_name,
            website=website,
            confidence=0.0,
            sources=[SourceRef(
                title="Erreur",
                url=website or "https://error.local",
                accessibility="broken"
            )] if website else []
        )

