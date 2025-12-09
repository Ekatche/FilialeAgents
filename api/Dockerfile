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
RUN uv sync --no-dev

# Copie du code source API
COPY api/ .

# Copie et rend exécutable le script d'entrypoint
COPY api/docker-entrypoint.sh /app/docker-entrypoint.sh

# Création du répertoire de logs
RUN mkdir -p /app/logs

# Rendre le script exécutable et ajuster les permissions
RUN chmod +x /app/docker-entrypoint.sh

# Utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Port d'exposition
EXPOSE 8012

# Health check (désactivé en production - Render gère ses propres healthchecks)
# Utile uniquement pour Docker Compose local
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://localhost:8012/health || exit 1

# Commande de démarrage (applique les migrations puis lance l'API)
CMD ["/app/docker-entrypoint.sh"]
