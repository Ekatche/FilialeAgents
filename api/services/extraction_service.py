"""
Service for querying company extractions with pagination and filters.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import CompanyExtraction, ExtractionStatus, ExtractionType
import logging

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for querying extractions"""

    @staticmethod
    async def list_extractions(
        portal_id: str,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """
        List extractions with pagination and filters.

        Args:
            portal_id: HubSpot Portal UUID
            db: Database session
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status (pending, running, completed, failed)
            search_query: Search in company_name
            start_date: Filter by start date
            end_date: Filter by end date
            sort_by: Field to sort by (created_at, cost_eur, etc.)
            sort_order: Sort order (asc, desc)

        Returns:
            Dictionary with items, total, pagination info
        """
        # Build base query
        query = select(CompanyExtraction).where(
            CompanyExtraction.hubspot_portal_id == portal_id
        )

        # Apply filters
        if status:
            try:
                status_enum = ExtractionStatus(status.lower())
                query = query.where(CompanyExtraction.status == status_enum)
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")

        if search_query:
            query = query.where(
                CompanyExtraction.company_name.ilike(f"%{search_query}%")
            )

        if start_date:
            query = query.where(CompanyExtraction.created_at >= start_date)

        if end_date:
            # Set to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            query = query.where(CompanyExtraction.created_at <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply sorting
        sort_column = getattr(CompanyExtraction, sort_by, CompanyExtraction.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await db.execute(query)
        extractions = result.scalars().all()

        # Convert to dict
        items = [
            {
                "id": str(extraction.id),
                "session_id": extraction.session_id,
                "company_name": extraction.company_name,
                "company_url": extraction.company_url,
                            "extraction_type": extraction.extraction_type,
                            "status": extraction.status,                "created_at": extraction.created_at,
                "completed_at": extraction.completed_at,
                "cost_eur": extraction.cost_eur,
                "cost_usd": extraction.cost_usd,
                "total_tokens": extraction.total_tokens,
                "subsidiaries_count": extraction.subsidiaries_count,
                "processing_time": extraction.processing_time,
                "error_message": extraction.error_message,
            }
            for extraction in extractions
        ]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def get_recent_extractions(
        portal_id: str,
        db: AsyncSession,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get recent extractions for dashboard.

        Args:
            portal_id: HubSpot Portal UUID
            db: Database session
            limit: Number of recent extractions to return

        Returns:
            List of recent extractions
        """
        query = (
            select(CompanyExtraction)
            .where(CompanyExtraction.hubspot_portal_id == portal_id)
            .order_by(CompanyExtraction.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        extractions = result.scalars().all()

        return [
            {
                "id": str(extraction.id),
                "session_id": extraction.session_id,
                "company_name": extraction.company_name,
                "company_url": extraction.company_url,
                            "extraction_type": extraction.extraction_type,
                            "status": extraction.status,                "created_at": extraction.created_at,
                "completed_at": extraction.completed_at,
                "cost_eur": extraction.cost_eur,
                "cost_usd": extraction.cost_usd,
                "total_tokens": extraction.total_tokens,
                "subsidiaries_count": extraction.subsidiaries_count,
                "processing_time": extraction.processing_time,
                "error_message": extraction.error_message,
            }
            for extraction in extractions
        ]


# Global instance
extraction_service = ExtractionService()

