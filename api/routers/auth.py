"""
Authentication router for HubSpot OAuth.
"""

from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from dependencies.auth import get_current_user, get_current_active_user, get_current_portal
from services.session_service import session_service
from models.auth import (
    Token,
    RefreshTokenRequest,
    OAuthCallbackResponse,
    User as UserSchema,
    PortalInfoResponse,
    UpdateProfileRequest,
    UserPreferences,
    UpdatePreferencesRequest,
    UserProfileResponse
)
from models.db_models import User, HubSpotPortal
from services.auth_service import auth_service
from services.jwt_service import jwt_service


router = APIRouter(prefix="/auth", tags=["Authentication"])

# HTTP Bearer token scheme
security = HTTPBearer()

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
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle HubSpot OAuth callback.

    This endpoint receives the authorization code from HubSpot and:
    1. Validates the state (CSRF protection)
    2. Exchanges code for tokens
    3. Retrieves user and company information from HubSpot
    4. Creates or updates HubSpot Portal and User in database
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

        if not user_info.hub_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HubSpot hub_id not found in token info"
            )

        # Step 3: Get portal information from HubSpot
        portal_info = await auth_service.get_hubspot_portal_info(
            tokens["access_token"],
            user_info.hub_id
        )

        # Step 4: Create or update HubSpot portal
        hubspot_portal = await auth_service.create_or_update_hubspot_portal(
            portal_info,
            db
        )

        # Step 5: Create or update user (lié au portail)
        user = await auth_service.create_or_update_user(
            user_info,
            hubspot_portal,
            db
        )

        # Step 6: Store OAuth tokens
        await auth_service.store_oauth_tokens(user, tokens, db)

        # Commit all changes
        await db.commit()

        # Step 6: Generate JWT tokens
        jwt_tokens = jwt_service.create_tokens_for_user(
            user_id=str(user.id),
            email=user.email,
            portal_id=str(hubspot_portal.id),
            role=user.role
        )

        # Step 6.5: Create session for tracking
        try:
            # Récupérer IP et user agent si disponible
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            await session_service.create_session(
                user_id=str(user.id),
                access_token=jwt_tokens["access_token"],
                refresh_token=jwt_tokens["refresh_token"],
                auth_method="hubspot",
                ip_address=ip_address,
                user_agent=user_agent,
                db=db
            )
        except Exception as e:
            # Log error but don't fail authentication
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Erreur création session (non bloquant): {e}")

        # Step 7: Return response
        user_response = UserSchema(
            user_id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            portal_id=str(hubspot_portal.id),
            portal_name=hubspot_portal.name,
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

        # Generate new access token and refresh token
        jwt_tokens = jwt_service.create_tokens_for_user(
            user_id=token_data.user_id,
            email=token_data.email,
            portal_id=token_data.portal_id,
            role=token_data.role
        )

        # Update session with new tokens
        try:
            # Update access token hash
            session = await session_service.update_session_token(
                refresh_token=request.refresh_token,
                new_access_token=jwt_tokens["access_token"],
                db=db
            )
            # Also update refresh token hash if a new refresh token was generated
            if session and jwt_tokens.get("refresh_token") != request.refresh_token:
                await session_service.update_session_refresh_token(
                    old_refresh_token=request.refresh_token,
                    new_refresh_token=jwt_tokens["refresh_token"],
                    db=db
                )
        except Exception as e:
            # Log error but don't fail token refresh
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Erreur mise à jour session lors du refresh (non bloquant): {e}")

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
    current_user: User = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout the current user.

    This endpoint revokes the current session.

    **Permissions**: Any authenticated user can logout.
    """
    # Revoke the current session
    token = credentials.credentials
    await session_service.revoke_session(token, db=db)
    
    return {
        "message": "Successfully logged out",
        "user_id": str(current_user.id)
    }


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal)
):
    """
    Get information about the current authenticated user.

    Returns user information including portal details.

    **Permissions**: Any authenticated user can access their own information.
    """
    return UserSchema(
        user_id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        portal_id=str(portal.id),
        portal_name=portal.name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login_at
    )


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active sessions for the current user.
    
    Returns a list of active sessions with metadata.
    
    **Permissions**: Users can only view their own sessions.
    """
    sessions = await session_service.get_user_sessions(
        user_id=str(current_user.id),
        active_only=True,
        db=db
    )
    
    return [
        {
            "id": str(session.id),
            "auth_method": session.auth_method,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "created_at": session.created_at.isoformat(),
            "last_activity_at": session.last_activity_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
        }
        for session in sessions
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke a specific session.
    
    Users can only revoke their own sessions.
    
    **Permissions**: Users can only revoke their own sessions.
    """
    success = await session_service.revoke_session_by_id(
        session_id=session_id,
        user_id=str(current_user.id),
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already revoked"
        )
    
    return {
        "message": "Session revoked successfully",
        "session_id": session_id
    }


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke all active sessions for the current user.
    
    This will log out the user from all devices.
    
    **Permissions**: Users can only revoke their own sessions.
    """
    count = await session_service.revoke_all_user_sessions(
        user_id=str(current_user.id),
        db=db
    )
    
    return {
        "message": f"Revoked {count} session(s)",
        "count": count
    }


@router.get("/portal", response_model=PortalInfoResponse)
async def get_current_portal_info(
    portal: HubSpotPortal = Depends(get_current_portal)
):
    """
    Get information about the current user's HubSpot Portal.

    Returns detailed portal information including plan, settings, and limits.

    **Permissions**: Any authenticated user can access their portal's information.
    """
    return PortalInfoResponse(
        id=str(portal.id),
        hubspot_portal_id=portal.hubspot_portal_id,
        name=portal.name,
        domain=portal.domain,
        timezone=portal.timezone,
        is_active=portal.is_active,
        created_at=portal.created_at,
        updated_at=portal.updated_at,
        settings=portal.settings
    )


@router.put("/profile", response_model=UserSchema)
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    portal: HubSpotPortal = Depends(get_current_portal),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile.

    Allows users to update their first_name and last_name.

    **Permissions**: Any authenticated user can update their own profile.
    """
    # Update user fields
    if request.first_name is not None:
        current_user.first_name = request.first_name
    if request.last_name is not None:
        current_user.last_name = request.last_name

    # Save changes
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return UserSchema(
        user_id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        portal_id=str(portal.id),
        portal_name=portal.name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login_at
    )


@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current user's preferences.

    Returns user preferences for notifications and UI settings.
    Note: Currently returns default values. Preferences are stored client-side.

    **Permissions**: Any authenticated user can access their preferences.
    """
    # TODO: Store preferences in database when implementing notification system
    # For now, return defaults (preferences are stored client-side)
    return UserPreferences(
        email_notifications=True,
        push_notifications=False,
        weekly_report=True,
        dark_mode=False,
        auto_save=True
    )


@router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's preferences.

    Allows users to configure notification and UI preferences.
    Note: Currently stored client-side. Backend storage will be added with notification system.

    **Permissions**: Any authenticated user can update their preferences.
    """
    # TODO: Store in database when implementing notification system
    # For now, just echo back the values (client will store in localStorage)
    return UserPreferences(
        email_notifications=request.email_notifications if request.email_notifications is not None else True,
        push_notifications=request.push_notifications if request.push_notifications is not None else False,
        weekly_report=request.weekly_report if request.weekly_report is not None else True,
        dark_mode=request.dark_mode if request.dark_mode is not None else False,
        auto_save=request.auto_save if request.auto_save is not None else True
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
