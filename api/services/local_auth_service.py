"""
Local Authentication Service (pour tests sans HubSpot OAuth).
"""

import uuid
import bcrypt
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.db_models import User, HubSpotPortal, UserRole
from services.jwt_service import JWTService
from services.session_service import session_service
from core.config import settings


class LocalAuthService:
    """Service pour l'authentification locale (email/password)."""

    def __init__(self):
        # Cost factor pour bcrypt (12 rounds = bon équilibre sécurité/performance)
        self.bcrypt_rounds = 12

    def _prepare_password(self, password: str) -> bytes:
        """
        Prépare le mot de passe pour bcrypt en le hashant avec SHA-256.
        Cela permet de contourner la limitation de 72 bytes de bcrypt.
        
        Args:
            password: Mot de passe en clair
            
        Returns:
            Hash SHA-256 du mot de passe (32 bytes, toujours < 72 bytes)
        """
        # Hasher avec SHA-256 pour obtenir toujours 32 bytes (bien en dessous de 72)
        return hashlib.sha256(password.encode('utf-8')).digest()

    def hash_password(self, password: str) -> str:
        """
        Hash un mot de passe avec bcrypt (après préparation SHA-256).
        
        Args:
            password: Mot de passe en clair (peut être de n'importe quelle longueur)
            
        Returns:
            Hash bcrypt encodé en UTF-8
        """
        # Préparer le mot de passe (SHA-256 pour contourner la limite de 72 bytes)
        password_prepared = self._prepare_password(password)
        
        # Générer le salt et hasher avec bcrypt
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        hashed = bcrypt.hashpw(password_prepared, salt)
        
        # Retourner en string UTF-8
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Vérifie un mot de passe contre son hash.
        
        Args:
            plain_password: Mot de passe en clair
            hashed_password: Hash bcrypt stocké
            
        Returns:
            True si le mot de passe correspond, False sinon
        """
        try:
            # Préparer le mot de passe (même méthode que pour le hashage)
            password_prepared = self._prepare_password(plain_password)
            
            # Convertir le hash en bytes
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Vérifier avec bcrypt
            return bcrypt.checkpw(password_prepared, hashed_bytes)
        except Exception:
            # En cas d'erreur (format invalide, etc.), retourner False
            return False

    async def register_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        team_name: str
    ) -> Tuple[User, HubSpotPortal]:
        """
        Enregistre un nouvel utilisateur en mode local.

        Args:
            db: Session de base de données
            email: Email de l'utilisateur
            password: Mot de passe en clair
            first_name: Prénom
            last_name: Nom
            team_name: Nom de l'équipe/portail

        Returns:
            Tuple (User, HubSpotPortal)

        Raises:
            HTTPException: Si l'email existe déjà
        """
        # Vérifier si l'email existe déjà
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur avec cet email existe déjà"
            )

        # Créer un portail unique pour chaque équipe/utilisateur
        # En mode local, on crée quand même un portail unique par équipe
        # pour que chaque utilisateur/équipe ait ses propres extractions
        
        # Vérifier si un portail avec ce nom d'équipe existe déjà
        result = await db.execute(
            select(HubSpotPortal).where(HubSpotPortal.name == team_name)
        )
        existing_portal = result.scalar_one_or_none()
        
        if existing_portal:
            # Utiliser le portail existant
            portal = existing_portal
        else:
            # Créer un nouveau portail
            # Générer un hubspot_portal_id unique (nombre aléatoire)
            portal_id_number = abs(hash(f"{email}-{team_name}-{datetime.now().isoformat()}")) % 1000000000
            
            # En mode local, utiliser un ID fixe pour le portail local par défaut
            # seulement si c'est le premier utilisateur et qu'aucun portail n'existe
            if settings.is_local:
                # Vérifier s'il existe déjà des portails
                result = await db.execute(select(HubSpotPortal))
                existing_portals = result.scalars().all()
                
                # Si c'est le premier portail et qu'on est en mode local,
                # on peut utiliser le portail local par défaut
                if len(existing_portals) == 0:
                    portal_uuid = uuid.UUID(settings.LOCAL_DEFAULT_PORTAL_ID)
                    portal = HubSpotPortal(
                        id=portal_uuid,
                        hubspot_portal_id=0,  # ID fictif pour mode local
                        name=team_name,  # Utiliser le nom de l'équipe
                        domain="localhost",
                        is_active=True,
                    )
                else:
                    # Créer un nouveau portail avec un UUID généré
                    portal = HubSpotPortal(
                        hubspot_portal_id=portal_id_number,
                        name=team_name,
                        domain="localhost",
                        is_active=True,
                    )
            else:
                # Mode production : créer un nouveau portail
                portal = HubSpotPortal(
                    hubspot_portal_id=portal_id_number,
                    name=team_name,
                    is_active=True,
                )
            
            db.add(portal)
            await db.flush()  # Pour obtenir l'ID du portail

        # Créer l'utilisateur
        # Générer un hubspot_user_id unique pour mode local
        hubspot_user_id = f"local-{uuid.uuid4()}"

        user = User(
            hubspot_portal_id=portal.id,
            hubspot_user_id=hubspot_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=self.hash_password(password),
            role=UserRole.ADMIN.value,  # Premier user = admin
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await db.refresh(portal)

        return user, portal

    async def authenticate_user(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authentifie un utilisateur.

        Args:
            db: Session de base de données
            email: Email de l'utilisateur
            password: Mot de passe en clair

        Returns:
            User si authentifié, None sinon
        """
        # Récupérer l'utilisateur
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Si pas de password_hash, c'est un user HubSpot OAuth
        if not user.password_hash:
            return None

        # Vérifier le mot de passe
        if not self.verify_password(password, user.password_hash):
            return None

        # Vérifier que l'utilisateur est actif
        if not user.is_active:
            return None

        # Mettre à jour last_login_at
        user.last_login_at = datetime.now()
        await db.commit()

        return user

    async def create_tokens_for_user(
        self, 
        user: User, 
        portal: HubSpotPortal,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """
        Crée les tokens JWT pour un utilisateur.

        Args:
            user: Utilisateur
            portal: Portail HubSpot

        Returns:
            Dict avec access_token, refresh_token, etc.
        """
        # Créer le token JWT avec le format attendu par JWTService.verify_token
        # JWTService.verify_token cherche "sub" pour user_id (standard JWT)
        token_data = {
            "sub": str(user.id),  # Standard JWT: "sub" (subject) = user_id
            "email": user.email,
            "portal_id": str(portal.id),
            "hubspot_portal_id": portal.hubspot_portal_id,
            "role": user.role,
        }

        access_token = JWTService.create_access_token(token_data)
        refresh_token = JWTService.create_refresh_token(token_data)

        # Create session for tracking
        try:
            await session_service.create_session(
                user_id=str(user.id),
                access_token=access_token,
                refresh_token=refresh_token,
                auth_method="local",
                ip_address=ip_address,
                user_agent=user_agent,
                db=None  # Will create its own session
            )
        except Exception as e:
            # Log error but don't fail authentication
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Erreur création session (non bloquant): {e}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # En secondes
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "portal_id": str(portal.id),
                "portal_name": portal.name,
            }
        }


# Instance globale
local_auth_service = LocalAuthService()
