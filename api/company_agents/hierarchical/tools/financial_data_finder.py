"""
Outil Financial Data Finder

Trouve les données financières (CA, effectifs, année création) d'une société mère.

Modèle : gpt-4.1-mini avec web_search_preview
"""

import os
import logging
from typing import Optional, Dict, Any
import asyncio

from agents import function_tool
from openai import OpenAI

from company_agents.common.tools.json_parser_helper import parse_json_response
from company_agents.common.context import get_session_context
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker

logger = logging.getLogger(__name__)

# Client OpenAI (initialisation paresseuse)
_client = None

def get_client():
    """Initialise le client OpenAI de manière paresseuse."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY non définie")
            return None
        _client = OpenAI(api_key=api_key)
    return _client


@function_tool
async def financial_data_finder(
    company_name: str,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    Trouve les données financières (CA, effectifs, année création).

    Args:
        company_name: Nom de la société mère
        website: Site web connu (optionnel, utilisé pour guider la recherche)

    Returns:
        Dict avec revenue, employees, founded_year, sources
    """
    logger.info(f"💰 Recherche données financières: {company_name}")

    try:
        # Construire la requête avec stratégies de recherche spécifiques
        query_parts = [f"Chiffre d'affaires, effectifs et année de création de {company_name}"]
        
        if website:
            # Construire des URLs spécifiques à chercher
            base_url = website.rstrip('/')
            query_parts.append(
                f"Recherche PRIORITAIREMENT sur le site web officiel: {website}\n"
                f"- Pages à consulter en priorité (dans cet ordre):\n"
                f"  1. {base_url}/about ou {base_url}/about-us ou {base_url}/qui-sommes-nous\n"
                f"  2. {base_url}/company ou {base_url}/entreprise\n"
                f"  3. {base_url}/annual-report ou {base_url}/rapport-annuel\n"
                f"  4. {base_url}/investors ou {base_url}/investisseurs\n"
                f"  5. {base_url}/contact ou {base_url}/contactez-nous\n"
                f"- Si ces pages n'existent pas, chercher dans le footer, mentions légales, ou page d'accueil"
            )

        query = "\n".join(query_parts)

        client = get_client()
        if not client:
            return {"error": "Client OpenAI non configuré"}

        system_prompt = """Tu es un expert en recherche de données financières d'entreprises.

**MISSION** :
Trouver le chiffre d'affaires, les effectifs et l'année de création d'une société mère.

**STRATÉGIE DE RECHERCHE** :
1. Si un site web est fourni, commence PAR TOUJOURS par chercher sur ce site officiel
2. Consulte les pages prioritaires mentionnées dans la requête (About, Company, Annual Report, Investors)
3. Si le site officiel ne contient pas les informations, cherche dans :
   - Registres officiels (Infogreffe, Companies House, North Data selon le pays)
   - Bases de données corporatives (LinkedIn Company, Bloomberg, Orbis)
   - Rapports annuels publics
   - Articles de presse financière fiables
4. LIMITE : Maximum 3-5 recherches web pour éviter les coûts excessifs
5. Analyse en profondeur chaque résultat avant de faire une nouvelle recherche

**FORMAT DE SORTIE JSON STRICT** :
Tu DOIS retourner UNIQUEMENT un objet JSON valide, sans texte avant ou après. Format exact :

{
  "revenue": "CA en format texte (ex: '2.5 milliards EUR', '500M USD', '1.2B €') ou null",
  "employees": "Effectif en format texte (ex: '5000 employés', '10K employees', '~3000 personnes') ou null",
  "founded_year": 1990 ou null,
  "sources": ["URL1", "URL2"]
}

**RÈGLES STRICTES** :
- Retourne UNIQUEMENT le JSON, sans texte explicatif
- Pas de markdown, pas de code blocks, juste le JSON brut
- Si tu ne trouves pas l'information, retourne null pour les champs manquants
- JAMAIS inventer de données financières
- Les sources sont les URLs où tu as trouvé les informations (minimum 1 source si données trouvées)
- Pour l'année de création, retourne uniquement l'année (nombre entier entre 1800 et 2025)
- Pour le CA et effectifs, garde le format original trouvé (avec unités, devise si mentionnée)"""

        # Utiliser Responses API pour gpt-4.1-mini avec web_search
        full_input = f"{system_prompt}\n\n{query}"

        # Créer client synchrone pour responses.create (API synchrone uniquement)
        api_key = os.getenv("OPENAI_API_KEY")
        sync_client = OpenAI(api_key=api_key)

        # Appel dans thread pool pour ne pas bloquer
        def call_responses_api():
            return sync_client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "web_search_preview"}],
                input=full_input
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_responses_api)

        # Compter les web_search calls
        web_search_calls = 0
        web_search_items_seen = set()
        raw_result = None

        if hasattr(response, 'output') and response.output:
            for item in response.output:
                item_id = id(item)
                is_web_search = False

                if hasattr(item, 'type'):
                    if item.type == 'web_search':
                        is_web_search = True
                    elif 'web_search' in str(item.type).lower():
                        is_web_search = True

                if not is_web_search:
                    item_type_name = type(item).__name__.lower()
                    if 'web_search' in item_type_name or 'websearch' in item_type_name:
                        is_web_search = True

                if is_web_search and item_id not in web_search_items_seen:
                    web_search_calls += 1
                    web_search_items_seen.add(item_id)
                    logger.debug(f"🔍 [financial_data_finder] Web_search call détecté: type={getattr(item, 'type', 'N/A')}, class={type(item).__name__}")

                # Extraire le message de sortie - plusieurs stratégies de fallback
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        text_parts = []
                        for content_item in item.content:
                            if hasattr(content_item, 'type'):
                                if content_item.type == 'output_text':
                                    if hasattr(content_item, 'text'):
                                        text_parts.append(content_item.text)
                                elif content_item.type == 'text':
                                    if hasattr(content_item, 'text'):
                                        text_parts.append(content_item.text)
                                # Fallback: essayer d'accéder directement au texte
                                elif hasattr(content_item, 'text'):
                                    text_parts.append(content_item.text)
                        if text_parts:
                            raw_result = '\n'.join(text_parts)
                # Fallback 1: attribut text direct
                elif hasattr(item, 'text') and not raw_result:
                    raw_result = item.text
                # Fallback 2: attribut content direct (string)
                elif hasattr(item, 'content') and isinstance(item.content, str) and not raw_result:
                    raw_result = item.content
                # Fallback 3: attribut message si disponible
                elif hasattr(item, 'message') and not raw_result:
                    if isinstance(item.message, str):
                        raw_result = item.message
                    elif hasattr(item.message, 'content'):
                        raw_result = str(item.message.content)

        if web_search_calls > 0:
            logger.info(f"🔍 [financial_data_finder] Total: {web_search_calls} web_search call(s) pour {company_name}")

        # Tracking des tokens
        try:
            session_id = get_session_context()
            
            usage = response.usage
            if usage:
                input_tokens = getattr(usage, 'input_tokens', None) or getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', None) or getattr(usage, 'completion_tokens', 0)

                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name="financial_data_finder",
                    model="gpt-4.1-mini",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    web_search_calls=web_search_calls
                )
        except Exception as e:
            logger.warning(f"⚠️ Erreur tracking tokens financial_data_finder: {e}")

        # Si pas de résultat trouvé, essayer d'autres attributs (fallback)
        if not raw_result:
            # Essayer plusieurs attributs possibles de la réponse
            fallback_attrs = ['output_text', 'text', 'content', 'message', 'response_text', 'result']
            for attr in fallback_attrs:
                if hasattr(response, attr):
                    attr_value = getattr(response, attr)
                    if attr_value:
                        if isinstance(attr_value, str):
                            raw_result = attr_value
                            logger.debug(f"✅ Résultat extrait depuis response.{attr}")
                            break
                        elif isinstance(attr_value, list) and len(attr_value) > 0:
                            # Si c'est une liste, essayer d'extraire le texte du premier élément
                            first_item = attr_value[0]
                            if hasattr(first_item, 'text'):
                                raw_result = first_item.text
                                logger.debug(f"✅ Résultat extrait depuis response.{attr}[0].text")
                                break
                            elif isinstance(first_item, str):
                                raw_result = first_item
                                logger.debug(f"✅ Résultat extrait depuis response.{attr}[0]")
                                break
            
            if not raw_result:
                # Log détaillé pour debug
                logger.error(f"❌ Impossible d'extraire le résultat pour {company_name}")
                logger.error(f"   Type de response: {type(response)}")
                logger.error(f"   Attributs disponibles: {dir(response)}")
                if hasattr(response, 'output'):
                    logger.error(f"   response.output type: {type(response.output)}")
                    logger.error(f"   response.output length: {len(response.output) if hasattr(response.output, '__len__') else 'N/A'}")
                return {
                    "revenue": None,
                    "employees": None,
                    "founded_year": None,
                    "sources": []
                }

        logger.info(f"✅ Données financières trouvées: {company_name}")

        # Parser le JSON
        parsed = parse_json_response(raw_result, "financial_data_finder")

        # Vérifier si erreur de parsing
        if "error" in parsed and "raw_content" in parsed:
            if any(k in parsed for k in ['revenue', 'employees', 'founded_year']):
                logger.info(f"✅ Données financières extraites depuis texte formaté")
                return {
                    "revenue": parsed.get("revenue"),
                    "employees": parsed.get("employees"),
                    "founded_year": parsed.get("founded_year"),
                    "sources": parsed.get("sources", [])
                }
            else:
                logger.warning(f"⚠️ Erreur parsing données financières: {parsed.get('error')}")
                return {
                    "revenue": None,
                    "employees": None,
                    "founded_year": None,
                    "sources": []
                }

        # Retourner les données parsées
        return {
            "revenue": parsed.get("revenue"),
            "employees": parsed.get("employees"),
            "founded_year": parsed.get("founded_year"),
            "sources": parsed.get("sources", [])
        }

    except Exception as e:
        logger.error(f"❌ Erreur recherche données financières: {e}")
        return {"error": str(e)}

