"""Models package for authentication and user management."""

from .auth import (
    User as UserSchema,
    UserInDB,
    OAuthToken as OAuthTokenSchema,
    TokenData,
    Token,
    HubSpotUserInfo,
    HubSpotPortalInfo,
    RefreshTokenRequest,
    OAuthCallbackResponse,
)

from .db_models import (
    HubSpotPortal,
    User,
    OAuthToken,
    CompanyExtraction,
    PortalUsage,
    UserRole,
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
    "HubSpotPortalInfo",
    "RefreshTokenRequest",
    "OAuthCallbackResponse",
    # SQLAlchemy models
    "HubSpotPortal",
    "User",
    "OAuthToken",
    "CompanyExtraction",
    "PortalUsage",
    # Enums
    "UserRole",
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
