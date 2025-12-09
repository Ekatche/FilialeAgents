au# 💰 Système de Tracking des Coûts - FilialeAgents

## 📋 Vue d'ensemble

Ce document décrit le système de tracking des coûts pour l'application FilialeAgents. Le système permet de calculer le coût exact de chaque recherche d'entreprise en fonction des tokens utilisés par les différents modèles AI.

---

## 🤖 Modèles AI Utilisés

### Modèles configurés dans le système

| Modèle | Usage | Prix Input (/1M tokens) | Prix Output (/1M tokens) |
|--------|-------|-------------------------|--------------------------|
| **gpt-4o** | Tâches complexes (Cartographe, Validator, Restructurer) | $2.50 | $10.00 |
| **gpt-4o-mini** | Tâches standard (Orchestrateur, Analyzer, Extractor) | $0.15 | $0.60 |
| **gpt-4o-search-preview** | Recherches web OpenAI | $2.50 | $10.00 |
| **sonar-pro** (Perplexity) | Recherches approfondies | $3.00 | $15.00 |

### Pipeline d'extraction typique

```
1. Company Analyzer        → gpt-4o-mini    (~5K input + ~2K output)
2. Information Extractor   → gpt-4o-mini    (~5K input + ~2K output)
3. Subsidiary Extractor    → gpt-4o         (~10K input + ~5K output par filiale)
   └─ Web Search           → gpt-4o-search-preview OU sonar-pro
4. Meta Validator          → gpt-4o         (~8K input + ~3K output)
5. Data Restructurer       → gpt-4o         (~6K input + ~2K output)
```

---

## 💾 Modèle de Données

### Colonnes ajoutées à `company_extractions`

```python
# Coûts
cost_usd: Float           # Coût total en USD
cost_eur: Float           # Coût total en EUR
total_tokens: Integer     # Nombre total de tokens
input_tokens: Integer     # Tokens d'entrée
output_tokens: Integer    # Tokens de sortie
models_usage: JSONB       # Détail par modèle
```

### Structure de `models_usage` (JSONB)

```json
{
  "models_breakdown": [
    {
      "model": "gpt-4o-mini",
      "input_tokens": 5000,
      "output_tokens": 2000,
      "cost_usd": 0.0018,
      "cost_eur": 0.001656
    },
    {
      "model": "gpt-4o",
      "input_tokens": 50000,
      "output_tokens": 25000,
      "cost_usd": 0.375,
      "cost_eur": 0.345
    }
  ],
  "total_input_tokens": 55000,
  "total_output_tokens": 27000,
  "total_tokens": 82000,
  "total_cost_usd": 0.3768,
  "total_cost_eur": 0.346656,
  "exchange_rate": 0.92
}
```

---

## 🔧 Utilisation du Service

### 1. Import du service

```python
from api.services.cost_tracking_service import (
    cost_tracking_service,
    ModelPricing
)
```

### 2. Calculer le coût d'une extraction

```python
# Collecter l'usage des modèles pendant l'extraction
models_usage = [
    {
        "model": "gpt-4o-mini",
        "input_tokens": 5000,
        "output_tokens": 2000
    },
    {
        "model": "gpt-4o",
        "input_tokens": 50000,
        "output_tokens": 25000
    },
    {
        "model": "sonar-pro",
        "input_tokens": 20000,
        "output_tokens": 10000
    }
]

# Calculer le coût total
cost_data = cost_tracking_service.calculate_extraction_cost(models_usage)

# Résultat:
# {
#     "total_input_tokens": 75000,
#     "total_output_tokens": 37000,
#     "total_tokens": 112000,
#     "total_cost_usd": 0.5268,
#     "total_cost_eur": 0.484656,
#     "models_breakdown": [...],
#     "exchange_rate": 0.92
# }
```

### 3. Sauvegarder dans la base de données

```python
# Après l'extraction
extraction = CompanyExtraction(
    organization_id=org_id,
    user_id=user_id,
    company_name="Company Name",
    # ... autres champs ...

    # Coûts
    cost_usd=cost_data["total_cost_usd"],
    cost_eur=cost_data["total_cost_eur"],
    total_tokens=cost_data["total_tokens"],
    input_tokens=cost_data["total_input_tokens"],
    output_tokens=cost_data["total_output_tokens"],
    models_usage=cost_data  # Tout l'objet
)
```

### 4. Récupérer les statistiques d'une organisation

```python
# Coûts totaux
stats = await cost_tracking_service.get_organization_costs(
    organization_id=org_id,
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31),
    db=db
)

# Résultat:
# {
#     "organization_id": "uuid",
#     "total_searches": 50,
#     "completed_searches": 48,
#     "total_cost_eur": 24.50,
#     "total_cost_usd": 26.63,
#     "total_tokens": 5000000,
#     "average_cost_per_search_eur": 0.510,
#     "start_date": "2025-01-01T00:00:00",
#     "end_date": "2025-01-31T23:59:59"
# }
```

### 5. Coûts mensuels

```python
monthly = await cost_tracking_service.get_monthly_costs(
    organization_id=org_id,
    year=2025,
    month=1,
    db=db
)
```

### 6. Recherches les plus coûteuses

```python
top_expensive = await cost_tracking_service.get_top_expensive_searches(
    organization_id=org_id,
    limit=10,
    db=db
)
```

### 7. Estimation avant recherche

```python
# Estimer le coût d'une recherche avant de la lancer
estimate = cost_tracking_service.estimate_search_cost(
    extraction_type="advanced",  # ou "simple"
    has_subsidiaries=True,
    subsidiaries_count=10
)

# Résultat:
# {
#     "total_cost_usd": 0.45,
#     "total_cost_eur": 0.414,
#     "total_tokens": 195000,
#     "estimate_type": "approximate",
#     "extraction_type": "advanced",
#     "estimated_subsidiaries": 10
# }
```

---

## 🔨 Intégration dans le Processus d'Extraction

### Étape 1 : Instrumenter les agents

Dans chaque agent qui utilise un modèle AI, capturer l'usage des tokens :

```python
# Dans company_analyzer.py, information_extractor.py, etc.

class CompanyAnalyzer:
    async def analyze(self, company_name: str):
        # Utiliser l'agent OpenAI
        result = await self.agent.run(...)

        # Capturer les tokens (si disponible via l'API OpenAI Agents)
        tokens_used = {
            "model": "gpt-4o-mini",
            "input_tokens": result.usage.input_tokens,  # Si disponible
            "output_tokens": result.usage.output_tokens
        }

        return result, tokens_used
```

### Étape 2 : Agréger dans l'orchestrateur

Dans `extraction_manager.py` ou le point d'entrée de l'extraction :

```python
async def extract_company(company_name: str, organization_id: str, user_id: str):
    all_tokens_usage = []

    # 1. Company Analyzer
    result1, tokens1 = await company_analyzer.analyze(company_name)
    all_tokens_usage.append(tokens1)

    # 2. Information Extractor
    result2, tokens2 = await information_extractor.extract(result1)
    all_tokens_usage.append(tokens2)

    # 3. Subsidiary Extractor
    result3, tokens3 = await subsidiary_extractor.extract(result2)
    all_tokens_usage.append(tokens3)

    # 4. Meta Validator
    result4, tokens4 = await meta_validator.validate(result3)
    all_tokens_usage.append(tokens4)

    # 5. Data Restructurer
    final_result, tokens5 = await data_restructurer.restructure(result4)
    all_tokens_usage.append(tokens5)

    # Calculer le coût total
    cost_data = cost_tracking_service.calculate_extraction_cost(all_tokens_usage)

    # Sauvegarder dans la DB
    extraction = CompanyExtraction(
        organization_id=organization_id,
        user_id=user_id,
        company_name=company_name,
        extraction_data=final_result,
        cost_usd=cost_data["total_cost_usd"],
        cost_eur=cost_data["total_cost_eur"],
        total_tokens=cost_data["total_tokens"],
        input_tokens=cost_data["total_input_tokens"],
        output_tokens=cost_data["total_output_tokens"],
        models_usage=cost_data
    )

    return extraction
```

### Étape 3 : Vérifier les limites de plan

Avant de lancer une extraction, vérifier si l'organisation a dépassé son budget :

```python
# Dans extraction.py (router)

@router.post("/extract")
async def extract_company(
    request: CompanyExtractionRequest,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    # Estimer le coût
    estimated_cost = cost_tracking_service.estimate_search_cost(
        extraction_type="simple",
        has_subsidiaries=True,
        subsidiaries_count=5  # Estimation
    )

    # Vérifier le budget mensuel (si configuré)
    if organization.monthly_budget_eur:
        monthly_stats = await cost_tracking_service.get_monthly_costs(
            organization.id,
            year=datetime.now().year,
            month=datetime.now().month,
            db=db
        )

        if monthly_stats["total_cost_eur"] + estimated_cost["total_cost_eur"] > organization.monthly_budget_eur:
            raise HTTPException(
                status_code=403,
                detail=f"Budget mensuel dépassé. Budget: {organization.monthly_budget_eur}€, Utilisé: {monthly_stats['total_cost_eur']}€"
            )

    # Lancer l'extraction
    ...
```

---

## 📊 Endpoints API à Créer

### 1. Statistiques de coûts

```python
GET /api/costs/organization/{organization_id}
    ?start_date=2025-01-01
    &end_date=2025-01-31
```

### 2. Coûts mensuels

```python
GET /api/costs/organization/{organization_id}/monthly/{year}/{month}
```

### 3. Recherches les plus coûteuses

```python
GET /api/costs/organization/{organization_id}/top-expensive
    ?limit=10
```

### 4. Estimation de coût

```python
POST /api/costs/estimate
{
    "extraction_type": "advanced",
    "has_subsidiaries": true,
    "subsidiaries_count": 10
}
```

### 5. Export des coûts

```python
GET /api/costs/organization/{organization_id}/export
    ?format=csv
    ?start_date=2025-01-01
    &end_date=2025-01-31
```

---

## 🎨 Affichage dans le Frontend

### Carte de coût pour une recherche

```tsx
<div className="cost-card">
  <h3>Coût de la recherche</h3>
  <div className="cost-amount">
    <span className="eur">{extraction.cost_eur.toFixed(4)}€</span>
    <span className="usd">({extraction.cost_usd.toFixed(4)}$)</span>
  </div>
  <div className="tokens-info">
    <span>{extraction.total_tokens.toLocaleString()} tokens</span>
    <span className="breakdown">
      {extraction.input_tokens.toLocaleString()} in / {extraction.output_tokens.toLocaleString()} out
    </span>
  </div>
  <details>
    <summary>Détail par modèle</summary>
    {extraction.models_usage.models_breakdown.map(model => (
      <div key={model.model} className="model-row">
        <span>{model.model}</span>
        <span>{model.cost_eur.toFixed(4)}€</span>
      </div>
    ))}
  </details>
</div>
```

### Dashboard de coûts

```tsx
<div className="costs-dashboard">
  <div className="stat-card">
    <h4>Coût total ce mois</h4>
    <div className="value">{monthlyStats.total_cost_eur.toFixed(2)}€</div>
    <div className="subtext">{monthlyStats.completed_searches} recherches</div>
  </div>

  <div className="stat-card">
    <h4>Coût moyen par recherche</h4>
    <div className="value">{monthlyStats.average_cost_per_search_eur.toFixed(4)}€</div>
  </div>

  <div className="stat-card">
    <h4>Budget mensuel</h4>
    <div className="value">
      {monthlyStats.total_cost_eur.toFixed(2)}€ / {organization.monthly_budget_eur}€
    </div>
    <div className="progress-bar">
      <div style={{width: `${(monthlyStats.total_cost_eur / organization.monthly_budget_eur) * 100}%`}} />
    </div>
  </div>
</div>
```

---

## 🔐 Contrôles et Limites

### 1. Ajouter un budget mensuel à Organization

```python
# Dans db_models.py
class Organization(Base):
    # ... autres champs ...
    monthly_budget_eur = Column(Float, nullable=True)  # Budget mensuel en EUR
```

### 2. Alertes de dépassement

- Alerte à 80% du budget
- Alerte à 100% du budget
- Blocage à 110% du budget (optionnel)

### 3. Notifications

- Email à l'admin quand 80% atteint
- Email à tous les admins quand 100% atteint

---

## 📈 Analytics

### Métriques à tracker

1. **Coût moyen par recherche**
2. **Coût par type de recherche** (simple vs advanced)
3. **Coût par filiale extraite**
4. **Évolution mensuelle des coûts**
5. **Top 10 recherches les plus coûteuses**
6. **Distribution des coûts par modèle AI**
7. **Ratio coût/valeur** (si applicable)

---

## 🛠️ Maintenance

### Mise à jour des prix

Les prix des modèles AI peuvent changer. Pour mettre à jour :

1. Modifier `ModelPricing` dans `cost_tracking_service.py`
2. Les nouveaux prix s'appliqueront automatiquement aux nouvelles recherches
3. Les anciennes recherches conservent leurs coûts historiques

### Mise à jour du taux de change

```python
# Option 1: Mise à jour manuelle
ModelPricing.USD_TO_EUR_RATE = Decimal("0.93")

# Option 2: Fetch automatique depuis une API
import httpx

async def update_exchange_rate():
    response = await httpx.get("https://api.exchangerate-api.com/v4/latest/USD")
    data = response.json()
    ModelPricing.USD_TO_EUR_RATE = Decimal(str(data["rates"]["EUR"]))
```

---

## 📋 Checklist d'implémentation

- [x] Service de tracking créé
- [x] Modèle de données étendu
- [x] Migration créée
- [ ] Instrumenter les agents pour capturer les tokens
- [ ] Intégrer dans l'orchestrateur
- [ ] Créer les endpoints API
- [ ] Ajouter les vérifications de budget
- [ ] Créer les composants frontend
- [ ] Ajouter les notifications d'alerte
- [ ] Tests unitaires
- [ ] Documentation utilisateur

---

**Document créé le:** 2025-01-24
**Dernière mise à jour:** 2025-01-24
**Version:** 1.0
