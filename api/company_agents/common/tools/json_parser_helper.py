"""
Helper pour parser le JSON depuis les réponses GPT qui peuvent contenir des markdown code blocks.
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def extract_json_from_markdown(text: str) -> str:
    """
    Extrait le JSON d'un texte qui peut contenir des markdown code blocks.

    Gère les formats :
    - ```json\n{...}\n```
    - ```\n{...}\n```
    - {...} (JSON pur)

    Args:
        text: Texte brut pouvant contenir du JSON

    Returns:
        JSON nettoyé (string)
    """
    if not text:
        return text

    # Strip whitespace
    text = text.strip()

    # Pattern 1: ```json ... ```
    pattern1 = r'```json\s*(.*?)\s*```'
    match = re.search(pattern1, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Pattern 2: ``` ... ```
    pattern2 = r'```\s*(.*?)\s*```'
    match = re.search(pattern2, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Pattern 3: JSON nu (commence par { ou [)
    if text.startswith('{') or text.startswith('['):
        return text

    # Si rien ne matche, retourner tel quel
    return text


def extract_info_from_text(text: str, tool_name: str) -> dict:
    """
    Extrait les informations depuis un texte formaté si le JSON parsing échoue.
    Utilise des regex pour trouver les patterns communs.
    """
    result = {}
    
    # Patterns pour extraire les informations (basés sur le format réel du modèle)
    patterns = {
        'phone': [
            r'(?:Téléphone|Phone|Tel\.?|Tél\.?|Tél|Tel)[\s:]+([+\d\s\-\(\)\.]+)',
            r'\*\*Téléphone\*\*[\s:]+([+\d\s\-\(\)\.]+)',  # Format markdown **Téléphone**: ...
            r'\+?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}',
            r'\+?\d{2,3}[\s\-\.]?\d{1,2}[\s\-\.]?\d{2}[\s\-\.]?\d{2}[\s\-\.]?\d{2}[\s\-\.]?\d{2}',  # Format FR: +33 1 23 45 67 89
        ],
        'email': [
            r'(?:Email|E-mail|Mail|E-mail|Courriel|Contact)[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'\*\*Email\*\*[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Format markdown **Email**: ...
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'contact@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Format contact@company.com
            r'info@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Format info@company.com
        ],
        'website': [
            r'(?:Site web|Website|Site|Web)[\s:]+(https?://[^\s\n,]+|www\.[^\s\n,]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'https?://[^\s\n,]+',
            r'www\.[^\s\n,]+',
            r'\b[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # Domaine simple (ergopack.com)
        ],
        'revenue': [
            r'(?:Chiffre d\'affaires|CA|Revenue|Turnover|Revenus)[\s:]+([^\n,]+?)(?:\n|,|$)',
            r'\*\*Chiffre d\'affaires\*\*[\s:]+([^\n,]+?)',
            r'\*\*CA\*\*[\s:]+([^\n,]+?)',
            r'(?:CA|Revenue)[\s:]+([0-9.,\s]+(?:millions?|milliards?|M|B|EUR|USD|€|\$)?)',
            r'([0-9.,\s]+(?:millions?|milliards?|M|B)\s*(?:EUR|USD|€|\$|euros?|dollars?)?)',
        ],
        'employees': [
            r'(?:Effectifs|Employees|Employés|Staff|Personnel)[\s:]+([^\n,]+?)(?:\n|,|$)',
            r'\*\*Effectifs\*\*[\s:]+([^\n,]+?)',
            r'\*\*Employees\*\*[\s:]+([^\n,]+?)',
            r'([0-9.,\s]+(?:employés?|employees?|personnes?|people))',
            r'([0-9.,]+)\s*(?:employés?|employees?|personnes?|people)',
        ],
        'founded_year': [
            r'(?:Année de création|Founded|Créé en|Créée en|Since|Depuis)[\s:]+([0-9]{4})',
            r'\*\*Année de création\*\*[\s:]+([0-9]{4})',
            r'\*\*Founded\*\*[\s:]+([0-9]{4})',
            r'(?:depuis|since|founded in)\s+([0-9]{4})',
            r'\b(19[0-9]{2}|20[0-2][0-9])\b',  # Année entre 1900 et 2029
        ],
        'headquarters_address': [
            r'(?:Adresse complète|Adresse|Address|Adresse du siège|Headquarters)[\s:]+([^\n]+?)(?:\n|$)',
            r'\*\*Adresse\*\*[\s:]+([^\n]+?)',
            r'\*\*Address\*\*[\s:]+([^\n]+?)',
            r'([A-Z][a-zA-Z\s,]+(?:[0-9]{5}|[0-9]{4})[^\n]+)',  # Adresse avec code postal
            r'([0-9]+[,\s]+[A-Z][a-zA-Z\s,]+(?:[0-9]{5}|[0-9]{4})[^\n]+)',  # Numéro + rue + code postal
        ],
        'headquarters_city': [
            r'(?:Ville|City)[\s:]+([A-Z][a-zA-Z\s\-]+)',
            r'\*\*Ville\*\*[\s:]+([A-Z][a-zA-Z\s\-]+)',  # Format markdown **Ville**: ...
            r'\*\*City\*\*[\s:]+([A-Z][a-zA-Z\s\-]+)',
            r'\b([A-Z][a-zA-Z]+)\s*\([^)]+\)',  # Ex: "Lauingen (Donau)"
            r',\s*([A-Z][a-zA-Z\s\-]+)\s*(?:[0-9]{5}|[0-9]{4})',  # Ville avant code postal
        ],
        'headquarters_country': [
            r'(?:Pays|Country)[\s:]+([A-Z][a-zA-Z\s]+)',
            r'\*\*Pays\*\*[\s:]+([A-Z][a-zA-Z\s]+)',  # Format markdown **Pays**: ...
            r'\*\*Country\*\*[\s:]+([A-Z][a-zA-Z\s]+)',
            r',\s*([A-Z][a-zA-Z]+)\s*$',  # À la fin d'une adresse
            r'\b(France|Germany|United Kingdom|UK|USA|United States|Switzerland|Switzerland|Italy|Spain|Netherlands|Belgium)\b',
        ],
        'latitude': [
            r'(?:Latitude|Lat)[\s:]+([0-9]+\.[0-9]+)',
            r'Latitude[\s:]+([0-9]+\.[0-9]+)',
        ],
        'longitude': [
            r'(?:Longitude|Lon)[\s:]+([0-9]+\.[0-9]+)',
            r'Longitude[\s:]+([0-9]+\.[0-9]+)',
            r'\*\*Longitude\*\*[\s:]+([0-9]+\.[0-9]+)',  # Format markdown **Longitude**: ...
        ],
        'confidence': [
            r'(?:Confiance|Confidence|Score)[\s:]+([0-9]+\.[0-9]+|[0-9]+)',
            r'\*\*Confiance\*\*[\s:]+([0-9]+\.[0-9]+|[0-9]+)',  # Format markdown **Confiance**: ...
            r'Confidence[\s:]+([0-9]+\.[0-9]+)',
        ],
    }
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                value = value.strip()
                # Filtrer les valeurs invalides
                if value and value.lower() not in ['non trouvé', 'non trouve', 'unknown', 'n/a', 'null', 'none', 'not found', 'n.d.', 'n.d']:
                    # Pour website, éviter de capturer des mots aléatoires
                    if key == 'website' and not (value.startswith('http') or value.startswith('www.') or '.' in value):
                        continue
                    # Pour founded_year, valider que c'est une année raisonnable
                    if key == 'founded_year':
                        try:
                            year = int(value)
                            if year < 1800 or year > 2025:
                                continue
                        except ValueError:
                            continue
                    result[key] = value
                    break
    
    return result


def parse_json_response(raw_result: str, tool_name: str = "unknown") -> dict:
    """
    Parse une réponse JSON en gérant les markdown code blocks.
    Si le JSON parsing échoue, essaie d'extraire les informations depuis le texte formaté.

    Args:
        raw_result: Résultat brut du modèle GPT
        tool_name: Nom de l'outil (pour les logs)

    Returns:
        Dict parsé ou dict avec erreur
    """
    # Logger les données brutes pour debug
    logger.debug(f"📋 [{tool_name}] Données brutes reçues ({len(raw_result)} caractères)")

    try:
        # Nettoyer le markdown
        cleaned = extract_json_from_markdown(raw_result)

        # Parser le JSON
        result = json.loads(cleaned)
        return result

    except json.JSONDecodeError as e:
        # Logger les données brutes en cas d'erreur de parsing
        logger.warning(
            f"⚠️ [{tool_name}] JSON invalide, tentative d'extraction depuis texte: {e}"
        )
        logger.warning(
            f"📄 [{tool_name}] Données brutes (premiers 500 caractères):\n{raw_result[:500]}"
        )
        # Essayer d'extraire les informations depuis le texte brut
        extracted = extract_info_from_text(raw_result, tool_name)
        if extracted:
            logger.info(f"✅ [{tool_name}] Informations extraites depuis texte formaté: {list(extracted.keys())}")
            # Ajouter les sources si présentes dans le texte
            if 'sources' not in extracted:
                source_patterns = [
                    r'(?:Source|Sources|URL)[\s:]+(https?://[^\s\n]+)',
                    r'https?://[^\s\n]+',
                ]
                sources = []
                for pattern in source_patterns:
                    matches = re.findall(pattern, raw_result, re.IGNORECASE)
                    sources.extend(matches)
                if sources:
                    extracted['sources'] = list(set(sources))
            return extracted
        else:
            logger.error(
                f"❌ [{tool_name}] Impossible d'extraire les informations. "
                f"Contenu: {cleaned[:200]}..."
        )
        return {
            "error": f"Erreur de format JSON: {str(e)}",
            "raw_content": raw_result[:500]  # Limiter la taille
        }
    except Exception as e:
        logger.error(f"❌ [{tool_name}] Erreur parsing: {e}")
        return {
            "error": f"Erreur parsing: {str(e)}",
            "raw_content": raw_result[:500]
        }
