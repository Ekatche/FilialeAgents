# 📋 Liste des Éléments Trackés par l'Endpoint `/hierarchical/extract`

## Vue d'ensemble

Ce document liste **UNIQUEMENT les éléments trackés** dans l'endpoint `/hierarchical/extract`. Utilisez cette liste pour vérifier sur la plateforme OpenAI si tous les éléments correspondent.

---

## 1. TOKENS TRACKÉS

### 1.1 Phase 0 : Éclaireur

**Agent**: `eclaireur`  
**Modèle**: `gpt-4o-search-preview`  
**Source**: `api/company_agents/hierarchical/agents/eclaireur.py` (lignes 355-422)

#### Tokens extraits depuis `response.usage`:
- ✅ **input_tokens** (ou `prompt_tokens` en fallback)
- ✅ **output_tokens** (ou `completion_tokens` en fallback)
- ✅ **total_tokens** (ou calculé: `input_tokens + output_tokens`)
- ⚠️ **reasoning_tokens** : Tentative d'extraction depuis :
  - `usage.completion_tokens_details.reasoning_tokens` (méthode principale)
  - `usage.reasoning_tokens` (fallback)
  - `usage.reasoning_token_count` (fallback)
  - `usage.reasoning_tokens_used` (fallback)
  - **Résultat actuel**: Toujours 0 (non détectés)
- ⚠️ **tool_tokens** : Tentative d'extraction depuis :
  - `usage.completion_tokens_details.tool_tokens` (méthode principale)
  - `usage.tool_tokens` (fallback)
  - `usage.tool_token_count` (fallback)
  - `usage.tool_tokens_used` (fallback)
  - **Résultat actuel**: Toujours 0 (non détectés)

#### Tokens envoyés au tracker:
- `input_tokens`: Valeur extraite
- `output_tokens`: Valeur extraite + reasoning_tokens + tool_tokens (si > 0)
- **Note**: Si reasoning_tokens ou tool_tokens sont détectés, ils sont ajoutés à `output_tokens` pour le calcul du coût

#### Coûts calculés:
```
Coût tokens = (input_tokens × $2.50/1M) + (effective_output_tokens × $10.00/1M)
```

#### Web Search Calls:
- ✅ **Comptage**: Extraction depuis `response.choices[0].message.tool_calls` (nombre réel)
- ✅ **Méthode**: Parcours des `tool_calls` pour compter ceux de type `web_search` ou avec `function.name` contenant `web_search`
- ✅ **Fallback**: Si pas de `tool_calls` explicites, le modèle peut avoir fait des recherches web intégrées (non comptables exactement)
- ✅ **Coût**: `nombre_appels × $0.01` (ajouté à phase_0.total_cost_usd)

---

### 1.2 Phase 1 : Cartographe Minimal

**Agent**: `cartographe_minimal`  
**Tool**: `minimal_subsidiary_search_gpt5`  
**Modèle**: `gpt-5.1` (ou `gpt-5`)  
**Source**: `api/company_agents/hierarchical/tools/minimal_subsidiary_search.py` (lignes 708-826)

#### Tokens extraits depuis `response.usage`:
- ✅ **input_tokens** (ou `prompt_tokens` en fallback)
- ✅ **output_tokens** (ou `completion_tokens` en fallback)
- ✅ **total_tokens** (depuis `usage.total_tokens` ou calculé)
- ⚠️ **reasoning_tokens** : Tentative d'extraction depuis :
  - `usage.completion_tokens_details.reasoning_tokens` (méthode principale)
  - `usage.reasoning_tokens` (fallback)
  - `usage.reasoning_token_count` (fallback)
  - `usage.reasoning_tokens_used` (fallback)
  - **Estimation**: Si `total_tokens > input_tokens + output_tokens`, la différence est estimée comme reasoning_tokens
  - **Résultat actuel**: Toujours 0 (non détectés dans les logs)
- ⚠️ **tool_tokens** : Tentative d'extraction depuis :
  - `usage.completion_tokens_details.tool_tokens` (méthode principale)
  - `usage.tool_tokens` (fallback)
  - `usage.tool_token_count` (fallback)
  - `usage.tool_tokens_used` (fallback)
  - **Résultat actuel**: Toujours 0 (non détectés)

#### Tokens envoyés au tracker:
- `input_tokens`: Valeur extraite
- `output_tokens`: Valeur extraite + reasoning_tokens + tool_tokens (si > 0)

#### Coûts calculés:
```
Coût tokens = (input_tokens × $2.50/1M) + (effective_output_tokens × $10.00/1M)
```

#### Web Search Calls:
- ✅ **Comptage**: Extraction depuis `response.output` (nombre réel)
- ✅ **Méthode**: Parcours des items dans `response.output` pour compter ceux de type `web_search` ou avec un nom de classe contenant `web_search`
- ✅ **Coût**: `nombre_appels × $0.01` (ajouté à phase_1.total_cost_usd)
- **Note**: Le comptage est maintenant basé sur le nombre réel d'appels web_search détectés dans la réponse

---

### 1.3 Phase 2 : Extracteur Détaillé

**Agent**: `extracteur_detaille`  
**Modèle**: `gpt-4o`  
**Source**: `api/company_agents/hierarchical/agents/extracteur_detaille.py`

#### Tokens trackés:

**A. Agent principal (extracteur_detaille)**:
- ✅ **input_tokens**: Depuis `result.context_wrapper.usage.input_tokens`
- ✅ **output_tokens**: Depuis `result.context_wrapper.usage.output_tokens`
- ⚠️ **reasoning_tokens**: Non trackés actuellement
- ⚠️ **tool_tokens**: Non trackés actuellement
- **Source**: Lignes 472-482

**B. Tool contact_finder**:
- ✅ **input_tokens**: Trackés individuellement pour chaque appel
- ✅ **output_tokens**: Trackés individuellement pour chaque appel
- **Modèle**: `gpt-4o-search-preview` (lignes 178, 203, 303, 328)
- **Source**: Lignes 200-210, 325-335
- **Nombre d'appels**: 1 par entité (15 entités = 15 appels pour ErgoPack)

#### Coûts calculés:
```
Coût agent principal = (input_tokens × $2.50/1M) + (output_tokens × $10.00/1M)
Coût contact_finder = (input_tokens × $2.50/1M) + (output_tokens × $10.00/1M) × nombre_appels
Coût Phase 2 = Coût agent principal + Coût contact_finder (tous appels)
```

#### Web Search Calls:
- ❌ **Agent principal**: `gpt-4o` n'a pas de web_search
- ✅ **contact_finder**: Utilise `gpt-4o-search-preview` et peut effectuer des web_search calls
  - **Comptage**: Extraction depuis `response.choices[0].message.tool_calls` (nombre réel)
  - **Coût**: `nombre_appels × $0.01` (ajouté à phase_2.total_cost_usd si > 0)

---

## 2. APPELS TRACKÉS

### 2.1 Web Search Calls

**Comptage** (lignes 430-451 de `hierarchical_cost_tracking.py`):
- ✅ **Méthode principale**: Utilise `tool_usage.get("web_search_calls", 0)` depuis le tracker (nombre réel tracké)
- ✅ **Fallback**: Si `web_search_calls` n'est pas disponible, détection basée sur le modèle (ancienne méthode)

**Comptage par phase**:
- Phase 0: Nombre réel depuis `tool_calls` de l'Éclaireur (généralement 0-3 appels)
- Phase 1: Nombre réel depuis `response.output` du Cartographe Minimal (généralement 10-20 appels)
- Phase 2: Nombre réel depuis `tool_calls` de contact_finder (généralement 0-1 appel par entité)

**Coût par appel**:
- Reasoning models (`gpt-5.1`, `gpt-4o-search-preview`): **$0.01** par appel

**Total web_search calls** (exemple ErgoPack - valeurs réelles trackées):
- Phase 0: Nombre réel depuis tool_calls (ex: 2 appels) × $0.01 = $0.02
- Phase 1: Nombre réel depuis response.output (ex: 15 appels) × $0.01 = $0.15
- Phase 2: Nombre réel depuis tool_calls contact_finder (ex: 0 appels) × $0.01 = $0.00
- **Total**: Somme des appels réels trackés

---

### 2.2 Contact Finder Calls

**Agent**: `contact_finder`  
**Modèle**: `gpt-4o-search-preview` (utilisé dans `extracteur_detaille.py`)  
**Nombre d'appels**: 1 par entité extraite

**Tokens trackés par appel**:
- ✅ `input_tokens`: ~260 tokens par appel
- ✅ `output_tokens`: ~48-64 tokens par appel

**Coût par appel**:
```
Coût = (260 × $2.50/1M) + (50 × $10.00/1M) ≈ $0.00065 + $0.0005 = $0.00115
```

**Total contact_finder** (15 entités):
```
15 × $0.00115 ≈ $0.01725
```

**Note**: `contact_finder` utilise `gpt-4o-search-preview` et les web_search calls sont maintenant trackés et comptés dans phase_2 si > 0.

---

## 3. MODÈLES UTILISÉS ET PRIX (Endpoint `/hierarchical/extract`)

### 3.1 Modèles avec Web Search (Reasoning)

#### gpt-4o-search-preview
- **Usage**: Phase 0 (Éclaireur) + Phase 2 (contact_finder)
- Input: **$2.50 / 1M tokens**
- Output: **$10.00 / 1M tokens**
- Reasoning: **$10.00 / 1M tokens** (si trackés)
- Tool: **$10.00 / 1M tokens** (si trackés)
- Web search calls: **$10.00 / 1K calls** = **$0.01 par appel**
- **Note**: Utilisé dans l'Éclaireur (Phase 0) et dans `contact_finder` (Phase 2), mais les appels web_search ne sont comptés que pour l'Éclaireur

#### gpt-5.1 / gpt-5_1 / gpt-5 (Phase 1)
- **Usage**: Phase 1 (Cartographe Minimal)
- Input: **$2.50 / 1M tokens**
- Output: **$10.00 / 1M tokens**
- Reasoning: **$10.00 / 1M tokens** (si trackés)
- Tool: **$10.00 / 1M tokens** (si trackés)
- Web search calls: **$10.00 / 1K calls** = **$0.01 par appel**
- **Note**: `gpt-5.1` et `gpt-5_1` sont des alias (point vs underscore)

### 3.2 Modèles Standard (Sans Web Search)

#### gpt-4o (Phase 2)
- **Usage**: Phase 2 (Extracteur Détaillé - agent principal)
- Input: **$2.50 / 1M tokens**
- Output: **$10.00 / 1M tokens**
- Reasoning: **$10.00 / 1M tokens** (si trackés, mais non documenté pour gpt-4o)
- Tool: **$10.00 / 1M tokens** (si trackés)
- Web search calls: **$0.00** (non disponible)

### 3.3 Tableau Récapitulatif des Modèles (Endpoint `/hierarchical/extract`)

| Modèle | Input ($/1M) | Output ($/1M) | Web Search Calls ($/1K) | Statut Tracking | Usage dans l'Endpoint |
|--------|--------------|---------------|--------------------------|-----------------|----------------------|
| `gpt-4o-search-preview` | $2.50 | $10.00 | $10.00 | ✅ Tracké | Phase 0 (Éclaireur) + Phase 2 (contact_finder) |
| `gpt-5.1` / `gpt-5_1` / `gpt-5` | $2.50 | $10.00 | $10.00 | ✅ Tracké | Phase 1 (Cartographe Minimal) |
| `gpt-4o` | $2.50 | $10.00 | $0.00 | ✅ Tracké | Phase 2 (Extracteur Détaillé - agent principal) |

**Légende**:
- ✅ **Tracké**: Modèle défini dans `hierarchical_cost_tracking.py` et tracké dans l'endpoint `/hierarchical/extract`

---

## 4. CALCUL DÉTAILLÉ POUR ERGOPACK (Exemple)

### 4.1 Phase 0 : Éclaireur

**Tokens trackés**:
- Input: 4,337 tokens
- Output: 120 tokens
- Reasoning: 0 tokens (non détectés)
- Tool: 0 tokens (non détectés)

**Coût tokens**:
```
(4,337 × $2.50/1M) + (120 × $10.00/1M) = $0.0108 + $0.0012 = $0.0120
```

**Web search calls**:
```
1 × $0.01 = $0.01
```

**Total Phase 0**:
```
$0.0120 + $0.01 = $0.0220
```

---

### 4.2 Phase 1 : Cartographe Minimal

**Tokens trackés**:
- Input: 21,304 tokens
- Output: 1,517 tokens
- Reasoning: 0 tokens (non détectés)
- Tool: 0 tokens (non détectés)

**Coût tokens**:
```
(21,304 × $2.50/1M) + (1,517 × $10.00/1M) = $0.0533 + $0.0152 = $0.0685
```

**Web search calls**:
```
16 × $0.01 = $0.16
```

**Total Phase 1**:
```
$0.0685 + $0.16 = $0.2285
```

---

### 4.3 Phase 2 : Extracteur Détaillé

**A. Agent principal (15 entités)**:
- Input total: ~28,950 tokens (15 × ~1,930 tokens/entité)
- Output total: ~1,395 tokens (15 × ~93 tokens/entité)

**Coût agent principal**:
```
(28,950 × $2.50/1M) + (1,395 × $10.00/1M) = $0.0724 + $0.0140 = $0.0864
```

**B. Tool contact_finder (15 appels)**:
- Input total: ~3,900 tokens (15 × ~260 tokens/appel)
- Output total: ~750 tokens (15 × ~50 tokens/appel)

**Coût contact_finder**:
```
(3,900 × $2.50/1M) + (750 × $10.00/1M) = $0.0098 + $0.0075 = $0.0173
```

**Total Phase 2**:
```
$0.0864 + $0.0173 = $0.1037
```

---

### 4.4 Total Calculé

```
Total = Phase 0 + Phase 1 + Phase 2
Total = $0.0220 + $0.2285 + $0.1037 = $0.3542
```

**Coût réel OpenAI**: **$0.57**

**Différence**: **$0.57 - $0.3542 = $0.2158** (non tracké)

---

## 5. ÉLÉMENTS NON TRACKÉS (HYPOTHÈSES)

### 5.1 Tokens Reasoning

**Phase 0 (Éclaireur)**:
- Output visible: 120 tokens
- Reasoning estimé (si 3-5x output): 360-600 tokens
- Coût manquant: (360-600) × $10/1M = **$0.0036 - $0.006**

**Phase 1 (Cartographe Minimal)**:
- Output visible: 1,517 tokens
- Reasoning estimé (si 3-5x output): 4,551-7,585 tokens
- Coût manquant: (4,551-7,585) × $10/1M = **$0.0455 - $0.0759**

**Phase 2 (Extracteur Détaillé)**:
- Output visible: ~1,395 tokens
- Reasoning estimé (si gpt-4o utilise reasoning): 0-1,000 tokens
- Coût manquant: (0-1,000) × $10/1M = **$0 - $0.01**

**Total reasoning estimé**: **$0.0491 - $0.0919**

---

### 5.2 Tokens Tool (pour web_search)

**Phase 1**:
- 16 appels web_search
- Tokens tool estimés par appel: 100-200 tokens
- Total estimé: 1,600-3,200 tokens
- Coût manquant: (1,600-3,200) × $10/1M = **$0.016 - $0.032**

---

### 5.3 Autres Coûts Possibles

- **Frais de service OpenAI**: Non documenté, possible mais peu probable
- **Tokens cachés dans les réponses intermédiaires**: Non trackés
- **Coûts de cache/retry**: Non trackés

---

## 6. STRUCTURE DE DONNÉES TRACKÉES

### 6.1 ToolTokensTracker

Chaque appel tracké contient:
```python
{
    "tool": "nom_du_tool",  # ex: "eclaireur", "minimal_subsidiary_search_gpt5", "contact_finder", "extracteur_detaille"
    "model": "nom_du_modele",  # ex: "gpt-4o-search-preview", "gpt-5.1", "gpt-4o"
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int  # input_tokens + output_tokens
}
```

### 6.2 HierarchicalExtractionCosts

Structure finale:
```python
{
    "session_id": str,
    "company_name": str,
    "total_cost_usd": float,  # Somme de toutes les phases
    "total_tokens": int,  # Somme de tous les tokens
    "phases": [
        {
            "phase_name": "phase_0|phase_1|phase_2",
            "total_cost_usd": float,  # Inclut tokens + web_search calls
            "agents": [
                {
                    "agent_name": str,
                    "model": str,
                    "total_cost_usd": float,
                    "entities": [
                        {
                            "entity_name": str,
                            "tool_calls": [
                                {
                                    "model": str,
                                    "input_tokens": int,
                                    "output_tokens": int,
                                    "cost_usd": float
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

---

## 7. POINTS À VÉRIFIER SUR OPENAI DASHBOARD

### 7.1 Pour chaque modèle utilisé dans `/hierarchical/extract`

1. **gpt-4o-search-preview** (Phase 0 - Éclaireur):
   - [ ] Input tokens exacts
   - [ ] Output tokens exacts
   - [ ] Reasoning tokens (si disponibles)
   - [ ] Tool tokens (si disponibles)
   - [ ] Nombre d'appels web_search
   - [ ] Coût total

2. **gpt-5.1 / gpt-5_1 / gpt-5** (Phase 1 - Cartographe Minimal):
   - [ ] Input tokens exacts
   - [ ] Output tokens exacts
   - [ ] Reasoning tokens (si disponibles)
   - [ ] Tool tokens (si disponibles)
   - [ ] Nombre d'appels web_search
   - [ ] Coût total

3. **gpt-4o** (Phase 2 - Extracteur Détaillé, agent principal):
   - [ ] Input tokens exacts
   - [ ] Output tokens exacts
   - [ ] Reasoning tokens (si disponibles)
   - [ ] Tool tokens (si disponibles)
   - [ ] Coût total

4. **gpt-4o-search-preview** (Phase 2 - contact_finder):
   - [ ] Input tokens exacts (pour chaque appel)
   - [ ] Output tokens exacts (pour chaque appel)
   - [ ] Nombre d'appels contact_finder
   - [ ] Coût total (tous appels contact_finder)
   - **Note**: Les appels contact_finder utilisent `gpt-4o-search-preview` mais ne sont pas comptés comme web_search calls

### 7.2 Coûts supplémentaires

- [ ] Frais de service (si applicable)
- [ ] Coûts de cache (si applicable)
- [ ] Coûts de retry (si applicable)

---

## 8. FICHIERS DE CODE CONCERNÉS

1. **Tracking des tokens**:
   - `api/company_agents/metrics/tool_tokens_tracker.py` : Stockage des tokens
   - `api/company_agents/hierarchical/agents/eclaireur.py` : Extraction Phase 0
   - `api/company_agents/hierarchical/tools/minimal_subsidiary_search.py` : Extraction Phase 1
   - `api/company_agents/hierarchical/agents/extracteur_detaille.py` : Extraction Phase 2

2. **Calcul des coûts**:
   - `api/services/hierarchical_cost_tracking.py` : Calcul et agrégation

3. **Prix des modèles**:
   - `api/services/hierarchical_cost_tracking.py` : Fonction `_get_model_pricing()` (lignes 225-285)
   - **Modèles utilisés dans `/hierarchical/extract`**: `gpt-4o-search-preview`, `gpt-5_1`, `gpt-5.1`, `gpt-5`, `gpt-4o`

---

## 9. RÉSUMÉ DES COÛTS CALCULÉS (ErgoPack)

| Phase | Agent | Tokens Input | Tokens Output | Reasoning | Tool | Web Search | Coût Total |
|-------|-------|--------------|---------------|-----------|------|------------|------------|
| Phase 0 | Éclaireur | 4,337 | 120 | 0 | 0 | 1 appel | $0.0220 |
| Phase 1 | Cartographe | 21,304 | 1,517 | 0 | 0 | 16 appels | $0.2285 |
| Phase 2 | Extracteur | 28,950 | 1,395 | 0 | 0 | 0 | $0.0864 |
| Phase 2 | contact_finder | 3,900 | 750 | 0 | 0 | 0 | $0.0173 |
| **TOTAL** | | **58,491** | **3,782** | **0** | **0** | **17 appels** | **$0.3542** |

**Coût réel OpenAI**: **$0.57**  
**Différence**: **$0.2158** (non tracké)

---

## 10. QUESTIONS POUR VÉRIFICATION OPENAI (Endpoint `/hierarchical/extract`)

1. Les tokens reasoning sont-ils visibles dans le dashboard OpenAI pour `gpt-5.1` et `gpt-4o-search-preview` ?
2. Les tokens tool sont-ils visibles pour les appels web_search ?
3. Le nombre d'appels web_search correspond-il à 17 appels (1 pour Éclaireur + 16 pour Cartographe) ?
4. Y a-t-il des coûts supplémentaires non listés ici ?
5. Les tokens input/output correspondent-ils exactement aux valeurs trackées ?
6. Les tokens de `contact_finder` (utilisant `gpt-4o-search-preview`) sont-ils correctement trackés et facturés ?
7. Le modèle `gpt-5.1` et `gpt-5_1` sont-ils facturés de la même manière (alias) ?

---

**Date de création**: 2025-12-01  
**Dernière mise à jour**: 2025-12-01

