"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from models.db_models import User, HubSpotPortal, UserRole
from services.jwt_service import jwt_service
from services.session_service import session_service


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify and decode token
    token_data = jwt_service.verify_token(token, token_type="access")

    # Verify session is active
    session = await session_service.get_session_by_token(token, db=db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database with eager loading of hubspot_portal
    result = await db.execute(
        select(User)
        .options(selectinload(User.hubspot_portal))
        .where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.

    Args:
        current_user: Current user from JWT

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require the current user to have admin role.

    Args:
        current_user: Current active user

    Returns:
        User object if admin

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def get_current_portal(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> HubSpotPortal:
    """
    Get the HubSpot portal of the current user.

    Args:
        current_user: Current active user
        db: Database session

    Returns:
        HubSpotPortal object

    Raises:
        HTTPException: If portal not found or inactive
    """
    portal = current_user.hubspot_portal

    if portal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal not found"
        )

    if not portal.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal is inactive"
        )

    return portal


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, or None.
    Useful for endpoints that can work both with and without authentication.

    Args:
        credentials: HTTP Authorization credentials (optional)
        db: Database session

    Returns:
        User object or None
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        token_data = jwt_service.verify_token(token, token_type="access")

        result = await db.execute(
            select(User)
            .options(selectinload(User.hubspot_portal))
            .where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        return user if user and user.is_active else None

    except (HTTPException, Exception):
        return None
