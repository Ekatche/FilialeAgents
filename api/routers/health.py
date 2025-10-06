"""
Routes pour les endpoints de santé et système
"""

import os
import httpx
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from core.models import HealthCheckResponse
from functions import get_version, check_openai_agents_availability

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=dict)
async def root():
    """Endpoint racine avec informations sur l'API"""
    return {
        "message": "Company Information Extraction API",
        "version": get_version(),
        "docs": "/docs",
        "health": "/health",
        "extract": "/extract",
        "credits": "/credits",
    }


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Vérification de l'état de l'API"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=get_version(),
        openai_agents_available=check_openai_agents_availability(),
    )


@router.get("/credits")
async def get_openai_credits():
    """Retourne les crédits OpenAI restants et informations de facturation"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "error": "OPENAI_API_KEY non configurée",
                "timestamp": datetime.now().isoformat(),
            }

        # Headers pour les requêtes à l'API OpenAI
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        account_info = {
            "api_key_configured": True,
            "api_key_prefix": api_key[:10] + "...",
        }

        async with httpx.AsyncClient() as client:
            # 1. Vérifier le statut de l'API
            try:
                subscription_response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                    timeout=10.0,
                )

                if subscription_response.status_code == 200:
                    account_info.update(
                        {
                            "api_status": "active",
                            "models_accessible": True,
                            "models_count": len(subscription_response.json().get("data", [])),
                        }
                    )
                else:
                    account_info.update(
                        {
                            "api_status": "limited",
                            "api_error": f"Status {subscription_response.status_code}",
                        }
                    )
            except Exception as api_error:
                account_info.update(
                    {
                        "api_status": "error",
                        "api_error": str(api_error),
                    }
                )

            # 2. Essayer de récupérer les informations de facturation
            try:
                # Essayer l'endpoint de subscription
                subscription_response = await client.get(
                    "https://api.openai.com/v1/dashboard/billing/subscription",
                    headers=headers,
                    timeout=10.0,
                )

                # Essayer l'endpoint de balance
                balance_response = await client.get(
                    "https://api.openai.com/v1/dashboard/billing/usage",
                    headers=headers,
                    timeout=10.0,
                )

                if balance_response.status_code == 200:
                    balance_data = balance_response.json()
                    account_info.update(
                        {
                            "billing_available": True,
                            "balance_info": balance_data,
                            "total_balance": balance_data.get(
                                "total_balance", "Unknown"
                            ),
                            "currency": balance_data.get("currency", "USD"),
                        }
                    )
                else:
                    # Aucun endpoint de billing accessible, donner des infos générales
                    account_info.update(
                        {
                            "billing_available": False,
                            "billing_error": f"Endpoints non accessibles (subscription: {subscription_response.status_code}, balance: {balance_response.status_code})",
                            "note": "Les APIs de billing OpenAI sont limitées selon le type de compte",
                            "alternative": "Consultez https://platform.openai.com/usage pour vos informations de crédit",
                        }
                    )

            except Exception as billing_error:
                account_info.update(
                    {
                        "billing_available": False,
                        "billing_error": str(billing_error),
                        "note": "Impossible de récupérer les informations de facturation",
                        "suggestion": "Vérifiez votre clé API et consultez https://platform.openai.com/usage",
                    }
                )

            # 3. Informations sur les limites et quotas (approximatifs)
            account_info.update(
                {
                    "quota_info": {
                        "note": "Les quotas exacts ne sont disponibles que dans le dashboard OpenAI",
                        "dashboard_url": "https://platform.openai.com/usage",
                        "general_limits": {
                            "gpt-4": "10,000 RPM (requests per minute) typique",
                            "gpt-3.5-turbo": "10,000 RPM typique",
                            "rate_limits_vary": "Les limites dépendent de votre tier de facturation",
                        },
                    }
                }
            )

        # Déterminer le statut global
        if account_info.get("api_status") == "active":
            if account_info.get("billing_available"):
                status = "success"
            else:
                status = "partial_success"
        else:
            status = "limited"

        return {
            "status": status,
            "data": account_info,
            "timestamp": datetime.now().isoformat(),
            "recommendations": [
                "Consultez https://platform.openai.com/usage pour les détails complets",
                "Vérifiez vos limites de taux sur https://platform.openai.com/settings/limits",
                "Surveillez votre facturation sur https://platform.openai.com/settings/billing",
            ],
        }

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des crédits: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
