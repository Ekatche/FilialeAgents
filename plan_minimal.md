# Plan minimal — Orchestration multi‑agents (état actuel)

## 1) Orchestration (extraction_manager.py)

- Séquence déterministe: Analyse → Info → Filiales → (Validation si nécessaire) → Restructuration.
- Résolution de la cible: si `company_analyzer.relationship == "subsidiary"` et `parent_company` renseigné → cible = parent, sinon = entité résolue ou input.
- Retries/timeouts par agent centralisés via `_run_agent_with_retry`.
- Parsing JSON robuste: déballage `content`, extraction bloc `{...}`/`[...]`, réparation des troncatures.
- Feature flag de filtres post‑extraction: `ENABLE_SUBS_FILTERS` (par défaut False pour évaluer le prompt seul).

## 2) Agents (rôle, outils, modèles, sortie)

- 🔍 Éclaireur (`company_analyzer`)

  - Rôle: statut corporate (parent/subsidiary/independent), parent éventuel.
  - Outils: WebSearchTool — 2+ requêtes obligatoires.
  - Modèle: gpt-4.1-mini.
  - Sortie: `CompanyLinkage` (schéma strict).

- ⛏️ Mineur (`information_extractor`)

  - Rôle: fiche entreprise (siège, secteur, activités, sources ≥2 dont ≥1 rang 1/2).
  - Outils: WebSearchTool.
  - Modèle: gpt-4.1-mini.
  - Sortie: `CompanyCard` (schéma strict).

- 🗺️ Cartographe (`subsidiary_extractor`)

  - Rôle: TOP 10 filiales (sources officielles), coordonnées, sites; si 0 filiale → fallback “présences géographiques” (`branch`/`division`).
  - Outils: aucun (recherche intégrée Sonar Perplexity via API compatible OpenAI).
  - Modèle: sonar-pro (temperature=0.0, max_tokens=3200).
  - Sortie: `SubsidiaryReport` (schéma strict).

- ⚖️ Superviseur (`meta_validator`)

  - Rôle: cohérence globale, conflicts, scores (géographie/structure/sources/overall), recommandations, warnings.
  - Outils: aucun.
  - Modèle: gpt-4o-mini.
  - Sortie: `MetaValidationReport` (schéma strict).

- 🔄 Restructurateur (`data_restructurer`)
  - Rôle: normaliser en `CompanyInfo`, respecter limites (sources, GPS, champs interdits).
  - Outils: aucun.
  - Modèle: gpt-4.1-mini.
  - Sortie: `CompanyInfo` (schéma strict).

## 3) Garde‑fous de prompt (format & fiabilité)

- Réponses JSON strictes: un seul objet, une seule ligne, pas de markdown ni wrapper (`{"content": ...}`).
- FINALIZER: auto‑contrôle avant envoi (pas de virgules finales, échappement OK, clés du schéma uniquement).
- `subsidiary_extractor`: fallback “présences géographiques” si 0 filiale avec source officielle.
- Règle de fraîcheur (prompt): prioriser <24 mois; `published_date` si disponible, sinon pages officielles (About/Contact/IR) du domaine légitime + mention de vérification dans `methodology_notes`.

## 4) Filtres post‑extraction (orchestrateur)

- Accessibilité d’URLs: HEAD/GET avec tolérance 403 sur domaines légitimes; suppression des sources cassées.
- Fraîcheur (optionnelle): `_filter_fresh_sources(..., max_age_months=24)` retire les filiales n’ayant aucune source officielle ≤24 mois; sans dates, conserve si au moins une URL officielle https valide.
- Activation: via `ENABLE_SUBS_FILTERS=True`.

## 5) Tracking temps réel & warnings

- `agent_tracking_service`: étapes, durées, progression; warnings surfacés au frontend.
- Journalisation: temps d’exécution, tailles JSON, URLs exclues.

## 6) Exécution & dépendances

- Backend: FastAPI (`api/`), démarrage via `make start` (uv). Frontend: `make start-frontend`.
- Dépendances: `pyproject.toml` + `uv.lock` (pas de `requirements.txt`).

## 7) Tests & validations

- Healthcheck: `make test` (vérifie `/health`).
- Validation manuelle: POST `/extract` et `/extract-from-url` (Swagger `/docs`).

## 8) Documentation

- README racine mis à jour (structure, endpoints, notes flag).
- Ce plan reflète l’état actuel et remplace l’ancien plan “refactorisation”.
