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

    # Endpoints à exclure du logging (healthchecks, metrics, etc.)
    EXCLUDED_PATHS = {"/health/live", "/metrics"}

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Skip logging pour les healthchecks et autres endpoints fréquents
        should_log = request.url.path not in self.EXCLUDED_PATHS

        if should_log:
            logger.info(
                f"📥 {request.method} {request.url.path} - "
                f"Client: {request.client.host if request.client else 'unknown'}"
            )

        # Traitement de la requête
        response = await call_next(request)

        # Calcul du temps de traitement
        process_time = time.time() - start_time

        if should_log:
            logger.info(
                f"📤 {request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )

        # Ajouter le temps de traitement dans les headers (toujours)
        response.headers["X-Process-Time"] = str(process_time)

        return response
