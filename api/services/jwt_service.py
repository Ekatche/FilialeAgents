"""
JWT Service for token generation and validation.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from fastapi import HTTPException, status

from core.config import settings
from models.auth import TokenData


class JWTService:
    """Service for handling JWT token operations."""

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Dictionary containing the token payload
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token with longer expiration.

        Args:
            data: Dictionary containing the token payload

        Returns:
            Encoded JWT refresh token string
        """
        to_encode = data.copy()

        expire = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> TokenData:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string to verify
            token_type: Expected token type ("access" or "refresh")

        Returns:
            TokenData object with user information

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Extract user data
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials - missing user_id",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token_data = TokenData(
                user_id=user_id,
                email=payload.get("email"),
                organization_id=payload.get("organization_id"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None
            )

            return token_data

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode a JWT token without verification (use with caution).

        Args:
            token: JWT token string to decode

        Returns:
            Dictionary containing the token payload

        Raises:
            HTTPException: If token cannot be decoded
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not decode token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def create_tokens_for_user(
        user_id: str,
        email: str,
        organization_id: str,
        role: str
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens for a user.

        Args:
            user_id: User UUID
            email: User email
            organization_id: Organization UUID
            role: User role

        Returns:
            Dictionary with access_token and refresh_token
        """
        token_data = {
            "sub": user_id,
            "email": email,
            "organization_id": organization_id,
            "role": role
        }

        access_token = JWTService.create_access_token(token_data)
        refresh_token = JWTService.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }


# Global instance
jwt_service = JWTService()
