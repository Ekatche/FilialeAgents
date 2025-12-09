"""
Outil Headquarters Finder

Trouve l'adresse complète du siège social d'une société mère.

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
async def headquarters_finder(
    company_name: str,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    Trouve l'adresse complète du siège social.

    Args:
        company_name: Nom de la société mère
        website: Site web connu (optionnel, utilisé pour guider la recherche)

    Returns:
        Dict avec headquarters_address, headquarters_city, headquarters_country, sources
    """
    logger.info(f"🏢 Recherche siège social: {company_name}")

    try:
        # Construire la requête avec stratégies de recherche spécifiques
        query_parts = [f"Adresse complète du siège social de {company_name} (adresse complète, ville, pays)"]
        
        if website:
            # Construire des URLs spécifiques à chercher
            base_url = website.rstrip('/')
            query_parts.append(
                f"Recherche PRIORITAIREMENT sur le site web officiel: {website}\n"
                f"- Pages à consulter en priorité (dans cet ordre):\n"
                f"  1. {base_url}/contact ou {base_url}/contactez-nous ou {base_url}/contact-us\n"
                f"  2. {base_url}/legal ou {base_url}/mentions-legales ou {base_url}/imprint ou {base_url}/impressum\n"
                f"  3. {base_url}/about ou {base_url}/about-us ou {base_url}/qui-sommes-nous\n"
                f"  4. Footer du site (bas de page) - souvent contient l'adresse du siège\n"
                f"  5. {base_url}/headquarters ou {base_url}/siège-social\n"
                f"- Si ces pages n'existent pas, chercher dans le footer, mentions légales, ou page d'accueil"
            )

        query = "\n".join(query_parts)

        client = get_client()
        if not client:
            return {"error": "Client OpenAI non configuré"}

        system_prompt = """Tu es un expert en recherche d'adresses de sièges sociaux d'entreprises.

**MISSION** :
Trouver l'adresse complète du siège social d'une société mère (adresse complète, ville, pays).

**STRATÉGIE DE RECHERCHE** :
1. Si un site web est fourni, commence PAR TOUJOURS par chercher sur ce site officiel
2. Consulte les pages prioritaires mentionnées dans la requête (Contact, Mentions légales, About, Footer)
3. Le footer (bas de page) contient souvent l'adresse complète du siège social
4. Les mentions légales / Legal Notice / Impressum contiennent généralement l'adresse officielle
5. Si le site officiel ne contient pas les informations, cherche dans :
   - Registres officiels (Infogreffe, Companies House, North Data selon le pays)
   - Bases de données corporatives (LinkedIn Company, Bloomberg)
   - Rapports annuels publics
6. LIMITE : Maximum 3-5 recherches web pour éviter les coûts excessifs
7. Analyse en profondeur chaque résultat avant de faire une nouvelle recherche

**FORMAT DE SORTIE JSON STRICT** :
Tu DOIS retourner UNIQUEMENT un objet JSON valide, sans texte avant ou après. Format exact :

{
  "headquarters_address": "Adresse complète (ex: '123 Rue Example, 75001 Paris, France') ou null",
  "headquarters_city": "Ville (ex: 'Paris') ou null",
  "headquarters_country": "Pays (ex: 'France') ou null",
  "sources": ["URL1", "URL2"]
}

**RÈGLES STRICTES** :
- Retourne UNIQUEMENT le JSON, sans texte explicatif
- Pas de markdown, pas de code blocks, juste le JSON brut
- Si tu ne trouves pas l'information, retourne null pour les champs manquants
- JAMAIS inventer d'adresse
- Les sources sont les URLs où tu as trouvé les informations (minimum 1 source si données trouvées)
- Pour l'adresse complète, inclure le numéro, nom de rue, code postal, ville et pays si disponibles
- Pour le pays, utiliser le nom complet en français ou anglais (ex: 'France', 'Germany', 'United Kingdom')"""

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
                    logger.debug(f"🔍 [headquarters_finder] Web_search call détecté: type={getattr(item, 'type', 'N/A')}, class={type(item).__name__}")

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
            logger.info(f"🔍 [headquarters_finder] Total: {web_search_calls} web_search call(s) pour {company_name}")

        # Tracking des tokens
        try:
            session_id = get_session_context()
            
            usage = response.usage
            if usage:
                input_tokens = getattr(usage, 'input_tokens', None) or getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', None) or getattr(usage, 'completion_tokens', 0)

                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name="headquarters_finder",
                    model="gpt-4.1-mini",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    web_search_calls=web_search_calls
                )
        except Exception as e:
            logger.warning(f"⚠️ Erreur tracking tokens headquarters_finder: {e}")

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
                    "headquarters_address": None,
                    "headquarters_city": None,
                    "headquarters_country": None,
                    "sources": []
                }

        logger.info(f"✅ Siège social trouvé: {company_name}")

        # Parser le JSON
        parsed = parse_json_response(raw_result, "headquarters_finder")

        # Vérifier si erreur de parsing
        if "error" in parsed and "raw_content" in parsed:
            if any(k in parsed for k in ['headquarters_address', 'headquarters_city', 'headquarters_country']):
                logger.info(f"✅ Adresse extraite depuis texte formaté")
                return {
                    "headquarters_address": parsed.get("headquarters_address"),
                    "headquarters_city": parsed.get("headquarters_city"),
                    "headquarters_country": parsed.get("headquarters_country"),
                    "sources": parsed.get("sources", [])
                }
            else:
                logger.warning(f"⚠️ Erreur parsing adresse: {parsed.get('error')}")
                return {
                    "headquarters_address": None,
                    "headquarters_city": None,
                    "headquarters_country": None,
                    "sources": []
                }

        # Retourner les données parsées
        return {
            "headquarters_address": parsed.get("headquarters_address"),
            "headquarters_city": parsed.get("headquarters_city"),
            "headquarters_country": parsed.get("headquarters_country"),
            "sources": parsed.get("sources", [])
        }

    except Exception as e:
        logger.error(f"❌ Erreur recherche siège social: {e}")
        return {"error": str(e)}

