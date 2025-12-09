"""Pydantic models for cost tracking and statistics."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ModelUsageDetail(BaseModel):
    """Detail of usage for a specific model."""

    model: str = Field(..., description="Model name (e.g., 'gpt-4o', 'gpt-4o-mini')")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    cost_usd: float = Field(..., description="Cost in USD")
    cost_eur: float = Field(..., description="Cost in EUR")


class ExtractionCostDetail(BaseModel):
    """Detailed cost information for an extraction."""

    id: str = Field(..., description="Extraction ID")
    company_name: str = Field(..., description="Company name")
    created_at: datetime = Field(..., description="Extraction creation date")
    cost_usd: Optional[float] = Field(None, description="Total cost in USD")
    cost_eur: Optional[float] = Field(None, description="Total cost in EUR")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    input_tokens: Optional[int] = Field(None, description="Input tokens")
    output_tokens: Optional[int] = Field(None, description="Output tokens")
    models_breakdown: Optional[List[ModelUsageDetail]] = Field(None, description="Breakdown by model")
    subsidiaries_count: int = Field(0, description="Number of subsidiaries extracted")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    extraction_type: str = Field(..., description="Type of extraction")

    class Config:
        from_attributes = True


class OrganizationCostStats(BaseModel):
    """Cost statistics for an organization (portal)."""

    portal_id: str = Field(..., description="HubSpot Portal ID", serialization_alias="organization_id")
    total_searches: int = Field(..., description="Total number of searches")
    completed_searches: int = Field(..., description="Number of completed searches")
    total_cost_eur: float = Field(..., description="Total cost in EUR")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    total_tokens: int = Field(..., description="Total tokens used")
    average_cost_per_search_eur: float = Field(..., description="Average cost per search in EUR")
    start_date: Optional[str] = Field(None, description="Start date of the period")
    end_date: Optional[str] = Field(None, description="End date of the period")
    
    model_config = {"populate_by_name": True}  # Permet d'utiliser portal_id ou organization_id lors de la désérialisation


class MonthlyCostStats(OrganizationCostStats):
    """Monthly cost statistics."""

    year: int = Field(..., description="Year")
    month: int = Field(..., description="Month (1-12)")
    month_name: str = Field(..., description="Month name")


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""

    extraction_type: str = Field(
        "simple",
        description="Type of extraction: 'simple' or 'advanced'"
    )
    has_subsidiaries: bool = Field(True, description="Whether the company has subsidiaries")
    subsidiaries_count: int = Field(5, ge=0, le=100, description="Estimated number of subsidiaries")


class CostEstimateResponse(BaseModel):
    """Response with cost estimation."""

    total_input_tokens: int = Field(..., description="Estimated input tokens")
    total_output_tokens: int = Field(..., description="Estimated output tokens")
    total_tokens: int = Field(..., description="Total estimated tokens")
    total_cost_usd: float = Field(..., description="Estimated cost in USD")
    total_cost_eur: float = Field(..., description="Estimated cost in EUR")
    models_breakdown: List[ModelUsageDetail] = Field(..., description="Breakdown by model")
    exchange_rate: float = Field(..., description="USD to EUR exchange rate")
    estimate_type: str = Field("approximate", description="Type of estimate")
    extraction_type: str = Field(..., description="Type of extraction")
    estimated_subsidiaries: int = Field(..., description="Number of subsidiaries estimated")


class TopExpensiveSearch(BaseModel):
    """Information about an expensive search."""

    id: str = Field(..., description="Extraction ID")
    company_name: str = Field(..., description="Company name")
    created_at: str = Field(..., description="Creation date (ISO format)")
    cost_eur: float = Field(..., description="Cost in EUR")
    cost_usd: float = Field(..., description="Cost in USD")
    total_tokens: int = Field(..., description="Total tokens used")
    subsidiaries_count: int = Field(..., description="Number of subsidiaries")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")


class CostTrend(BaseModel):
    """Cost trend for a period."""

    period: str = Field(..., description="Period identifier (e.g., '2025-01', 'Week 1')")
    total_cost_eur: float = Field(..., description="Total cost for the period")
    searches_count: int = Field(..., description="Number of searches")
    average_cost_eur: float = Field(..., description="Average cost per search")


class CostDistributionByModel(BaseModel):
    """Cost distribution by AI model."""

    model: str = Field(..., description="Model name")
    total_cost_eur: float = Field(..., description="Total cost in EUR")
    total_tokens: int = Field(..., description="Total tokens used")
    usage_count: int = Field(..., description="Number of times used")
    percentage: float = Field(..., description="Percentage of total cost")


class ExtractionListItem(BaseModel):
    """Lightweight model for extraction list (without full extraction_data)."""

    id: str = Field(..., description="Extraction ID")
    session_id: str = Field(..., description="Session ID")
    company_name: str = Field(..., description="Company name")
    company_url: Optional[str] = Field(None, description="Company URL")
    extraction_type: str = Field(..., description="Type of extraction (name/url)")
    status: str = Field(..., description="Extraction status")
    created_at: datetime = Field(..., description="Creation date")
    completed_at: Optional[datetime] = Field(None, description="Completion date")
    cost_eur: Optional[float] = Field(None, description="Cost in EUR")
    cost_usd: Optional[float] = Field(None, description="Cost in USD")
    total_tokens: Optional[int] = Field(None, description="Total tokens")
    subsidiaries_count: int = Field(0, description="Number of subsidiaries")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        from_attributes = True


class ExtractionListResponse(BaseModel):
    """Paginated response for extraction list."""

    items: List[ExtractionListItem] = Field(..., description="List of extractions")
    total: int = Field(..., description="Total number of extractions")
    page: int = Field(..., description="Current page (1-indexed)")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class DashboardStats(BaseModel):
    """Consolidated dashboard statistics."""

    # Current month stats
    current_month: MonthlyCostStats = Field(..., description="Current month statistics")

    # Recent searches (last 5)
    recent_searches: List[ExtractionListItem] = Field(..., description="Recent extractions")

    # Quick stats
    total_searches_all_time: int = Field(..., description="Total searches all time")
    success_rate: float = Field(..., description="Success rate (0-1)")
