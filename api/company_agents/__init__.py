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
    LocationInfo,
)

# Import différé pour éviter les dépendances circulaires
# from .extraction_core import extract_company_data

# Extraction core - import différé pour éviter les problèmes de dépendances
# from .extraction_core import (
#     extract_company_data_from_url,
#     extract_company_data_unified,
# )

__all__ = [
    # Models
    "CompanyInfo",
    "SubsidiaryReport",
    "CompanyCard",
    "Subsidiary",
    "SubsidiaryDetail",
    "ExtractionMetadata",
    "SourceRef",
    "LocationInfo",
    # Core Extraction - import différé
    # "extract_company_data",
    # Core Extraction - import différé
    # "extract_company_data_from_url",
    # "extract_company_data_unified",
]
