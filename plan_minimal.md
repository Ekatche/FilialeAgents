# Plan de refactorisation multi-agents

## 1. Cartographie & instrumentation

- Tracer les entrées/sorties de chaque fonction orchestratrice (`run_analyze_and_info`, `run_extract_subsidiaries_details`, etc.).
- Ajouter des logs DEBUG avant/après chaque appel d’agent pour suivre statut, temps, taille JSON.

## 2. Réarchitecture de l’orchestrateur

- Réintroduire un plan minimal : Analyse → Info de base → Filiales → Validation.
- Remplacer l’interdiction des appels multiples par un contrôle programmatique.
- Déplacer la logique de sélection de cible côté orchestrateur (plus de `choose_target_entity` exposé).
- Supporter une boucle limitée (max 4 tours) avec état partagé.

## 3. Critères d’activation des agents

- `company_analyzer` toujours appelé en premier ; relance/fallback si `relationship="unknown"` ou sources vides.
- `information_extractor` déclenché si adresse/secteur manquants ou signaux de qualité insuffisants.
- `subsidiary_extractor` appelé pour la société cible, avec relance ciblée si <3 filiales trouvées.
- `meta_validator` activé en cas d’incohérences (parent divergent, sources absentes, filiales non sourcées).

## 4. Ajustement des prompts

- `company_analyzer` : conserver la structure actuelle, ajouter fallback orienté registres locaux.
- `information_extractor` : simplifier, limiter le JSON, retirer les filiales.
- `subsidiary_extractor` : cibler TOP 10 filiales, réduire complexité JSON.
- `meta_validator` : prompt concis pour vérification croisée et recommandations.

## 5. Gestion outils & modèles

- Maintenir un mapping clair Agent ↔ Outils.
- Définir le modèle par agent (fallback gpt-5-mini optionnel).
- Limiter les requêtes Web par agent ; journaliser les dépassements.

## 6. Tracking temps réel

- Étendre `agent_tracking_service` à 4 étapes (Analyse, Info, Filiales, Validation).
- Remonter les warnings (parent absent, sources 404) au frontend.
- Journaliser temps d’exécution et nombre de requêtes Web par agent.

## 7. API & infrastructure

- FastAPI : middleware pour formater les erreurs agents.
- Redis : stocker statut/logs par session pour reprise.
- Timeout spécifique par agent configurable via env.

## 8. Validation & tests

- Scénarios : société mère (Apple), filiale (Axxair), PME indépendante, cas ambigu.
- Vérifier : sources valides, nombre de filiales, cohérence parent/enfant, JSON final.

## 9. Documentation

- Mettre à jour README et docs internes.
- Lister variables/env nécessaires.
- Rédiger guide d’exploitation (relance, interprétation warnings).

## 10. Déploiement progressif

1. Implémentation en local.
2. Tests unitaires/intégration.
3. Mise à jour du frontend.
4. Déploiement staging + logs détaillés.
5. Validation finale avant prod.
