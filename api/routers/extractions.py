"""
Router for extraction listing and management.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_active_user, get_current_portal
from models.db_models import User, HubSpotPortal
from models.costs import (
    ExtractionListResponse,
    ExtractionListItem,
    DashboardStats,
    MonthlyCostStats,
)
from services.extraction_service import extraction_service
from services.cost_stats_service import cost_stats_service

router = APIRouter(prefix="/extractions", tags=["Extractions"])


@router.get("", response_model=ExtractionListResponse)
async def list_extractions(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed)"),
    search: Optional[str] = Query(None, description="Search in company name"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db),
):
    """
    List extractions with pagination and filters.

    **Permissions**: Users can only view extractions from their portal.
    """
    # Parse dates if provided
    start_datetime = None
    end_datetime = None

    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format: YYYY-MM-DD",
            )

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format: YYYY-MM-DD",
            )

    result = await extraction_service.list_extractions(
        portal_id=str(portal.id),
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        search_query=search,
        start_date=start_datetime,
        end_date=end_datetime,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ExtractionListResponse(**result)


@router.get("/recent", response_model=List[ExtractionListItem])
async def get_recent_extractions(
    limit: int = Query(5, ge=1, le=20, description="Number of recent extractions"),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent extractions for dashboard.

    **Permissions**: Users can only view extractions from their portal.
    """
    extractions = await extraction_service.get_recent_extractions(
        portal_id=str(portal.id),
        db=db,
        limit=limit,
    )

    return [ExtractionListItem(**extraction) for extraction in extractions]


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db),
):
    """
    Get consolidated dashboard statistics.

    Returns:
    - Current month stats
    - Recent searches (last 5)
    - Quick stats (total searches, success rate)

    **Permissions**: Users can only view their portal's stats.
    """
    # Get current month stats
    now = datetime.now()
    monthly_stats = await cost_stats_service.get_monthly_costs(
        portal_id=str(portal.id),
        year=now.year,
        month=now.month,
        db=db,
    )

    month_names = [
        "Janvier",
        "Février",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Août",
        "Septembre",
        "Octobre",
        "Novembre",
        "Décembre",
    ]

    current_month = MonthlyCostStats(
        **monthly_stats,
        year=now.year,
        month=now.month,
        month_name=month_names[now.month - 1],
    )

    # Get recent searches
    recent_extractions = await extraction_service.get_recent_extractions(
        portal_id=str(portal.id),
        db=db,
        limit=5,
    )

    # Get total searches all time
    all_time_stats = await cost_stats_service.get_portal_costs(
        portal_id=str(portal.id),
        start_date=None,
        end_date=None,
        db=db,
    )

    # Calculate success rate
    total_searches = all_time_stats.get("total_searches", 0)
    completed_searches = all_time_stats.get("completed_searches", 0)
    success_rate = (completed_searches / total_searches) if total_searches > 0 else 0.0

    return DashboardStats(
        current_month=current_month,
        recent_searches=[ExtractionListItem(**ext) for ext in recent_extractions],
        total_searches_all_time=total_searches,
        success_rate=success_rate,
    )

