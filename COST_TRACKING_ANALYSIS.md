# 🔍 Analyse Technique du Code pour le Tracking des Coûts

**Date** : 2025-10-25
**Status** : Analyse complétée ✅

---

## 📋 Architecture du Système d'Extraction

### Flux d'exécution actuel

```
1. extraction_core.py::extract_company_data()
   ↓
2. orchestrate_extraction() [orchestrator/extraction_orchestrator.py]
   ↓
3. agent_caller.py::call_*_agent()
   ↓
4. agent_wrappers.py::run_agent_with_metrics()
   ↓
5. Runner.run(agent, input, max_turns)
   ↓
6. result (avec potentiellement result.usage)
```

### Agents exécutés séquentiellement

1. **🔍 Éclaireur** (Company Analyzer) - `gpt-4o-mini`
2. **⛏️ Mineur** (Information Extractor) - `gpt-4o-mini`
3. **🗺️ Cartographe** (Subsidiary Extractor) - `gpt-4o` + `gpt-4o-search-preview` OU `sonar-pro`
4. **⚖️ Superviseur** (Meta Validator) - `gpt-4o`
5. **🔄 Restructurateur** (Data Restructurer) - `gpt-4o`

---

## ✅ Ce qui existe déjà

### 1. Système de Métriques (metrics/)

- **AgentMetrics** : Track le temps, étapes, statut
- **performance_metrics** : Dictionnaire extensible pour données custom
- **run_agent_with_metrics()** : Wrapper qui execute les agents

### 2. Service de Tracking des Coûts

- `cost_tracking_service.py` : Calcul des coûts basé sur tokens
- `ModelPricing` : Prix par modèle (gpt-4o, gpt-4o-mini, etc.)
- `calculate_extraction_cost()` : Fonction principale de calcul

### 3. Base de Données

Table `company_extractions` avec colonnes :
```python
cost_usd: Float
cost_eur: Float
total_tokens: Integer
input_tokens: Integer
output_tokens: Integer
models_usage: JSONB
```

### 4. Frontend

- `ExtractionCostCard.tsx` : Composant déjà créé ✅
- Intégré dans `results-page.tsx` ✅
- Hook `useCosts` pour API ✅

---

## 🎯 Points d'Injection pour le Tracking

### Point 1 : Capture des tokens dans run_agent_with_metrics()

**Fichier** : `api/company_agents/metrics/agent_wrappers.py`
**Ligne** : ~123 (après `result = await Runner.run(...)`)

**Action** :
```python
# Après l'exécution de l'agent
result = await Runner.run(agent, input=current_input, max_turns=max_turns)

# AJOUTER : Capturer les tokens si disponibles
if hasattr(result, 'usage') and result.usage:
    agent_metrics.performance_metrics["tokens"] = {
        "model": agent.model if hasattr(agent, 'model') else "unknown",
        "input_tokens": result.usage.prompt_tokens,
        "output_tokens": result.usage.completion_tokens,
        "total_tokens": result.usage.total_tokens
    }
```

### Point 2 : Retourner les tokens dans agent_caller.py

**Fichier** : `api/company_agents/orchestrator/agent_caller.py`
**Fonctions** : `call_company_analyzer`, `call_information_extractor`, etc.

**Action** : Modifier pour retourner non seulement le résultat mais aussi les métriques (ou enrichir ExtractionState)

### Point 3 : Agréger dans orchestrate_extraction()

**Fichier** : `api/company_agents/orchestrator/extraction_orchestrator.py`
**Ligne** : ~200 (avant le return final)

**Action** :
```python
# AJOUTER : Récupérer les métriques de tous les agents
all_models_usage = []

# Récupérer les tokens de chaque agent
analyzer_metrics = metrics_collector.get_agent_metrics("🔍 Éclaireur", session_id)
if analyzer_metrics and "tokens" in analyzer_metrics.performance_metrics:
    all_models_usage.append(analyzer_metrics.performance_metrics["tokens"])

# ... même chose pour les autres agents

# Ajouter au résultat final
result["models_usage_raw"] = all_models_usage
```

### Point 4 : Calculer et sauvegarder dans extraction_core.py

**Fichier** : `api/company_agents/extraction_core.py`
**Ligne** : ~79 (après ajout des metadata, avant le return)

**Action** :
```python
# AJOUTER : Calculer les coûts
from services.cost_tracking_service import cost_tracking_service

if "models_usage_raw" in result:
    cost_data = cost_tracking_service.calculate_extraction_cost(
        result["models_usage_raw"]
    )

    # Ajouter les coûts au résultat
    result["extraction_costs"] = {
        "cost_usd": cost_data["total_cost_usd"],
        "cost_eur": cost_data["total_cost_eur"],
        "total_tokens": cost_data["total_tokens"],
        "input_tokens": cost_data["total_input_tokens"],
        "output_tokens": cost_data["total_output_tokens"],
        "models_breakdown": cost_data["models_breakdown"],
        "search_type": "advanced" if deep_search else "simple"
    }
```

### Point 5 : Sauvegarder en DB dans status_manager

**Fichier** : `api/status.py` ou `api/services/agent_tracking_service.py`
**Fonction** : `store_extraction_results()` ou équivalent

**Action** : Enrichir l'enregistrement `CompanyExtraction` avec les données de coût

---

## 🚧 Problème Potentiel

**L'API OpenAI Agents ne retourne peut-être pas `result.usage`**

### Solution A : Vérifier si result.usage existe
```python
if hasattr(result, 'usage') and result.usage:
    # Capturer les tokens
else:
    logger.warning(f"⚠️ Pas de données d'usage pour {agent_name}")
```

### Solution B : Utiliser un callback sur les appels API
Si `Runner.run()` ne retourne pas l'usage, il faut instrumenter au niveau des appels directs à l'API OpenAI.

### Solution C : Estimation basée sur tiktoken
En dernier recours, estimer les tokens avec la bibliothèque `tiktoken`.

---

## 📝 Plan d'Implémentation

### Étape 1 : Test de capture des tokens

1. Modifier `run_agent_with_metrics()` pour logger `result.__dict__`
2. Lancer une extraction de test
3. Vérifier si `usage` est présent dans le résultat

### Étape 2A : Si usage est disponible

1. ✅ Modifier `run_agent_with_metrics()` pour capturer les tokens
2. ✅ Modifier `orchestrate_extraction()` pour agréger
3. ✅ Modifier `extraction_core.py` pour calculer et stocker
4. ✅ Modifier le stockage DB pour sauvegarder les coûts

### Étape 2B : Si usage n'est pas disponible

1. Instrumenter les appels directs à l'API OpenAI
2. Utiliser un callback/middleware pour capturer les tokens
3. Alternatives : tiktoken pour estimation

### Étape 3 : Liaison avec la DB

1. Identifier où `CompanyExtraction` est créé/updaté
2. Ajouter les champs de coût lors de la sauvegarde
3. Associer au `session_id`

### Étape 4 : Vérification Frontend

1. Tester l'endpoint `/costs/extraction/session/{session_id}`
2. Vérifier que le frontend affiche les données
3. Valider les montants

---

## 🔑 Fichiers Clés à Modifier

| Fichier | Action | Priorité |
|---------|--------|----------|
| `metrics/agent_wrappers.py` | Capturer tokens dans performance_metrics | 🔴 HAUTE |
| `orchestrator/extraction_orchestrator.py` | Agréger tokens de tous les agents | 🔴 HAUTE |
| `extraction_core.py` | Calculer coûts et ajouter au résultat | 🔴 HAUTE |
| `status.py` ou équivalent | Sauvegarder en DB | 🔴 HAUTE |
| `services/agent_tracking_service.py` | Enrichir le tracking | 🟡 MOYENNE |

---

## 🎯 Critères de Succès

- [ ] Les tokens sont capturés pour chaque agent
- [ ] Les coûts sont calculés correctement (USD + EUR)
- [ ] Les coûts sont sauvegardés dans `company_extractions`
- [ ] Le `session_id` est bien lié aux coûts
- [ ] Le frontend affiche les coûts de la session
- [ ] Le type de recherche (simple/advanced) est stocké

---

## 📊 Tests à Effectuer

### Test 1 : Recherche Simple
```bash
# Lancer une recherche simple
# Vérifier les logs pour voir les tokens capturés
# Vérifier la DB : cost_eur devrait être ~0.05-0.10€
```

### Test 2 : Recherche Avancée
```bash
# Lancer une recherche avec deep_search=true
# Vérifier que sonar-pro est utilisé
# Vérifier la DB : cost_eur devrait être ~0.20-0.50€
```

### Test 3 : Affichage Frontend
```bash
# Naviguer vers la page de résultats
# Vérifier que la ExtractionCostCard s'affiche
# Vérifier les montants EUR et USD
# Vérifier le détail par modèle
```

---

## 🚀 Prochaine Étape

**ÉTAPE 1** : Tester si `result.usage` est disponible

Ajouter un log temporaire dans `run_agent_with_metrics()` :
```python
# Ligne ~123 après result = await Runner.run(...)
logger.info(f"🔍 [DEBUG] result attributes: {dir(result)}")
logger.info(f"🔍 [DEBUG] result.__dict__: {result.__dict__}")
```

Lancer une extraction et analyser les logs.

---

**Document créé le** : 2025-10-25
**Status** : Prêt pour implémentation
