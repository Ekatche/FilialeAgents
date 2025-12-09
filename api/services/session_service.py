"""
Service for managing user authentication sessions.
Works for both local and HubSpot authentication methods.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from models.db_models import UserSession, User
from core.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user authentication sessions."""

    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash a token using SHA-256 for storage.
        
        Args:
            token: JWT token string
            
        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @staticmethod
    async def create_session(
        user_id: str,
        access_token: str,
        refresh_token: str,
        auth_method: str = "local",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> UserSession:
        """
        Create a new user session.
        
        Args:
            user_id: User UUID
            access_token: JWT access token
            refresh_token: JWT refresh token
            auth_method: Authentication method ('local' or 'hubspot')
            ip_address: Optional IP address
            user_agent: Optional user agent string
            db: Optional database session (creates new if None)
            
        Returns:
            Created UserSession object
        """
        session_token_hash = SessionService._hash_token(access_token)
        refresh_token_hash = SessionService._hash_token(refresh_token)
        
        # Calculate expiration based on refresh token (7 days by default)
        # Use timezone-aware UTC time
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            # Check if session already exists (shouldn't happen, but safety check)
            result = await db.execute(
                select(UserSession).where(UserSession.session_token_hash == session_token_hash)
            )
            existing_session = result.scalar_one_or_none()
            
            if existing_session:
                # Update existing session
                existing_session.refresh_token_hash = refresh_token_hash
                existing_session.last_activity_at = datetime.now(timezone.utc)
                existing_session.expires_at = expires_at
                existing_session.is_active = True
                if ip_address:
                    existing_session.ip_address = ip_address
                if user_agent:
                    existing_session.user_agent = user_agent
                await db.commit()
                await db.refresh(existing_session)
                logger.info(f"📝 Session mise à jour: {existing_session.id} (user: {user_id})")
                return existing_session
            
            # Create new session
            session = UserSession(
                user_id=user_id,
                session_token_hash=session_token_hash,
                refresh_token_hash=refresh_token_hash,
                auth_method=auth_method,
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
                expires_at=expires_at,
                last_activity_at=datetime.now(timezone.utc)
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.info(f"✅ Session créée: {session.id} (user: {user_id}, method: {auth_method})")
            return session
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur création session: {e}", exc_info=True)
            raise
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def get_session_by_token(
        access_token: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[UserSession]:
        """
        Get a session by access token hash.
        
        Args:
            access_token: JWT access token
            db: Optional database session
            
        Returns:
            UserSession if found and active, None otherwise
        """
        session_token_hash = SessionService._hash_token(access_token)
        
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.session_token_hash == session_token_hash,
                    UserSession.is_active == True
                )
            )
            session = result.scalar_one_or_none()
            
            if session:
                # Check if session is expired
                if session.expires_at < datetime.now(timezone.utc):
                    logger.warning(f"⚠️ Session expirée: {session.id}")
                    session.is_active = False
                    await db.commit()
                    return None
                
                # Update last activity
                session.last_activity_at = datetime.now(timezone.utc)
                await db.commit()
            
            return session
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération session: {e}", exc_info=True)
            return None
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def update_session_token(
        refresh_token: str,
        new_access_token: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[UserSession]:
        """
        Update session with new access token (used during token refresh).
        
        Args:
            refresh_token: Current refresh token
            new_access_token: New access token
            db: Optional database session
            
        Returns:
            Updated UserSession if found, None otherwise
        """
        refresh_token_hash = SessionService._hash_token(refresh_token)
        new_session_token_hash = SessionService._hash_token(new_access_token)
        
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.refresh_token_hash == refresh_token_hash,
                    UserSession.is_active == True
                )
            )
            session = result.scalar_one_or_none()
            
            if session:
                # Check if session is expired
                # Use timezone-aware UTC time for comparison
                if session.expires_at < datetime.now(timezone.utc):
                    logger.warning(f"⚠️ Session expirée lors du refresh: {session.id}")
                    session.is_active = False
                    await db.commit()
                    return None
                
                # Update access token hash and last activity
                session.session_token_hash = new_session_token_hash
                session.last_activity_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(session)
                logger.info(f"✅ Session mise à jour avec nouveau token: {session.id}")
                return session
            
            return None
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur mise à jour session: {e}", exc_info=True)
            return None
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def update_session_refresh_token(
        old_refresh_token: str,
        new_refresh_token: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[UserSession]:
        """
        Update session refresh token hash (when refresh token is rotated).
        
        Args:
            old_refresh_token: Current refresh token
            new_refresh_token: New refresh token
            db: Optional database session
            
        Returns:
            Updated UserSession if found, None otherwise
        """
        old_refresh_token_hash = SessionService._hash_token(old_refresh_token)
        new_refresh_token_hash = SessionService._hash_token(new_refresh_token)
        
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.refresh_token_hash == old_refresh_token_hash,
                    UserSession.is_active == True
                )
            )
            session = result.scalar_one_or_none()
            
            if session:
                # Check if session is expired
                if session.expires_at < datetime.now(timezone.utc):
                    logger.warning(f"⚠️ Session expirée lors du refresh token update: {session.id}")
                    session.is_active = False
                    await db.commit()
                    return None
                
                # Update refresh token hash
                session.refresh_token_hash = new_refresh_token_hash
                session.last_activity_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(session)
                logger.info(f"✅ Refresh token mis à jour pour session: {session.id}")
                return session
            
            return None
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur mise à jour refresh token: {e}", exc_info=True)
            return None
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def revoke_session(
        access_token: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Revoke (deactivate) a session.
        
        Args:
            access_token: JWT access token
            db: Optional database session
            
        Returns:
            True if session was revoked, False otherwise
        """
        session_token_hash = SessionService._hash_token(access_token)
        
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(UserSession).where(UserSession.session_token_hash == session_token_hash)
            )
            session = result.scalar_one_or_none()
            
            if session:
                session.is_active = False
                await db.commit()
                logger.info(f"🔒 Session révoquée: {session.id} (user: {session.user_id})")
                return True
            
            return False
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur révocation session: {e}", exc_info=True)
            return False
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def revoke_session_by_id(
        session_id: str,
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Revoke a specific session by ID (for user management).
        
        Args:
            session_id: Session UUID
            user_id: User UUID (for security check)
            db: Optional database session
            
        Returns:
            True if session was revoked, False otherwise
        """
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id
                )
            )
            session = result.scalar_one_or_none()
            
            if session:
                session.is_active = False
                await db.commit()
                logger.info(f"🔒 Session révoquée: {session.id} (user: {user_id})")
                return True
            
            return False
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur révocation session: {e}", exc_info=True)
            return False
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def revoke_all_user_sessions(
        user_id: str,
        db: Optional[AsyncSession] = None
    ) -> int:
        """
        Revoke all active sessions for a user.
        
        Args:
            user_id: User UUID
            db: Optional database session
            
        Returns:
            Number of sessions revoked
        """
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
            sessions = result.scalars().all()
            
            count = 0
            for session in sessions:
                session.is_active = False
                count += 1
            
            await db.commit()
            logger.info(f"🔒 {count} sessions révoquées pour user: {user_id}")
            return count
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur révocation sessions: {e}", exc_info=True)
            return 0
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def get_user_sessions(
        user_id: str,
        active_only: bool = True,
        db: Optional[AsyncSession] = None
    ) -> List[UserSession]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User UUID
            active_only: If True, only return active sessions
            db: Optional database session
            
        Returns:
            List of UserSession objects
        """
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            query = select(UserSession).where(UserSession.user_id == user_id)
            if active_only:
                query = query.where(UserSession.is_active == True)
            
            query = query.order_by(UserSession.last_activity_at.desc())
            result = await db.execute(query)
            sessions = result.scalars().all()
            
            return list(sessions)
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération sessions: {e}", exc_info=True)
            return []
        finally:
            if should_close_db:
                await db.close()

    @staticmethod
    async def cleanup_expired_sessions(
        db: Optional[AsyncSession] = None
    ) -> int:
        """
        Clean up expired sessions.
        
        Args:
            db: Optional database session
            
        Returns:
            Number of sessions cleaned up
        """
        should_close_db = False
        if db is None:
            db = AsyncSessionLocal()
            should_close_db = True
        
        try:
            # Deactivate expired sessions
            result = await db.execute(
                select(UserSession).where(
                    UserSession.is_active == True,
                    UserSession.expires_at < datetime.now(timezone.utc)
                )
            )
            expired_sessions = result.scalars().all()
            
            count = 0
            for session in expired_sessions:
                session.is_active = False
                count += 1
            
            await db.commit()
            
            if count > 0:
                logger.info(f"🧹 {count} sessions expirées nettoyées")
            
            return count
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Erreur nettoyage sessions: {e}", exc_info=True)
            return 0
        finally:
            if should_close_db:
                await db.close()


# Global instance
session_service = SessionService()

