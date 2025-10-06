# 🏢 OpenAiAgents - Extraction d'Informations d'Entreprise

Ce projet contient des expérimentations et une API complète pour l'extraction d'informations d'entreprise en utilisant OpenAI Agents.

## 📁 Structure du Projet

```
OpenAiAgents/
├── api/                                # 🚀 API FastAPI (backend)
│   ├── main.py                         # Entrée ASGI
│   ├── start.py                        # Démarrage local
│   ├── routers/                        # Routes FastAPI
│   ├── services/                       # Services (tracking, validation, websocket)
│   ├── company_agents/                 # Orchestrateur et agents
│   │   ├── extraction_core.py          # Entrée orchestrateur
│   │   ├── extraction_manager.py       # Orchestration Analyse → Info → Filiales → Validation → Restructuration
│   │   ├── models.py                   # Schémas Pydantic (CompanyInfo, SubsidiaryReport, ...)
│   │   └── subs_agents/                # Agents: analyzer, info, subs, meta, restructurer
│   └── README.md                       # Doc API (si présent)
├── frontend/                           # 🌐 Frontend Next.js
├── scripts/
│   └── clear-extraction-cache.sh       # Script utilitaire (optionnel)
├── nginx/                              # Config Nginx (déploiement)
├── tests/
│   └── filialesAgents.ipynb            # 📓 Notebook d’expérimentation
├── docker-compose.yml
├── Makefile
├── pyproject.toml                      # Dépendances gérées avec uv (pas de requirements.txt)
└── uv.lock                             # Verrouillage des dépendances
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

## 🚀 Démarrage rapide

### Prérequis

- Python 3.11+ et uv (`pip install uv`)
- Node 18+ (pour le frontend)
- Docker (optionnel)

### Configuration

- Dupliquez `.env.example` en `.env` et renseignez les clés nécessaires (ex: `PERPLEXITY_API_KEY`, `OPENAI_API_KEY` si utilisé).

### Démarrage (Makefile recommandé)

```bash
# Aide et installation
make help
make setup

# Démarrer l'API puis le frontend
make start
make start-frontend

# Vérifier les services
make status

# Ouvrir la documentation Swagger
make docs
```

### Endpoints principaux

- POST `http://localhost:8000/extract` (corps: `{ "company_name": "..." }`) → `CompanyInfo`
- POST `http://localhost:8000/extract-from-url` (corps: `{ "url": "..." }`) → `CompanyInfo`
- Docs Swagger: `http://localhost:8000/docs`

### Notes

- Le filtrage post-extraction est désactivé par défaut pour évaluer l’impact du prompt.
  - Voir `ENABLE_SUBS_FILTERS` dans `api/company_agents/extraction_manager.py`.
  - Passez à `True` pour réactiver les filtres (accessibilité/fraîcheur ≤24 mois).

## 📚 Documentation

- **API Documentation** : [api/README.md](api/README.md) - Documentation complète de l'API
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

# Pour l'API (uv)
uv sync
```

## 🧪 Tests

### Tests de l'API

```bash
make test
make docs
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

## 📜 Plan minimal (orchestration multi-agents)

Résumé d’implémentation aligné avec `api/company_agents/extraction_manager.py` et `plan_minimal.md`:

- Séquence: Analyse → Info → Filiales → Validation → Restructuration
- Critères (extraits):
  - `company_analyzer` d’abord; fallback si `relationship="unknown"` ou sources vides.
  - `information_extractor` si info-clés manquantes/faible qualité.
  - `subsidiary_extractor` (TOP 10, sources officielles, fallback “présences géographiques” si 0 filiale).
  - `meta_validator` si incohérences (parent divergent, sources absentes, filiales non sourcées).
- Tracking: progression et warnings exposés via `agent_tracking_service`.
- Fraîcheur: priorité <24 mois (désactivable via `ENABLE_SUBS_FILTERS`).
- Sortie finale: `CompanyInfo` (via restructurateur).

Voir le détail: [`plan_minimal.md`](./plan_minimal.md).

## 🤖 Agents (état actuel)

- 🔍 Éclaireur (`company_analyzer`)

  - Rôle: identifier l’entité légale, statut corporate (parent/subsidiary/independent), parent éventuel.
  - Outils: WebSearchTool
  - Modèle: gpt-4.1-mini
  - Sortie: `CompanyLinkage` (schéma strict)

- ⛏️ Mineur (`information_extractor`)

  - Rôle: extraire la fiche d’identité (siège, secteur, activités, sources).
  - Outils: WebSearchTool
  - Modèle: gpt-4.1-mini
  - Sortie: `CompanyCard` (schéma strict)

- 🗺️ Cartographe (`subsidiary_extractor`)

  - Rôle: extraire les 10 principales filiales avec localisations et sources officielles; fallback “présences géographiques” si 0 filiale.
  - Outils: aucun (recherche intégrée Sonar via Perplexity API Compatible OpenAI)
  - Modèle: sonar-pro (Perplexity), temperature=0.0, max_tokens=3200
  - Sortie: `SubsidiaryReport` (schéma strict)

- ⚖️ Superviseur (`meta_validator`)

  - Rôle: valider la cohérence globale, scorer (géographie/structure/sources/overall), produire recommandations et warnings.
  - Outils: aucun
  - Modèle: gpt-4o-mini
  - Sortie: `MetaValidationReport` (schéma strict)

- 🔄 Restructurateur (`data_restructurer`)
  - Rôle: normaliser les données en `CompanyInfo` final, sans champs additionnels, avec respect des limites (sources, GPS, etc.).
  - Outils: aucun
  - Modèle: gpt-4.1-mini
  - Sortie: `CompanyInfo` (schéma strict)
