"""
Service de synchronisation des extractions vers HubSpot.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from core.config import settings
from models.db_models import User, OAuthToken, CompanyExtraction
from services.auth_service import auth_service

logger = logging.getLogger(__name__)


class HubSpotSyncService:
    """Service pour synchroniser les extractions vers HubSpot."""

    HUBSPOT_API_BASE = "https://api.hubapi.com"
    ASSOCIATION_TYPE_PARENT = "1"  # Type d'association parent-enfant dans HubSpot

    async def get_valid_access_token(self, user: User, db: AsyncSession) -> str:
        """
        Récupère un token d'accès valide pour l'utilisateur.
        Rafraîchit le token si nécessaire.

        Args:
            user: Utilisateur
            db: Session de base de données

        Returns:
            Token d'accès valide

        Raises:
            HTTPException: Si aucun token n'est trouvé ou si le rafraîchissement échoue
        """
        # Récupérer le token OAuth
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.user_id == user.id)
        )
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Aucun token OAuth trouvé. Veuillez vous reconnecter via HubSpot."
            )

        # Vérifier si le token est expiré
        if oauth_token.is_expired:
            logger.info(f"Token expiré pour l'utilisateur {user.id}, rafraîchissement...")
            try:
                new_tokens = await auth_service.refresh_oauth_token(user, db)
                access_token = new_tokens["access_token"]
            except Exception as e:
                logger.error(f"Erreur lors du rafraîchissement du token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Impossible de rafraîchir le token OAuth. Veuillez vous reconnecter."
                )
        else:
            # Décrypter le token existant
            access_token = auth_service.decrypt_token(oauth_token.access_token)

        return access_token

    def extract_domain_from_website(self, website: Optional[str]) -> Optional[str]:
        """
        Extrait le domaine depuis une URL de site web.

        Args:
            website: URL du site web (ex: "https://www.example.com")

        Returns:
            Domaine extrait (ex: "example.com") ou None
        """
        if not website:
            return None

        try:
            # Ajouter https:// si le protocole est manquant
            if not website.startswith(("http://", "https://")):
                website = f"https://{website}"

            parsed = urlparse(website)
            domain = parsed.netloc or parsed.path.split("/")[0]

            # Retirer www. si présent
            if domain.startswith("www."):
                domain = domain[4:]

            return domain if domain else None
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction du domaine depuis {website}: {e}")
            return None

    async def create_company(
        self,
        access_token: str,
        name: str,
        domain: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crée une entreprise dans HubSpot.

        Args:
            access_token: Token d'accès HubSpot
            name: Nom de l'entreprise (requis)
            domain: Domaine de l'entreprise (optionnel mais recommandé)
            properties: Propriétés supplémentaires (phone, address, city, country, etc.)

        Returns:
            ID de l'entreprise créée dans HubSpot

        Raises:
            HTTPException: Si la création échoue
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Préparer les propriétés
        company_properties = {
            "name": name
        }

        if domain:
            company_properties["domain"] = domain

        # Ajouter les propriétés supplémentaires
        if properties:
            # Mapping des champs vers les propriétés HubSpot
            field_mapping = {
                "phone": "phone",
                "address": "address",
                "city": "city",
                "country": "country",
                "sector": "industry",
                "employees": "numberofemployees",
                "revenue": "annualrevenue",
                "website": "website",
            }

            for key, hubspot_prop in field_mapping.items():
                if key in properties and properties[key]:
                    company_properties[hubspot_prop] = str(properties[key])

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.HUBSPOT_API_BASE}/crm/v3/objects/companies",
                    headers=headers,
                    json={"properties": company_properties}
                )

                if response.status_code == 409:
                    # Entreprise existe déjà, essayer de la trouver par domaine ou nom
                    logger.warning(f"Entreprise existe déjà: {name}, recherche par domaine...")
                    if domain:
                        search_result = await self.search_company_by_domain(access_token, domain)
                        if search_result:
                            return search_result
                    # Si pas trouvée, lever une exception
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Une entreprise avec ce nom ou domaine existe déjà dans HubSpot"
                    )

                response.raise_for_status()
                result = response.json()
                company_id = result["id"]
                logger.info(f"✅ Entreprise créée dans HubSpot: {name} (ID: {company_id})")
                return company_id

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                logger.error(f"Erreur lors de la création de l'entreprise {name}: {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Erreur lors de la création de l'entreprise dans HubSpot: {error_detail}"
                )
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la création de l'entreprise: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur lors de la création de l'entreprise: {str(e)}"
                )

    async def search_company_by_domain(
        self,
        access_token: str,
        domain: str
    ) -> Optional[str]:
        """
        Recherche une entreprise par domaine dans HubSpot.

        Args:
            access_token: Token d'accès HubSpot
            domain: Domaine à rechercher

        Returns:
            ID de l'entreprise si trouvée, None sinon
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Recherche par domaine avec l'API de recherche HubSpot
                search_body = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "domain",
                                    "operator": "EQ",
                                    "value": domain
                                }
                            ]
                        }
                    ],
                    "properties": ["domain", "name"],
                    "limit": 10
                }

                response = await client.post(
                    f"{self.HUBSPOT_API_BASE}/crm/v3/objects/companies/search",
                    headers=headers,
                    json=search_body
                )

                if response.status_code == 200:
                    results = response.json().get("results", [])
                    if results:
                        # Retourner le premier résultat
                        return results[0]["id"]

                return None
            except Exception as e:
                logger.warning(f"Erreur lors de la recherche par domaine: {e}")
                return None

    async def create_company_association(
        self,
        access_token: str,
        from_company_id: str,
        to_company_id: str,
        association_type: str = None
    ) -> bool:
        """
        Crée une association parent-enfant entre deux entreprises dans HubSpot.

        Args:
            access_token: Token d'accès HubSpot
            from_company_id: ID de l'entreprise parent
            to_company_id: ID de l'entreprise enfant
            association_type: Type d'association (défaut: "1" pour parent)

        Returns:
            True si l'association a été créée avec succès

        Raises:
            HTTPException: Si la création échoue
        """
        if association_type is None:
            association_type = self.ASSOCIATION_TYPE_PARENT

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Créer l'association parent -> enfant
                response = await client.put(
                    f"{self.HUBSPOT_API_BASE}/crm/v3/objects/companies/{from_company_id}/associations/companies/{to_company_id}/{association_type}",
                    headers=headers
                )

                response.raise_for_status()
                logger.info(f"✅ Association créée: {from_company_id} -> {to_company_id}")
                return True

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                logger.error(f"Erreur lors de la création de l'association: {error_detail}")
                # Ne pas lever d'exception si l'association existe déjà
                if e.response.status_code == 409:
                    logger.info(f"Association déjà existante: {from_company_id} -> {to_company_id}")
                    return True
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Erreur lors de la création de l'association: {error_detail}"
                )
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la création de l'association: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erreur lors de la création de l'association: {str(e)}"
                )

    async def sync_extraction_to_hubspot(
        self,
        extraction: CompanyExtraction,
        user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Synchronise une extraction complète vers HubSpot.

        Args:
            extraction: Extraction à synchroniser
            user: Utilisateur effectuant la synchronisation
            db: Session de base de données

        Returns:
            Dictionnaire avec le statut de la synchronisation et les IDs HubSpot
        """
        # Récupérer un token valide
        access_token = await self.get_valid_access_token(user, db)

        # Vérifier que l'extraction contient des données
        if not extraction.extraction_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'extraction ne contient pas de données à synchroniser"
            )

        extraction_data = extraction.extraction_data
        sync_results = {
            "parent_company_hubspot_id": None,
            "subsidiaries_sync": [],
            "sync_status": "pending",
            "synced_at": None,
            "synced_by_user_id": str(user.id),
            "errors": []
        }

        try:
            # 1. Synchroniser l'entreprise mère (si présente)
            parent_company_info = extraction_data.get("parent_company_info")
            if parent_company_info:
                parent_name = parent_company_info.get("company_name")
                if parent_name:
                    parent_domain = self.extract_domain_from_website(
                        parent_company_info.get("website")
                    )

                    parent_properties = {
                        "phone": parent_company_info.get("phone"),
                        "address": parent_company_info.get("headquarters_address"),
                        "city": parent_company_info.get("headquarters_city"),
                        "country": parent_company_info.get("headquarters_country"),
                        "sector": parent_company_info.get("sector"),
                        "employees": parent_company_info.get("employees"),
                        "revenue": parent_company_info.get("revenue"),
                        "website": parent_company_info.get("website"),
                    }

                    try:
                        parent_id = await self.create_company(
                            access_token,
                            name=parent_name,
                            domain=parent_domain,
                            properties=parent_properties
                        )
                        sync_results["parent_company_hubspot_id"] = parent_id
                        logger.info(f"✅ Entreprise mère synchronisée: {parent_name} (ID: {parent_id})")
                    except Exception as e:
                        error_msg = f"Erreur lors de la synchronisation de l'entreprise mère: {str(e)}"
                        logger.error(error_msg)
                        sync_results["errors"].append(error_msg)
                        sync_results["sync_status"] = "partial"

            # 2. Synchroniser les filiales
            detailed_entities = extraction_data.get("detailed_entities", [])
            parent_id = sync_results["parent_company_hubspot_id"]

            for entity in detailed_entities:
                entity_name = entity.get("legal_name")
                if not entity_name:
                    continue

                entity_domain = self.extract_domain_from_website(entity.get("website"))

                entity_properties = {
                    "phone": entity.get("phone"),
                    "address": None,  # Les filiales n'ont pas toujours d'adresse complète
                    "city": None,
                    "country": entity.get("country"),
                    "sector": entity.get("sector"),
                    "employees": entity.get("employees"),
                    "revenue": entity.get("revenue"),
                    "website": entity.get("website"),
                }

                subsidiary_sync = {
                    "legal_name": entity_name,
                    "hubspot_id": None,
                    "synced_at": None,
                    "status": "pending",
                    "error": None
                }

                try:
                    subsidiary_id = await self.create_company(
                        access_token,
                        name=entity_name,
                        domain=entity_domain,
                        properties=entity_properties
                    )
                    subsidiary_sync["hubspot_id"] = subsidiary_id
                    subsidiary_sync["synced_at"] = datetime.utcnow().isoformat()
                    subsidiary_sync["status"] = "success"
                    logger.info(f"✅ Filiale synchronisée: {entity_name} (ID: {subsidiary_id})")

                    # 3. Créer l'association parent-enfant si l'entreprise mère existe
                    if parent_id:
                        try:
                            await self.create_company_association(
                                access_token,
                                from_company_id=parent_id,
                                to_company_id=subsidiary_id
                            )
                            logger.info(f"✅ Association créée: {parent_id} -> {subsidiary_id}")
                        except Exception as e:
                            error_msg = f"Erreur lors de la création de l'association pour {entity_name}: {str(e)}"
                            logger.warning(error_msg)
                            subsidiary_sync["error"] = error_msg
                            # Ne pas échouer la synchronisation pour une erreur d'association

                except Exception as e:
                    error_msg = f"Erreur lors de la synchronisation de la filiale {entity_name}: {str(e)}"
                    logger.error(error_msg)
                    subsidiary_sync["status"] = "failed"
                    subsidiary_sync["error"] = error_msg
                    sync_results["errors"].append(error_msg)
                    sync_results["sync_status"] = "partial"

                sync_results["subsidiaries_sync"].append(subsidiary_sync)

            # Déterminer le statut final
            if sync_results["sync_status"] != "partial":
                if sync_results["parent_company_hubspot_id"] or sync_results["subsidiaries_sync"]:
                    sync_results["sync_status"] = "completed"
                else:
                    sync_results["sync_status"] = "failed"

            sync_results["synced_at"] = datetime.utcnow().isoformat()

            # Mettre à jour l'extraction avec les résultats de synchronisation
            extraction.hubspot_sync_data = sync_results
            await db.commit()

            logger.info(f"✅ Synchronisation terminée pour l'extraction {extraction.id}: {sync_results['sync_status']}")
            return sync_results

        except Exception as e:
            error_msg = f"Erreur lors de la synchronisation: {str(e)}"
            logger.error(error_msg)
            sync_results["sync_status"] = "failed"
            sync_results["errors"].append(error_msg)
            sync_results["synced_at"] = datetime.utcnow().isoformat()

            # Sauvegarder l'état même en cas d'erreur
            extraction.hubspot_sync_data = sync_results
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )


# Instance globale du service
hubspot_sync_service = HubSpotSyncService()

