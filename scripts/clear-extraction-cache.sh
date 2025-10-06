#!/bin/bash
# Script pour vider le cache d'extraction Redis

echo "🧹 Nettoyage du cache d'extraction Redis..."

# Vérifier si Docker est en cours d'exécution
if ! docker ps | grep -q "openai-agents-redis"; then
    echo "❌ Redis n'est pas en cours d'exécution"
    exit 1
fi

# Vider le cache Redis
docker exec openai-agents-redis redis-cli FLUSHALL

echo "✅ Cache Redis vidé avec succès"
echo ""
echo "💡 Pour éviter ce problème à l'avenir :"
echo "   1. Utilisez DISABLE_EXTRACTION_CACHE=true pour désactiver le cache"
echo "   2. Incrémentez CACHE_VERSION dans extraction_manager.py après chaque changement"
echo "   3. Utilisez ce script après chaque modification des modèles"
