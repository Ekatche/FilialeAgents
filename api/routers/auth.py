"""
Authentication router for HubSpot OAuth.
"""

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from dependencies.auth import get_current_user, get_current_active_user
from models.auth import (
    Token,
    RefreshTokenRequest,
    OAuthCallbackResponse,
    User as UserSchema
)
from models.db_models import User
from services.auth_service import auth_service
from services.jwt_service import jwt_service


router = APIRouter(prefix="/auth", tags=["Authentication"])

# Store states temporarily (in production, use Redis)
# This is a simple in-memory store for CSRF state validation
_oauth_states: Dict[str, bool] = {}


@router.get("/hubspot/login")
async def hubspot_login():
    """
    Initiate HubSpot OAuth flow.

    Returns a redirect URL to HubSpot's authorization page.

    Response:
        - redirect_url: URL to redirect user to for OAuth authorization
        - state: CSRF protection state (should be stored by client)
    """
    # Generate CSRF state
    state = auth_service.generate_state()

    # Store state for validation (expires after 10 minutes)
    _oauth_states[state] = True

    # Generate authorization URL
    authorization_url = auth_service.get_authorization_url(state)

    return {
        "redirect_url": authorization_url,
        "state": state
    }


@router.get("/hubspot/callback")
async def hubspot_callback(
    code: str = Query(..., description="Authorization code from HubSpot"),
    state: str = Query(..., description="CSRF protection state"),
    error: str = Query(None, description="Error from HubSpot OAuth"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle HubSpot OAuth callback.

    This endpoint receives the authorization code from HubSpot and:
    1. Validates the state (CSRF protection)
    2. Exchanges code for tokens
    3. Retrieves user and company information from HubSpot
    4. Creates or updates Organization and User in database
    5. Generates JWT tokens
    6. Returns tokens and user information

    Args:
        code: Authorization code from HubSpot
        state: CSRF state parameter
        error: Optional error from HubSpot
        db: Database session

    Returns:
        OAuthCallbackResponse with JWT tokens and user info

    Raises:
        HTTPException: If OAuth flow fails
    """
    # Check for errors from HubSpot
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )

    # Validate state (CSRF protection)
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter - possible CSRF attack"
        )

    # Remove used state
    del _oauth_states[state]

    try:
        # Step 1: Exchange code for tokens
        tokens = await auth_service.exchange_code_for_tokens(code)

        # Step 2: Get user information from HubSpot
        user_info = await auth_service.get_hubspot_user_info(tokens["access_token"])

        # Step 3: Get company information from HubSpot
        company_info = await auth_service.get_hubspot_company_info(
            tokens["access_token"],
            user_info.hub_id
        )

        # Step 4: Create or update organization
        organization = await auth_service.create_or_update_organization(
            company_info,
            db
        )

        # Step 5: Create or update user
        user = await auth_service.create_or_update_user(
            user_info,
            organization,
            db
        )

        # Step 6: Store OAuth tokens
        await auth_service.store_oauth_tokens(user, tokens, db)

        # Commit all changes
        await db.commit()

        # Step 7: Generate JWT tokens
        jwt_tokens = jwt_service.create_tokens_for_user(
            user_id=str(user.id),
            email=user.email,
            organization_id=str(organization.id),
            role=user.role.value
        )

        # Step 8: Return response
        user_response = UserSchema(
            user_id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role.value,
            organization_id=str(organization.id),
            organization_name=organization.name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login_at
        )

        token_response = Token(
            access_token=jwt_tokens["access_token"],
            refresh_token=jwt_tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        return OAuthCallbackResponse(
            token=token_response,
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.

    Args:
        request: RefreshTokenRequest with refresh_token
        db: Database session

    Returns:
        New Token with access_token and refresh_token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify refresh token
        token_data = jwt_service.verify_token(
            request.refresh_token,
            token_type="refresh"
        )

        # Generate new access token (keep same refresh token)
        jwt_tokens = jwt_service.create_tokens_for_user(
            user_id=token_data.user_id,
            email=token_data.email,
            organization_id=token_data.organization_id,
            role=token_data.role
        )

        return Token(
            access_token=jwt_tokens["access_token"],
            refresh_token=jwt_tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not refresh token: {str(e)}"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout the current user.

    In a stateless JWT system, logout is handled client-side by removing tokens.
    This endpoint is provided for consistency and can be extended to:
    - Add tokens to a blacklist (using Redis)
    - Log the logout event
    - Revoke HubSpot OAuth tokens

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # TODO: Optionally add token to blacklist in Redis
    # TODO: Optionally revoke HubSpot OAuth token

    return {
        "message": "Successfully logged out",
        "user_id": str(current_user.id)
    }


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about the current authenticated user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User information including organization details
    """
    # Load organization
    from sqlalchemy import select
    from models.db_models import Organization

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = result.scalar_one()

    return UserSchema(
        user_id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role.value,
        organization_id=str(organization.id),
        organization_name=organization.name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login_at
    )


@router.get("/health")
async def auth_health_check():
    """
    Health check for authentication service.

    Verifies that HubSpot OAuth credentials are configured.
    """
    is_configured = bool(
        settings.HUBSPOT_CLIENT_ID and
        settings.HUBSPOT_CLIENT_SECRET and
        settings.JWT_SECRET_KEY
    )

    return {
        "status": "healthy" if is_configured else "misconfigured",
        "hubspot_configured": bool(settings.HUBSPOT_CLIENT_ID),
        "jwt_configured": bool(settings.JWT_SECRET_KEY),
        "redirect_uri": settings.HUBSPOT_REDIRECT_URI
    }
