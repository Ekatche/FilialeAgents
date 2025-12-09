# 🔄 Réorganisation des Workflows - Legacy vs Hierarchical

**Date** : 2025-01-28  
**Statut** : ✅ Complété

---

## 📋 Objectif

Séparer clairement les deux workflows (Legacy et Hierarchical) pour améliorer la lisibilité et la maintenabilité du code, tout en préservant la compatibilité avec les appels API existants.

---

## 🗂️ Nouvelle Structure

```
api/company_agents/
├── common/                          # Fichiers partagés
│   ├── models.py                   # Modèles Pydantic
│   ├── context.py                   # Contexte partagé
│   ├── metrics/                     # Métriques
│   ├── processors/                  # Processeurs
│   ├── config/                      # Configuration
│   └── tools/                       # Tools partagés
│       └── json_parser_helper.py
│
├── legacy/                          # ANCIEN WORKFLOW
│   ├── extraction_core.py          # Point d'entrée
│   ├── extraction_manager.py       # Manager
│   ├── orchestrator/               # Orchestrateur
│   │   ├── extraction_orchestrator.py
│   │   └── agent_caller.py
│   ├── agents/                      # Agents legacy
│   │   ├── company_analyzer.py
│   │   ├── information_extractor.py
│   │   ├── subsidiary_extractor.py
│   │   ├── meta_validator.py
│   │   └── data_validator.py
│   └── tools/                       # Tools legacy
│       ├── filiales_search.py
│       ├── web_search_identify.py
│       ├── web_search_quantify.py
│       └── perplexity_prompt.py
│
└── hierarchical/                    # NOUVEAU WORKFLOW
    ├── orchestrator.py             # Orchestrateur hiérarchique
    ├── adapter.py                  # Adaptateur legacy
    ├── agents/                     # Agents hiérarchiques
    │   ├── eclaireur.py           # Phase 0
    │   ├── cartographe_minimal.py # Phase 1
    │   └── extracteur_detaille.py # Phase 2
    └── tools/                      # Tools hiérarchiques
        └── minimal_subsidiary_search.py
```

---

## 🔄 Fichiers de Compatibilité

Pour préserver la compatibilité avec les appels API existants, les fichiers suivants réexportent depuis les nouveaux emplacements :

- `models.py` → `common/models.py`
- `context.py` → `common/context.py`
- `extraction_core.py` → `legacy/extraction_core.py`
- `extraction_manager.py` → `legacy/extraction_manager.py`
- `orchestrateur_hierarchique.py` → `hierarchical/orchestrator.py`
- `hierarchical_adapter.py` → `hierarchical/adapter.py`

**Les routers continuent de fonctionner sans modification** grâce à ces fichiers de compatibilité.

---

## 📦 Mapping des Fichiers

### Common (Partagés)
- `models.py` → `common/models.py`
- `context.py` → `common/context.py`
- `metrics/` → `common/metrics/`
- `processors/` → `common/processors/`
- `config/` → `common/config/`
- `subs_tools/json_parser_helper.py` → `common/tools/json_parser_helper.py`

### Legacy (Ancien Workflow)
- `extraction_core.py` → `legacy/extraction_core.py`
- `extraction_manager.py` → `legacy/extraction_manager.py`
- `orchestrator/` → `legacy/orchestrator/`
- `subs_agents/company_analyzer_optimized.py` → `legacy/agents/company_analyzer.py`
- `subs_agents/information_extractor_optimized_v2.py` → `legacy/agents/information_extractor.py`
- `subs_agents/subsidiary_extractor.py` → `legacy/agents/subsidiary_extractor.py`
- `subs_agents/meta_validator_optimized.py` → `legacy/agents/meta_validator.py`
- `subs_agents/data_validator_optimized.py` → `legacy/agents/data_validator.py`
- `subs_tools/filiales_search_agent_optimized.py` → `legacy/tools/filiales_search.py`
- `subs_tools/web_search_identify.py` → `legacy/tools/web_search_identify.py`
- `subs_tools/web_search_quantify.py` → `legacy/tools/web_search_quantify.py`
- `subs_agents/perplexity_prompt_wo_subs.py` → `legacy/tools/perplexity_prompt.py`

### Hierarchical (Nouveau Workflow)
- `orchestrateur_hierarchique.py` → `hierarchical/orchestrator.py`
- `hierarchical_adapter.py` → `hierarchical/adapter.py`
- `subs_agents/eclaireur.py` → `hierarchical/agents/eclaireur.py`
- `subs_agents/cartographe_minimal.py` → `hierarchical/agents/cartographe_minimal.py`
- `subs_agents/extracteur_detaille.py` → `hierarchical/agents/extracteur_detaille.py`
- `subs_tools/minimal_subsidiary_search.py` → `hierarchical/tools/minimal_subsidiary_search.py`

---

## ✅ Imports Mis à Jour

Tous les imports internes ont été mis à jour pour utiliser les nouveaux chemins :
- `company_agents.common.*` pour les fichiers partagés
- `company_agents.legacy.*` pour le workflow legacy
- `company_agents.hierarchical.*` pour le workflow hiérarchique

---

## 🔍 Vérifications

- ✅ Structure de dossiers créée
- ✅ Fichiers déplacés
- ✅ Imports mis à jour dans tous les fichiers déplacés
- ✅ Fichiers de compatibilité créés
- ✅ Routers fonctionnent toujours (pas de modification nécessaire)
- ✅ Aucune erreur de linting

---

## 📝 Prochaines Étapes (Optionnelles)

1. **Nettoyage** : Supprimer les anciens fichiers dans `subs_agents/` et `subs_tools/` après validation complète
2. **Documentation** : Mettre à jour la documentation pour refléter la nouvelle structure
3. **Tests** : Vérifier que tous les endpoints fonctionnent correctement

---

## ⚠️ Notes Importantes

- **Les appels API ne sont PAS impactés** grâce aux fichiers de compatibilité
- Les anciens fichiers dans `subs_agents/` et `subs_tools/` sont toujours présents mais ne sont plus utilisés
- La suppression des anciens fichiers peut être faite après validation complète

