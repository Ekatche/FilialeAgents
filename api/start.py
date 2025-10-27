#!/usr/bin/env python3
"""
Script de démarrage pour l'API d'extraction d'entreprise
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv
from core.config import settings

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


def main():
    """Démarre l'API"""
    print("🚀 Démarrage de l'API d'extraction d'entreprise")
    print("=" * 50)

    # Vérifier la configuration
    if not settings.OPENAI_API_KEY:
        print("⚠️ OPENAI_API_KEY non définie - certaines fonctionnalités seront limitées")
    else:
        print("✅ Configuration OpenAI OK")

    # Afficher les informations
    print(f"📋 Version: {settings.API_VERSION}")
    print(f"🌐 Host: 0.0.0.0")
    print(f"🔌 Port: 8012")
    print(f"🔧 Debug: {settings.DEBUG}")
    print(f"📚 Documentation: http://localhost:8012/docs")
    print("=" * 50)

    # Démarrer l'API
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8012,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
