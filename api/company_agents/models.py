# -*- coding: utf-8 -*-
"""
Models de données 'entreprise & filiales' — Version nettoyée
Seuls les modèles utilisés sont conservés
"""

from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from urllib.parse import urlparse


# ====================================================================
# Utilitaires simples
# ====================================================================


def _is_url(s: str) -> bool:
    try:
        p = urlparse(s)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


# ====================================================================
# COUCHE 1 : Modèles communs
# ====================================================================


class SourceRef(BaseModel):
    """Référence source unifiée pour tous les agents"""

    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=500)
    publisher: Optional[str] = Field(default=None, max_length=200)
    published_date: Optional[str] = Field(default=None, max_length=10)
    tier: Literal["official", "financial_media", "pro_db", "other"] = Field(
        default="other"
    )
    accessibility: Optional[Literal["ok", "protected", "rate_limited", "broken"]] = (
        Field(default=None)
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not _is_url(v):
            raise ValueError("URL invalide")
        return v


class LocationInfo(BaseModel):
    """Information de localisation unifiée"""

    model_config = ConfigDict(extra="forbid", strict=True)

    label: Optional[str] = Field(default=None, max_length=200)
    line1: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    website: Optional[str] = Field(default=None, max_length=500)
    sources: Optional[List[SourceRef]] = Field(default=None, max_length=3)

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and not _is_url(v):
            raise ValueError("Website URL invalide")
        return v


class ParentRef(BaseModel):
    """Référence vers une société mère"""

    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str = Field(..., min_length=1, max_length=200)
    country: Optional[str] = Field(default=None, max_length=100)
    sources: List[SourceRef] = Field(min_length=1, max_length=7)


# ====================================================================
# COUCHE 2 : Modèles intermédiaires
# ====================================================================


class CompanyCard(BaseModel):
    """Fiche d'identité entreprise (output Information Extractor)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    company_name: str = Field(..., min_length=1, max_length=200)
    headquarters: str = Field(..., min_length=1, max_length=500)
    parent_company: Optional[str] = Field(default=None, max_length=200)
    sector: str = Field(..., min_length=1, max_length=200)
    activities: List[str] = Field(..., min_length=1, max_length=6)
    methodology_notes: Optional[List[str]] = Field(default=None, max_length=6)
    revenue_recent: Optional[str] = Field(default=None, max_length=100)
    employees: Optional[str] = Field(default=None, max_length=100)
    founded_year: Optional[int] = Field(default=None, ge=1800, le=2030)
    sources: List[SourceRef] = Field(..., min_length=2, max_length=7)


class Subsidiary(BaseModel):
    """Filiale d'entreprise (output Subsidiary Extractor)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str = Field(..., min_length=1, max_length=200)
    type: Literal["subsidiary", "division", "branch", "joint_venture"] = Field(
        default="subsidiary"
    )
    activity: Optional[str] = Field(default=None, max_length=300)
    headquarters: LocationInfo = Field(...)
    sites: Optional[List[LocationInfo]] = Field(default=None, max_length=7)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sources: List[SourceRef] = Field(..., min_length=1, max_length=2)


class ExtractionSummary(BaseModel):
    """Résumé d'extraction"""

    model_config = ConfigDict(extra="forbid", strict=True)

    total_found: int = Field(..., ge=0)
    methodology_used: Optional[List[str]] = Field(default=None, max_length=5)


class SubsidiaryReport(BaseModel):
    """Rapport complet des filiales (output Subsidiary Extractor)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    company_name: str = Field(..., min_length=1, max_length=200)
    parents: List[ParentRef] = Field(default_factory=list, max_length=3)
    subsidiaries: List[Subsidiary] = Field(default_factory=list, max_length=10)
    methodology_notes: Optional[List[str]] = Field(default=None, max_length=5)
    extraction_summary: Optional[ExtractionSummary] = Field(default=None)


# ====================================================================
# COUCHE 4 : Modèle final API
# ====================================================================


class ExtractionMetadata(BaseModel):
    """Métadonnées d'extraction"""

    model_config = ConfigDict(extra="forbid", strict=True)

    input_type: Optional[str] = Field(default=None, max_length=50)
    session_id: Optional[str] = Field(default=None, max_length=100)
    processing_time: Optional[float] = Field(default=None, ge=0)


class SubsidiaryDetail(BaseModel):
    """Détail d'une filiale pour l'API finale"""

    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str = Field(..., min_length=1, max_length=200)
    headquarters: Optional[LocationInfo] = Field(default=None)
    activity: Optional[str] = Field(default=None, max_length=200)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    sources: List[SourceRef] = Field(default_factory=list, max_length=2)


class CompanyInfo(BaseModel):
    """Modèle final de sortie API - compatible frontend"""

    model_config = ConfigDict(extra="forbid", strict=True)

    company_name: str = Field(..., min_length=1, max_length=200)
    headquarters_address: str = Field(..., min_length=1, max_length=500)
    headquarters_city: Optional[str] = Field(default=None, max_length=100)
    headquarters_country: Optional[str] = Field(default=None, max_length=100)
    parent_company: Optional[str] = Field(default=None, max_length=200)
    sector: str = Field(..., min_length=1, max_length=200)
    activities: List[str] = Field(..., min_length=1, max_length=6)
    revenue_recent: Optional[str] = Field(default=None, max_length=100)
    employees: Optional[str] = Field(default=None, max_length=100)
    founded_year: Optional[int] = Field(default=None, ge=1800, le=2030)
    subsidiaries_details: List[SubsidiaryDetail] = Field(
        default_factory=list, max_length=10
    )
    sources: List[SourceRef] = Field(..., min_length=2, max_length=7)
    methodology_notes: Optional[List[str]] = Field(default=None, max_length=6)
    extraction_metadata: Optional[ExtractionMetadata] = Field(default=None)
    extraction_date: Optional[str] = Field(default=None)
