"""
Modèles Pydantic pour la synchronisation HubSpot.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SubsidiarySyncResult(BaseModel):
    """Résultat de synchronisation d'une filiale."""

    legal_name: str = Field(..., description="Nom légal de la filiale")
    hubspot_id: Optional[str] = Field(None, description="ID HubSpot de l'entreprise créée")
    synced_at: Optional[str] = Field(None, description="Date de synchronisation (ISO format)")
    status: str = Field(..., description="Statut: success, failed, pending")
    error: Optional[str] = Field(None, description="Message d'erreur si échec")


class HubSpotSyncResponse(BaseModel):
    """Réponse de synchronisation HubSpot."""

    parent_company_hubspot_id: Optional[str] = Field(
        None, description="ID HubSpot de l'entreprise mère"
    )
    subsidiaries_sync: List[SubsidiarySyncResult] = Field(
        default_factory=list, description="Résultats de synchronisation des filiales"
    )
    sync_status: str = Field(
        ..., description="Statut global: completed, partial, failed, pending"
    )
    synced_at: Optional[str] = Field(None, description="Date de synchronisation (ISO format)")
    synced_by_user_id: str = Field(..., description="ID de l'utilisateur ayant effectué la synchronisation")
    errors: List[str] = Field(default_factory=list, description="Liste des erreurs rencontrées")

    class Config:
        from_attributes = True


class HubSpotSyncStatusResponse(BaseModel):
    """Statut de synchronisation HubSpot."""

    extraction_id: str = Field(..., description="ID de l'extraction")
    sync_data: Optional[HubSpotSyncResponse] = Field(None, description="Données de synchronisation")
    is_synced: bool = Field(..., description="True si l'extraction a été synchronisée")
    last_sync_at: Optional[str] = Field(None, description="Date de la dernière synchronisation")

