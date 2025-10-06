"""
Configuration de sécurité et CORS
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings


def setup_cors(app: FastAPI) -> None:
    """Configure le middleware CORS"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )


def setup_security_headers(app: FastAPI) -> None:
    """Configure les headers de sécurité"""
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
