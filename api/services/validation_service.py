"""
Service de validation des données
"""

import logging
from typing import Tuple
from functions import validate_company_name, clean_company_name

logger = logging.getLogger(__name__)


def detect_input_type(input_str: str) -> str:
    """Détecte automatiquement si l'input est une URL ou un nom d'entreprise"""
    input_str = input_str.strip()
    if input_str.startswith(("http://", "https://", "www.")):
        return "url"
    elif "." in input_str and len(input_str.split(".")) >= 2:
        # Pourrait être un domaine sans protocole
        return "url"
    else:
        return "company_name"


def detect_execution_mode(input_str: str, mode: str) -> str:
    """Détermine le mode d'exécution optimal"""
    if mode != "auto":
        return mode

    # Logique automatique : grandes entreprises ou URLs complexes → async
    if detect_input_type(input_str) == "url":
        return "async"  # URLs souvent plus complexes

    # Heuristiques pour détecter grandes entreprises
    large_company_indicators = [
        "group", "holding", "international", "worldwide",
        "corporation", "corp", "inc", "ltd", "plc"
    ]

    if any(indicator in input_str.lower() for indicator in large_company_indicators):
        return "async"  # Grandes entreprises → traitement async

    return "sync"  # PME → traitement sync rapide


def validate_extraction_input(input_str: str) -> Tuple[bool, str, str]:
    """
    Valide l'input d'extraction et retourne (is_valid, cleaned_input, input_type)
    """
    if not input_str or not input_str.strip():
        return False, "", "invalid"
    
    cleaned_input = input_str.strip()
    input_type = detect_input_type(cleaned_input)
    
    if input_type == "company_name":
        # Validation spécifique pour les noms d'entreprise
        if not validate_company_name(cleaned_input):
            return False, cleaned_input, "invalid_company_name"
        cleaned_input = clean_company_name(cleaned_input)
    
    return True, cleaned_input, input_type


def validate_session_id(session_id: str) -> bool:
    """Valide qu'un session_id est valide"""
    if not session_id or not session_id.strip():
        return False
    
    # Vérifier que c'est un UUID valide
    try:
        import uuid
        uuid.UUID(session_id)
        return True
    except ValueError:
        return False
