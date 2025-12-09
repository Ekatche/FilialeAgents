"""
Router pour l'authentification locale (sans HubSpot OAuth).
Pour les tests en local uniquement.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.local_auth_service import local_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/local", tags=["local-auth"])


# ==========================================
#   MODÈLES DE REQUÊTE/RÉPONSE
# ==========================================

class RegisterRequest(BaseModel):
    """Requête d'inscription locale."""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    password: str = Field(..., min_length=6, description="Mot de passe (min 6 caractères)")
    first_name: str = Field(..., min_length=1, description="Prénom")
    last_name: str = Field(..., min_length=1, description="Nom")
    team_name: str = Field(..., min_length=1, description="Nom de l'équipe/organisation")


class LoginRequest(BaseModel):
    """Requête de connexion locale."""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    password: str = Field(..., description="Mot de passe")


class AuthResponse(BaseModel):
    """Réponse d'authentification."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


# ==========================================
#   ENDPOINTS
# ==========================================

@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Inscription locale (pour tests sans HubSpot OAuth).

    Crée un utilisateur et un portail (équipe) local.

    Args:
        request: Données d'inscription
        db: Session de base de données

    Returns:
        Tokens JWT et informations utilisateur

    Raises:
        HTTPException 400: Si l'email existe déjà
    """
    try:
        # Créer l'utilisateur et le portail
        user, portal = await local_auth_service.register_user(
            db=db,
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            team_name=request.team_name
        )

        logger.info(f"✅ Utilisateur local créé: {user.email} (portal: {portal.name})")

        # Créer les tokens
        tokens = await local_auth_service.create_tokens_for_user(user, portal)

        return AuthResponse(**tokens)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur inscription locale: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'inscription"
        )


@router.get("/me")
async def get_current_user_local(db: AsyncSession = Depends(get_db)):
    """
    Récupère les informations de l'utilisateur local par défaut (mode local uniquement).

    En mode local, retourne toujours l'utilisateur du portail local par défaut.
    Cet endpoint ne nécessite pas d'authentification.

    Returns:
        Informations de l'utilisateur et du portail
    """
    from core.config import settings
    from sqlalchemy import select
    from models.db_models import HubSpotPortal
    import uuid

    try:
        # Récupérer le portail local
        portal_uuid = uuid.UUID(settings.LOCAL_DEFAULT_PORTAL_ID)
        result = await db.execute(
            select(HubSpotPortal).where(HubSpotPortal.id == portal_uuid)
        )
        portal = result.scalar_one_or_none()

        if not portal:
            # Si le portail n'existe pas, retourner des valeurs par défaut
            return {
                "user_id": "local-user",
                "email": "local@localhost",
                "first_name": "Local",
                "last_name": "User",
                "role": "admin",
                "portal_id": settings.LOCAL_DEFAULT_PORTAL_ID,
                "portal_name": "Local Development",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_login": None
            }

        # Retourner les informations du portail local
        return {
            "user_id": "local-user",
            "email": "local@localhost",
            "first_name": "Local",
            "last_name": "User",
            "role": "admin",
            "portal_id": str(portal.id),
            "portal_name": portal.name,
            "is_active": True,
            "created_at": portal.created_at.isoformat(),
            "last_login": None
        }

    except Exception as e:
        logger.error(f"❌ Erreur récupération utilisateur local: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'utilisateur"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Connexion locale (pour tests sans HubSpot OAuth).

    Args:
        request: Email et mot de passe
        http_request: FastAPI Request object (pour IP et user agent)
        db: Session de base de données

    Returns:
        Tokens JWT et informations utilisateur

    Raises:
        HTTPException 401: Si les identifiants sont incorrects
    """
    try:
        # Authentifier l'utilisateur
        user = await local_auth_service.authenticate_user(
            db=db,
            email=request.email,
            password=request.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )

        # Récupérer le portail
        from sqlalchemy import select
        from models.db_models import HubSpotPortal

        result = await db.execute(
            select(HubSpotPortal).where(HubSpotPortal.id == user.hubspot_portal_id)
        )
        portal = result.scalar_one()

        logger.info(f"✅ Connexion locale réussie: {user.email}")

        # Récupérer IP et user agent
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("user-agent")

        # Créer les tokens
        tokens = await local_auth_service.create_tokens_for_user(
            user, 
            portal,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return AuthResponse(**tokens)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur connexion locale: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la connexion"
        )
