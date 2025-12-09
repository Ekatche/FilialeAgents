"""
Router pour la synchronisation des extractions vers HubSpot.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_active_user, get_current_portal
from models.db_models import User, HubSpotPortal, CompanyExtraction
from models.hubspot_sync import HubSpotSyncResponse, HubSpotSyncStatusResponse
from services.hubspot_sync_service import hubspot_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hubspot/sync", tags=["HubSpot Sync"])


@router.post("/{extraction_id}", response_model=HubSpotSyncResponse)
async def sync_extraction_to_hubspot(
    extraction_id: str,
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronise une extraction vers HubSpot.

    Cette endpoint crée les entreprises (mère et filiales) dans HubSpot
    et établit les relations parent-enfant.

    **Permissions**: L'utilisateur doit avoir un token OAuth HubSpot valide
    avec les scopes `crm.objects.companies.write`.

    **Processus**:
    1. Récupère les données de l'extraction
    2. Crée l'entreprise mère dans HubSpot (si présente)
    3. Crée chaque filiale dans HubSpot
    4. Établit les associations parent-enfant
    5. Enregistre les résultats dans `hubspot_sync_data`

    **Note**: Si une entreprise existe déjà dans HubSpot (même nom/domaine),
    une erreur sera retournée. La synchronisation partielle est possible :
    si certaines filiales échouent, les autres seront quand même synchronisées.
    """
    try:
        extraction_uuid = UUID(extraction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID d'extraction invalide"
        )

    # Récupérer l'extraction
    result = await db.execute(
        select(CompanyExtraction).where(
            CompanyExtraction.id == extraction_uuid,
            CompanyExtraction.hubspot_portal_id == portal.id
        )
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction non trouvée ou n'appartient pas à votre portail"
        )

    # Vérifier que l'extraction est complétée
    if extraction.status.value != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"L'extraction n'est pas complétée (statut: {extraction.status.value})"
        )

    # Vérifier que l'extraction contient des données
    if not extraction.extraction_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'extraction ne contient pas de données à synchroniser"
        )

    # Effectuer la synchronisation
    try:
        sync_results = await hubspot_sync_service.sync_extraction_to_hubspot(
            extraction=extraction,
            user=current_user,
            db=db
        )

        return HubSpotSyncResponse(**sync_results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la synchronisation: {str(e)}"
        )


@router.get("/{extraction_id}/status", response_model=HubSpotSyncStatusResponse)
async def get_sync_status(
    extraction_id: str,
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db),
):
    """
    Récupère le statut de synchronisation HubSpot d'une extraction.

    Retourne les informations sur la dernière synchronisation effectuée,
    incluant les IDs HubSpot des entreprises créées et le statut de chaque filiale.
    """
    try:
        extraction_uuid = UUID(extraction_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID d'extraction invalide"
        )

    # Récupérer l'extraction
    result = await db.execute(
        select(CompanyExtraction).where(
            CompanyExtraction.id == extraction_uuid,
            CompanyExtraction.hubspot_portal_id == portal.id
        )
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction non trouvée ou n'appartient pas à votre portail"
        )

    # Récupérer les données de synchronisation
    sync_data = extraction.hubspot_sync_data

    if sync_data:
        return HubSpotSyncStatusResponse(
            extraction_id=extraction_id,
            sync_data=HubSpotSyncResponse(**sync_data),
            is_synced=True,
            last_sync_at=sync_data.get("synced_at")
        )
    else:
        return HubSpotSyncStatusResponse(
            extraction_id=extraction_id,
            sync_data=None,
            is_synced=False,
            last_sync_at=None
        )

