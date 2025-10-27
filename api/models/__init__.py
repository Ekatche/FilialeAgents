"""Models package for authentication and user management."""

from .auth import (
    User as UserSchema,
    UserInDB,
    OAuthToken as OAuthTokenSchema,
    TokenData,
    Token,
    HubSpotUserInfo,
    RefreshTokenRequest,
    OAuthCallbackResponse,
)

from .db_models import (
    Organization,
    User,
    OAuthToken,
    CompanyExtraction,
    OrganizationUsage,
    UserRole,
    PlanType,
    ExtractionStatus,
    ExtractionType,
)

from .costs import (
    ModelUsageDetail,
    ExtractionCostDetail,
    OrganizationCostStats,
    MonthlyCostStats,
    CostEstimateRequest,
    CostEstimateResponse,
    TopExpensiveSearch,
    CostTrend,
    CostDistributionByModel,
)

__all__ = [
    # Pydantic schemas
    "UserSchema",
    "UserInDB",
    "OAuthTokenSchema",
    "TokenData",
    "Token",
    "HubSpotUserInfo",
    "RefreshTokenRequest",
    "OAuthCallbackResponse",
    # SQLAlchemy models
    "Organization",
    "User",
    "OAuthToken",
    "CompanyExtraction",
    "OrganizationUsage",
    # Enums
    "UserRole",
    "PlanType",
    "ExtractionStatus",
    "ExtractionType",
    # Cost models
    "ModelUsageDetail",
    "ExtractionCostDetail",
    "OrganizationCostStats",
    "MonthlyCostStats",
    "CostEstimateRequest",
    "CostEstimateResponse",
    "TopExpensiveSearch",
    "CostTrend",
    "CostDistributionByModel",
]
