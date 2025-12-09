#!/bin/bash
set -e

echo "🔄 Running database migrations..."
# Utiliser directement alembic depuis le venv si uv.lock est vide
if [ -s /app/uv.lock ]; then
    uv run alembic upgrade head
else
    /app/.venv/bin/alembic upgrade head
fi

echo "✅ Migrations complete"
echo "🚀 Starting API server..."
# Utiliser directement python depuis le venv si uv.lock est vide
if [ -s /app/uv.lock ]; then
    exec uv run python start.py
else
    exec /app/.venv/bin/python start.py
fi
