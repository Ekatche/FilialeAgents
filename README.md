# 🏢 OpenAiAgents - Extraction d'Informations d'Entreprise

Ce projet contient des expérimentations et une API complète pour l'extraction d'informations d'entreprise en utilisant OpenAI Agents.

## 📁 Structure du Projet

```
OpenAiAgents/
├── api/                           # 🚀 API FastAPI de production
│   ├── main.py                   # API principale
│   ├── models.py                 # Modèles Pydantic
│   ├── agents.py                 # Agents OpenAI
│   ├── functions.py              # Fonctions utilitaires
│   ├── config.py                 # Configuration
│   ├── requirements.txt          # Dépendances
│   ├── README.md                 # Documentation API
│   ├── start.py                  # Script de démarrage
│   ├── test_api.py               # Tests simples
│   └── demo.py                   # Démonstration
├── EquipeAgents.ipynb            # 📓 Notebook d'expérimentation original
├── EquipeAgents_Reorganise.ipynb # 📓 Notebook réorganisé
├── filialesAgents.ipynb          # 📓 Notebook spécialisé filiales
├── pyproject.toml                # Configuration Python
└── uv.lock                       # Verrouillage des dépendances
```

## 🎯 Objectifs

### 📓 Notebooks d'Expérimentation

- **EquipeAgents.ipynb** : Expérimentations originales avec les agents OpenAI
- **EquipeAgents_Reorganise.ipynb** : Version réorganisée et optimisée
- **filialesAgents.ipynb** : Spécialisation pour l'extraction de filiales

### 🚀 API de Production

- **api/** : API FastAPI complète et prête pour la production
- Extraction intelligente d'informations d'entreprise
- Support des filiales et relations parent-enfant
- **🛡️ Système de monitoring des quotas OpenAI** (évite les erreurs 429)
- **📦 Cache intelligent** pour réduire les coûts API
- **🚨 Alertes préventives** pour les limites de quota

## 🚀 Utilisation Rapide

### 🔧 Gestion du Cache Redis

Le système utilise un cache Redis pour éviter les recalculs coûteux. **Après chaque modification des modèles Pydantic ou des agents**, vous devez :

#### Option 1 : Vider le cache manuellement

```bash
# Script automatique
./scripts/clear-extraction-cache.sh

# Ou manuellement
docker exec openai-agents-redis redis-cli FLUSHALL
```

#### Option 2 : Désactiver le cache temporairement

```bash
# Dans votre terminal
export DISABLE_EXTRACTION_CACHE=true
docker compose up -d
```

#### Option 3 : Incrémenter la version du cache

Modifiez `CACHE_VERSION = "v3"` dans `api/company_agents/extraction_manager.py` après chaque changement de modèle.

### 1. Expérimentations (Notebooks)

```bash
# Ouvrir les notebooks pour les expérimentations
jupyter notebook EquipeAgents.ipynb
jupyter notebook filialesAgents.ipynb
```

### 2. API de Production

#### Option A: Scripts rapides

```bash
# Démarrage rapide
./start_api.sh

# Tests rapides
./test_api.sh
```

#### Option B: Makefile (recommandé)

```bash
# Voir toutes les commandes disponibles
make help

# Installation et configuration
make setup

# Démarrage de l'API
make start

# Tests
make test

# Vérification du statut
make status

# Monitoring des quotas
make monitor

# Documentation
make docs
```

#### Option C: Manuel

```bash
# Aller dans le dossier API
cd api/

# Installer les dépendances
pip install -r requirements.txt

# Configurer la clé API
export OPENAI_API_KEY="votre-cle-api"

# Démarrer l'API
python start.py
```

## 📚 Documentation

- **API Documentation** : [api/README.md](api/README.md) - Documentation complète de l'API
- **Configuration des Quotas** : [api/QUOTA_CONFIG.md](api/QUOTA_CONFIG.md) - Guide de configuration des quotas
- **Swagger UI** : http://localhost:8000/docs (quand l'API est démarrée)

## 🔧 Configuration

### Variables d'Environnement

```bash
export OPENAI_API_KEY="votre-cle-api-openai"
```

### Dépendances

```bash
# Pour les notebooks
pip install jupyter notebook

# Pour l'API
cd api/
pip install -r requirements.txt
```

## 🧪 Tests

### Tests de l'API

```bash
cd api/
python test_api.py
python demo.py
```

### Tests manuels

```bash
# Health check
curl http://localhost:8000/health

# Extraction d'entreprise
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"company_name": "Apple Inc."}'
```

## 📈 Évolution du Projet

1. **Phase 1** : Expérimentations dans les notebooks
2. **Phase 2** : Réorganisation et optimisation
3. **Phase 3** : Conversion en API FastAPI (✅ Terminé)
4. **Phase 4** : Déploiement et production

## 🤝 Contribution

1. Utilisez les notebooks pour les expérimentations
2. Une fois validé, intégrez dans l'API
3. Testez avec les scripts fournis
4. Documentez les changements

## 📄 Licence

Ce projet est sous licence MIT.

## 🆘 Support

- **Issues** : [GitHub Issues](https://github.com/votre-repo/issues)
- **Documentation API** : [api/README.md](api/README.md)
- **Documentation Swagger** : http://localhost:8000/docs
