"""
Fonctions utilitaires pour l'extraction d'informations d'entreprise
"""

import logging
from datetime import datetime
from typing import Optional
from company_agents.models import CompanyInfo
from core.models import CompanyExtractionResponse


def validate_company_name(company_name: str) -> bool:
    """
    Valide le nom d'entreprise

    Args:
        company_name: Nom de l'entreprise

    Returns:
        bool: True si valide
    """
    if not company_name or not company_name.strip():
        return False

    # Vérifier la longueur
    if len(company_name.strip()) < 2:
        return False

    # Vérifier qu'il n'y a pas que des caractères spéciaux
    if not any(c.isalnum() for c in company_name):
        return False

    return True


def clean_company_name(company_name: str) -> str:
    """
    Nettoie le nom d'entreprise

    Args:
        company_name: Nom de l'entreprise

    Returns:
        str: Nom nettoyé
    """
    # Supprimer les espaces en début/fin
    cleaned = company_name.strip()

    # Supprimer les caractères de contrôle
    cleaned = "".join(char for char in cleaned if ord(char) >= 32)

    # Limiter la longueur
    if len(cleaned) > 200:
        cleaned = cleaned[:200]

    return cleaned


def format_response_for_api(
    company_info, processing_time: float, session_id: str = None
) -> CompanyExtractionResponse:
    """
    Formate la réponse pour l'API

    Args:
        company_info: Objet CompanyInfo ou dictionnaire de résultat
        processing_time: Temps de traitement en secondes
        session_id: ID de session pour le suivi en temps réel

    Returns:
        CompanyExtractionResponse: Réponse formatée
    """
    # Si c'est un objet CompanyInfo, accéder aux attributs directement
    if hasattr(company_info, "company_name"):
        return CompanyExtractionResponse(
            company_name=getattr(company_info, "company_name", ""),
            headquarters_address=getattr(company_info, "headquarters_address", ""),
            headquarters_city=getattr(company_info, "headquarters_city", ""),
            headquarters_country=getattr(company_info, "headquarters_country", ""),
            parent_company=getattr(company_info, "parent_company", None),
            subsidiaries=getattr(company_info, "subsidiaries", []),
            subsidiaries_details=[
                sub.dict() if hasattr(sub, "dict") else sub
                for sub in getattr(company_info, "subsidiaries_details", [])
            ],
            core_business=getattr(company_info, "core_business", ""),
            industry_sector=getattr(company_info, "industry_sector", ""),
            revenue=getattr(company_info, "revenue", None),
            employee_count=getattr(company_info, "employee_count", None),
            confidence_score=getattr(company_info, "confidence_score", 0.0),
            sources=getattr(company_info, "sources", []),
            extraction_date=getattr(
                company_info, "extraction_date", datetime.now().isoformat()
            ),
            extraction_status=getattr(company_info, "extraction_status", "completed"),
            total_subsidiaries=len(getattr(company_info, "subsidiaries", [])),
            detailed_subsidiaries=len(
                getattr(company_info, "subsidiaries_details", [])
            ),
            optimization_note=getattr(company_info, "optimization_note", ""),
            processing_time_seconds=processing_time,
            error_message=getattr(company_info, "error_message", None),
            source_url=getattr(company_info, "source_url", None),
            session_id=session_id,
        )
    else:
        # Fallback pour les dictionnaires (compatibilité)
        return CompanyExtractionResponse(
            company_name=company_info.get("company_name", ""),
            headquarters_address=company_info.get("headquarters_address", ""),
            headquarters_city=company_info.get("headquarters_city", ""),
            headquarters_country=company_info.get("headquarters_country", ""),
            parent_company=company_info.get("parent_company"),
            subsidiaries=company_info.get("subsidiaries", []),
            subsidiaries_details=company_info.get("subsidiaries_details", []),
            core_business=company_info.get("core_business", ""),
            industry_sector=company_info.get("industry_sector", ""),
            revenue=company_info.get("revenue"),
            employee_count=company_info.get("employee_count"),
            confidence_score=company_info.get("confidence_score", 0.0),
            sources=company_info.get("sources", []),
            extraction_date=company_info.get(
                "extraction_date", datetime.now().isoformat()
            ),
            extraction_status=company_info.get("extraction_status", "unknown"),
            total_subsidiaries=company_info.get("total_subsidiaries", 0),
            detailed_subsidiaries=company_info.get("detailed_subsidiaries", 0),
            optimization_note=company_info.get("optimization_note", ""),
            processing_time_seconds=processing_time,
            error_message=company_info.get("error_message"),
            source_url=company_info.get("source_url"),
            session_id=session_id,
        )


def setup_logging():
    """Configure le logging pour l'application"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("company_extraction.log"),
            logging.StreamHandler(),
        ],
    )

    # Réduire le niveau de log pour les bibliothèques externes
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("agents").setLevel(logging.WARNING)


def get_version() -> str:
    """Retourne la version de l'application"""
    return "1.0.0"


def check_openai_agents_availability() -> bool:
    """
    Vérifie si OpenAI Agents est disponible

    Returns:
        bool: True si disponible
    """
    try:
        import openai

        return True
    except ImportError:
        return False