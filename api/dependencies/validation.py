"""
Dépendances de validation pour FastAPI
"""

from fastapi import Depends, HTTPException
from services.validation_service import validate_extraction_input, validate_session_id


def validate_company_name_dependency(company_name: str) -> str:
    """
    Dépendance pour valider un nom d'entreprise
    """
    is_valid, cleaned_input, input_type = validate_extraction_input(company_name)
    
    if not is_valid:
        if input_type == "invalid_company_name":
            raise HTTPException(
                status_code=400,
                detail="Nom d'entreprise invalide. Veuillez fournir un nom valide."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Input invalide. Veuillez fournir un nom d'entreprise ou une URL valide."
            )
    
    return cleaned_input


def validate_url_dependency(url: str) -> str:
    """
    Dépendance pour valider une URL
    """
    is_valid, cleaned_input, input_type = validate_extraction_input(url)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"URL invalide: {url}"
        )
    
    if input_type != "url":
        raise HTTPException(
            status_code=400,
            detail="L'input fourni n'est pas une URL valide"
        )
    
    return cleaned_input


def validate_session_id_dependency(session_id: str) -> str:
    """
    Dépendance pour valider un session_id
    """
    if not validate_session_id(session_id):
        raise HTTPException(
            status_code=400,
            detail="Session ID invalide"
        )
    
    return session_id
