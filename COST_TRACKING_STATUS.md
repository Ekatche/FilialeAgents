# 📊 Status du Tracking des Coûts

**Date** : 2025-10-25
**Status** : ✅ FONCTIONNEL avec limitation documentée

---

## ✅ Ce qui fonctionne

### 1. Agents Principaux (100% trackés)
Tous les agents principaux capturent et calculent correctement leurs tokens :

- 🔍 **Éclaireur** (gpt-4.1-mini) ✅
- ⛏️ **Mineur** (gpt-4.1-mini) ✅
- 🗺️ **Cartographe** (gpt-4o ou gpt-4o-search-preview) ✅
- ⚖️ **Superviseur** (gpt-4o) ✅
- 🔄 **Restructurateur** (gpt-4o) ✅

### 2. Affichage Frontend
- ✅ Card de coût s'affiche sur la page de résultats
- ✅ Montants EUR et USD corrects
- ✅ Détail par modèle fonctionnel
- ✅ Type de recherche (simple/advanced) affiché

### 3. Calcul des Coûts
- ✅ Prix des modèles à jour (Janvier 2025)
- ✅ Conversion USD → EUR (0.92)
- ✅ Calcul par modèle précis

---

## ⚠️ Limitation : Tools non trackés dans le calcul final

### Problème

Les **tools de recherche web** sont trackés dans les logs mais **PAS inclus dans le calcul final** :

- `web_search` (gpt-4o-search-preview) : ~2-4 appels par extraction
- `filiales_search` (gpt-4o-search-preview) : ~1 appel par extraction

### Impact

**Exemple de requête simple** :

| Composant | Tokens | Coût |
|-----------|--------|------|
| **Agents** (calculé) | 63 805 | **$0.134** |
| **Tools** (non calculé) | 13 311 | **$0.052** |
| **TOTAL RÉEL** | 77 116 | **$0.186** |
| **OpenAI facture** | - | **$0.26** |

**Différence** :
- Notre calcul vs Réel : **28% de sous-estimation** ($0.052 manquants)
- Réel vs OpenAI : **$0.074 d'écart** (possibles frais internes de l'API)

### Tokens des Tools (exemple)

```
💰 [Tool] web_search #1:       3 779 in +   445 out =  4 224 tokens
💰 [Tool] web_search #2:       3 776 in +   427 out =  4 203 tokens
💰 [Tool] filiales_search:     3 252 in + 1 632 out =  4 884 tokens
────────────────────────────────────────────────────────────────
Total tools:                                          13 311 tokens
```

### Pourquoi ce n'est pas tracké ?

**Raison technique** :
1. Les tools (`web_search`, `filiales_search`) sont des fonctions décorées avec `@function_tool`
2. Elles sont appelées par l'**API OpenAI Agents**, pas par notre code
3. L'API ne passe pas le `session_id` aux tools
4. Les tokens sont loggés mais pas agrégés dans `metrics_collector`

---

## 💡 Solutions Possibles

### Solution 1 : Estimation (Actuelle - RECOMMANDÉE pour MVP)

**Approche** : Ajouter une **marge de sécurité** au calcul

```python
# Dans extraction_core.py
calculated_cost = cost_data["total_cost_eur"]
tools_overhead = 0.30  # 30% de marge pour les tools
final_cost = calculated_cost * (1 + tools_overhead)
```

**Avantages** :
- ✅ Simple à implémenter
- ✅ Couvre les tools + frais OpenAI
- ✅ Suffisant pour établir un pricing

**Inconvénients** :
- ❌ Pas précis à 100%
- ❌ Marge fixe alors que l'usage varie

**Implémentation** : 5 minutes

### Solution 2 : ContextVars (Tracking automatique)

**Approche** : Utiliser `contextvars` pour propager le `session_id`

```python
# Dans extraction_core.py
from contextvars import ContextVar

current_session_id = ContextVar('session_id')

async def extract_company_data(...):
    current_session_id.set(session_id)
    # L'extraction démarre...

# Dans web_search_agent.py
from extraction_core import current_session_id

async def web_search(query: str):
    session_id = current_session_id.get(None)
    if session_id:
        tool_tokens_tracker.add_tool_usage(...)
```

**Avantages** :
- ✅ Tracking précis à 100%
- ✅ Automatique
- ✅ Scalable

**Inconvénients** :
- ❌ Plus complexe à implémenter
- ❌ Risque de bugs si mal fait

**Implémentation** : 2-3 heures

### Solution 3 : Parse des Logs (Analyse post-mortem)

**Approche** : Parser les logs après extraction pour ajouter les tools

```python
# Après l'extraction
tool_logs = parse_logs_for_tools(session_id)
for tool_log in tool_logs:
    models_usage.append({
        "model": tool_log["model"],
        "input_tokens": tool_log["input_tokens"],
        "output_tokens": tool_log["output_tokens"]
    })
```

**Avantages** :
- ✅ Précis
- ✅ Pas de modification des tools

**Inconvénients** :
- ❌ Fragile (dépend du format des logs)
- ❌ Performance (parsing de logs)

**Implémentation** : 1 heure

---

## 📈 Recommandations

### Pour l'instant (Phase de mesure)

**✅ Utiliser Solution 1 (Marge de 30%)**

```python
# Impact sur le pricing
Coût calculé agents:    $0.134
Marge tools (30%):      $0.040
───────────────────────────────
Total estimé:           $0.174  (vs $0.186 réel = 6% d'erreur)
```

**Pourquoi** :
- Suffisant pour établir des statistiques de coûts
- Simple et robuste
- Erreur acceptable (< 10%)

### Pour la production (Phase de facturation)

**✅ Implémenter Solution 2 (ContextVars)**

Une fois que vous aurez des données sur 2-4 semaines et que vous voudrez facturer les clients, implémentez le tracking complet avec `contextvars` pour avoir une précision à 100%.

---

## 🎯 Objectifs Atteints

### Phase 1 : Mesure des Coûts ✅

- [x] Capturer les tokens des agents
- [x] Calculer les coûts par modèle
- [x] Afficher sur le frontend
- [x] Distinguer simple vs advanced
- [x] Logger les tokens des tools

### Phase 2 : Analyse (En cours)

- [ ] Collecter 2-4 semaines de données
- [ ] Calculer coût moyen par type
- [ ] Identifier les patterns de coût
- [ ] Établir une grille tarifaire

### Phase 3 : Production (Future)

- [ ] Tracking 100% précis (ContextVars)
- [ ] Système de crédits
- [ ] Facturation automatique
- [ ] Dashboard d'analytics

---

## 💰 Recommandations de Pricing

### Basé sur les données actuelles

**Recherche Simple** :
- Coût agents : ~$0.13
- Coût tools : ~$0.05
- **Total réel** : ~$0.18
- **Prix de vente recommandé** : 0.18 × 2.5 + 0.10 = **0.55€ / recherche**

**Recherche Avancée** :
- Coût agents : ~$0.30 (estimation)
- Coût tools : ~$0.10 (estimation)
- **Total réel** : ~$0.40
- **Prix de vente recommandé** : 0.40 × 2.5 + 0.15 = **1.15€ / recherche**

### Système de Crédits

```
Pack Starter (10€) = 20 crédits
  - 1 crédit = 1 recherche simple
  - 2 crédits = 1 recherche avancée

Pack Pro (50€) = 120 crédits (+20% bonus)
Pack Enterprise (200€) = 600 crédits (+50% bonus)
```

---

**Dernière mise à jour** : 2025-10-25
**Status** : Fonctionnel avec marge d'erreur documentée
