"""
Package agents - Modules pour l'extraction d'informations d'entreprise
"""

from .common.models import (
    SourceRef,
    EntityRef,
    EclaireurReport,
    MinimalMappingReport,
    DetailedEntityInfo,
)

__all__ = [
    # Models
    "SourceRef",
    "EntityRef",
    "EclaireurReport",
    "MinimalMappingReport",
    "DetailedEntityInfo",
]
