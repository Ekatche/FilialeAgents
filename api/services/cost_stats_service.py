"""
Service simple pour les statistiques de coûts.
Lit les coûts depuis la base de données (CompanyExtraction).
Ne calcule PAS les coûts (c'est fait par HierarchicalCostTracker).
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from uuid import UUID as UUIDType
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from models.db_models import CompanyExtraction, ExtractionStatus

logger = logging.getLogger(__name__)


class CostStatsService:
    """Service pour récupérer les statistiques de coûts depuis la base de données."""

    @staticmethod
    async def get_portal_costs(
        portal_id: Union[str, UUIDType],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques de coûts pour un portail HubSpot.

        Args:
            portal_id: HubSpot Portal UUID (string ou UUID)
            start_date: Date de début optionnelle
            end_date: Date de fin optionnelle
            db: Session de base de données

        Returns:
            Dictionnaire avec les statistiques de coûts
        """
        # Convertir portal_id en UUID si c'est une string
        if isinstance(portal_id, str):
            try:
                portal_uuid = UUIDType(portal_id)
            except ValueError as e:
                logger.error(f"❌ Invalid portal_id format: {portal_id} - {e}")
                raise ValueError(f"Invalid portal_id format: {portal_id}")
        else:
            portal_uuid = portal_id

        logger.debug(f"🔍 Recherche coûts pour portal_id={portal_uuid}")

        query = select(CompanyExtraction).where(
            CompanyExtraction.hubspot_portal_id == portal_uuid
        )

        if start_date:
            query = query.where(CompanyExtraction.created_at >= start_date)
            logger.debug(f"  📅 Filtre start_date: {start_date}")
        if end_date:
            query = query.where(CompanyExtraction.created_at <= end_date)
            logger.debug(f"  📅 Filtre end_date: {end_date}")

        result = await db.execute(query)
        extractions = result.scalars().all()

        logger.info(
            f"📊 Extractions trouvées: {len(extractions)} pour portal_id={portal_uuid}"
        )

        total_cost_eur = Decimal("0")
        total_cost_usd = Decimal("0")
        total_tokens = 0
        total_searches = len(extractions)
        completed_searches = 0
        extractions_with_costs = 0

        for extraction in extractions:
            if extraction.cost_eur:
                total_cost_eur += Decimal(str(extraction.cost_eur))
                extractions_with_costs += 1
            if extraction.cost_usd:
                total_cost_usd += Decimal(str(extraction.cost_usd))
            if extraction.total_tokens:
                total_tokens += extraction.total_tokens
            if extraction.status == ExtractionStatus.COMPLETED:
                completed_searches += 1

        logger.info(
            f"💰 Statistiques calculées: "
            f"total_searches={total_searches}, "
            f"completed={completed_searches}, "
            f"with_costs={extractions_with_costs}, "
            f"total_cost_eur={float(total_cost_eur)}, "
            f"total_tokens={total_tokens}"
        )

        avg_cost_per_search_eur = (
            total_cost_eur / Decimal(str(completed_searches))
            if completed_searches > 0
            else Decimal("0")
        )

        return {
            "portal_id": str(portal_uuid),
            "total_searches": total_searches,
            "completed_searches": completed_searches,
            "total_cost_eur": float(total_cost_eur),
            "total_cost_usd": float(total_cost_usd),
            "total_tokens": total_tokens,
            "average_cost_per_search_eur": float(avg_cost_per_search_eur),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }

    @staticmethod
    async def get_monthly_costs(
        portal_id: Union[str, UUIDType],
        year: int,
        month: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques de coûts pour un mois spécifique.

        Args:
            portal_id: HubSpot Portal UUID (string ou UUID)
            year: Année (ex: 2025)
            month: Mois (1-12)
            db: Session de base de données

        Returns:
            Dictionnaire avec les statistiques mensuelles
        """
        from calendar import monthrange

        # Obtenir le premier et dernier jour du mois
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month, monthrange(year, month)[1])

        start_datetime = datetime.combine(first_day.date(), datetime.min.time())
        end_datetime = datetime.combine(last_day.date(), datetime.max.time())

        logger.debug(
            f"📅 Recherche coûts mensuels: portal_id={portal_id}, "
            f"year={year}, month={month}, "
            f"range={start_datetime} -> {end_datetime}"
        )

        return await CostStatsService.get_portal_costs(
            portal_id,
            start_datetime,
            end_datetime,
            db
        )

    @staticmethod
    async def get_top_expensive_searches(
        portal_id: Union[str, UUIDType],
        limit: int = 10,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les recherches les plus coûteuses pour un portail.

        Args:
            portal_id: HubSpot Portal UUID (string ou UUID)
            limit: Nombre de résultats à retourner
            db: Session de base de données

        Returns:
            Liste des extractions triées par coût (décroissant)
        """
        # Convertir portal_id en UUID si c'est une string
        if isinstance(portal_id, str):
            try:
                portal_uuid = UUIDType(portal_id)
            except ValueError as e:
                logger.error(f"❌ Invalid portal_id format: {portal_id} - {e}")
                raise ValueError(f"Invalid portal_id format: {portal_id}")
        else:
            portal_uuid = portal_id

        logger.debug(
            f"🔍 Recherche top {limit} recherches coûteuses pour portal_id={portal_uuid}"
        )

        query = (
            select(CompanyExtraction)
            .where(CompanyExtraction.hubspot_portal_id == portal_uuid)
            .where(CompanyExtraction.cost_eur.isnot(None))
            .order_by(CompanyExtraction.cost_eur.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        extractions = result.scalars().all()

        logger.info(
            f"💰 Top recherches coûteuses trouvées: {len(extractions)} pour portal_id={portal_uuid}"
        )

        return [
            {
                "id": str(extraction.id),
                "company_name": extraction.company_name,
                "created_at": extraction.created_at.isoformat(),
                "cost_eur": extraction.cost_eur,
                "cost_usd": extraction.cost_usd,
                "total_tokens": extraction.total_tokens,
                "subsidiaries_count": extraction.subsidiaries_count,
                "processing_time": extraction.processing_time
            }
            for extraction in extractions
        ]


# Instance globale
cost_stats_service = CostStatsService()

