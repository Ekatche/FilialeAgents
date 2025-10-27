"""
HubSpot OAuth Authentication Service.
"""

import secrets
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from core.config import settings
from models.db_models import Organization, User, OAuthToken, UserRole
from models.auth import HubSpotUserInfo


class AuthService:
    """Service for HubSpot OAuth authentication."""

    def __init__(self):
        """Initialize auth service with encryption key."""
        # Generate or load encryption key for tokens
        # In production, store this in environment variable or secret manager
        self._encryption_key = settings.JWT_SECRET_KEY.encode()[:32].ljust(32, b'0')
        self._cipher = Fernet(Fernet.generate_key())

    def encrypt_token(self, token: str) -> str:
        """Encrypt a token before storing in database."""
        return self._cipher.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token from database."""
        return self._cipher.decrypt(encrypted_token.encode()).decode()

    def generate_state(self) -> str:
        """Generate a random state for CSRF protection."""
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str) -> str:
        """
        Generate HubSpot OAuth authorization URL.

        Args:
            state: CSRF protection state parameter

        Returns:
            Complete authorization URL
        """
        params = {
            "client_id": settings.HUBSPOT_CLIENT_ID,
            "redirect_uri": settings.HUBSPOT_REDIRECT_URI,
            "scope": " ".join(settings.HUBSPOT_SCOPES),
            "state": state,
        }

        base_url = "https://app.hubspot.com/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from HubSpot

        Returns:
            Dictionary with access_token, refresh_token, expires_in

        Raises:
            HTTPException: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.HUBSPOT_CLIENT_ID,
            "client_secret": settings.HUBSPOT_CLIENT_SECRET,
            "redirect_uri": settings.HUBSPOT_REDIRECT_URI,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.hubapi.com/oauth/v1/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for tokens: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error during token exchange: {str(e)}"
                )

    async def get_hubspot_user_info(self, access_token: str) -> HubSpotUserInfo:
        """
        Get user information from HubSpot.

        Args:
            access_token: HubSpot access token

        Returns:
            HubSpotUserInfo object

        Raises:
            HTTPException: If API call fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                # Get access token info (includes user_id and hub_id)
                response = await client.get(
                    "https://api.hubapi.com/oauth/v1/access-tokens/" + access_token,
                    headers=headers
                )
                response.raise_for_status()
                token_info = response.json()

                # Get user details
                user_id = token_info.get("user_id") or token_info.get("user")
                hub_id = token_info.get("hub_id")

                # Try to get user email from user details endpoint
                user_response = await client.get(
                    f"https://api.hubapi.com/settings/v3/users/{user_id}",
                    headers=headers
                )

                if user_response.status_code == 200:
                    user_data = user_response.json()
                    email = user_data.get("email")
                else:
                    # Fallback: use user_id as email if endpoint fails
                    email = f"{user_id}@hubspot.temp"

                return HubSpotUserInfo(
                    user_id=str(user_id),
                    email=email,
                    user=token_info.get("user"),
                    hub_id=hub_id,
                    hub_domain=token_info.get("hub_domain")
                )

            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get user info: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error getting user info: {str(e)}"
                )

    async def get_hubspot_company_info(
        self,
        access_token: str,
        hub_id: int
    ) -> Dict[str, Any]:
        """
        Get company information from HubSpot.

        Args:
            access_token: HubSpot access token
            hub_id: HubSpot portal/hub ID

        Returns:
            Dictionary with company information

        Raises:
            HTTPException: If API call fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                # Get account details
                response = await client.get(
                    f"https://api.hubapi.com/account-info/v3/details",
                    headers=headers
                )
                response.raise_for_status()
                account_info = response.json()

                return {
                    "company_id": str(hub_id),
                    "name": account_info.get("companyName", f"HubSpot Account {hub_id}"),
                    "domain": account_info.get("companyCurrency", ""),  # ou autre champ pertinent
                }

            except httpx.HTTPStatusError as e:
                # If API fails, return basic info
                return {
                    "company_id": str(hub_id),
                    "name": f"HubSpot Account {hub_id}",
                    "domain": ""
                }
            except Exception as e:
                # Fallback to basic info
                return {
                    "company_id": str(hub_id),
                    "name": f"HubSpot Account {hub_id}",
                    "domain": ""
                }

    async def create_or_update_organization(
        self,
        company_info: Dict[str, Any],
        db: AsyncSession
    ) -> Organization:
        """
        Create or update an organization from HubSpot company data.

        Args:
            company_info: Company information from HubSpot
            db: Database session

        Returns:
            Organization object
        """
        hubspot_company_id = company_info["company_id"]

        # Check if organization exists
        result = await db.execute(
            select(Organization).where(
                Organization.hubspot_company_id == hubspot_company_id
            )
        )
        organization = result.scalar_one_or_none()

        if organization:
            # Update existing organization
            organization.name = company_info.get("name", organization.name)
            organization.domain = company_info.get("domain", organization.domain)
            organization.updated_at = datetime.utcnow()
        else:
            # Create new organization
            organization = Organization(
                hubspot_company_id=hubspot_company_id,
                name=company_info.get("name", f"HubSpot Account {hubspot_company_id}"),
                domain=company_info.get("domain", ""),
                plan_type="free",  # Default plan
                max_searches_per_month=10,  # Default limit
                is_active=True
            )
            db.add(organization)

        await db.flush()
        return organization

    async def determine_user_role(
        self,
        hubspot_user_id: str,
        organization: Organization,
        db: AsyncSession
    ) -> UserRole:
        """
        Determine user role based on organization.

        Rules:
        - First user in organization = ADMIN
        - All other users = MEMBER

        Args:
            hubspot_user_id: HubSpot user ID
            organization: Organization object
            db: Database session

        Returns:
            UserRole enum
        """
        # Count existing users in organization
        result = await db.execute(
            select(User).where(User.organization_id == organization.id)
        )
        existing_users = result.scalars().all()

        if len(existing_users) == 0:
            # First user = ADMIN
            return UserRole.ADMIN
        else:
            # Check if this user already exists with ADMIN role
            for user in existing_users:
                if user.hubspot_user_id == hubspot_user_id:
                    return user.role

            # New user = MEMBER
            return UserRole.MEMBER

    async def create_or_update_user(
        self,
        user_info: HubSpotUserInfo,
        organization: Organization,
        db: AsyncSession
    ) -> User:
        """
        Create or update a user from HubSpot user data.

        Args:
            user_info: User information from HubSpot
            organization: Organization the user belongs to
            db: Database session

        Returns:
            User object
        """
        # Check if user exists
        result = await db.execute(
            select(User).where(User.hubspot_user_id == user_info.user_id)
        )
        user = result.scalar_one_or_none()

        # Determine role
        role = await self.determine_user_role(
            user_info.user_id,
            organization,
            db
        )

        if user:
            # Update existing user
            user.email = user_info.email
            user.organization_id = organization.id
            user.last_login_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            # Keep existing role if user already exists
        else:
            # Create new user
            user = User(
                hubspot_user_id=user_info.user_id,
                email=user_info.email,
                organization_id=organization.id,
                role=role,
                is_active=True,
                last_login_at=datetime.utcnow()
            )
            db.add(user)

        await db.flush()
        return user

    async def store_oauth_tokens(
        self,
        user: User,
        tokens: Dict[str, Any],
        db: AsyncSession
    ) -> OAuthToken:
        """
        Store or update OAuth tokens for a user.

        Args:
            user: User object
            tokens: Token data from HubSpot
            db: Database session

        Returns:
            OAuthToken object
        """
        # Calculate expiration time
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Encrypt tokens
        encrypted_access = self.encrypt_token(tokens["access_token"])
        encrypted_refresh = self.encrypt_token(tokens["refresh_token"])

        # Check if token exists
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.user_id == user.id)
        )
        oauth_token = result.scalar_one_or_none()

        if oauth_token:
            # Update existing token
            oauth_token.access_token = encrypted_access
            oauth_token.refresh_token = encrypted_refresh
            oauth_token.expires_at = expires_at
            oauth_token.scope = tokens.get("scope", "")
            oauth_token.updated_at = datetime.utcnow()
        else:
            # Create new token
            oauth_token = OAuthToken(
                user_id=user.id,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                token_type=tokens.get("token_type", "bearer"),
                expires_at=expires_at,
                scope=tokens.get("scope", "")
            )
            db.add(oauth_token)

        await db.flush()
        return oauth_token

    async def refresh_oauth_token(
        self,
        user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Refresh HubSpot OAuth token.

        Args:
            user: User object
            db: Database session

        Returns:
            New token data

        Raises:
            HTTPException: If refresh fails
        """
        # Get current token
        result = await db.execute(
            select(OAuthToken).where(OAuthToken.user_id == user.id)
        )
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No OAuth token found for user"
            )

        # Decrypt refresh token
        refresh_token = self.decrypt_token(oauth_token.refresh_token)

        # Request new tokens from HubSpot
        data = {
            "grant_type": "refresh_token",
            "client_id": settings.HUBSPOT_CLIENT_ID,
            "client_secret": settings.HUBSPOT_CLIENT_SECRET,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.hubapi.com/oauth/v1/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                new_tokens = response.json()

                # Store new tokens
                await self.store_oauth_tokens(user, new_tokens, db)

                return new_tokens

            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Failed to refresh token: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error refreshing token: {str(e)}"
                )


# Global instance
auth_service = AuthService()
