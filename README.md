# 🏢 FilialeAgents - Extraction Intelligente d'Entreprises

Système d'extraction multi-agents utilisant OpenAI Agents pour l'analyse complète d'entreprises et leurs filiales.

## 📑 Table des Matières

1. [Vue d'Ensemble](#-vue-densemble)
2. [Architecture Multi-Agents](#-architecture-multi-agents)
3. [Fonctionnalités Clés](#-fonctionnalités-clés)
4. [Démarrage Rapide](#-démarrage-rapide)
5. [Configuration](#-configuration)
6. [API et Frontend](#-api-et-frontend)
7. [Tests](#-tests)
8. [Documentation Technique](#-documentation-technique)

---

## 🎯 Vue d'Ensemble

FilialeAgents est un système d'extraction d'informations d'entreprises basé sur une architecture multi-agents. Il combine plusieurs agents spécialisés pour extraire, valider et structurer des données sur les entreprises et leurs filiales.

### Caractéristiques Principales

- 🤖 **5 Agents Spécialisés** : Pipeline orchestré pour une extraction complète
- 🛡️ **Guardrails Actifs** : Validation en temps réel avec correction automatique
- 📞 **Extraction de Contacts** : Téléphone et email pour entreprises et filiales
- 🔍 **Vérification URLs** : Validation d'accessibilité avec codes HTTP
- 📊 **Suivi Temps Réel** : WebSocket avec métriques détaillées
- 🌐 **Frontend Next.js** : Interface utilisateur moderne et réactive

---

## 🤖 Architecture Multi-Agents

### Pipeline d'Extraction (5 Étapes)

```
┌─────────────────────────────────────────────────────────┐
│ 1. 🔍 ÉCLAIREUR (Company Analyzer)                     │
│    → Identification entité légale                       │
│    → Détection relation parent/filiale                  │
│    → Extraction target_domain                           │
│    → Guardrails: URLs accessibles + domaine valide      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. ⛏️ MINEUR (Information Extractor)                    │
│    → Extraction informations clés                       │
│    → Siège social, secteur, activités                   │
│    → Chiffre d'affaires, effectifs                      │
│    → Recherche stricte on-domain (site:{domain})        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. 🗺️ CARTOGRAPHE (Subsidiary Extractor)               │
│    → Version Simple (deep_search=False) :                │
│      • Recherche via gpt-4o-search-preview               │
│      • Rapide et économique                              │
│    → Version Avancée (deep_search=True) :                │
│      • Recherche via Perplexity Sonar (sonar-pro)       │
│      • Approfondie et exhaustive                         │
│    → Extraction contacts (phone, email)                 │
│    → Localisations avec coordonnées GPS                 │
│    → Plan B: infos entreprise si pas de filiales        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. ⚖️ SUPERVISEUR (Meta Validator)                      │
│    → Validation cohérence globale                       │
│    → Scoring géographique/structure/sources             │
│    → Vérification core business filiales                │
│    → Exclusion filiales non corrélées                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. 🔄 RESTRUCTURATEUR (Data Restructurer)               │
│    → Normalisation vers CompanyInfo final               │
│    → Enrichissement GPS si manquant                     │
│    → Extraction contacts depuis main_company_info       │
│    → Validation schéma Pydantic strict                  │
└─────────────────────────────────────────────────────────┘
```

### Détails des Agents

#### 🔍 Éclaireur (Company Analyzer)
- **Modèle** : gpt-4.1-mini
- **Outils** : WebSearchTool
- **Output** : `CompanyLinkage` (entity_legal_name, target_domain, relationship, parent_company, sources)
- **Guardrails** : 
  - Validation domaine cible
  - Vérification ≥1 source on-domain
  - Check accessibilité URLs avec retry automatique

#### ⛏️ Mineur (Information Extractor)
- **Modèle** : gpt-4.1-mini
- **Outils** : WebSearchTool
- **Output** : `CompanyCard` (company_name, headquarters, sector, activities, revenue, employees, sources)
- **Spécificité** : Recherche strictement on-domain (`site:{target_domain}`) pour éviter homonymes

#### 🗺️ Cartographe (Subsidiary Extractor)

Le Cartographe existe en **deux versions** selon le type de recherche :

##### Version Simple (`deep_search=False`)
- **Modèle** : gpt-4o
- **Outil** : `subsidiary_search` (gpt-4o-search-preview)
- **Pipeline** : Recherche rapide et économique
- **Usage** : Extractions standard avec coût optimisé
- **Output** : `SubsidiaryReport` (subsidiaries avec localisations, contacts, citations)

##### Version Avancée (`deep_search=True`)
- **Modèle** : gpt-4o
- **Outil** : `research_subsidiaries_with_perplexity` (sonar-pro / Perplexity)
- **Pipeline** : Recherche approfondie et exhaustive
- **Usage** : Extractions complexes nécessitant une recherche plus complète
- **Output** : `SubsidiaryReport` (subsidiaries avec localisations, contacts, citations)

##### Features Communes
- Extraction téléphone + email pour chaque filiale
- Distinction filiales juridiques vs présence commerciale
- Plan B : Si pas de filiales → infos détaillées entreprise principale
- Citations réelles des sources (avec titres corrects)
- Géocodage automatique (coordonnées GPS)

#### ⚖️ Superviseur (Meta Validator)
- **Modèle** : gpt-4o-mini
- **Outils** : Aucun (validation pure)
- **Output** : `MetaValidationReport` (scores, conflicts, recommendations, excluded_subsidiaries)
- **Validations** :
  - Cohérence géographique (filiales dans zones attendues)
  - Cohérence métier (core business aligné avec parent)
  - Qualité sources (officielles prioritaires)

#### 🔄 Restructurateur (Data Restructurer)
- **Modèle** : gpt-4.1-mini
- **Outils** : Aucun (transformation pure)
- **Output** : `CompanyInfo` (format API final)
- **Responsabilités** :
  - Normalisation pays (USA → United States)
  - Enrichissement GPS si données manquantes
  - Extraction contacts depuis `main_company_info`
  - Copie phone/email filiales vers `headquarters` si manquants

---

## 🎯 Fonctionnalités Clés

### 📞 Extraction de Contacts

Le système extrait **automatiquement** les coordonnées de contact :

#### Entreprise Principale
- **Téléphone** : Format international (ex: `+33 4 28 29 81 10`)
- **Email** : Email général (ex: `contact@company.com`)
- **Sources** : Page Contact, Footer, Mentions légales, LinkedIn

#### Filiales
- **Téléphone** : Numéro direct de la filiale
- **Email** : Email spécifique si disponible
- **Copie automatique** : Si présent au niveau racine mais pas dans `headquarters`

#### Affichage Frontend
- 📞 **Liens cliquables** : `tel:+33...` pour appel direct
- 📧 **Liens email** : `mailto:contact@...` pour envoi email
- 🎨 **Design cohérent** : Icônes, couleurs, hover effects

**Sources prioritaires** :
1. `extraction_summary.main_company_info` (Cartographe)
2. `company_info` direct (Mineur)
3. `methodology_notes` (parsing intelligent)
4. `analyzer_data` (Éclaireur)

---

### 🏢 Présence Commerciale

Le système distingue deux types de présence internationale :

#### Filiales Juridiques (`subsidiaries_details`)
- Entités juridiques avec personnalité propre
- Exemples : "ACOEM France SAS", "ACOEM Germany GmbH"
- Extraction via Perplexity Sonar (recherche approfondie)

#### Présence Commerciale (`commercial_presence_details`)
- Bureaux commerciaux sans personnalité juridique
- Partenaires, distributeurs autorisés, représentants
- Types : `office`, `partner`, `distributor`, `representative`
- Relations : `owned`, `partnership`, `authorized_distributor`, `franchise`

**Exemples** :
- Bureau commercial à Munich (type: `office`, relationship: `owned`)
- Distributeur au Brésil (type: `distributor`, relationship: `authorized_distributor`)
- Partenaire en Inde (type: `partner`, relationship: `partnership`)

**Validation** :
- Le **Superviseur** exclut les présences non corrélées
- Le **Restructurateur** reclassifie automatiquement si erreur de catégorie

---

### 🛡️ Guardrails et Validation

#### Système de Guardrails Actifs

Le système implémente des **guardrails OpenAI Agents** pour valider les outputs en temps réel :

##### 1. Éclaireur - Validation URLs
```python
@output_guardrail
async def eclaireur_output_guardrail(ctx, output):
    """
    Vérifie :
    - target_domain présent (mode URL)
    - ≥1 source on-domain accessible
    - Toutes URLs accessibles (HTTP 200-299)
    """
    # Vérification active avec HTTPX
    dead_links = await check_urls_accessibility(sources)
    
    if dead_links:
        raise OutputGuardrailFailure(
            output_info={
                "removed_dead_links": [
                    f"{url} (HTTP {status_code})"
                ]
            }
        )
```

##### 2. Retry Automatique avec Correction Hints

Quand un guardrail échoue, le système **retente automatiquement** avec un hint détaillé :

```
[CORRECTION_HINT]: Corrige la sortie pour respecter:
1) target_domain présent si détectable;
2) ≥1 source on-domain valide;
3) exclure/remplacer toute URL morte par une page on-domain valide.

⚠️ URLs NON ACCESSIBLES détectées:
  - https://www.agencenile.com/mentions-legales (HTTP 404)
  - https://example.com/timeout (Timeout)

Remplace chaque URL ci-dessus par une page on-domain accessible (contact/about/home).
```

**Avantages** :
- ✅ L'agent sait **exactement** quelle URL corriger
- ✅ Code HTTP/erreur fourni (404, Timeout, ConnectionError)
- ✅ Instructions claires pour correction
- ✅ Maximum 3 tentatives par agent

##### 3. Vérification Accessibilité

```python
async def _check_url_accessibility(url: str) -> Dict[str, Any]:
    """
    Vérifie l'accessibilité d'une URL.
    
    Returns:
        {
            "url": str,
            "accessible": bool,
            "status_code": int | None,
            "error": str | None
        }
    """
    # Timeout: 10s, Follow redirects, User-Agent custom
```

**Codes d'erreur gérés** :
- `HTTP 404` : Page non trouvée
- `HTTP 403` : Accès interdit
- `HTTP 500+` : Erreur serveur
- `Timeout` : Délai dépassé (>10s)
- `ConnectionError` : Serveur injoignable
- `SSLError` : Certificat SSL invalide

---

### 📊 Suivi Temps Réel (WebSocket)

#### Heartbeat et Reconnexion

##### Backend (FastAPI)
```python
async def handle_websocket_connection(websocket, session_id):
    """
    WebSocket avec heartbeat automatique.
    
    - Ping toutes les 25s (< 30s Nginx timeout)
    - Format: {"type": "ping", "timestamp": "..."}
    - Attente pong du client
    """
    last_ping = datetime.now()
    while True:
        try:
            update = await asyncio.wait_for(queue.get(), timeout=25.0)
            await websocket.send_text(update)
        except asyncio.TimeoutError:
            # Envoyer ping
            ping_message = json.dumps({
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            })
            await websocket.send_text(ping_message)
```

##### Frontend (React)
```typescript
// Auto-reconnect si déconnexion
useEffect(() => {
  const ws = new WebSocket(WS_URL);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Répondre aux pings
    if (data.type === "ping") {
      ws.send(JSON.stringify({
        type: "pong",
        timestamp: new Date().toISOString()
      }));
      return;
    }
    
    // Traiter les updates
    handleProgressUpdate(data);
  };
  
  ws.onclose = () => {
    // Reconnexion après 3s
    setTimeout(() => connectWebSocket(), 3000);
  };
}, []);
```

#### Métriques en Temps Réel

Le système envoie des **métriques détaillées** pour chaque agent :

```json
{
  "agent_name": "🔍 Éclaireur",
  "status": "running",
  "progress_percentage": 0.66,
  "current_step": "Recherche web",
  "total_steps": 5,
  "completed_steps": 3,
  "performance_metrics": {
    "elapsed_time": 15420,
    "steps_completed": 3,
    "total_steps": 5,
    "quality_score": 0.85,
    "items_processed": 2,
    "subsidiaries_found": 0,
    "citations_count": 5,
    "error_rate": 0.0
  }
}
```

**États d'agent** :
- `waiting` : En attente de démarrage
- `initializing` : Initialisation
- `running` : En cours d'exécution
- `finalizing` : Finalisation
- `completed` : Terminé avec succès
- `error` : Erreur rencontrée

---

### 🗺️ Cartographe - Plan B (Pas de Filiales)

Si le Cartographe ne trouve **aucune filiale**, il active automatiquement le **Plan B** :

#### Recherche Enrichie
```
Aucune filiale identifiée pour {company_name}.

Informations sur l'entreprise principale :
- Siège social : [adresse complète]
- Chiffre d'affaires : [montant] [devise] ([année])
- Effectif : [nombre] employés
- Téléphone : [numéro]
- Email : [email]
- Site web : [URL]
- Sources consultées : [liste]
```

#### Structuration
Le Cartographe structure ces infos dans `extraction_summary.main_company_info` :

```json
{
  "subsidiaries": [],
  "extraction_summary": {
    "total_found": 0,
    "main_company_info": {
      "address": "13 Rue Julien Veyrenc, 26000 Valence, France",
      "revenue": "2.5M EUR (2023)",
      "employees": "25",
      "phone": "+33 4 75 82 16 42",
      "email": "contact@agencenile.com"
    },
    "methodology_used": [
      "Recherche Perplexity - site officiel",
      "Page Contact",
      "Registre Infogreffe"
    ]
  },
  "methodology_notes": [
    "Aucune filiale trouvée après recherche approfondie.",
    "Informations sur l'entreprise principale disponibles."
  ]
}
```

Le **Restructurateur** extrait ensuite `phone` et `email` de `main_company_info` vers le `CompanyInfo` final.

---

### 💰 Tracking des Coûts d'Extraction

Le système calcule automatiquement le coût de chaque extraction basé sur les tokens utilisés par les modèles AI.

#### Format de Réponse

Chaque `CompanyInfo` inclut un champ `extraction_costs` (optionnel) :

```json
{
  "extraction_costs": {
    "cost_usd": 0.0456,
    "cost_eur": 0.0420,
    "total_tokens": 75000,
    "input_tokens": 55000,
    "output_tokens": 20000,
    "models_breakdown": [
      {
        "model": "gpt-4o-mini",
        "input_tokens": 10000,
        "output_tokens": 4000,
        "cost_usd": 0.0030,
        "cost_eur": 0.0028
      },
      {
        "model": "sonar-pro",
        "input_tokens": 20000,
        "output_tokens": 10000,
        "cost_usd": 0.0350,
        "cost_eur": 0.0322
      }
    ],
    "search_type": "advanced",
    "exchange_rate": 0.92
  }
}
```

#### Endpoints de Coûts

```bash
# Statistiques de coûts par organisation
GET /costs/organization/stats?start_date=2024-01-01&end_date=2024-12-31

# Estimation du coût avant extraction
POST /costs/estimate
Content-Type: application/json
{
  "company_name": "Agence Nile",
  "deep_search": false
}

# Détail d'une extraction spécifique
GET /costs/extraction/{extraction_id}
```

#### Modèles et Tarification

| Modèle | Usage | Prix Input (/1M) | Prix Output (/1M) |
|--------|-------|------------------|-------------------|
| `gpt-4o` | Tâches complexes | $2.50 | $10.00 |
| `gpt-4o-mini` | Tâches standard | $0.15 | $0.60 |
| `gpt-4o-search-preview` | Recherches web | $2.50 | $10.00 |
| `sonar-pro` (Perplexity) | Recherches approfondies | $3.00 | $15.00 |

**Coût typique** :
- Recherche simple (`deep_search=False`) : ~0.01-0.05€
- Recherche approfondie (`deep_search=True`) : ~0.05-0.20€

**Note** : Le paramètre `deep_search` détermine quel Cartographe est utilisé (Simple ou Avancé).

---

## 🚀 Démarrage Rapide

### Prérequis

- **Python 3.11+** et **uv** (`pip install uv`)
- **Node 18+** (pour le frontend)
- **Docker** (optionnel, recommandé)
- **Redis** (inclus dans Docker Compose)

### Installation

```bash
# Cloner le repository
git clone https://github.com/votre-repo/FilialeAgents.git
cd FilialeAgents

# Configuration des variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API (PERPLEXITY_API_KEY, OPENAI_API_KEY)
```

### Démarrage avec Docker (Recommandé)

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f api
docker-compose logs -f frontend

# Arrêter les services
docker-compose down
```

**Services disponibles** :
- API : http://localhost:8012
- Frontend : http://localhost:3002
- Swagger UI : http://localhost:8012/docs
- Redis : localhost:6379

### Démarrage Manuel (Makefile)

```bash
# Aide et installation
make help
make setup

# Démarrer l'API
make start

# Dans un autre terminal, démarrer le frontend
make start-frontend

# Vérifier les services
make status

# Ouvrir la documentation Swagger
make docs
```

---

## 🔧 Configuration

### Variables d'Environnement

Créez un fichier `.env` à la racine :

```bash
# API Keys
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...

# Redis
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8012

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8012
NEXT_PUBLIC_WS_URL=ws://localhost:8012/ws

# Guardrails
ENABLE_URL_FILTERING=true
ENABLE_GUARDRAILS=true

# Logging
LOG_LEVEL=INFO
```

### Configuration Agents

Les agents sont configurés dans `api/company_agents/config/agent_config.py` :

```python
# Éclaireur
COMPANY_ANALYZER_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_turns": 5,
    "guardrails": ["eclaireur_output_guardrail"]
}

# Cartographe (Perplexity)
SUBSIDIARY_EXTRACTOR_CONFIG = {
    "model": "sonar-pro",
    "temperature": 0.0,
    "max_tokens": 3200,
    "search_recency_filter": "month"
}
```

---

## 🌐 API et Frontend

### API Endpoints

#### Extraction

```bash
# Extraction par nom
POST /extract
Content-Type: application/json
{
  "company_name": "Agence Nile"
}

# Extraction par URL
POST /extract
Content-Type: application/json
{
  "company_name": "https://www.agencenile.com/"
}

# Récupération des résultats
GET /results/{session_id}

# Tracking temps réel
WS /ws/{session_id}

# Extraction asynchrone (recommandé pour extractions longues)
POST /extract-async
Content-Type: application/json
{
  "company_name": "Agence Nile",
  "deep_search": false
}

# Réponse : 202 Accepted
{
  "session_id": "abc-123",
  "status": "started",
  "message": "Extraction démarrée pour Agence Nile"
}

# Extraction depuis URL (asynchrone)
POST /extract-from-url-async
Content-Type: application/json
{
  "url": "https://www.agencenile.com/",
  "include_subsidiaries": true,
  "deep_search": false
}
```

#### Health & Monitoring

```bash
GET /health              # Health check
GET /docs                # Swagger UI
GET /tracking/{session_id}  # État extraction
```

### Exemples d'Utilisation

#### cURL

```bash
# Lancer une extraction
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "https://www.agencenile.com/"}'

# Résultat : {"session_id": "abc-123", "status": "processing"}

# Récupérer les résultats
curl "http://localhost:8012/results/abc-123"
```

#### Python

```python
import requests

# Extraction
response = requests.post(
    "http://localhost:8012/extract",
    json={"company_name": "https://www.agencenile.com/"}
)
session_id = response.json()["session_id"]

# Résultats
results = requests.get(f"http://localhost:8012/results/{session_id}").json()
print(results["company_name"])
print(results["phone"])
print(results["email"])
```

### Frontend (Next.js)

#### Pages Principales

- **`/`** : Page de recherche avec input URL/nom
- **`/results?session={id}`** : Affichage résultats avec :
  - Vue d'ensemble entreprise
  - Informations de contact (cliquables)
  - Liste des filiales
  - Visualisation graphique
  - Métriques d'extraction

#### Composants Clés

```typescript
// Progress en temps réel
<AgentProgress 
  sessionId={sessionId}
  onComplete={() => router.push(`/results?session=${sessionId}`)}
/>

// Affichage contacts
{company.phone && (
  <a href={`tel:${company.phone}`}>
    📞 {company.phone}
  </a>
)}

// Liste filiales
<SubsidiariesList subsidiaries={company.subsidiaries_details} />
```

---

## 🧪 Tests

### Tests Automatiques

```bash
# API Tests
make test

# Tests guardrails
cd api/company_agents/guardrails
pytest tests/

# Coverage
pytest --cov=company_agents --cov-report=html
```

### Tests Manuels

#### Test Complet (Agence Nile)

```bash
# 1. Lancer l'extraction
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "https://www.agencenile.com/"}'

# 2. Vérifier les logs
docker-compose logs -f api | grep "Éclaireur\|Cartographe\|Guardrail"

# 3. Résultats attendus
# - company_name: "Agence Nile"
# - phone: "+33 4 75 82 16 42"
# - email: "contact@agencenile.com"
# - headquarters_city: "Valence"
# - subsidiaries_details: [] (pas de filiales)
```

#### Test avec Filiales (S.F.E. Group)

```bash
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "S.F.E. Group"}'

# Résultats attendus
# - subsidiaries_details: [...]
# - Chaque filiale avec phone/email si disponible
# - Coordonnées GPS enrichies
```

### Tests Guardrails

```bash
# Test URL morte (doit déclencher guardrail)
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "https://www.example-with-dead-links.com/"}'

# Logs attendus :
# - "🚨 Guardrail Éclaireur déclenché"
# - "URLs NON ACCESSIBLES: [...]"
# - "⚠️ Guardrail déclenché (tentative 1/3)"
# - "✅ Guardrail Éclaireur: validation OK" (après correction)
```

---

## 📚 Documentation Technique

### Structure du Projet

```
FilialeAgents/
├── api/                                # Backend FastAPI
│   ├── main.py                         # Entry point ASGI
│   ├── start.py                        # Démarrage local
│   ├── routers/                        # Routes API
│   │   ├── extraction.py               # POST /extract
│   │   ├── health.py                   # GET /health
│   │   ├── tracking.py                 # GET /tracking/{session_id}
│   │   └── websocket.py                # WS /ws/{session_id}
│   ├── services/                       # Services
│   │   ├── extraction_service.py       # Orchestration extraction
│   │   ├── websocket_service.py        # Gestion WebSocket + heartbeat
│   │   └── agent_tracking_service.py   # Tracking état agents
│   ├── company_agents/                 # Agents et orchestration
│   │   ├── extraction_core.py          # Point d'entrée extraction
│   │   ├── orchestrator/               # Orchestration
│   │   │   ├── extraction_orchestrator.py  # Pipeline 5 étapes
│   │   │   └── agent_caller.py         # Appels agents + métriques
│   │   ├── subs_agents/                # Agents spécialisés
│   │   │   ├── company_analyzer.py     # 🔍 Éclaireur
│   │   │   ├── information_extractor.py # ⛏️ Mineur
│   │   │   ├── subsidiary_extractor.py # 🗺️ Cartographe
│   │   │   ├── meta_validator.py       # ⚖️ Superviseur
│   │   │   └── data_validator.py       # 🔄 Restructurateur
│   │   ├── guardrails/                 # Guardrails
│   │   │   ├── eclaireur.py            # Guardrail Éclaireur
│   │   │   ├── __init__.py             # load_guardrails()
│   │   │   └── README.md               # Doc guardrails
│   │   ├── metrics/                    # Métriques temps réel
│   │   │   ├── metrics_collector.py    # Collection métriques
│   │   │   ├── real_time_tracker.py    # Envoi WebSocket
│   │   │   ├── agent_wrappers.py       # Wrappers agents + retry
│   │   │   └── agent_hooks.py          # Hooks guardrails
│   │   ├── models.py                   # Modèles Pydantic
│   │   └── config/                     # Configuration
│   ├── status/                         # Gestion état Redis
│   │   ├── manager.py                  # StatusManager
│   │   └── models.py                   # AgentStatus, AgentState
│   └── middleware/                     # Middlewares
│       └── logging.py                  # Logging requêtes
├── frontend/                           # Frontend Next.js
│   ├── src/
│   │   ├── app/                        # Pages Next.js 14
│   │   │   ├── page.tsx                # Page recherche
│   │   │   └── results/page.tsx        # Page résultats
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── agent-progress.tsx  # Progress WebSocket
│   │   │   │   └── enhanced-agent-progress.tsx
│   │   │   ├── company/
│   │   │   │   ├── company-overview.tsx  # Vue entreprise + contacts
│   │   │   │   ├── subsidiaries-list.tsx # Liste filiales
│   │   │   │   └── subsidiaries-visualization.tsx
│   │   │   └── search/
│   │   │       └── search-page.tsx     # Formulaire recherche
│   │   ├── hooks/
│   │   │   ├── use-company-data.ts     # Fetch résultats
│   │   │   └── use-safe-search-params.ts
│   │   └── lib/
│   │       └── api.ts                  # Types TypeScript
│   └── public/                         # Assets statiques
├── docs/                               # Documentation
│   └── ARCHITECTURE.md                 # Architecture détaillée
├── docker-compose.yml                  # Services Docker
├── pyproject.toml                      # Dépendances Python (uv)
├── Makefile                            # Commandes utilitaires
└── README.md                           # Ce fichier
```

### Modèles de Données

#### CompanyInfo (Output Final)
```python
class CompanyInfo(BaseModel):
    company_name: str
    headquarters_address: str
    headquarters_city: Optional[str]
    headquarters_country: Optional[str]
    parent_company: Optional[str]
    sector: str
    activities: List[str]
    revenue_recent: Optional[str]
    employees: Optional[str]
    founded_year: Optional[int]
    phone: Optional[str]              # ← Ajouté
    email: Optional[str]              # ← Ajouté
    subsidiaries_details: List[SubsidiaryDetail]
    # 🆕 Présence commerciale (bureaux, partenaires, distributeurs)
    commercial_presence_details: List[CommercialPresence]
    sources: List[SourceRef]
    methodology_notes: Optional[List[str]]
    extraction_metadata: Optional[ExtractionMetadata]
    extraction_date: Optional[str]
```

#### SubsidiaryDetail
```python
class SubsidiaryDetail(BaseModel):
    legal_name: str
    headquarters: Optional[LocationInfo]  # Contient phone, email
    activity: Optional[str]
    confidence: Optional[float]
    sources: List[SourceRef]
```

#### LocationInfo
```python
class LocationInfo(BaseModel):
    label: Optional[str]
    line1: Optional[str]
    city: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    phone: Optional[str]              # ← Contact
    email: Optional[str]              # ← Contact
    website: Optional[str]
    sources: Optional[List[SourceRef]]
```

#### CommercialPresence
```python
class CommercialPresence(BaseModel):
    name: str                          # Nom du bureau/partenaire/distributeur
    type: Literal["office", "partner", "distributor", "representative"]
    relationship: Literal["owned", "partnership", "authorized_distributor", "franchise"]
    activity: Optional[str]
    location: LocationInfo
    phone: Optional[str]
    email: Optional[str]
    confidence: Optional[float]
    sources: List[SourceRef]
    since_year: Optional[int]
    status: Optional[Literal["active", "inactive", "unverified"]]
```

### Documentation Détaillée

- **Architecture** : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API Reference** : [api/README.md](api/README.md)
- **Guardrails** : [api/company_agents/guardrails/README.md](api/company_agents/guardrails/README.md)
- **Frontend** : [frontend/README.md](frontend/README.md)
- **Swagger UI** : http://localhost:8012/docs

---

## 🛠️ Développement

### Architecture Technique

- **Backend** : FastAPI + OpenAI Agents SDK + Perplexity API
- **Frontend** : Next.js 14 + React + TypeScript + Tailwind CSS
- **Database** : Redis (sessions + cache)
- **WebSocket** : FastAPI WebSocket + Auto-reconnect
- **Validation** : Pydantic + Custom Guardrails
- **Deployment** : Docker Compose + Nginx

### Bonnes Pratiques

1. **Agents** : Prompts clairs, schémas stricts, guardrails actifs
2. **Métriques** : Tracking temps réel, logs structurés
3. **Validation** : Pydantic strict, guardrails OpenAI, retry automatique
4. **Performance** : Cache Redis, requêtes parallèles, timeouts
5. **UX** : WebSocket temps réel, progress granulaire, liens cliquables

### Dépendances Principales

**Backend** :
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "openai>=1.50.0",
    "agents>=0.1.0",
    "pydantic>=2.5.0",
    "redis>=5.0.0",
    "httpx>=0.25.0",
]
```

**Frontend** :
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "axios": "^1.6.0",
    "framer-motion": "^10.0.0"
  }
}
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Veuillez :

1. **Fork** le repository
2. Créer une **branche feature** (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une **Pull Request**

### Guidelines

- Suivre les conventions de code existantes
- Ajouter des tests pour les nouvelles fonctionnalités
- Mettre à jour la documentation
- Utiliser des messages de commit descriptifs

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🆘 Support

- **Issues** : [GitHub Issues](https://github.com/votre-repo/FilialeAgents/issues)
- **Documentation API** : [api/README.md](api/README.md)
- **Swagger UI** : http://localhost:8012/docs
- **Email** : support@votre-domaine.com

---

## 📊 Statut du Projet

- ✅ **Pipeline Multi-Agents** : Opérationnel (5 agents)
- ✅ **Guardrails** : Actifs avec retry automatique
- ✅ **Extraction Contacts** : Téléphone + Email
- ✅ **WebSocket Temps Réel** : Heartbeat + Auto-reconnect
- ✅ **Frontend Next.js** : Interface complète
- ✅ **Docker Compose** : Déploiement simplifié
- 🚧 **Tests E2E** : En cours
- 🚧 **CI/CD** : En cours

---

## 🎉 Remerciements

- OpenAI pour l'Agents SDK
- Perplexity pour l'API Sonar
- La communauté FastAPI et Next.js

---

**Développé avec ❤️ par l'équipe FilialeAgents**
