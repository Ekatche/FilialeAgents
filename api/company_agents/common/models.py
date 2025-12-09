# -*- coding: utf-8 -*-
"""
Models de données pour le workflow hiérarchique.

Modèles utilisés par les agents hiérarchiques :
- SourceRef : Référence source standardisée (utilisée par tous les agents)
- EntityRef : Référence minimale à une entité (output Cartographe Minimal - Phase 1)
- EclaireurReport : Output de l'Éclaireur (Phase 0 - identification société mère)
- ParentCompanyInfo : Output de l'Enrichisseur Société Mère (Phase 0.5 - enrichissement informations générales)
- MinimalMappingReport : Output du Cartographe Minimal (Phase 1 - identification entités)
- DetailedEntityInfo : Output de l'Extracteur Détaillé (Phase 2 - extraction détaillée)
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


# ====================================================================
# COUCHE 2 : Modèles pour Architecture Hiérarchique
# ====================================================================


class EntityRef(BaseModel):
    """
    Référence minimale à une entité identifiée (output Cartographe Minimal).

    Utilisé pour identifier les entités liées sans extraction détaillée.
    L'extraction détaillée sera faite par un agent dédié ultérieurement.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str = Field(..., min_length=1, max_length=200, description="Nom légal exact de l'entité")
    confidence: float = Field(ge=0, le=1, description="Confiance dans l'identification (0-1)")
    country: Optional[str] = Field(default=None, max_length=100, description="Pays de juridiction si détectable")
    ownership_percentage: Optional[float] = Field(default=None, ge=0, le=100, description="% de participation si connu")
    brief_context: Optional[str] = Field(default=None, max_length=500, description="Contexte minimal (1 phrase)")
    website: Optional[str] = Field(default=None, max_length=500, description="Site web de l'entité (URL réelle uniquement)")

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and not _is_url(v):
            raise ValueError("Website URL invalide")
        return v


class EclaireurReport(BaseModel):
    """
    Output de l'Éclaireur (Phase 0).

    Identifie la société mère à partir d'une URL ou d'un nom d'entreprise.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    parent_company_name: str = Field(..., min_length=1, max_length=200, description="Nom de la société mère")
    parent_website: Optional[str] = Field(default=None, max_length=500, description="Site web de la société mère")
    sector: Optional[str] = Field(default=None, max_length=200, description="Secteur d'activité principal de l'entreprise")
    confidence: float = Field(ge=0, le=1, description="Confiance dans l'identification (0-1)")
    is_parent_company: bool = Field(default=False, description="True si l'input était déjà la société mère")
    sources: List[SourceRef] = Field(min_items=1, max_items=10, description="Sources utilisées")
    methodology_notes: List[str] = Field(default_factory=list, max_items=10, description="Notes méthodologiques")


class MinimalMappingReport(BaseModel):
    """
    Output du Cartographe Minimal.

    Contient uniquement la liste des entités identifiées, sans extraction détaillée.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    entities_identified: List[EntityRef] = Field(
        default_factory=list,
        max_items=30,
        description="Liste des entités identifiées (limité à 30)"
    )
    total_found: int = Field(ge=0, description="Nombre total d'entités identifiées")
    search_strategy: Literal["perplexity", "gpt-4o-search", "gpt-4o-mini-search", "gpt-5-web-search"] = Field(
        default="perplexity",
        description="Stratégie de recherche utilisée"
    )
    sources: List[SourceRef] = Field(min_items=1, max_items=10, description="Sources de la cartographie")
    methodology_notes: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="Notes méthodologiques"
    )


class DetailedEntityInfo(BaseModel):
    """
    Output de l'Extracteur Détaillé (par entité).

    Contient les informations essentielles d'une entité :
    - Données de base (pays, statut légal)
    - Données d'activité (secteur, effectif, CA)
    - Liens de propriété
    - Contacts (phone, email)
    
    Notes:
    - Le website est fourni par le Cartographe Minimal et n'est pas extrait ici
    - entity_type a une valeur par défaut "subsidiary"
    - extraction_date n'est plus dans ce modèle (une seule date dans extraction_stats au niveau global)
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    # Identité
    legal_name: str = Field(..., min_length=1, max_length=200)
    entity_type: str = Field(default="subsidiary", max_length=50, description="Type d'entité (subsidiary, holding, participation, etc.)")
    website: Optional[str] = Field(default=None, max_length=500, description="Site web de l'entité")

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and not _is_url(v):
            raise ValueError("Website URL invalide")
        return v
    

    # Données de base
    country: Optional[str] = Field(default=None, max_length=100, description="Pays de l'entité")
    legal_status: Optional[Literal["Active", "Dissolved", "Liquidation", "Unknown"]] = Field(
        default=None,
        description="Statut légal de l'entité"
    )

    # Données d'activité
    sector: Optional[str] = Field(default=None, max_length=200, description="Secteur économique")
    activities: Optional[List[str]] = Field(default=None, max_items=5, description="Activités principales")
    employees: Optional[str] = Field(default=None, max_length=50, description="Effectif")
    revenue: Optional[str] = Field(default=None, max_length=100, description="Chiffre d'affaires")

    # Liens de propriété
    ownership_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Détails de propriété (% participation, date acquisition, etc.)"
    )

    # Contacts
    phone: Optional[str] = Field(default=None, max_length=50, description="Téléphone")
    email: Optional[str] = Field(default=None, max_length=100, description="Email")

    # Métadonnées
    confidence: float = Field(ge=0, le=1, description="Confiance globale dans les données")
    sources: List[SourceRef] = Field(default_factory=list, min_items=0, max_items=7, description="Sources des données")
    # Note: extraction_date est retiré car une seule date est stockée dans extraction_stats au niveau global


class ParentCompanyInfo(BaseModel):
    """
    Informations enrichies sur la société mère.
    
    Contient les informations générales de la société mère :
    - Données financières (CA, effectifs, année création)
    - Adresse complète du siège social
    - Contacts (phone, email)
    """
    
    model_config = ConfigDict(extra="forbid", strict=True)

    # Identité
    company_name: str = Field(..., min_length=1, max_length=200, description="Nom de la société mère")
    website: Optional[str] = Field(default=None, max_length=500, description="Site web officiel")

    # Données financières
    revenue: Optional[str] = Field(default=None, max_length=100, description="Chiffre d'affaires")
    employees: Optional[str] = Field(default=None, max_length=50, description="Effectif")
    founded_year: Optional[int] = Field(default=None, ge=1800, le=2100, description="Année de création")

    # Siège social
    headquarters_address: Optional[str] = Field(default=None, max_length=500, description="Adresse complète du siège social")
    headquarters_city: Optional[str] = Field(default=None, max_length=100, description="Ville du siège social")
    headquarters_country: Optional[str] = Field(default=None, max_length=100, description="Pays du siège social")

    # Contacts
    phone: Optional[str] = Field(default=None, max_length=50, description="Téléphone")
    email: Optional[str] = Field(default=None, max_length=100, description="Email")

    # Métadonnées
    confidence: float = Field(ge=0, le=1, description="Confiance globale dans les données")
    sources: List[SourceRef] = Field(default_factory=list, min_items=0, max_items=10, description="Sources des données")