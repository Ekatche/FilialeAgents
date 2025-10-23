# -*- coding: utf-8 -*-
"""
Models de données 'entreprise & filiales' — Version nettoyée
Seuls les modèles utilisés sont conservés
"""

from __future__ import annotations
from typing import List, Optional, Literal
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
    context: Optional[str] = Field(default=None, max_length=500, description="Contexte enrichi pour la recherche de filiales")
    enterprise_type: Optional[Literal["complex", "simple"]] = Field(default=None, description="Type d'entreprise: complex (grand groupe) ou simple (PME)")
    has_filiales_only: Optional[bool] = Field(default=None, description="L'entreprise possède-t-elle UNIQUEMENT des filiales juridiques (true) ou un mélange filiales+bureaux/distributeurs (false) ?")
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
    sources: List[SourceRef] = Field(..., min_length=1, max_length=10)  # Augmenté pour permettre plus de sources


class CommercialPresence(BaseModel):
    """Présence commerciale sans filiale juridique"""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(..., min_length=1, max_length=200, description="Nom du bureau/partenaire/distributeur")
    type: Literal["office", "partner", "distributor", "representative"] = Field(
        ...,
        description="Type de présence : bureau commercial, partenaire, distributeur, représentant"
    )
    relationship: Literal["owned", "partnership", "authorized_distributor", "franchise"] = Field(
        ...,
        description="Nature de la relation : propriété, partenariat, distributeur autorisé, franchise"
    )
    activity: Optional[str] = Field(default=None, max_length=300, description="Activité spécifique")
    
    # Localisation
    location: LocationInfo = Field(..., description="Localisation du bureau/partenaire")
    
    # Contacts (optionnels, peuvent être dans location aussi)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    
    # Métadonnées
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sources: List[SourceRef] = Field(..., min_length=1, max_length=5)
    
    # Informations additionnelles
    since_year: Optional[int] = Field(default=None, ge=1900, le=2030, description="Année d'établissement")
    status: Optional[Literal["active", "inactive", "unverified"]] = Field(default="unverified")


class MainCompanyInfo(BaseModel):
    """Informations sur l'entreprise principale (quand pas de filiales)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    address: Optional[str] = Field(default=None, max_length=500)
    revenue: Optional[str] = Field(default=None, max_length=100)
    employees: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)


class PresenceByType(BaseModel):
    """Répartition des présences commerciales par type"""
    
    model_config = ConfigDict(extra="forbid", strict=True)
    
    office: Optional[int] = Field(default=0, ge=0)
    partner: Optional[int] = Field(default=0, ge=0)
    distributor: Optional[int] = Field(default=0, ge=0)
    representative: Optional[int] = Field(default=0, ge=0)


class ExtractionSummary(BaseModel):
    """Résumé d'extraction"""

    model_config = ConfigDict(extra="forbid", strict=True)

    total_found: int = Field(..., ge=0, description="Nombre total de filiales juridiques")
    
    # 🆕 NOUVEAU : Statistiques présence commerciale
    total_commercial_presence: Optional[int] = Field(default=0, ge=0, description="Nombre de présences commerciales")
    presence_by_type: Optional[PresenceByType] = Field(
        default=None,
        description="Répartition par type de présence commerciale"
    )
    countries_covered: Optional[List[str]] = Field(
        default=None,
        max_length=50,
        description="Liste des pays avec présence (filiales + commerciale)"
    )
    
    main_company_info: Optional[MainCompanyInfo] = Field(default=None)
    methodology_used: Optional[List[str]] = Field(default=None, max_length=5)


class SubsidiaryReport(BaseModel):
    """Rapport complet des filiales ET présence commerciale (output Subsidiary Extractor)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    company_name: str = Field(..., min_length=1, max_length=200)

    parent_website: Optional[str] = Field(
        default=None, 
        max_length=500,
        description="Site web principal du groupe, utilisé en fallback"
    )
    
    parents: List[ParentRef] = Field(default_factory=list, max_length=3)
    subsidiaries: List[Subsidiary] = Field(default_factory=list, max_length=10)
    
    # 🆕 NOUVEAU : Présence commerciale
    commercial_presence: List[CommercialPresence] = Field(
        default_factory=list, 
        max_length=20,
        description="Bureaux commerciaux, partenaires, distributeurs sans personnalité juridique"
    )
    
    methodology_notes: Optional[List[str]] = Field(default=None, max_length=15)  # Augmenté pour plus de détails
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
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    # Filiales juridiques
    subsidiaries_details: List[SubsidiaryDetail] = Field(
        default_factory=list, max_length=10
    )
    
    # 🆕 NOUVEAU : Présence commerciale
    commercial_presence_details: List[CommercialPresence] = Field(
        default_factory=list,
        max_length=20,
        description="Bureaux, partenaires, distributeurs"
    )
    
    sources: List[SourceRef] = Field(..., min_length=2, max_length=7)
    methodology_notes: Optional[List[str]] = Field(default=None, max_length=6)
    extraction_metadata: Optional[ExtractionMetadata] = Field(default=None)
    extraction_date: Optional[str] = Field(default=None)
