"""
Fonctions utilitaires pour l'extraction d'informations d'entreprise
"""

import json
import csv
import logging
from datetime import datetime
from typing import Dict, Optional
from company_agents.models import CompanyInfo
from core.models import CompanyExtractionResponse


def display_company_with_subsidiaries(company_info: CompanyInfo) -> str:
    """
    Affiche les informations d'entreprise avec les détails des filiales

    Args:
        company_info: Informations d'entreprise

    Returns:
        str: Texte formaté des informations
    """
    output = []
    output.append(f"\n🏢 ENTREPRISE: {company_info.company_name}")
    output.append(f"📍 Siège: {company_info.headquarters_address}")
    output.append(
        f"🏙️ {company_info.headquarters_city}, {company_info.headquarters_country}"
    )
    output.append(f"💼 Secteur: {company_info.industry_sector}")
    output.append(f"📊 Confiance: {company_info.confidence_score:.2f}")

    if company_info.subsidiaries:
        output.append(f"\n🏢 FILIALES ({len(company_info.subsidiaries)}):")
        # Afficher d'abord la liste des noms
        for i, subsidiary_name in enumerate(company_info.subsidiaries, 1):
            output.append(f"   {i}. {subsidiary_name}")

        # Afficher les détails si disponibles
        if (
            hasattr(company_info, "subsidiaries_details")
            and company_info.subsidiaries_details
        ):
            output.append(
                f"\n📍 DÉTAILS DES FILIALES ({len(company_info.subsidiaries_details)}):"
            )
            for i, subsidiary in enumerate(company_info.subsidiaries_details, 1):
                output.append(f"\n   {i}. {subsidiary.subsidiary_name}")
                output.append(f"      📍 {subsidiary.subsidiary_address}")
                output.append(
                    f"      🏙️ {subsidiary.subsidiary_city}, {subsidiary.subsidiary_country}"
                )
                output.append(f"      🏭 Type: {subsidiary.subsidiary_type}")
                output.append(f"      💼 Activité: {subsidiary.business_activity}")
                output.append(f"      👥 Employés: {subsidiary.employee_count}")
                output.append(f"      📅 Créée: {subsidiary.establishment_date}")
                output.append(f"      📊 Confiance: {subsidiary.confidence_score:.2f}")
        else:
            output.append("\n   ⚠️ Détails des filiales non disponibles")
            output.append(
                "   💡 L'agent a identifié les filiales mais n'a pas encore extrait les détails"
            )
    else:
        output.append("\n⚠️ Aucune filiale identifiée")

    return "\n".join(output)


def export_subsidiaries_to_csv(
    company_info: CompanyInfo, filename: Optional[str] = None
) -> str:
    """
    Exporte les filiales vers un fichier CSV

    Args:
        company_info: Informations d'entreprise
        filename: Nom du fichier (optionnel)

    Returns:
        str: Nom du fichier créé
    """
    if not filename:
        safe_name = company_info.company_name.replace(" ", "_").replace("/", "_")
        filename = (
            f"subsidiaries_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "subsidiary_name",
                "subsidiary_address",
                "subsidiary_city",
                "subsidiary_country",
                "subsidiary_type",
                "business_activity",
                "employee_count",
                "establishment_date",
                "confidence_score",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for subsidiary in company_info.subsidiaries_details:
                writer.writerow(
                    {
                        "subsidiary_name": subsidiary.subsidiary_name,
                        "subsidiary_address": subsidiary.subsidiary_address,
                        "subsidiary_city": subsidiary.subsidiary_city,
                        "subsidiary_country": subsidiary.subsidiary_country,
                        "subsidiary_type": subsidiary.subsidiary_type,
                        "business_activity": subsidiary.business_activity,
                        "employee_count": subsidiary.employee_count,
                        "establishment_date": subsidiary.establishment_date,
                        "confidence_score": subsidiary.confidence_score,
                    }
                )

        logging.info(f"📊 Filiales exportées vers: {filename}")
        return filename

    except Exception as e:
        logging.error(f"❌ Erreur lors de l'export CSV: {e}")
        raise


def export_company_to_json(
    company_info: CompanyInfo, filename: Optional[str] = None
) -> str:
    """
    Exporte les informations d'entreprise vers un fichier JSON

    Args:
        company_info: Informations d'entreprise
        filename: Nom du fichier (optionnel)

    Returns:
        str: Nom du fichier créé
    """
    if not filename:
        safe_name = company_info.company_name.replace(" ", "_").replace("/", "_")
        filename = (
            f"company_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    try:
        # Convertir en dictionnaire
        data = {
            "company_name": company_info.company_name,
            "headquarters_address": company_info.headquarters_address,
            "headquarters_city": company_info.headquarters_city,
            "headquarters_country": company_info.headquarters_country,
            "parent_company": company_info.parent_company,
            "subsidiaries": company_info.subsidiaries,
            "subsidiaries_details": [
                {
                    "subsidiary_name": sub.subsidiary_name,
                    "subsidiary_address": sub.subsidiary_address,
                    "subsidiary_city": sub.subsidiary_city,
                    "subsidiary_country": sub.subsidiary_country,
                    "subsidiary_type": sub.subsidiary_type,
                    "business_activity": sub.business_activity,
                    "employee_count": sub.employee_count,
                    "establishment_date": sub.establishment_date,
                    "parent_company": sub.parent_company,
                    "confidence_score": sub.confidence_score,
                    "sources": sub.sources,
                }
                for sub in company_info.subsidiaries_details
            ],
            "core_business": company_info.core_business,
            "industry_sector": company_info.industry_sector,
            "revenue": company_info.revenue,
            "employee_count": company_info.employee_count,
            "confidence_score": company_info.confidence_score,
            "sources": company_info.sources,
            "extraction_date": company_info.extraction_date,
        }

        with open(filename, "w", encoding="utf-8") as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)

        logging.info(f"💾 Données d'entreprise exportées vers: {filename}")
        return filename

    except Exception as e:
        logging.error(f"❌ Erreur lors de l'export JSON: {e}")
        raise


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


def extract_company_from_url(url: str) -> Optional[str]:
    """
    Extrait le nom d'entreprise à partir d'une URL

    Args:
        url: URL de l'entreprise

    Returns:
        Optional[str]: Nom d'entreprise extrait ou None
    """
    try:
        from urllib.parse import urlparse

        # Parser l'URL
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Supprimer www. et les extensions
        if domain.startswith("www."):
            domain = domain[4:]

        # Supprimer l'extension
        domain = domain.split(".")[0]

        # Remplacer les tirets par des espaces
        company_name = domain.replace("-", " ").replace("_", " ")

        # Capitaliser
        company_name = " ".join(word.capitalize() for word in company_name.split())

        return company_name if company_name else None

    except Exception as e:
        logging.error(f"❌ Erreur lors de l'extraction du nom depuis l'URL: {e}")
        return None


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
