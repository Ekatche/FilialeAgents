"""
Cost statistics and tracking router.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import (
    get_current_active_user,
    get_current_portal,
    require_admin
)
from models.db_models import User, HubSpotPortal, CompanyExtraction
from models.costs import (
    OrganizationCostStats,
    MonthlyCostStats,
    CostEstimateRequest,
    CostEstimateResponse,
    TopExpensiveSearch,
    ExtractionCostDetail,
    ModelUsageDetail
)
from services.cost_stats_service import cost_stats_service


router = APIRouter(prefix="/costs", tags=["Cost Tracking"])


@router.get("/portal/stats", response_model=OrganizationCostStats)
async def get_portal_cost_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost statistics for the current user's HubSpot portal.

    Returns aggregated cost data for all extractions within the specified date range.
    If no dates are provided, returns statistics for all time.

    **Permissions**: Any authenticated user can view their portal's stats.
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
                detail="Invalid start_date format. Use ISO format: YYYY-MM-DD"
            )

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
            # Set to end of day
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format: YYYY-MM-DD"
            )

    # Get statistics
    stats = await cost_stats_service.get_portal_costs(
        portal_id=str(portal.id),
        start_date=start_datetime,
        end_date=end_datetime,
        db=db
    )

    return OrganizationCostStats(**stats)


@router.get("/portal/monthly/{year}/{month}", response_model=MonthlyCostStats)
async def get_monthly_cost_stats(
    year: int = Path(..., ge=2020, le=2100, description="Year"),
    month: int = Path(..., ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost statistics for a specific month.

    Returns detailed cost breakdown for the specified month and year.

    **Permissions**: Any authenticated user can view their portal's monthly stats.
    """
    # Get monthly statistics
    stats = await cost_stats_service.get_monthly_costs(
        portal_id=str(portal.id),
        year=year,
        month=month,
        db=db
    )

    # Add month name
    month_names = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return MonthlyCostStats(
        **stats,
        year=year,
        month=month,
        month_name=month_names[month - 1]
    )


@router.get("/portal/top-expensive", response_model=List[TopExpensiveSearch])
async def get_top_expensive_searches(
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the most expensive searches for the portal.

    Returns a list of extractions sorted by cost (descending).

    **Permissions**: Any authenticated user can view their portal's expensive searches.
    """
    searches = await cost_stats_service.get_top_expensive_searches(
        portal_id=str(portal.id),
        limit=limit,
        db=db
    )

    return [TopExpensiveSearch(**search) for search in searches]


@router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_extraction_cost(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Estimate the cost of an extraction before running it.

    Provides an approximate cost based on:
    - Extraction type (simple vs advanced)
    - Whether the company has subsidiaries
    - Estimated number of subsidiaries

    **Note**: This is an estimate. Actual costs may vary based on:
    - Actual data complexity
    - Number of subsidiaries found
    - Search depth required

    **Permissions**: Any authenticated user can request estimates.
    """
    # Estimation simplifiée (les coûts réels sont calculés par HierarchicalCostTracker)
    # Pour l'instant, retourner une estimation basique
    # TODO: Implémenter une estimation basée sur les données historiques si nécessaire
    from services.hierarchical_cost_tracking import CostContext
    
    # Estimation basique : ~20K tokens pour une extraction simple
    estimated_input = 10000
    estimated_output = 10000
    
    if request.has_subsidiaries:
        # Ajouter ~5K tokens par filiale
        estimated_input += request.subsidiaries_count * 5000
        estimated_output += request.subsidiaries_count * 3000
    
    # Utiliser gpt-4.1-mini comme modèle de référence
    model = "gpt-4_1-mini"
    pricing = CostContext._get_model_pricing(model)
    cost_usd = (estimated_input * pricing["input"]) + (estimated_output * pricing["output"])
    
    # Taux de change approximatif
    exchange_rate = 0.92
    cost_eur = cost_usd * exchange_rate
    
    return CostEstimateResponse(
        total_input_tokens=estimated_input,
        total_output_tokens=estimated_output,
        total_tokens=estimated_input + estimated_output,
        total_cost_usd=float(cost_usd),
        total_cost_eur=float(cost_eur),
        models_breakdown=[{
            "model": model,
            "input_tokens": estimated_input,
            "output_tokens": estimated_output,
            "cost_usd": float(cost_usd),
            "cost_eur": float(cost_eur)
        }],
        exchange_rate=exchange_rate,
        estimate_type="approximate",
        extraction_type=request.extraction_type,
        estimated_subsidiaries=request.subsidiaries_count if request.has_subsidiaries else 0
    )


@router.get("/extraction/{extraction_id}", response_model=ExtractionCostDetail)
async def get_extraction_cost_detail(
    extraction_id: str,
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed cost information for a specific extraction.

    Returns comprehensive cost breakdown including:
    - Total costs in USD and EUR
    - Token usage (input/output)
    - Cost breakdown by AI model
    - Processing time and metadata

    **Permissions**: Users can only view extractions from their portal.
    """
    # Load extraction - try by ID first, then by session_id
    result = await db.execute(
        select(CompanyExtraction).where(
            (CompanyExtraction.id == extraction_id) | 
            (CompanyExtraction.session_id == extraction_id)
        )
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction not found"
        )

    # Verify extraction belongs to user's portal
    if str(extraction.hubspot_portal_id) != str(portal.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this extraction"
        )

    # Build response
    models_breakdown = None
    if extraction.models_usage and isinstance(extraction.models_usage, dict):
        breakdown = extraction.models_usage.get("models_breakdown", [])
        if breakdown:
            models_breakdown = [
                ModelUsageDetail(**model) for model in breakdown
            ]

    return ExtractionCostDetail(
        id=str(extraction.id),
        company_name=extraction.company_name,
        created_at=extraction.created_at,
        cost_usd=extraction.cost_usd,
        cost_eur=extraction.cost_eur,
        total_tokens=extraction.total_tokens,
        input_tokens=extraction.input_tokens,
        output_tokens=extraction.output_tokens,
        models_breakdown=models_breakdown,
        subsidiaries_count=extraction.subsidiaries_count,
        processing_time=extraction.processing_time,
            extraction_type=extraction.extraction_type,
    )


@router.get("/extraction/session/{session_id}", response_model=ExtractionCostDetail)
async def get_extraction_cost_by_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed cost information for a specific extraction by session_id.

    Returns comprehensive cost breakdown including:
    - Total costs in USD and EUR
    - Token usage (input/output)
    - Cost breakdown by AI model
    - Processing time and metadata

    **Permissions**: Users can only view extractions from their portal.
    """
    # Load extraction by session_id
    result = await db.execute(
        select(CompanyExtraction).where(CompanyExtraction.session_id == session_id)
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction not found"
        )

    # Verify extraction belongs to user's portal
    if str(extraction.hubspot_portal_id) != str(portal.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this extraction"
        )

    # Build response data
    response_data = {
        "id": str(extraction.id),
        "company_name": extraction.company_name,
        "created_at": extraction.created_at,
        "cost_usd": extraction.cost_usd,
        "cost_eur": extraction.cost_eur,
        "total_tokens": extraction.total_tokens,
        "input_tokens": extraction.input_tokens,
        "output_tokens": extraction.output_tokens,
        "models_breakdown": [],
        "subsidiaries_count": extraction.subsidiaries_count,
        "processing_time": extraction.processing_time,
        "extraction_type": extraction.extraction_type
    }

    # Add models breakdown if available
    if extraction.models_usage and isinstance(extraction.models_usage, dict):
        breakdown = extraction.models_usage.get("models_breakdown", [])
        response_data["models_breakdown"] = breakdown

    return ExtractionCostDetail(**response_data)


@router.get("/portal/current-month", response_model=MonthlyCostStats)
async def get_current_month_stats(
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost statistics for the current month.

    Convenience endpoint that returns stats for the current month automatically.

    **Permissions**: Any authenticated user can view their organization's current month stats.
    """
    now = datetime.now()

    stats = await cost_stats_service.get_monthly_costs(
        portal_id=str(portal.id),
        year=now.year,
        month=now.month,
        db=db
    )

    month_names = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    return MonthlyCostStats(
        **stats,
        year=now.year,
        month=now.month,
        month_name=month_names[now.month - 1]
    )


@router.get("/portal/budget-status")
async def get_budget_status(
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get budget status for the current month.

    Returns information about budget usage and remaining budget.

    **Permissions**: Any authenticated user can view their organization's budget status.
    """
    now = datetime.now()

    # Get current month stats
    stats = await cost_stats_service.get_monthly_costs(
        portal_id=str(portal.id),
        year=now.year,
        month=now.month,
        db=db
    )

    # Get portal budget (if set)
    monthly_budget = portal.max_searches_per_month  # You may want to add a budget_eur field

    # Calculate budget info
    # Note: You may want to add a monthly_budget_eur field to HubSpotPortal model
    # For now, we'll return basic info
    return {
        "hubspot_portal_id": str(portal.id),
        "portal_name": portal.name,
        "current_month": f"{now.year}-{now.month:02d}",
        "total_cost_eur": stats["total_cost_eur"],
        "total_searches": stats["total_searches"],
        "completed_searches": stats["completed_searches"],
        "average_cost_per_search_eur": stats["average_cost_per_search_eur"],
        # Budget info (to be implemented)
        "has_budget_limit": False,  # Set to True when monthly_budget_eur is added
        "monthly_budget_eur": None,  # Add this field to HubSpotPortal
        "remaining_budget_eur": None,
        "budget_usage_percentage": None,
        "warning_threshold_reached": False,  # 80% of budget
        "limit_reached": False  # 100% of budget
    }


@router.get("/health")
async def costs_health_check():
    """
    Health check for cost stats service.

    Verifies that the cost stats service is properly configured.
    """
    return {
        "status": "healthy",
        "service": "cost_stats",
        "version": "2.0",
        "note": "Cost calculation is handled by HierarchicalCostTracker"
    }


# ==========================================
#   ALIAS POUR COMPATIBILITÉ FRONTEND
# ==========================================
# Le frontend utilise "organization" mais l'API utilise "portal"
# On ajoute des alias pour éviter de casser le frontend


@router.get("/organization/current-month", response_model=MonthlyCostStats)
async def get_current_month_stats_alias(
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """Alias pour /portal/current-month (compatibilité frontend)"""
    return await get_current_month_stats(current_user, portal, db)


@router.get("/organization/monthly/{year}/{month}", response_model=MonthlyCostStats)
async def get_monthly_cost_stats_alias(
    year: int = Path(..., ge=2020, le=2100),
    month: int = Path(..., ge=1, le=12),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """Alias pour /portal/monthly/{year}/{month} (compatibilité frontend)"""
    return await get_monthly_cost_stats(year, month, current_user, portal, db)


@router.get("/organization/top-expensive", response_model=List[TopExpensiveSearch])
async def get_top_expensive_searches_alias(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """Alias pour /portal/top-expensive (compatibilité frontend)"""
    return await get_top_expensive_searches(limit, current_user, portal, db)


@router.get("/organization/budget-status")
async def get_budget_status_alias(
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """Alias pour /portal/budget-status (compatibilité frontend)"""
    return await get_budget_status(current_user, portal, db)
