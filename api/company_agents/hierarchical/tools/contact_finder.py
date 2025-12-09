"""
Outil Contact Finder

Trouve les coordonnées de contact (téléphone, email) d'une entité.
Le website est fourni par le Cartographe Minimal et ne doit pas être extrait ici.

Modèle : gpt-4.1-mini avec web_search_preview
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
import asyncio
import re

from agents import function_tool
from openai import OpenAI

from company_agents.common.tools.json_parser_helper import parse_json_response
from company_agents.common.context import get_session_context
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker

logger = logging.getLogger(__name__)


def validate_entity_website_coherence(entity_name: str, website: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Valide la cohérence entre le nom de l'entité et le website fourni.
    
    Détecte les incohérences comme :
    - "FROMM Chile SA" avec website "https://www.fromm-pack.fr/" (Chile vs .fr)
    - "Company USA Inc" avec website "https://company.de" (USA vs .de)
    
    Returns:
        Tuple (is_coherent, warning_message)
        - is_coherent: True si cohérent, False si incohérence détectée
        - warning_message: Message d'avertissement si incohérence détectée
    """
    if not website:
        return True, None
    
    # Extraire le pays depuis le nom de l'entité (patterns communs)
    country_patterns = {
        r'\b(Chile|Chilean)\b': 'Chile',
        r'\b(USA|United States|US)\b': 'USA',
        r'\b(France|French|Français|Française)\b': 'France',
        r'\b(Germany|German|Deutschland|Deutsch)\b': 'Germany',
        r'\b(UK|United Kingdom|Britain|British)\b': 'UK',
        r'\b(Spain|Spanish|España|Espagnol)\b': 'Spain',
        r'\b(Italy|Italian|Italia|Italien)\b': 'Italy',
        r'\b(Netherlands|Dutch|Nederland|Holland)\b': 'Netherlands',
        r'\b(Belgium|Belgian|Belgique|Belge)\b': 'Belgium',
        r'\b(Switzerland|Swiss|Suisse|Schweiz)\b': 'Switzerland',
        r'\b(Canada|Canadian)\b': 'Canada',
        r'\b(Mexico|Mexican|México)\b': 'Mexico',
        r'\b(Brazil|Brazilian|Brasil)\b': 'Brazil',
        r'\b(Argentina|Argentine)\b': 'Argentina',
    }
    
    entity_country = None
    for pattern, country in country_patterns.items():
        if re.search(pattern, entity_name, re.IGNORECASE):
            entity_country = country
            break
    
    # Extraire le TLD du website
    tld_to_country = {
        '.fr': 'France',
        '.de': 'Germany',
        '.uk': 'UK',
        '.com': None,  # .com est international, pas de pays spécifique
        '.org': None,
        '.net': None,
        '.es': 'Spain',
        '.it': 'Italy',
        '.nl': 'Netherlands',
        '.be': 'Belgium',
        '.ch': 'Switzerland',
        '.ca': 'Canada',
        '.mx': 'Mexico',
        '.br': 'Brazil',
        '.ar': 'Argentina',
        '.cl': 'Chile',
        '.us': 'USA',
    }
    
    website_country = None
    for tld, country in tld_to_country.items():
        if tld in website.lower():
            website_country = country
            break
    
    # Vérifier la cohérence
    if entity_country and website_country:
        if entity_country != website_country:
            warning = (
                f"⚠️ INCOHÉRENCE DÉTECTÉE: L'entité '{entity_name}' mentionne le pays '{entity_country}' "
                f"mais le website '{website}' a un TLD correspondant à '{website_country}'. "
                f"Le website pourrait ne pas correspondre à cette entité spécifique."
            )
            logger.warning(warning)
            return False, warning
    
    return True, None

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
async def contact_finder(
    entity_name: str,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    Trouve les coordonnées de contact (téléphone, email).
    Le website est fourni par le Cartographe Minimal et ne doit pas être extrait ici.

    Args:
        entity_name: Nom légal de l'entité
        website: Site web connu (optionnel, utilisé uniquement pour guider la recherche)

    Returns:
        Dict avec phone, email, sources (sans website)
    """
    logger.info(f"📞 Recherche contacts: {entity_name}")

    try:
        # VALIDATION DE COHÉRENCE : Vérifier si le website correspond à l'entité
        is_coherent, coherence_warning = validate_entity_website_coherence(entity_name, website)
        
        if not is_coherent:
            logger.warning(f"⚠️ {coherence_warning}")
            # Ne pas utiliser le website si incohérence détectée
            website = None
        
        # Construire la requête avec stratégies de recherche spécifiques
        query_parts = [f"Coordonnées de contact de {entity_name} (téléphone, email)"]
        
        if website:
            # Construire des URLs spécifiques à chercher
            base_url = website.rstrip('/')
            query_parts.append(
                f"Recherche PRIORITAIREMENT sur le site web officiel: {website}\n"
                f"- Pages à consulter en priorité (dans cet ordre):\n"
                f"  1. {base_url}/contact ou {base_url}/contactez-nous ou {base_url}/contact-us\n"
                f"  2. {base_url}/contact/ ou {base_url}/contactez-nous/\n"
                f"  3. Footer du site (bas de page) - souvent contient téléphone et email\n"
                f"  4. {base_url}/about ou {base_url}/about-us ou {base_url}/qui-sommes-nous\n"
                f"  5. {base_url}/legal ou {base_url}/mentions-legales ou {base_url}/imprint\n"
                f"- Si ces pages n'existent pas, chercher dans le footer, mentions légales, ou page d'accueil"
            )
        else:
            # Si pas de website ou website incohérent, chercher directement l'entité
            query_parts.append(
                f"⚠️ IMPORTANT: Le site web n'est pas fourni ou ne correspond pas à cette entité spécifique.\n"
                f"Cherche les coordonnées de contact directement pour '{entity_name}' dans :\n"
                f"- Registres officiels (selon le pays mentionné dans le nom)\n"
                f"- Bases de données corporatives (LinkedIn Company)\n"
                f"- Pages jaunes / annuaires professionnels du pays concerné"
            )

        query = "\n".join(query_parts)

        client = get_client()
        if not client:
            return {"error": "Client OpenAI non configuré"}

        system_prompt = """Tu es un expert en recherche de contacts d'entreprises.

**MISSION** :
Trouver les coordonnées de contact d'une entité (téléphone, email).
⚠️ IMPORTANT : Le site web est déjà fourni par le Cartographe Minimal, ne PAS l'extraire ici.

**VALIDATION DE COHÉRENCE CRITIQUE** :
⚠️ AVANT de chercher sur un site web fourni, VÉRIFIER qu'il correspond bien à l'entité recherchée :
- Si l'entité mentionne un pays dans son nom (ex: "FROMM Chile SA", "Company USA Inc")
- ET que le website a un TLD correspondant à un autre pays (ex: .fr pour France, .de pour Allemagne)
- ALORS le website ne correspond probablement PAS à cette entité spécifique
- Dans ce cas, chercher directement l'entité par son nom dans les registres du pays mentionné

**STRATÉGIE DE RECHERCHE** :
1. Si un site web est fourni ET cohérent avec l'entité, commence PAR TOUJOURS par chercher sur ce site officiel
2. Si le site web n'est pas fourni OU incohérent, cherche directement l'entité par son nom dans :
   - Registres officiels du pays mentionné dans le nom (ex: Chile → registre chilien)
   - Bases de données corporatives (LinkedIn Company)
   - Pages jaunes / annuaires professionnels du pays concerné
3. Consulte les pages prioritaires mentionnées dans la requête (Contact, Footer, About, Mentions légales)
4. Le footer (bas de page) contient souvent téléphone et email
5. La page Contact est la source la plus fiable pour ces informations
6. LIMITE : Maximum 2-3 recherches web pour éviter les coûts excessifs
7. Analyse en profondeur chaque résultat avant de faire une nouvelle recherche
8. Si tu trouves des contacts sur un site qui ne correspond pas à l'entité (ex: site français pour entité chilienne), 
   RETOURNE null plutôt que des contacts incorrects

**FORMAT DE SORTIE JSON STRICT** :
Tu DOIS retourner UNIQUEMENT un objet JSON valide, sans texte avant ou après. Format exact :

{
  "phone": "Numéro de téléphone (ex: '+33 1 23 45 67 89' ou '+49 123 456789') ou null",
  "email": "Adresse email (ex: 'contact@company.com' ou 'info@company.com') ou null",
  "sources": ["URL1", "URL2"]
}

**RÈGLES STRICTES** :
- Retourne UNIQUEMENT le JSON, sans texte explicatif
- Pas de markdown, pas de code blocks, juste le JSON brut
- Si tu ne trouves pas l'information, retourne null pour les champs manquants
- JAMAIS inventer d'email ou de téléphone
- Ne PAS retourner de champ "website" (déjà fourni par le Cartographe Minimal)
- Les sources sont les URLs où tu as trouvé les informations (minimum 1 source si données trouvées)
- Pour le téléphone, inclure l'indicatif pays si disponible (ex: +33 pour France, +49 pour Allemagne)
- Pour l'email, utiliser le format exact trouvé (minuscules, avec @ et domaine complet)"""

        # Utiliser Responses API pour gpt-4.1-mini avec web_search
        # Combiner system prompt et query en un seul input
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

        # Compter les web_search calls depuis response.output (format Responses API)
        # IMPORTANT: Compter chaque appel UNE SEULE FOIS pour éviter les doublons
        web_search_calls = 0
        web_search_items_seen = set()
        raw_result = None

        if hasattr(response, 'output') and response.output:
            # Parcourir la liste pour trouver le message final et compter les web_search calls
            for item in response.output:
                # Identifier l'item de manière unique pour éviter les doublons
                item_id = id(item)

                # Compter les items de type web_search (une seule fois par item)
                is_web_search = False

                if hasattr(item, 'type'):
                    if item.type == 'web_search':
                        is_web_search = True
                    elif 'web_search' in str(item.type).lower():
                        is_web_search = True

                # Vérifier aussi le nom de la classe
                if not is_web_search:
                    item_type_name = type(item).__name__.lower()
                    if 'web_search' in item_type_name or 'websearch' in item_type_name:
                        is_web_search = True

                # Compter une seule fois par item unique
                if is_web_search and item_id not in web_search_items_seen:
                    web_search_calls += 1
                    web_search_items_seen.add(item_id)
                    logger.debug(f"🔍 [contact_finder] Web_search call détecté: type={getattr(item, 'type', 'N/A')}, class={type(item).__name__}")

                # Extraire le message de sortie - plusieurs stratégies de fallback
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        # Extraire le texte de chaque élément de contenu
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
            logger.info(f"🔍 [contact_finder] Total: {web_search_calls} web_search call(s) pour {entity_name}")

        # Tracking des tokens pour le calcul des coûts
        try:
            session_id = get_session_context()
            
            usage = response.usage
            if usage:
                # Support pour les deux formats: ancien (prompt_tokens/completion_tokens) et nouveau (input_tokens/output_tokens)
                input_tokens = getattr(usage, 'input_tokens', None) or getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', None) or getattr(usage, 'completion_tokens', 0)

                # Calcul du coût estimé pour logging
                estimated_token_cost = (input_tokens * 0.40 + output_tokens * 1.60) / 1_000_000
                estimated_search_cost = web_search_calls * 0.01
                estimated_total = estimated_token_cost + estimated_search_cost

                logger.info(
                    f"💰 [contact_finder] {entity_name}: Coût estimé: "
                    f"Tokens: ${estimated_token_cost:.6f}, "
                    f"Web search: ${estimated_search_cost:.4f}, "
                    f"Total: ${estimated_total:.6f}"
                )

                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name="contact_finder",
                    model="gpt-4.1-mini",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    web_search_calls=web_search_calls
                )
        except Exception as e:
            logger.warning(f"⚠️ Erreur tracking tokens contact_finder: {e}")

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
                logger.error(f"❌ Impossible d'extraire le résultat de la réponse pour {entity_name}")
                logger.error(f"   Type de response: {type(response)}")
                logger.error(f"   Attributs disponibles: {dir(response)}")
                if hasattr(response, 'output'):
                    logger.error(f"   response.output type: {type(response.output)}")
                    logger.error(f"   response.output length: {len(response.output) if hasattr(response.output, '__len__') else 'N/A'}")
                return {
                    "phone": None,
                    "email": None,
                    "sources": []
                }

        logger.info(f"✅ Contacts trouvés: {entity_name}")

        # Parser le JSON
        parsed = parse_json_response(raw_result, "contact_finder")

        # Vérifier si erreur de parsing (mais peut avoir des données extraites depuis texte)
        if "error" in parsed and "raw_content" in parsed:
            # Si on a extrait des données depuis le texte, les utiliser
            if any(k in parsed for k in ['phone', 'email']):
                logger.info(f"✅ Données contacts extraites depuis texte formaté")
                return {
                    "phone": parsed.get("phone"),
                    "email": parsed.get("email"),
                    "sources": parsed.get("sources", [])
                }
            else:
                logger.warning(f"⚠️ Erreur parsing contacts: {parsed.get('error')}")
                return {
                    "phone": None,
                    "email": None,
                    "sources": []
                }

        # Retourner les données parsées (sans website)
        return {
            "phone": parsed.get("phone"),
            "email": parsed.get("email"),
            "sources": parsed.get("sources", [])
        }

    except Exception as e:
        logger.error(f"❌ Erreur recherche contacts: {e}")
        return {"error": str(e)}

