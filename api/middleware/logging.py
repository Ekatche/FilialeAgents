"""
Middleware de logging personnalisé
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware pour logger les requêtes HTTP"""

    async def dispatch(self, request: Request, call_next):
        # Log de la requête entrante
        start_time = time.time()
        
        logger.info(
            f"📥 {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        # Traitement de la requête
        response = await call_next(request)

        # Calcul du temps de traitement
        process_time = time.time() - start_time

        # Log de la réponse
        logger.info(
            f"📤 {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        # Ajouter le temps de traitement dans les headers
        response.headers["X-Process-Time"] = str(process_time)

        return response
