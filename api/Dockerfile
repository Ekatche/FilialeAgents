# =======================================================
# DOCKERFILE POUR L'API D'EXTRACTION D'ENTREPRISE
# Version mise à jour avec support WebSocket et suivi des agents
# =======================================================

FROM python:3.11-slim

# Métadonnées
LABEL maintainer="OpenAiAgents Team"
LABEL description="API d'extraction d'informations d'entreprise avec suivi des agents en temps réel"
LABEL version="2.0.0"
LABEL features="WebSocket,Real-time agent status,Session management"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation de uv
RUN pip install uv

# Copie des fichiers de configuration depuis la racine
COPY pyproject.toml uv.lock ./

# Installation des dépendances Python avec uv
RUN uv sync --frozen --no-dev

# Copie du code source API
COPY api/ .

# Création du répertoire de logs
RUN mkdir -p /app/logs

# Utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Port d'exposition
EXPOSE 8012

# Health check (inclut maintenant la vérification WebSocket)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8012/health || exit 1

# Commande de démarrage
CMD ["uv", "run", "python", "start.py"]
