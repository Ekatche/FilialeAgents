"""
Package agents - Modules pour l'extraction d'informations d'entreprise
"""

from .models import (
    CompanyInfo,
    SubsidiaryReport,
    CompanyCard,
    Subsidiary,
    SubsidiaryDetail,
    ExtractionMetadata,
    SourceRef,
)

from .extraction_core import extract_company_data


__all__ = [
    # Models
    "CompanyInfo",
    "SubsidiaryReport",
    "CompanyCard",
    "Subsidiary",
    "SubsidiaryDetail",
    "ExtractionMetadata",
    "SourceRef",
    # Core Extraction
    "extract_company_data",
]
