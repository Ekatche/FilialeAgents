"""Authentication Pydantic models for OAuth and JWT."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class HubSpotPortalInfo(BaseModel):
    """HubSpot Portal information from OAuth."""

    hubspot_portal_id: int = Field(..., description="HubSpot portal/hub ID")
    name: str = Field(..., description="Portal name")
    domain: Optional[str] = Field(None, description="Portal domain")
    timezone: Optional[str] = Field(None, description="Portal timezone")


class HubSpotUserInfo(BaseModel):
    """HubSpot user information from OAuth."""

    user_id: str = Field(..., description="HubSpot user ID")
    email: EmailStr = Field(..., description="User email address")
    user: Optional[str] = Field(None, description="HubSpot user identifier")
    hub_id: Optional[int] = Field(None, description="HubSpot hub/portal ID")
    hub_domain: Optional[str] = Field(None, description="HubSpot hub domain")


class OAuthToken(BaseModel):
    """OAuth token information."""

    access_token: str = Field(..., description="HubSpot OAuth access token")
    refresh_token: str = Field(..., description="HubSpot OAuth refresh token")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    token_type: str = Field(default="bearer", description="Token type")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Token creation timestamp")

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        # Add 60 seconds buffer for clock skew
        return elapsed >= (self.expires_in - 60)


class User(BaseModel):
    """User model for API responses."""

    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    role: str = Field(..., description="User role in portal")
    portal_id: str = Field(..., description="HubSpot Portal ID")
    portal_name: str = Field(..., description="HubSpot Portal name")
    is_active: bool = Field(True, description="User active status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="User creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        from_attributes = True


class UserInDB(User):
    """User model with additional fields stored in database."""

    oauth_token: Optional[OAuthToken] = Field(None, description="OAuth token information")


class TokenData(BaseModel):
    """JWT token payload data."""

    user_id: str = Field(..., description="User ID from token")
    email: Optional[EmailStr] = Field(None, description="User email from token")
    portal_id: Optional[str] = Field(None, description="HubSpot Portal ID from token")
    role: Optional[str] = Field(None, description="User role from token")
    exp: Optional[datetime] = Field(None, description="Token expiration time")


class Token(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Request to refresh an access token."""

    refresh_token: str = Field(..., description="JWT refresh token")


class OAuthCallbackResponse(BaseModel):
    """Response from OAuth callback with tokens and user info."""

    token: Token = Field(..., description="JWT tokens")
    user: User = Field(..., description="User information")


class PortalInfoResponse(BaseModel):
    """Detailed HubSpot Portal information."""

    id: str = Field(..., description="Portal UUID")
    hubspot_portal_id: int = Field(..., description="HubSpot portal/hub ID")
    name: str = Field(..., description="Portal name")
    domain: Optional[str] = Field(None, description="Portal domain")
    timezone: Optional[str] = Field(None, description="Portal timezone")
    is_active: bool = Field(..., description="Portal active status")
    created_at: datetime = Field(..., description="Portal creation timestamp")
    updated_at: datetime = Field(..., description="Portal last update timestamp")
    settings: Optional[dict] = Field(None, description="Portal settings JSON")

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""

    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")


class UserPreferences(BaseModel):
    """User preferences for notifications and UI."""

    email_notifications: bool = Field(True, description="Enable email notifications")
    push_notifications: bool = Field(False, description="Enable push notifications")
    weekly_report: bool = Field(True, description="Receive weekly activity report")
    dark_mode: bool = Field(False, description="Enable dark mode")
    auto_save: bool = Field(True, description="Auto-save analyses")


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""

    email_notifications: Optional[bool] = Field(None, description="Enable email notifications")
    push_notifications: Optional[bool] = Field(None, description="Enable push notifications")
    weekly_report: Optional[bool] = Field(None, description="Receive weekly activity report")
    dark_mode: Optional[bool] = Field(None, description="Enable dark mode")
    auto_save: Optional[bool] = Field(None, description="Auto-save analyses")


class UserProfileResponse(BaseModel):
    """Complete user profile with preferences."""

    user: User = Field(..., description="User information")
    preferences: UserPreferences = Field(..., description="User preferences")

    class Config:
        from_attributes = True
