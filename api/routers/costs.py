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
    get_current_organization,
    require_admin
)
from models.db_models import User, Organization, CompanyExtraction
from models.costs import (
    OrganizationCostStats,
    MonthlyCostStats,
    CostEstimateRequest,
    CostEstimateResponse,
    TopExpensiveSearch,
    ExtractionCostDetail,
    ModelUsageDetail
)
from services.cost_tracking_service import cost_tracking_service


router = APIRouter(prefix="/costs", tags=["Cost Tracking"])


@router.get("/organization/stats", response_model=OrganizationCostStats)
async def get_organization_cost_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost statistics for the current user's organization.

    Returns aggregated cost data for all extractions within the specified date range.
    If no dates are provided, returns statistics for all time.

    **Permissions**: Any authenticated user can view their organization's stats.
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
    stats = await cost_tracking_service.get_organization_costs(
        organization_id=str(organization.id),
        start_date=start_datetime,
        end_date=end_datetime,
        db=db
    )

    return OrganizationCostStats(**stats)


@router.get("/organization/monthly/{year}/{month}", response_model=MonthlyCostStats)
async def get_monthly_cost_stats(
    year: int = Path(..., ge=2020, le=2100, description="Year"),
    month: int = Path(..., ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost statistics for a specific month.

    Returns detailed cost breakdown for the specified month and year.

    **Permissions**: Any authenticated user can view their organization's monthly stats.
    """
    # Get monthly statistics
    stats = await cost_tracking_service.get_monthly_costs(
        organization_id=str(organization.id),
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


@router.get("/organization/top-expensive", response_model=List[TopExpensiveSearch])
async def get_top_expensive_searches(
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the most expensive searches for the organization.

    Returns a list of extractions sorted by cost (descending).

    **Permissions**: Any authenticated user can view their organization's expensive searches.
    """
    searches = await cost_tracking_service.get_top_expensive_searches(
        organization_id=str(organization.id),
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
    estimate = cost_tracking_service.estimate_search_cost(
        extraction_type=request.extraction_type,
        has_subsidiaries=request.has_subsidiaries,
        subsidiaries_count=request.subsidiaries_count
    )

    return CostEstimateResponse(**estimate)


@router.get("/extraction/{extraction_id}", response_model=ExtractionCostDetail)
async def get_extraction_cost_detail(
    extraction_id: str,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed cost information for a specific extraction.

    Returns comprehensive cost breakdown including:
    - Total costs in USD and EUR
    - Token usage (input/output)
    - Cost breakdown by AI model
    - Processing time and metadata

    **Permissions**: Users can only view extractions from their organization.
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

    # Verify extraction belongs to user's organization
    if str(extraction.organization_id) != str(organization.id):
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
        extraction_type=extraction.extraction_type.value
    )


@router.get("/extraction/session/{session_id}", response_model=ExtractionCostDetail)
async def get_extraction_cost_by_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed cost information for a specific extraction by session_id.

    Returns comprehensive cost breakdown including:
    - Total costs in USD and EUR
    - Token usage (input/output)
    - Cost breakdown by AI model
    - Processing time and metadata

    **Permissions**: Users can only view extractions from their organization.
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

    # Verify extraction belongs to user's organization
    if str(extraction.organization_id) != str(organization.id):
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
        "extraction_type": extraction.extraction_type.value
    }

    # Add models breakdown if available
    if extraction.models_usage and isinstance(extraction.models_usage, dict):
        breakdown = extraction.models_usage.get("models_breakdown", [])
        response_data["models_breakdown"] = breakdown

    return ExtractionCostDetail(**response_data)


@router.get("/organization/current-month", response_model=MonthlyCostStats)
async def get_current_month_stats(
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cost statistics for the current month.

    Convenience endpoint that returns stats for the current month automatically.

    **Permissions**: Any authenticated user can view their organization's current month stats.
    """
    now = datetime.now()

    stats = await cost_tracking_service.get_monthly_costs(
        organization_id=str(organization.id),
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


@router.get("/organization/budget-status")
async def get_budget_status(
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get budget status for the current month.

    Returns information about budget usage and remaining budget.

    **Permissions**: Any authenticated user can view their organization's budget status.
    """
    now = datetime.now()

    # Get current month stats
    stats = await cost_tracking_service.get_monthly_costs(
        organization_id=str(organization.id),
        year=now.year,
        month=now.month,
        db=db
    )

    # Get organization budget (if set)
    monthly_budget = organization.max_searches_per_month  # You may want to add a budget_eur field

    # Calculate budget info
    # Note: You should add a monthly_budget_eur field to Organization model
    # For now, we'll return basic info
    return {
        "organization_id": str(organization.id),
        "organization_name": organization.name,
        "current_month": f"{now.year}-{now.month:02d}",
        "total_cost_eur": stats["total_cost_eur"],
        "total_searches": stats["total_searches"],
        "completed_searches": stats["completed_searches"],
        "average_cost_per_search_eur": stats["average_cost_per_search_eur"],
        # Budget info (to be implemented)
        "has_budget_limit": False,  # Set to True when monthly_budget_eur is added
        "monthly_budget_eur": None,  # Add this field to Organization
        "remaining_budget_eur": None,
        "budget_usage_percentage": None,
        "warning_threshold_reached": False,  # 80% of budget
        "limit_reached": False  # 100% of budget
    }


@router.get("/health")
async def costs_health_check():
    """
    Health check for cost tracking service.

    Verifies that the cost tracking service is properly configured.
    """
    from services.cost_tracking_service import ModelPricing

    return {
        "status": "healthy",
        "models_configured": ["gpt-4o", "gpt-4o-mini", "gpt-4o-search-preview", "sonar-pro"],
        "exchange_rate_usd_to_eur": float(ModelPricing.USD_TO_EUR_RATE),
        "service": "cost_tracking",
        "version": "1.0"
    }
