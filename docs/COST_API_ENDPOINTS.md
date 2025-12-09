# 📊 API Endpoints - Statistiques de Coûts

Documentation complète des endpoints API pour le tracking des coûts.

---

## 🔐 Authentification

Tous les endpoints nécessitent une authentification via JWT Bearer token.

```bash
Authorization: Bearer {access_token}
```

---

## 📍 Endpoints Disponibles

### 1. Statistiques d'Organisation

**`GET /costs/organization/stats`**

Récupère les statistiques de coûts pour l'organisation de l'utilisateur.

**Query Parameters:**
- `start_date` (optional): Date de début au format ISO (YYYY-MM-DD)
- `end_date` (optional): Date de fin au format ISO (YYYY-MM-DD)

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/organization/stats?start_date=2025-01-01&end_date=2025-01-31" \
  -H "Authorization: Bearer {token}"
```

**Réponse:**
```json
{
  "organization_id": "uuid",
  "total_searches": 48,
  "completed_searches": 45,
  "total_cost_eur": 12.45,
  "total_cost_usd": 13.53,
  "total_tokens": 2500000,
  "average_cost_per_search_eur": 0.276,
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-01-31T23:59:59"
}
```

---

### 2. Statistiques Mensuelles

**`GET /costs/organization/monthly/{year}/{month}`**

Récupère les statistiques pour un mois spécifique.

**Path Parameters:**
- `year`: Année (ex: 2025)
- `month`: Mois (1-12)

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/organization/monthly/2025/1" \
  -H "Authorization: Bearer {token}"
```

**Réponse:**
```json
{
  "organization_id": "uuid",
  "total_searches": 48,
  "completed_searches": 45,
  "total_cost_eur": 12.45,
  "total_cost_usd": 13.53,
  "total_tokens": 2500000,
  "average_cost_per_search_eur": 0.276,
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-01-31T23:59:59",
  "year": 2025,
  "month": 1,
  "month_name": "Janvier"
}
```

---

### 3. Mois Actuel

**`GET /costs/organization/current-month`**

Récupère les statistiques du mois en cours (raccourci).

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/organization/current-month" \
  -H "Authorization: Bearer {token}"
```

**Réponse:** Identique à l'endpoint monthly.

---

### 4. Top Recherches Coûteuses

**`GET /costs/organization/top-expensive`**

Liste des recherches les plus coûteuses de l'organisation.

**Query Parameters:**
- `limit` (optional): Nombre de résultats (défaut: 10, max: 100)

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/organization/top-expensive?limit=5" \
  -H "Authorization: Bearer {token}"
```

**Réponse:**
```json
[
  {
    "id": "extraction-uuid",
    "company_name": "Total Energies",
    "created_at": "2025-01-15T14:30:00",
    "cost_eur": 1.25,
    "cost_usd": 1.36,
    "total_tokens": 150000,
    "subsidiaries_count": 25,
    "processing_time": 45.5
  },
  {
    "id": "extraction-uuid-2",
    "company_name": "Airbus",
    "created_at": "2025-01-20T10:15:00",
    "cost_eur": 0.98,
    "cost_usd": 1.07,
    "total_tokens": 120000,
    "subsidiaries_count": 18,
    "processing_time": 38.2
  }
]
```

---

### 5. Estimation de Coût

**`POST /costs/estimate`**

Estime le coût d'une extraction avant de la lancer.

**Body:**
```json
{
  "extraction_type": "advanced",
  "has_subsidiaries": true,
  "subsidiaries_count": 10
}
```

**Exemple:**
```bash
curl -X POST "http://localhost:8012/costs/estimate" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "extraction_type": "advanced",
    "has_subsidiaries": true,
    "subsidiaries_count": 10
  }'
```

**Réponse:**
```json
{
  "total_input_tokens": 195000,
  "total_output_tokens": 98000,
  "total_tokens": 293000,
  "total_cost_usd": 0.68,
  "total_cost_eur": 0.625,
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
      "input_tokens": 170000,
      "output_tokens": 86000,
      "cost_usd": 0.525,
      "cost_eur": 0.483
    },
    {
      "model": "sonar-pro",
      "input_tokens": 20000,
      "output_tokens": 10000,
      "cost_usd": 0.15,
      "cost_eur": 0.138
    }
  ],
  "exchange_rate": 0.92,
  "estimate_type": "approximate",
  "extraction_type": "advanced",
  "estimated_subsidiaries": 10
}
```

---

### 6. Détail d'une Extraction

**`GET /costs/extraction/{extraction_id}`**

Récupère les détails de coût pour une extraction spécifique.

**Path Parameters:**
- `extraction_id`: UUID de l'extraction

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/extraction/{extraction_id}" \
  -H "Authorization: Bearer {token}"
```

**Réponse:**
```json
{
  "id": "extraction-uuid",
  "company_name": "Total Energies",
  "created_at": "2025-01-15T14:30:00",
  "cost_usd": 1.36,
  "cost_eur": 1.25,
  "total_tokens": 150000,
  "input_tokens": 75000,
  "output_tokens": 75000,
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
    },
    {
      "model": "gpt-4o-search-preview",
      "input_tokens": 20000,
      "output_tokens": 48000,
      "cost_usd": 0.53,
      "cost_eur": 0.487
    }
  ],
  "subsidiaries_count": 25,
  "processing_time": 45.5,
  "extraction_type": "url"
}
```

---

### 7. Statut du Budget

**`GET /costs/organization/budget-status`**

Récupère le statut d'utilisation du budget mensuel.

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/organization/budget-status" \
  -H "Authorization: Bearer {token}"
```

**Réponse:**
```json
{
  "organization_id": "uuid",
  "organization_name": "Acme Corp",
  "current_month": "2025-01",
  "total_cost_eur": 45.67,
  "total_searches": 120,
  "completed_searches": 115,
  "average_cost_per_search_eur": 0.397,
  "has_budget_limit": false,
  "monthly_budget_eur": null,
  "remaining_budget_eur": null,
  "budget_usage_percentage": null,
  "warning_threshold_reached": false,
  "limit_reached": false
}
```

---

### 8. Health Check

**`GET /costs/health`**

Vérifie que le service de tracking est opérationnel.

**Exemple:**
```bash
curl -X GET "http://localhost:8012/costs/health"
```

**Réponse:**
```json
{
  "status": "healthy",
  "models_configured": [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4o-search-preview",
    "sonar-pro"
  ],
  "exchange_rate_usd_to_eur": 0.92,
  "service": "cost_tracking",
  "version": "1.0"
}
```

---

## 🔒 Permissions

| Endpoint | Permission Requise |
|----------|-------------------|
| `/costs/organization/stats` | User authentifié de l'organisation |
| `/costs/organization/monthly/{year}/{month}` | User authentifié de l'organisation |
| `/costs/organization/current-month` | User authentifié de l'organisation |
| `/costs/organization/top-expensive` | User authentifié de l'organisation |
| `/costs/estimate` | User authentifié |
| `/costs/extraction/{id}` | User authentifié de l'organisation propriétaire |
| `/costs/organization/budget-status` | User authentifié de l'organisation |
| `/costs/health` | Public (pas d'auth requise) |

**Note:** Les utilisateurs ne peuvent voir que les données de leur propre organisation.

---

## 📊 Codes de Statut HTTP

| Code | Description |
|------|-------------|
| 200 | Succès |
| 400 | Requête invalide (format de date incorrect, etc.) |
| 401 | Non authentifié (token manquant/invalide) |
| 403 | Accès refusé (extraction d'une autre organisation) |
| 404 | Ressource non trouvée (extraction inexistante) |
| 500 | Erreur serveur |

---

## 💡 Cas d'Usage

### 1. Dashboard de Coûts Mensuel

```typescript
// Récupérer les stats du mois en cours
const currentMonth = await fetch('/costs/organization/current-month', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// Afficher: "Vous avez dépensé {cost}€ ce mois sur {searches} recherches"
```

### 2. Estimation Avant Recherche

```typescript
// Avant de lancer une recherche avancée
const estimate = await fetch('/costs/estimate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    extraction_type: 'advanced',
    has_subsidiaries: true,
    subsidiaries_count: 15
  })
}).then(r => r.json());

// Afficher: "Cette recherche coûtera environ {estimate.total_cost_eur}€"
// Demander confirmation à l'utilisateur
```

### 3. Historique des Coûts

```typescript
// Récupérer les 3 derniers mois
const months = [
  await fetch('/costs/organization/monthly/2025/1').then(r => r.json()),
  await fetch('/costs/organization/monthly/2024/12').then(r => r.json()),
  await fetch('/costs/organization/monthly/2024/11').then(r => r.json())
];

// Créer un graphique d'évolution
```

### 4. Alertes de Budget

```typescript
// Vérifier le statut du budget
const budget = await fetch('/costs/organization/budget-status').then(r => r.json());

if (budget.budget_usage_percentage > 80) {
  showWarning('Vous avez utilisé 80% de votre budget mensuel');
}
```

---

## 🧪 Test avec cURL

```bash
# 1. Se connecter et obtenir un token
TOKEN=$(curl -X GET "http://localhost:8012/auth/hubspot/login" | jq -r '.token')

# 2. Statistiques du mois
curl -X GET "http://localhost:8012/costs/organization/current-month" \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Estimer une recherche
curl -X POST "http://localhost:8012/costs/estimate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"extraction_type":"advanced","has_subsidiaries":true,"subsidiaries_count":10}' | jq

# 4. Top 5 recherches coûteuses
curl -X GET "http://localhost:8012/costs/organization/top-expensive?limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 📝 Notes d'Implémentation

### Frontend

Exemples de composants React/Next.js à créer :

1. **CostBadge** - Affiche le coût d'une recherche
2. **MonthlyCostDashboard** - Dashboard mensuel
3. **CostEstimator** - Outil d'estimation avant recherche
4. **TopExpensiveList** - Liste des recherches coûteuses
5. **BudgetProgressBar** - Barre de progression du budget

### Backend

Pour intégrer le tracking dans le processus d'extraction :

1. Capturer les tokens après chaque appel AI
2. Agréger tous les usages
3. Calculer le coût avec `cost_tracking_service.calculate_extraction_cost()`
4. Sauvegarder dans `CompanyExtraction`

---

**Documentation générée le:** 2025-01-24
**Version API:** 1.0
**Base URL:** http://localhost:8012
