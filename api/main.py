"""
API FastAPI pour l'extraction d'informations d'entreprise
Version modulaire - Point d'entrée principal
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from core.config import settings

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
from core.security import setup_cors, setup_security_headers
from core.lifespan import lifespan
from middleware.logging import LoggingMiddleware
from routers import health, extraction, websocket, tracking, auth, costs

# Création de l'application FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL,
    redoc_url=settings.API_REDOC_URL,
    lifespan=lifespan,
)

# Configuration des middlewares
setup_cors(app)
setup_security_headers(app)
app.add_middleware(LoggingMiddleware)

# Inclusion des routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(costs.router)
app.include_router(extraction.router)
app.include_router(websocket.router)
app.include_router(tracking.router)

# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
