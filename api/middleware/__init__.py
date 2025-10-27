"""
Middleware pour l'API d'extraction d'entreprise
"""

from .logging import LoggingMiddleware

__all__ = [
    "LoggingMiddleware",
]
