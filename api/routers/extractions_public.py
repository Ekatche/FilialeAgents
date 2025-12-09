"""
Router for public extraction endpoints (no auth required - for local testing).
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from core.database import get_db
from models.db_models import CompanyExtraction
from models.costs import ExtractionListItem, DashboardStats
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/extractions", tags=["Public Extractions"])


@router.get("/recent", response_model=List[ExtractionListItem])
async def get_recent_extractions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent extractions (no auth required - for local testing).

    Args:
        limit: Number of extractions to return (max 50)
    """
    query = (
        select(CompanyExtraction)
        .order_by(desc(CompanyExtraction.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    extractions = result.scalars().all()

    items = [
        ExtractionListItem(
            id=str(extraction.id),
            session_id=extraction.session_id,
            company_name=extraction.company_name,
            company_url=extraction.company_url,
            extraction_type=extraction.extraction_type,
            status=extraction.status,
            created_at=extraction.created_at.isoformat(),
            completed_at=extraction.completed_at.isoformat() if extraction.completed_at else None,
            cost_eur=float(extraction.cost_eur) if extraction.cost_eur else None,
            cost_usd=float(extraction.cost_usd) if extraction.cost_usd else None,
            total_tokens=extraction.total_tokens,
            subsidiaries_count=extraction.subsidiaries_count,
            processing_time=extraction.processing_time,
            error_message=extraction.error_message,
        )
        for extraction in extractions
    ]

    return items


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard statistics (no auth required - for local testing).
    """
    # Get current month extractions
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    query = select(CompanyExtraction).where(
        CompanyExtraction.created_at >= start_of_month
    )

    result = await db.execute(query)
    monthly_extractions = result.scalars().all()

    # Calculate stats
    total_searches = len(monthly_extractions)
    completed_searches = sum(1 for e in monthly_extractions if e.status == "completed")
    total_cost_eur = sum(float(e.cost_eur or 0) for e in monthly_extractions)
    total_cost_usd = sum(float(e.cost_usd or 0) for e in monthly_extractions)
    total_tokens = sum(e.total_tokens or 0 for e in monthly_extractions)

    # Get recent searches (last 5)
    recent_query = (
        select(CompanyExtraction)
        .order_by(desc(CompanyExtraction.created_at))
        .limit(5)
    )
    recent_result = await db.execute(recent_query)
    recent_extractions = recent_result.scalars().all()

    recent_searches = [
        ExtractionListItem(
            id=str(extraction.id),
            session_id=extraction.session_id,
            company_name=extraction.company_name,
            company_url=extraction.company_url,
            extraction_type=extraction.extraction_type,
            status=extraction.status,
            created_at=extraction.created_at.isoformat(),
            completed_at=extraction.completed_at.isoformat() if extraction.completed_at else None,
            cost_eur=float(extraction.cost_eur) if extraction.cost_eur else None,
            cost_usd=float(extraction.cost_usd) if extraction.cost_usd else None,
            total_tokens=extraction.total_tokens,
            subsidiaries_count=extraction.subsidiaries_count,
            processing_time=extraction.processing_time,
            error_message=extraction.error_message,
        )
        for extraction in recent_extractions
    ]

    # Get total searches all time
    count_query = select(func.count()).select_from(CompanyExtraction)
    total_result = await db.execute(count_query)
    total_searches_all_time = total_result.scalar()

    # Calculate success rate
    success_rate = (completed_searches / total_searches * 100) if total_searches > 0 else 0

    return DashboardStats(
        current_month={
            "portal_id": "local",  # Mode local
            "total_searches": total_searches,
            "completed_searches": completed_searches,
            "total_cost_eur": total_cost_eur,
            "total_cost_usd": total_cost_usd,
            "total_tokens": total_tokens,
            "average_cost_per_search_eur": total_cost_eur / total_searches if total_searches > 0 else 0,
            "year": now.year,
            "month": now.month,
            "month_name": now.strftime("%B")
        },
        recent_searches=recent_searches,
        total_searches_all_time=total_searches_all_time or 0,
        success_rate=success_rate
    )


@router.get("/{extraction_id}")
async def get_extraction_by_id(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get extraction details by ID (no auth required - for local testing).
    """
    query = select(CompanyExtraction).where(CompanyExtraction.id == extraction_id)
    result = await db.execute(query)
    extraction = result.scalar_one_or_none()

    if not extraction:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Extraction not found")

    return {
        "id": str(extraction.id),
        "session_id": extraction.session_id,
        "company_name": extraction.company_name,
        "company_url": extraction.company_url,
        "extraction_type": extraction.extraction_type,
        "status": extraction.status,
        "created_at": extraction.created_at.isoformat(),
        "completed_at": extraction.completed_at.isoformat() if extraction.completed_at else None,
        "cost_eur": float(extraction.cost_eur) if extraction.cost_eur else None,
        "cost_usd": float(extraction.cost_usd) if extraction.cost_usd else None,
        "total_tokens": extraction.total_tokens,
        "subsidiaries_count": extraction.subsidiaries_count,
        "processing_time": extraction.processing_time,
        "error_message": extraction.error_message,
        "result_data": extraction.extraction_data,  # Résultats complets
    }


@router.get("/session/{session_id}")
async def get_extraction_by_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get extraction details by session_id (no auth required - for local testing).
    """
    query = select(CompanyExtraction).where(CompanyExtraction.session_id == session_id)
    result = await db.execute(query)
    extraction = result.scalar_one_or_none()

    if not extraction:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Extraction not found")

    return {
        "id": str(extraction.id),
        "session_id": extraction.session_id,
        "company_name": extraction.company_name,
        "company_url": extraction.company_url,
        "extraction_type": extraction.extraction_type,
        "status": extraction.status,
        "created_at": extraction.created_at.isoformat(),
        "completed_at": extraction.completed_at.isoformat() if extraction.completed_at else None,
        "cost_eur": float(extraction.cost_eur) if extraction.cost_eur else None,
        "cost_usd": float(extraction.cost_usd) if extraction.cost_usd else None,
        "total_tokens": extraction.total_tokens,
        "subsidiaries_count": extraction.subsidiaries_count,
        "processing_time": extraction.processing_time,
        "error_message": extraction.error_message,
        "result_data": extraction.extraction_data,  # Résultats complets
    }
