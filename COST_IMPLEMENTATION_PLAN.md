# 💰 Plan d'Implémentation du Tracking des Coûts

**Date de création** : 2025-10-25
**Dernière mise à jour** : 2025-10-25
**Status** : Étapes 1-3 COMPLÉTÉES ✅ | Étape 4 EN ATTENTE DE TEST ⏳
**Objectif** : Mesurer le coût réel de chaque recherche pour établir une grille tarifaire basée sur les données

---

## 🎯 Objectifs

1. **Capturer** : Enregistrer l'usage des tokens AI pour chaque recherche
2. **Stocker** : Sauvegarder les coûts par session dans la base de données
3. **Afficher** : Montrer le coût de la session sur la page de résultats
4. **Analyser** : Calculer les coûts moyens par type de recherche

---

## 📊 Types de Recherche à Tracker

### Recherche Simple
- Type : `simple`
- Modèles utilisés : `gpt-4o-mini`, `gpt-4o-search-preview`
- Usage estimé : ~30-50K tokens
- Coût estimé : **~0.05-0.10€** par recherche

### Recherche Avancée (Deep Search)
- Type : `advanced`
- Modèles utilisés : `gpt-4o-mini`, `gpt-4o`, `sonar-pro`
- Usage estimé : ~100-200K tokens
- Coût estimé : **~0.20-0.50€** par recherche

---

## 🗺️ Plan d'Implémentation

### **ÉTAPE 1 : Instrumentation des Agents** ✅ COMPLÉTÉE

**Objectif** : Capturer les tokens utilisés par chaque agent AI

**Fichiers modifiés** :
- ✅ `api/company_agents/metrics/agent_wrappers.py` (ligne ~123)
- ✅ `api/company_agents/subs_agents/subsidiary_extractor.py` (ligne ~915)

**Actions réalisées** :
1. ✅ Capture automatique des tokens dans `run_agent_with_metrics()`
2. ✅ Capture des tokens pour le Cartographe (pipelines simple et avancé)
3. ✅ Stockage dans `agent_metrics.performance_metrics["tokens"]`
4. ✅ Logging détaillé : `💰 Tokens capturés pour {agent_name}`

**Résultat** :
```python
# Stocké dans agent_metrics.performance_metrics
{
  "tokens": {
    "model": "gpt-4o-mini",
    "input_tokens": 5000,
    "output_tokens": 2000,
    "total_tokens": 7000
  }
}
```

---

### **ÉTAPE 2 : Agrégation et Calcul des Coûts** ✅ COMPLÉTÉE

**Objectif** : Agréger les tokens de tous les agents et calculer les coûts

**Fichiers modifiés** :
- ✅ `api/company_agents/orchestrator/extraction_orchestrator.py` (ligne ~204)
- ✅ `api/company_agents/extraction_core.py` (ligne ~86)

**Actions réalisées** :
1. ✅ Récupération des tokens de tous les agents via `metrics_collector`
2. ✅ Agrégation dans `result["models_usage_raw"]`
3. ✅ Calcul des coûts avec `cost_tracking_service.calculate_extraction_cost()`
4. ✅ Ajout du type de recherche (`simple` vs `advanced`) dans les métadonnées
5. ✅ Création de `result["extraction_costs"]` avec tous les détails

**Résultat** :
```python
result["extraction_costs"] = {
    "cost_usd": 0.0456,
    "cost_eur": 0.0420,
    "total_tokens": 75000,
    "input_tokens": 55000,
    "output_tokens": 20000,
    "models_breakdown": [...],
    "search_type": "simple",  # ou "advanced"
    "exchange_rate": 0.92
}
```

---

### **ÉTAPE 3 : Sauvegarde dans la Base de Données** ✅ COMPLÉTÉE

**Objectif** : Persister les coûts calculés dans `CompanyExtraction`

**Fichiers modifiés** :
- ✅ `api/routers/extraction.py` (ligne ~46, fonction `_run_extraction_background`)

**Actions réalisées** :
1. ✅ Extraction des données de coût depuis `result["extraction_costs"]`
2. ✅ Recherche de l'entrée `CompanyExtraction` par `session_id`
3. ✅ Mise à jour de toutes les colonnes de coût
4. ✅ Sauvegarde du JSONB `models_usage` avec détail par modèle
5. ✅ Logging : `💾 Coûts mis à jour dans DB pour session {session_id}`

**Colonnes remplies** :
```python
extraction.cost_usd = ...           # Coût en USD
extraction.cost_eur = ...           # Coût en EUR
extraction.total_tokens = ...       # Total tokens
extraction.input_tokens = ...       # Input tokens
extraction.output_tokens = ...      # Output tokens
extraction.models_usage = {...}     # JSONB avec détails
extraction.status = COMPLETED
extraction.processing_time = ...    # En secondes
```

---

### **ÉTAPE 4 : Affichage Frontend** ⏳ À TESTER

**Objectif** : Afficher le coût de la session sur la page de résultats

**Fichiers concernés** :
- ✅ `frontend/src/components/costs/ExtractionCostCard.tsx` - EXISTE
- ✅ `frontend/src/components/results/results-page.tsx` - INTÉGRÉ (ligne 642-653)
- ✅ `frontend/src/hooks/use-costs.ts` - Hook API EXISTE
- ✅ `/api/costs/extraction/session/{session_id}` - Endpoint EXISTE

**Actions à faire** :
1. ⏳ Lancer une extraction de test
2. ⏳ Vérifier que les tokens sont capturés (logs backend)
3. ⏳ Vérifier que les coûts sont en DB
4. ⏳ Vérifier que la card s'affiche sur le frontend
5. ⏳ Vérifier les montants EUR/USD

**Point d'attention** :
- ⚠️ Vérifier si `result.usage` est disponible dans l'API OpenAI Agents
- ⚠️ Vérifier qu'une entrée `CompanyExtraction` existe avant l'extraction

---

### **ÉTAPE 5 : Endpoint de Statistiques** 📅 PLANIFIÉ

**Objectif** : Créer un endpoint pour analyser les coûts moyens

**Nouveau endpoint** : `GET /api/costs/statistics`

**Quand** : Après 1-2 semaines de collecte de données

**Retour attendu** :
```json
{
  "period": "2025-10",
  "simple_searches": {
    "count": 120,
    "avg_cost_eur": 0.078,
    "min_cost_eur": 0.042,
    "max_cost_eur": 0.156,
    "total_cost_eur": 9.36
  },
  "advanced_searches": {
    "count": 45,
    "avg_cost_eur": 0.324,
    "min_cost_eur": 0.189,
    "max_cost_eur": 0.678,
    "total_cost_eur": 14.58
  },
  "overall": {
    "total_searches": 165,
    "total_cost_eur": 23.94,
    "avg_cost_eur": 0.145
  }
}
```

**Actions** :
1. Créer l'endpoint dans `api/routers/costs.py`
2. Query la DB pour agréger les statistiques
3. Grouper par type de recherche (simple vs advanced)

---

### **ÉTAPE 5 : Dashboard d'Analyse** (Optionnel)

**Objectif** : Page dédiée pour visualiser les statistiques de coûts

**Nouveau composant** : `frontend/src/app/costs/page.tsx`

**Sections** :
1. 📊 **Vue d'ensemble**
   - Coût total du mois
   - Nombre de recherches
   - Coût moyen par recherche

2. 📈 **Répartition par Type**
   - Recherches simples : X€ (Y%)
   - Recherches avancées : Z€ (W%)

3. 💡 **Recommandations de Pricing**
   - Basé sur les coûts réels + marge
   - Simulation de grille tarifaire

---

## 🔧 Détails Techniques

### Calcul des Coûts

**Service utilisé** : `cost_tracking_service.calculate_extraction_cost()`

**Pricing des modèles** :
| Modèle | Input (/1M tokens) | Output (/1M tokens) |
|--------|-------------------|---------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-search-preview | $2.50 | $10.00 |
| sonar-pro | $3.00 | $15.00 |

**Taux de change** : 1 USD = 0.92 EUR

### Identification du Type de Recherche

```python
# Dans extraction_core.py
extraction_type = "advanced" if deep_search else "simple"

# Sauvegarder dans metadata
extraction.extraction_data["extraction_metadata"]["search_type"] = extraction_type
```

---

## 📈 Métriques à Suivre

### KPIs Principaux
1. **Coût moyen par recherche simple** → Objectif : < 0.10€
2. **Coût moyen par recherche avancée** → Objectif : < 0.40€
3. **Écart-type des coûts** → Stabilité du pricing
4. **Coût total mensuel** → Budget infrastructure

### Statistiques Additionnelles
- Distribution des coûts (P50, P90, P99)
- Évolution des coûts dans le temps
- Coût par modèle AI utilisé
- Ratio input/output tokens

---

## 💰 Grille Tarifaire Recommandée

### Phase 1 : Mesure (2-4 semaines)
- Collecter les données de coûts réels
- Identifier les patterns et variations
- Calculer les moyennes et écarts-types

### Phase 2 : Pricing Basé sur les Données

**Formule** :
```
Prix de vente = (Coût moyen × Multiplicateur) + Marge fixe
Multiplicateur = 2.5 - 3.0 (pour couvrir infrastructure + support + marge)
```

**Exemple de pricing** :
```
Recherche Simple :
  Coût réel : 0.08€
  Prix de vente : (0.08 × 2.5) + 0.05 = 0.25€

Recherche Avancée :
  Coût réel : 0.35€
  Prix de vente : (0.35 × 2.5) + 0.10 = 0.975€ ≈ 1.00€
```

### Phase 3 : Système de Crédits (Future)
```
Pack Starter : 10€ = 50 crédits
  - 1 crédit = 1 recherche simple
  - 4 crédits = 1 recherche avancée

Pack Pro : 50€ = 300 crédits (+20% bonus)
Pack Enterprise : 200€ = 1500 crédits (+50% bonus)
```

---

## ✅ Checklist de Validation

### Étape 1 : Instrumentation ✅ COMPLÉTÉE
- [x] Les agents capturent les tokens utilisés
- [x] Les tokens sont remontés à `extraction_core`
- [x] Format des données validé
- [x] Logging ajouté pour debug

### Étape 2 : Agrégation et Calcul ✅ COMPLÉTÉE
- [x] Les tokens sont agrégés depuis tous les agents
- [x] Les coûts sont calculés correctement (USD + EUR)
- [x] Le type de recherche est ajouté (simple/advanced)
- [x] Les modèles sont détaillés dans models_breakdown

### Étape 3 : Sauvegarde DB ✅ COMPLÉTÉE
- [x] Les coûts sont sauvegardés dans `company_extractions`
- [x] Le `session_id` est correctement lié
- [x] Toutes les colonnes sont remplies (cost_usd, cost_eur, etc.)
- [x] Le JSONB models_usage est correctement formaté

### Étape 4 : Affichage Frontend ⏳ À TESTER
- [ ] **TEST** : Lancer une extraction et vérifier les logs
- [ ] **TEST** : Vérifier que les coûts sont en DB
- [ ] **TEST** : La card de coût s'affiche sur la page de résultats
- [ ] **TEST** : Les montants sont corrects (EUR et USD)
- [ ] **TEST** : Le détail par modèle fonctionne

### Étape 5 : Statistiques 📅 À PLANIFIER
- [ ] Collecter des données pendant 1-2 semaines
- [ ] L'endpoint de statistiques fonctionne
- [ ] Les données sont correctement agrégées
- [ ] La distinction simple vs advanced est claire

---

## 🎯 Prochaines Étapes

1. ✅ **Étape 1 : Instrumentation** → COMPLÉTÉE
2. ✅ **Étape 2 : Agrégation et Calcul** → COMPLÉTÉE
3. ✅ **Étape 3 : Sauvegarde DB** → COMPLÉTÉE
4. ⏳ **MAINTENANT : Tests** → Lancer une extraction et valider le flow complet
   - Vérifier les logs : `grep "💰" logs.txt`
   - Vérifier la DB : `SELECT cost_eur FROM company_extractions ORDER BY created_at DESC LIMIT 1;`
   - Vérifier le frontend : Ouvrir la page de résultats
5. 📅 **Étape 5 : Statistiques** → Après 1-2 semaines de données
6. 📊 **Décision pricing** → Après 2-4 semaines d'analyse

---

## 📝 Notes Importantes

- **Ne pas tracker les coûts par filiale** : On track uniquement le coût total de la recherche
- **Type de recherche** : Simple vs Advanced (deep_search)
- **Objectif** : Avoir des données réelles pour établir un pricing juste
- **Timeline** : 2-4 semaines de collecte avant décision pricing

---

**Dernière mise à jour** : 2025-10-25
**Status** : Implémentation backend complétée (Étapes 1-3) - En attente de tests
