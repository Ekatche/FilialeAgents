# Plan de Migration: Architecture Multi-Agents Hiérarchique

**Date**: 2025-01-27
**Version**: 1.0
**Statut**: Proposition

---

## 📋 Table des Matières

1. [Contexte et Objectifs](#contexte-et-objectifs)
2. [Analyse de l'Architecture Actuelle](#analyse-de-larchitecture-actuelle)
3. [Architecture Cible](#architecture-cible)
4. [Sélection des Modèles OpenAI](#sélection-des-modèles-openai)
5. [Plan de Migration Détaillé](#plan-de-migration-détaillé)
6. [Gains Attendus](#gains-attendus)
7. [Points d'Attention](#points-dattention)
8. [Timeline et Ressources](#timeline-et-ressources)

---

## 🎯 Contexte et Objectifs

### Problématique Actuelle

Le système d'extraction actuel présente les limitations suivantes:

1. **Recherches redondantes**: Certaines informations sont recherchées plusieurs fois par différents agents
2. **Cartographe monolithique**: Le Cartographe actuel effectue trop d'opérations en un seul appel (identification + extraction détaillée + contacts + GPS)
3. **Pas de parallélisation**: L'extraction de N filiales se fait séquentiellement, augmentant le temps d'exécution
4. **Coût élevé**: Le Cartographe effectue des recherches larges alors qu'une approche modulaire serait plus économique

### Objectifs de la Migration

1. **Éliminer les recherches redondantes** via un système de cache Redis
2. **Découper le Cartographe** en deux agents spécialisés:
   - **Cartographe Minimal**: Identification des entités uniquement
   - **Extracteur Détaillé**: Extraction détaillée par entité (parallélisable)
3. **Paralléliser les extractions** pour améliorer les performances
4. **Optimiser les coûts** via des agents spécialisés et un cache intelligent
5. **Améliorer la modularité** pour faciliter l'ajout de nouveaux agents

---

## 🔍 Analyse de l'Architecture Actuelle

### Pipeline Séquentiel (5 étapes)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 🔍 Éclaireur (Company Analyzer)                          │
│    Model: gpt-4o-mini                                       │
│    Tool: web_search_identify                                │
│    Output: CompanyLinkage                                   │
│    Coût moyen: ~0.01€                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ⛏️ Mineur (Information Extractor)                        │
│    Model: gpt-4o-mini                                       │
│    Tool: web_search_quantify                                │
│    Output: CompanyCard                                      │
│    Coût moyen: ~0.02€                                       │
│    ✅ DÉJÀ OPTIMISÉ: Réutilise données Éclaireur           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 🗺️ Cartographe (Subsidiary Extractor)                   │
│    Model: gpt-4o (simple) / sonar-pro (advanced)           │
│    Tools: subsidiary_search / research_subsidiaries         │
│    Output: SubsidiaryReport                                 │
│    Coût moyen: ~0.05-0.20€                                  │
│    ❌ PROBLÈME: Fait TROP de choses en un seul appel:      │
│       • Identification entités                              │
│       • Extraction adresses                                 │
│       • Extraction contacts (phone/email)                   │
│       • Géocodage GPS                                       │
│       • Validation sources                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ⚖️ Superviseur (Meta Validator)                          │
│    Model: gpt-4o-mini                                       │
│    Output: MetaValidationReport                             │
│    Coût moyen: ~0.01€                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 🔄 Restructurateur (Data Restructurer)                   │
│    Model: gpt-4o-mini                                       │
│    Output: CompanyInfo                                      │
│    Coût moyen: ~0.01€                                       │
└─────────────────────────────────────────────────────────────┘
```

### Points Forts Actuels

✅ **Éclaireur → Mineur**: Aucune recherche redondante (Mineur réutilise les données)
✅ **Guardrails actifs**: Validation URL avec retry automatique
✅ **Tracking temps réel**: WebSocket avec heartbeat
✅ **Two-mode support**: Simple (GPT-4o-search) vs Advanced (Perplexity)

### Points Faibles Identifiés

❌ **Cartographe monolithique**: Impossible d'enrichir une seule filiale sans tout re-chercher
❌ **Extraction séquentielle**: 10 filiales = 3-5 minutes d'attente
❌ **Coût élevé**: Recherches larges alors qu'une approche focalisée serait plus économique
❌ **Pas de cache**: Si on extrait deux fois la même entreprise, on refait toutes les recherches

---

## 🏗️ Architecture Cible

### Nouveau Pipeline (7 étapes avec parallélisation)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 🔍 Éclaireur (inchangé)                                  │
│    Model: gpt-4o-mini                                       │
│    Coût: ~0.01€                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ⛏️ Mineur (inchangé)                                     │
│    Model: gpt-4o-mini                                       │
│    Coût: ~0.02€                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 🗺️ Cartographe Minimal (NOUVEAU)                        │
│    Model: gpt-4o-mini (optimisé pour tâches structurées)   │
│    Tool: identify_related_entities                          │
│    Mission: Identifier UNIQUEMENT les entités liées        │
│             (filiales, participations, holdings, etc.)      │
│    Output: MinimalMappingReport                             │
│             - List[EntityRef] (nom + type + confidence)     │
│             - sources                                       │
│    Coût: ~0.01-0.03€ (réduit de 80% vs ancien)             │
│    ⚡ Avantage: Recherche focalisée, pas d'extraction      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 🔄 Orchestrateur d'Extraction Détaillée (NOUVEAU)       │
│    Type: Pure orchestration Python (pas de LLM call)       │
│    Mission: Lancer N agents en parallèle (1 par entité)    │
│    Config: max_concurrent = 5 (éviter rate limits)         │
│    Gestion:                                                 │
│      • Cache Redis check avant extraction                  │
│      • Semaphore pour limiter concurrence                  │
│      • Error handling par entité (pas de blocage global)   │
│      • WebSocket updates granulaires                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
          ┌───────────────┴───────────────┐
          ↓                               ↓
┌─────────────────────┐     ┌─────────────────────┐
│ 📄 Extracteur #1    │ ... │ 📄 Extracteur #N    │
│ (par entité)        │     │ (par entité)        │
│                     │     │                     │
│ Model: gpt-4o-mini  │     │ Model: gpt-4o-mini  │
│                     │     │                     │
│ Tools (séquence):   │     │ Tools (séquence):   │
│ 1. extract_basic    │     │ 1. extract_basic    │
│    → adresse        │     │    → adresse        │
│    → juridiction    │     │    → juridiction    │
│    → statut légal   │     │    → statut légal   │
│    → date création  │     │    → date création  │
│                     │     │                     │
│ 2. extract_activity │     │ 2. extract_activity │
│    → secteur NAICS  │     │    → secteur NAICS  │
│    → effectif       │     │    → effectif       │
│    → CA public      │     │    → CA public      │
│                     │     │                     │
│ 3. extract_ownership│     │ 3. extract_ownership│
│    → % participation│     │    → % participation│
│    → date acquisition│    │    → date acquisition│
│                     │     │                     │
│ 4. extract_contact  │     │ 4. extract_contact  │
│    → phone          │     │    → phone          │
│    → email          │     │    → email          │
│    → website        │     │    → website        │
│                     │     │                     │
│ 5. geocode_address  │     │ 5. geocode_address  │
│    → latitude       │     │    → latitude       │
│    → longitude      │     │    → longitude      │
│                     │     │                     │
│ Output:             │     │ Output:             │
│ DetailedEntityInfo  │     │ DetailedEntityInfo  │
│                     │     │                     │
│ Coût: ~0.01€/entité │     │ Coût: ~0.01€/entité │
│                     │     │                     │
│ ⚡ Cache Redis:     │     │ ⚡ Cache Redis:     │
│ Si déjà en cache →  │     │ Si déjà en cache →  │
│ retour immédiat     │     │ retour immédiat     │
│ (coût = 0€)         │     │ (coût = 0€)         │
└─────────────────────┘     └─────────────────────┘
          ↓                               ↓
          └───────────────┬───────────────┘
                          ↓
          Consolidation: List[DetailedEntityInfo]
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. ⚖️ Superviseur (adapté)                                  │
│    Model: gpt-4o-mini                                       │
│    Input: MinimalMappingReport + List[DetailedEntityInfo]  │
│    Coût: ~0.01€                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. 🔄 Restructurateur (adapté)                              │
│    Model: gpt-4o-mini                                       │
│    Mission: Transformer DetailedEntityInfo → CompanyInfo   │
│    Coût: ~0.01€                                             │
└─────────────────────────────────────────────────────────────┘
```

### Flux de Données

```python
# Étape 3: Cartographe Minimal
MinimalMappingReport {
  entities_identified: [
    EntityRef {
      legal_name: "ACOEM France SAS",
      entity_type: "subsidiary",
      confidence: 0.95,
      country: "France"
    },
    EntityRef {
      legal_name: "ACOEM Germany GmbH",
      entity_type: "subsidiary",
      confidence: 0.92,
      country: "Germany"
    },
    # ... N entités
  ],
  total_found: N,
  sources: [...]
}

# Étape 4: Extraction Parallèle (N agents en //)
[
  DetailedEntityInfo {  # Entité 1
    legal_name: "ACOEM France SAS",
    headquarters: LocationInfo {...},
    legal_status: "Active",
    registration_date: "2005-03-15",
    jurisdiction: "France - RCS Lyon",
    sector: "Environmental Monitoring",
    naics_code: "334512",
    employees: "120",
    ownership_details: {"percentage": 100, "acquired_date": "2005"},
    phone: "+33 4 28 29 81 10",
    email: "contact@acoem.fr",
    sources: [...]
  },
  DetailedEntityInfo {  # Entité 2
    ...
  }
]
```

---

## 🎯 Sélection des Modèles OpenAI

### Recommandations OpenAI 2025

Selon la [documentation officielle OpenAI](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/), les modèles sont optimisés pour différents cas d'usage:

| Modèle | Usage Recommandé | Prix (Input/Output per 1M tokens) | Performance |
|--------|------------------|-----------------------------------|-------------|
| **gpt-4o** | Tâches complexes nécessitant raisonnement profond, multilingue, génération de texte haute qualité | $2.50 / $10.00 | Meilleur raisonnement |
| **gpt-4o-mini** | Tâches structurées, extraction, classification, parallélisation massive, applications cost-sensitive | $0.15 / $0.60 | 82% MMLU, 60% moins cher que GPT-3.5 Turbo |
| **gpt-4.1** | Tâches de code avancées, instruction following | (Pricing à vérifier) | Meilleur que 4o sur code |
| **gpt-4.1-mini** | Version mini de 4.1, bon pour instructions suivies | (Pricing à vérifier) | Meilleur que 4o-mini sur instructions |

**Source**: [GPT-4o mini: advancing cost-efficient intelligence | OpenAI](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)

### Choix pour Notre Architecture

| Agent | Modèle Sélectionné | Justification |
|-------|-------------------|---------------|
| **Éclaireur** | `gpt-4o-mini` | ✅ Actuel. Tâche structurée (identification entité légale) |
| **Mineur** | `gpt-4o-mini` | ✅ Actuel. Quantification/extraction simple |
| **Cartographe Minimal** | `gpt-4o-mini` | ✅ Tâche structurée: classification d'entités. OpenAI recommande mini pour "applications that chain or parallelize multiple model calls" |
| **Extracteur Détaillé** | `gpt-4o-mini` | ✅ Extraction focalisée par entité. Optimisé pour parallélisation massive selon OpenAI. Context 128K, output 16K |
| **Superviseur** | `gpt-4o-mini` | ✅ Actuel. Validation cohérence = tâche structurée |
| **Restructurateur** | `gpt-4o-mini` | ✅ Actuel. Transformation de schéma |

**Note**: Tous les agents utilisent `gpt-4o-mini` car:
- ✅ **Performance excellente** sur tâches structurées (82% MMLU)
- ✅ **Optimisé pour parallélisation** (recommandation OpenAI explicite)
- ✅ **Context window suffisant** (128K tokens)
- ✅ **Coût optimisé** (60% moins cher que GPT-3.5 Turbo)

**Sources**:
- [Pricing | OpenAI](https://openai.com/api/pricing/)
- [GPT-4o mini: advancing cost-efficient intelligence](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)
- [OpenAI API: Comparing GPT-4o vs. GPT-4o-Mini in Cost & Performance](https://www.khueapps.com/blog/article/openai-api-comparing-gpt-4o-vs-gpt-4o-mini-in-cost-and-performance)

---

## 📅 Plan de Migration Détaillé

### Phase 1: Fondations (3-4 jours)

#### Étape 1.1: Créer les Nouveaux Modèles Pydantic

**Fichier**: `api/company_agents/models.py`

```python
# ====================================================================
# NOUVEAUX MODÈLES POUR ARCHITECTURE HIÉRARCHIQUE
# ====================================================================

class EntityRef(BaseModel):
    """Référence minimale à une entité identifiée (output Cartographe Minimal)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str = Field(..., min_length=1, max_length=200)
    entity_type: Literal[
        "subsidiary",        # Filiale juridique
        "participation",     # Participation minoritaire
        "sister",           # Entité sœur
        "holding",          # Holding
        "branch"            # Succursale/établissement
    ]
    confidence: float = Field(ge=0, le=1)
    country: Optional[str] = Field(default=None, max_length=100)
    ownership_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    brief_context: Optional[str] = Field(default=None, max_length=500)


class MinimalMappingReport(BaseModel):
    """Output du Cartographe Minimal"""

    model_config = ConfigDict(extra="forbid", strict=True)

    entities_identified: List[EntityRef] = Field(default_factory=list, max_items=50)
    total_found: int = Field(ge=0)
    search_strategy: Literal["perplexity", "gpt-4o-search"] = "perplexity"
    sources: List[SourceRef] = Field(min_items=1, max_items=10)
    methodology_notes: List[str] = Field(default_factory=list, max_items=5)


class DetailedEntityInfo(BaseModel):
    """Output de l'Extracteur Détaillé (par entité)"""

    model_config = ConfigDict(extra="forbid", strict=True)

    # Identité
    legal_name: str
    entity_type: str

    # Données de base
    headquarters: LocationInfo
    legal_status: Optional[Literal["Active", "Dissolved", "Liquidation", "Unknown"]] = None
    registration_date: Optional[str] = Field(default=None, max_length=10)
    jurisdiction: Optional[str] = Field(default=None, max_length=200)
    registration_number: Optional[str] = Field(default=None, max_length=50)

    # Données d'activité
    sector: Optional[str] = Field(default=None, max_length=200)
    naics_code: Optional[str] = Field(default=None, max_length=10)
    sic_code: Optional[str] = Field(default=None, max_length=10)
    nace_code: Optional[str] = Field(default=None, max_length=10)
    activities: Optional[List[str]] = Field(default=None, max_items=5)
    employees: Optional[str] = Field(default=None, max_length=50)
    revenue: Optional[str] = Field(default=None, max_length=100)

    # Liens de propriété
    ownership_details: Optional[Dict[str, Any]] = None

    # Contacts
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    website: Optional[str] = Field(default=None, max_length=500)

    # Métadonnées
    confidence: float = Field(ge=0, le=1)
    sources: List[SourceRef] = Field(min_items=1, max_items=7)
    extraction_date: str = Field(max_length=10)
```

**Tâches**:
- [ ] Ajouter les 3 nouveaux modèles dans `models.py`
- [ ] Valider les schémas avec `pydantic.TypeAdapter`
- [ ] Ajouter tests unitaires pour validation stricte

---

#### Étape 1.2: Créer le Service de Cache Redis

**Fichier**: `api/services/entity_cache_service.py`

```python
"""
Service de cache Redis pour éviter les recherches redondantes.
Stocke les résultats d'extraction par entité (legal_name + country).
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EntityCacheService:
    """Cache Redis pour DetailedEntityInfo."""

    def __init__(self, redis_client: redis.Redis, ttl_days: int = 7):
        self.redis = redis_client
        self.ttl = timedelta(days=ttl_days).total_seconds()
        self.prefix = "entity_cache:"

    def _generate_cache_key(
        self,
        legal_name: str,
        country: Optional[str] = None
    ) -> str:
        """Génère une clé de cache normalisée."""
        # Normalisation: minuscules, trim, suppression accents
        normalized = legal_name.lower().strip()
        if country:
            normalized += f":{country.lower()}"

        # Hash pour éviter les clés trop longues
        hash_key = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.prefix}{hash_key}"

    async def get(
        self,
        legal_name: str,
        country: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère une entité depuis le cache.

        Returns:
            Dict si en cache, None sinon
        """
        cache_key = self._generate_cache_key(legal_name, country)

        try:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                logger.info(f"✅ Cache HIT: {legal_name} ({country})")
                return data
            else:
                logger.debug(f"❌ Cache MISS: {legal_name} ({country})")
                return None
        except Exception as e:
            logger.error(f"⚠️ Erreur lecture cache: {e}")
            return None

    async def set(
        self,
        legal_name: str,
        data: Dict[str, Any],
        country: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Met en cache une entité extraite.

        Args:
            legal_name: Nom légal de l'entité
            data: Données DetailedEntityInfo (dict)
            country: Pays (optionnel)
            ttl: TTL custom en secondes (défaut: 7 jours)

        Returns:
            True si succès, False sinon
        """
        cache_key = self._generate_cache_key(legal_name, country)
        ttl_seconds = ttl or self.ttl

        try:
            # Ajouter metadata de cache
            data["_cached_at"] = datetime.utcnow().isoformat()
            data["_ttl_seconds"] = ttl_seconds

            await self.redis.setex(
                cache_key,
                int(ttl_seconds),
                json.dumps(data)
            )
            logger.info(f"✅ Cache SET: {legal_name} ({country}) - TTL: {ttl_seconds}s")
            return True
        except Exception as e:
            logger.error(f"⚠️ Erreur écriture cache: {e}")
            return False

    async def invalidate(
        self,
        legal_name: str,
        country: Optional[str] = None
    ) -> bool:
        """Invalide une entrée de cache."""
        cache_key = self._generate_cache_key(legal_name, country)
        try:
            deleted = await self.redis.delete(cache_key)
            if deleted:
                logger.info(f"🗑️ Cache INVALIDATED: {legal_name} ({country})")
            return bool(deleted)
        except Exception as e:
            logger.error(f"⚠️ Erreur invalidation cache: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache."""
        try:
            keys = await self.redis.keys(f"{self.prefix}*")
            return {
                "total_cached_entities": len(keys),
                "cache_prefix": self.prefix,
                "ttl_days": int(self.ttl / 86400)
            }
        except Exception as e:
            logger.error(f"⚠️ Erreur stats cache: {e}")
            return {}


# Singleton instance
_entity_cache_service: Optional[EntityCacheService] = None

def get_entity_cache_service() -> EntityCacheService:
    """Retourne l'instance singleton du service de cache."""
    global _entity_cache_service
    if _entity_cache_service is None:
        from status import get_redis_client
        redis_client = get_redis_client()
        _entity_cache_service = EntityCacheService(redis_client, ttl_days=7)
    return _entity_cache_service
```

**Tâches**:
- [ ] Créer `entity_cache_service.py`
- [ ] Implémenter `get()`, `set()`, `invalidate()`, `get_stats()`
- [ ] Ajouter tests unitaires (mock Redis)
- [ ] Documenter la stratégie de clés (legal_name + country)

---

### Phase 2: Cartographe Minimal (3-4 jours)

#### Étape 2.1: Créer l'Outil d'Identification

**Fichier**: `api/company_agents/subs_tools/entity_identifier_tool.py`

```python
"""
Outil d'identification des entités liées (focus sur identification pure).
"""

import time
import logging
from typing import Optional, List, Dict, Any
from agents import function_tool

logger = logging.getLogger(__name__)


@function_tool
async def identify_related_entities(
    company_name: str,
    sector: Optional[str] = None,
    website: Optional[str] = None,
    context: Optional[str] = None,
    search_mode: str = "thorough"
) -> Dict[str, Any]:
    """
    Identifie UNIQUEMENT les entités juridiquement liées sans extraction détaillée.

    Recherche focalisée sur:
    - Filiales juridiques (subsidiaries)
    - Participations minoritaires (participations)
    - Entités sœurs (sister companies)
    - Holdings
    - Succursales (branches)

    Args:
        company_name: Nom de l'entreprise à analyser
        sector: Secteur d'activité (aide à la désambiguïsation)
        website: Site web officiel (source prioritaire)
        context: Contexte enrichi du Mineur (optionnel)
        search_mode: "fast" (GPT-4o-search) ou "thorough" (Perplexity)

    Returns:
        dict avec:
          - entities: List[Dict] avec legal_name, entity_type, confidence, country
          - total_found: int
          - sources: List[Dict] des URLs sources
          - status: "success" ou "error"
          - duration_ms: Temps d'exécution
    """
    start_time = time.time()
    logger.info(f"🔍 Identification entités pour: {company_name}")

    try:
        # Prompt optimisé pour identification pure (pas d'extraction détaillée)
        prompt = f"""
Identifie UNIQUEMENT les entités juridiquement liées à {company_name}.

OBJECTIF: Lister les noms légaux des entités contrôlées ou liées.

RETOURNE POUR CHAQUE ENTITÉ:
- Nom légal complet (raison sociale officielle)
- Type: subsidiary, participation, sister, holding, ou branch
- Pays de juridiction (si détectable)
- Confidence (0-1) basée sur la clarté des sources

NE RECHERCHE PAS (sera fait par un agent dédié ultérieurement):
- Adresses détaillées
- Contacts (phone/email)
- Données financières détaillées (CA, effectifs)
- Coordonnées GPS

SOURCES PRIORITAIRES:
- Site web officiel ({website or "à identifier"})
- Rapports annuels consolidés
- Communiqués de presse officiels
- Registres légaux (Companies House, Infogreffe, etc.)

SECTEUR: {sector or "Non spécifié"}
CONTEXTE: {context or "Aucun contexte supplémentaire"}

FORMAT ATTENDU:
Pour chaque entité:
- Legal Name: [nom exact]
- Type: [subsidiary|participation|sister|holding|branch]
- Country: [pays]
- Confidence: [0-1]
- Brief context: [1 phrase max expliquant la relation]
"""

        # Sélection du moteur de recherche selon mode
        if search_mode == "thorough":
            # Utiliser Perplexity Sonar (recherche approfondie)
            from .perplexity_prompt_wo_subs import research_subsidiaries_with_perplexity_text
            search_result = await research_subsidiaries_with_perplexity_text(
                company_name=company_name,
                sector=sector,
                website=website,
                context=context,
                focus="identification_only"  # Flag pour prompt minimal
            )
        else:
            # Utiliser GPT-4o-search (recherche rapide)
            from .filiales_search_agent_optimized import subsidiary_search
            search_result = await subsidiary_search(
                company_name=company_name,
                sector=sector,
                website=website,
                focus="identification_only"
            )

        # Parser le résultat (adapter selon format retour)
        entities = _parse_identification_result(search_result)

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "entities": entities,
            "total_found": len(entities),
            "sources": search_result.get("citations", []),
            "status": "success",
            "duration_ms": duration_ms
        }

    except Exception as e:
        logger.error(f"❌ Erreur identification entités: {e}")
        return {
            "entities": [],
            "total_found": 0,
            "sources": [],
            "status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }


def _parse_identification_result(search_result: Dict) -> List[Dict]:
    """Parse le résultat de recherche pour extraire les entités identifiées."""
    # TODO: Implémenter le parsing selon le format retour de Perplexity/GPT-4o-search
    # Exemple de structure attendue:
    entities = []

    # Logique de parsing à implémenter
    # ...

    return entities
```

**Tâches**:
- [ ] Créer `entity_identifier_tool.py`
- [ ] Implémenter `identify_related_entities()`
- [ ] Ajouter support Perplexity + GPT-4o-search
- [ ] Implémenter `_parse_identification_result()`
- [ ] Tester avec ACOEM Group, S.F.E. Group, Agence Nile

---

#### Étape 2.2: Créer l'Agent Cartographe Minimal

**Fichier**: `api/company_agents/subs_agents/minimal_mapper.py`

```python
"""
Agent Cartographe Minimal: Identification des entités liées uniquement.
"""

import logging
from agents import Agent
from agents.agent_output import AgentOutputSchema
from company_agents.models import MinimalMappingReport
from company_agents.subs_tools.entity_identifier_tool import identify_related_entities

logger = logging.getLogger(__name__)


MINIMAL_MAPPER_INSTRUCTIONS = """
# RÔLE
Tu es le **🗺️ Cartographe Minimal**. Ta mission UNIQUE: identifier les entités liées.

# MISSION STRICTE
1. Appeler identify_related_entities avec les paramètres fournis
2. Parser le résultat JSON retourné par l'outil
3. Structurer la réponse en MinimalMappingReport

# FOCUS: Identification UNIQUEMENT
Tu identifies:
- ✅ Filiales juridiques (subsidiaries)
- ✅ Participations (participations)
- ✅ Entités sœurs (sister companies)
- ✅ Holdings
- ✅ Succursales (branches)

Tu NE cherches PAS:
- ❌ Adresses détaillées (sera fait par Extracteur Détaillé)
- ❌ Contacts phone/email (sera fait par Extracteur Détaillé)
- ❌ Données financières détaillées (sera fait par Extracteur Détaillé)
- ❌ Coordonnées GPS (sera fait par Extracteur Détaillé)

# INPUT REÇU
Tu reçois:
- company_name: Nom de l'entreprise (validé par Éclaireur)
- sector: Secteur d'activité (validé par Éclaireur)
- website: Site officiel (validé par Éclaireur)
- context: Contexte enrichi du Mineur (has_filiales_only, enterprise_type, etc.)
- search_mode: "fast" (GPT-4o-search) ou "thorough" (Perplexity)

# WORKFLOW
1. Appeler identify_related_entities(**input_params)
2. Vérifier status de la réponse
3. Si status == "success":
   - Parser entities retournées
   - Créer EntityRef pour chaque entité:
     * legal_name (obligatoire)
     * entity_type (obligatoire)
     * confidence (obligatoire, 0-1)
     * country (optionnel)
     * ownership_percentage (optionnel si détecté)
     * brief_context (optionnel, max 1 phrase)
4. Si status == "error":
   - Retourner MinimalMappingReport avec entities_identified = []
   - Ajouter methodology_notes expliquant l'erreur

# FORMAT OUTPUT
Retourner un JSON MinimalMappingReport strict:

```json
{
  "entities_identified": [
    {
      "legal_name": "ACOEM France SAS",
      "entity_type": "subsidiary",
      "confidence": 0.95,
      "country": "France",
      "ownership_percentage": 100,
      "brief_context": "Filiale à 100% du groupe ACOEM, spécialisée en monitoring environnemental"
    },
    ...
  ],
  "total_found": 10,
  "search_strategy": "perplexity",
  "sources": [
    {
      "title": "ACOEM Group - Our Subsidiaries",
      "url": "https://www.acoem.com/subsidiaries",
      "publisher": "ACOEM Group",
      "tier": "official"
    }
  ],
  "methodology_notes": [
    "Recherche Perplexity approfondie",
    "10 filiales identifiées via rapports annuels et site officiel"
  ]
}
```

# RÈGLES DE QUALITÉ
- Confidence ≥ 0.7 pour inclure une entité
- Si confidence < 0.7 → ajouter dans methodology_notes "entités incertaines exclues"
- Privilégier sources tier="official" ou "financial_media"
- Maximum 50 entités (si plus → prendre les 50 meilleures par confidence)

# GESTION D'ERREURS
- Si identify_related_entities échoue → retourner entities_identified = []
- Ajouter dans methodology_notes la raison de l'échec
- Ne JAMAIS inventer d'entités sans sources
"""


minimal_mapper_agent = Agent(
    name="🗺️ Cartographe Minimal",
    model="gpt-4o-mini",  # Optimisé pour tâches structurées
    instructions=MINIMAL_MAPPER_INSTRUCTIONS,
    tools=[identify_related_entities],
    output_schema=AgentOutputSchema(MinimalMappingReport, strict_json_schema=True)
)


async def call_minimal_mapper(
    company_name: str,
    sector: Optional[str] = None,
    website: Optional[str] = None,
    context: Optional[str] = None,
    search_mode: str = "thorough",
    session_id: Optional[str] = None
) -> MinimalMappingReport:
    """
    Appelle l'agent Cartographe Minimal.

    Args:
        company_name: Nom de l'entreprise
        sector: Secteur d'activité
        website: Site officiel
        context: Contexte enrichi du Mineur
        search_mode: "fast" ou "thorough"
        session_id: ID de session pour tracking

    Returns:
        MinimalMappingReport avec la liste des entités identifiées
    """
    logger.info(f"🗺️ Cartographe Minimal démarré: {company_name}")

    try:
        result = await minimal_mapper_agent.run_async(
            input_data={
                "company_name": company_name,
                "sector": sector,
                "website": website,
                "context": context,
                "search_mode": search_mode
            }
        )

        logger.info(f"✅ Cartographe Minimal terminé: {result.output.total_found} entités")
        return result.output

    except Exception as e:
        logger.error(f"❌ Erreur Cartographe Minimal: {e}")
        # Retourner rapport vide en cas d'erreur
        return MinimalMappingReport(
            entities_identified=[],
            total_found=0,
            search_strategy=search_mode,
            sources=[],
            methodology_notes=[f"Erreur: {str(e)}"]
        )
```

**Tâches**:
- [ ] Créer `minimal_mapper.py`
- [ ] Implémenter `minimal_mapper_agent` avec prompt optimisé
- [ ] Implémenter `call_minimal_mapper()` helper
- [ ] Ajouter logging structuré
- [ ] Tester avec différents search_mode (fast vs thorough)

---

### Phase 3: Agent d'Extraction Détaillée (4-5 jours)

#### Étape 3.1: Créer les Outils d'Extraction Spécialisés

**Fichier**: `api/company_agents/subs_tools/detailed_extraction_tools.py`

```python
"""
Outils d'extraction détaillée spécialisés par catégorie d'information.
"""

import time
import logging
from typing import Optional, Dict, Any
from agents import function_tool

logger = logging.getLogger(__name__)


@function_tool
async def extract_basic_info(
    entity_name: str,
    country: Optional[str] = None,
    entity_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrait les informations de base d'une entité.

    Focus:
    - Adresse du siège social
    - Juridiction (pays + région/état)
    - Statut légal (Active, Dissolved, etc.)
    - Date d'enregistrement/création
    - Numéro d'enregistrement légal

    Sources prioritaires:
    - Registres légaux officiels (Companies House, Infogreffe, etc.)
    - Site web officiel (page "About", "Contact")
    - Rapports annuels

    Args:
        entity_name: Nom légal de l'entité
        country: Pays (aide à cibler le bon registre)
        entity_type: Type d'entité (aide à la recherche)

    Returns:
        dict avec headquarters, legal_status, registration_date, jurisdiction, etc.
    """
    start_time = time.time()
    logger.info(f"📍 Extraction info de base: {entity_name}")

    try:
        # TODO: Implémenter la logique de recherche
        # - Construire query ciblée sur registres légaux
        # - Parser les résultats structurés

        result = {
            "headquarters": {
                "line1": "...",
                "city": "...",
                "country": country or "...",
                "postal_code": "..."
            },
            "legal_status": "Active",  # ou "Dissolved", "Liquidation", etc.
            "registration_date": "YYYY-MM-DD",
            "jurisdiction": f"{country} - [registre]",
            "registration_number": "...",
            "status": "success",
            "duration_ms": int((time.time() - start_time) * 1000),
            "sources": []
        }

        return result

    except Exception as e:
        logger.error(f"❌ Erreur extraction basic info: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }


@function_tool
async def extract_activity_data(
    entity_name: str,
    sector: Optional[str] = None,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrait les données d'activité d'une entité.

    Focus:
    - Secteur économique précis
    - Codes de classification (NAICS, SIC, NACE selon pays)
    - Effectif (nombre d'employés)
    - Chiffre d'affaires public (si disponible)
    - Activités principales (liste)

    Sources prioritaires:
    - Bases de données économiques (D&B, Bloomberg, etc.)
    - Rapports annuels
    - Sites de notation (Kompass, Societe.com, etc.)
    - Site web officiel

    Args:
        entity_name: Nom légal de l'entité
        sector: Secteur de départ (aide à la désambiguïsation)
        country: Pays (détermine le code de classification)

    Returns:
        dict avec sector, naics_code, employees, revenue, activities, etc.
    """
    start_time = time.time()
    logger.info(f"📊 Extraction données d'activité: {entity_name}")

    try:
        # TODO: Implémenter la logique de recherche
        # - Recherche focalisée sur bases de données économiques
        # - Parser les codes de classification selon pays

        result = {
            "sector": sector or "...",
            "naics_code": "...",  # Si USA/Canada
            "sic_code": "...",    # Si USA/UK
            "nace_code": "...",   # Si EU
            "employees": "...",
            "revenue": "...",
            "activities": ["...", "..."],
            "status": "success",
            "duration_ms": int((time.time() - start_time) * 1000),
            "sources": []
        }

        return result

    except Exception as e:
        logger.error(f"❌ Erreur extraction activity data: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }


@function_tool
async def extract_ownership_links(
    entity_name: str,
    parent_name: Optional[str] = None,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrait les liens de propriété d'une entité.

    Focus:
    - Pourcentage de participation du parent
    - Date d'acquisition (si applicable)
    - Structure capitalistique (si publique)
    - Autres actionnaires significatifs (si connus)

    Sources prioritaires:
    - Communiqués de presse officiels
    - Rapports annuels consolidés du parent
    - Registres légaux (actionnariat)
    - Bases de données financières (Bloomberg, Capital IQ, etc.)

    Args:
        entity_name: Nom légal de l'entité
        parent_name: Nom de la société mère (si connu)
        country: Pays (aide à cibler les registres)

    Returns:
        dict avec ownership_percentage, acquisition_date, shareholders, etc.
    """
    start_time = time.time()
    logger.info(f"🔗 Extraction liens de propriété: {entity_name}")

    try:
        # TODO: Implémenter la logique de recherche
        # - Recherche focalisée sur actionnariat/acquisitions
        # - Parser les pourcentages et dates

        result = {
            "ownership_percentage": 100,  # ou None si non détecté
            "acquisition_date": "YYYY-MM-DD",
            "shareholder_structure": [
                {
                    "name": parent_name or "...",
                    "percentage": 100,
                    "type": "parent"
                }
            ],
            "status": "success",
            "duration_ms": int((time.time() - start_time) * 1000),
            "sources": []
        }

        return result

    except Exception as e:
        logger.error(f"❌ Erreur extraction ownership links: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }


@function_tool
async def extract_contact_info(
    entity_name: str,
    website: Optional[str] = None,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrait les informations de contact d'une entité.

    Focus:
    - Téléphone (format international)
    - Email général (contact@...)
    - Site web officiel (si non fourni)

    Sources prioritaires:
    - Site web officiel (page Contact, footer, mentions légales)
    - Pages LinkedIn/réseaux sociaux de l'entreprise
    - Annuaires professionnels

    Args:
        entity_name: Nom légal de l'entité
        website: Site web (si déjà connu, focus sur scraping)
        country: Pays (aide au format téléphone)

    Returns:
        dict avec phone, email, website, etc.
    """
    start_time = time.time()
    logger.info(f"📞 Extraction contacts: {entity_name}")

    try:
        # TODO: Implémenter la logique de recherche
        # - Si website fourni → scraping page Contact
        # - Sinon → recherche site officiel puis scraping

        result = {
            "phone": "+XX X XX XX XX XX",
            "email": "contact@...",
            "website": website or "https://...",
            "status": "success",
            "duration_ms": int((time.time() - start_time) * 1000),
            "sources": []
        }

        return result

    except Exception as e:
        logger.error(f"❌ Erreur extraction contact info: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }


@function_tool
async def geocode_address(
    address: str,
    city: Optional[str] = None,
    country: Optional[str] = None
) -> Dict[str, Any]:
    """
    Géocode une adresse pour obtenir latitude/longitude.

    Utilise un service de géocodage (Google Maps, Nominatim, etc.).

    Args:
        address: Adresse à géocoder
        city: Ville (aide à la précision)
        country: Pays (aide à la précision)

    Returns:
        dict avec latitude, longitude, formatted_address
    """
    start_time = time.time()
    logger.info(f"🌍 Géocodage: {address}")

    try:
        # TODO: Implémenter géocodage via API
        # - Utiliser Nominatim (gratuit) ou Google Maps API
        # - Gérer les cas d'erreur (adresse introuvable)

        result = {
            "latitude": 45.7640,
            "longitude": 4.8357,
            "formatted_address": "...",
            "status": "success",
            "duration_ms": int((time.time() - start_time) * 1000)
        }

        return result

    except Exception as e:
        logger.error(f"❌ Erreur géocodage: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000)
        }
```

**Tâches**:
- [ ] Créer `detailed_extraction_tools.py`
- [ ] Implémenter les 5 outils:
  - [ ] `extract_basic_info()`
  - [ ] `extract_activity_data()`
  - [ ] `extract_ownership_links()`
  - [ ] `extract_contact_info()`
  - [ ] `geocode_address()`
- [ ] Tester chaque outil individuellement
- [ ] Ajouter gestion d'erreurs robuste

---

#### Étape 3.2: Créer l'Agent d'Extraction Détaillée

**Fichier**: `api/company_agents/subs_agents/detailed_extractor.py`

```python
"""
Agent d'Extraction Détaillée: Enrichit UNE entité à la fois.
Conçu pour être appelé en parallèle sur N entités.
"""

import logging
from typing import Optional
from datetime import datetime
from agents import Agent
from agents.agent_output import AgentOutputSchema
from company_agents.models import DetailedEntityInfo, EntityRef
from company_agents.subs_tools.detailed_extraction_tools import (
    extract_basic_info,
    extract_activity_data,
    extract_ownership_links,
    extract_contact_info,
    geocode_address
)
from services.entity_cache_service import get_entity_cache_service

logger = logging.getLogger(__name__)


DETAILED_EXTRACTOR_INSTRUCTIONS = """
# RÔLE
Tu es l'**📄 Extracteur Détaillé**. Ta mission: enrichir COMPLÈTEMENT une SEULE entité.

# INPUT REÇU
Tu reçois un EntityRef avec:
- legal_name: Nom légal exact
- entity_type: Type (subsidiary, participation, etc.)
- country: Pays (optionnel)
- ownership_percentage: % propriété (optionnel)
- brief_context: Contexte minimal (optionnel)

# WORKFLOW STRICT (5 étapes séquentielles)

## Étape 1: Informations de Base
Appeler extract_basic_info(entity_name=legal_name, country=country)

Résultat attendu:
- headquarters: Adresse complète du siège
- legal_status: "Active" | "Dissolved" | "Liquidation" | "Unknown"
- registration_date: Date d'enregistrement (YYYY-MM-DD)
- jurisdiction: Juridiction légale (pays + registre)
- registration_number: Numéro d'enregistrement

Si l'outil retourne status="error" → marquer tous les champs comme None + noter l'erreur.

## Étape 2: Données d'Activité
Appeler extract_activity_data(entity_name=legal_name, country=country)

Résultat attendu:
- sector: Secteur économique précis
- naics_code: Code NAICS (si USA/Canada)
- sic_code: Code SIC (si USA/UK)
- nace_code: Code NACE (si EU)
- employees: Effectif (ex: "120", "50-100", "Unknown")
- revenue: Chiffre d'affaires (ex: "5M EUR (2023)", "Unknown")
- activities: Liste d'activités principales

Si l'outil retourne status="error" → marquer champs comme None + noter l'erreur.

## Étape 3: Liens de Propriété
Appeler extract_ownership_links(entity_name=legal_name, country=country)

Résultat attendu:
- ownership_percentage: % de participation (0-100 ou None)
- acquisition_date: Date d'acquisition (YYYY-MM-DD ou None)
- shareholder_structure: Liste des actionnaires (optionnel)

Si l'outil retourne status="error" → marquer champs comme None + noter l'erreur.

## Étape 4: Contacts
Appeler extract_contact_info(entity_name=legal_name, country=country)

Résultat attendu:
- phone: Numéro international (ex: "+33 4 75 82 16 42")
- email: Email général (ex: "contact@example.com")
- website: Site web officiel

Si l'outil retourne status="error" → marquer champs comme None + noter l'erreur.

## Étape 5: Géocodage (si adresse disponible)
Si headquarters.line1 ET headquarters.city sont renseignés:
  Appeler geocode_address(
    address=headquarters.line1,
    city=headquarters.city,
    country=headquarters.country
  )

  Si succès → enrichir headquarters avec latitude/longitude
  Si erreur → laisser latitude/longitude à None

# CONSOLIDATION
Créer un objet DetailedEntityInfo avec:
- legal_name (input)
- entity_type (input)
- headquarters (étape 1 + étape 5)
- legal_status, registration_date, jurisdiction, registration_number (étape 1)
- sector, naics_code, sic_code, nace_code, employees, revenue, activities (étape 2)
- ownership_details (étape 3)
- phone, email, website (étape 4)
- confidence: Calculer basé sur le nombre de champs renseignés (0-1)
- sources: Consolider toutes les sources des 4 outils
- extraction_date: Date du jour (YYYY-MM-DD)

# CALCUL DE CONFIDENCE
```python
total_fields = 15  # Nombre de champs importants
filled_fields = count(non-None fields)
confidence = filled_fields / total_fields
```

Arrondir à 2 décimales (ex: 0.87).

# FORMAT OUTPUT
Retourner un JSON DetailedEntityInfo strict.

# GESTION D'ERREURS
- Si un outil échoue → marquer les champs comme None
- Ne JAMAIS inventer de données
- Toujours consolider les sources réelles
- Si TOUS les outils échouent → confidence = 0.0
"""


detailed_extractor_agent = Agent(
    name="📄 Extracteur Détaillé",
    model="gpt-4o-mini",  # Optimisé pour extraction structurée
    instructions=DETAILED_EXTRACTOR_INSTRUCTIONS,
    tools=[
        extract_basic_info,
        extract_activity_data,
        extract_ownership_links,
        extract_contact_info,
        geocode_address
    ],
    output_schema=AgentOutputSchema(DetailedEntityInfo, strict_json_schema=True)
)


async def extract_entity_details(
    entity_ref: EntityRef,
    session_id: Optional[str] = None,
    use_cache: bool = True
) -> Optional[DetailedEntityInfo]:
    """
    Extrait les détails complets d'une entité.

    Workflow:
    1. Check cache Redis
    2. Si en cache → retourner immédiatement
    3. Sinon → appeler l'agent d'extraction
    4. Mettre en cache le résultat
    5. Retourner DetailedEntityInfo

    Args:
        entity_ref: Référence minimale de l'entité
        session_id: ID de session pour tracking
        use_cache: Utiliser le cache Redis (True par défaut)

    Returns:
        DetailedEntityInfo ou None si erreur
    """
    logger.info(f"📄 Extraction détaillée: {entity_ref.legal_name}")

    # Étape 1: Vérifier cache
    if use_cache:
        cache_service = get_entity_cache_service()
        cached = await cache_service.get(
            legal_name=entity_ref.legal_name,
            country=entity_ref.country
        )
        if cached:
            logger.info(f"✅ Cache HIT: {entity_ref.legal_name}")
            return DetailedEntityInfo(**cached)

    # Étape 2: Extraction via agent
    try:
        result = await detailed_extractor_agent.run_async(
            input_data={
                "entity_ref": entity_ref.model_dump(),
                "session_id": session_id
            }
        )

        detailed_info = result.output
        logger.info(f"✅ Extraction terminée: {entity_ref.legal_name} (confidence: {detailed_info.confidence})")

        # Étape 3: Mise en cache
        if use_cache:
            await cache_service.set(
                legal_name=entity_ref.legal_name,
                data=detailed_info.model_dump(),
                country=entity_ref.country,
                ttl=7 * 86400  # 7 jours
            )

        return detailed_info

    except Exception as e:
        logger.error(f"❌ Erreur extraction {entity_ref.legal_name}: {e}")
        return None
```

**Tâches**:
- [ ] Créer `detailed_extractor.py`
- [ ] Implémenter `detailed_extractor_agent` avec workflow 5 étapes
- [ ] Implémenter `extract_entity_details()` avec cache Redis
- [ ] Ajouter calcul de confidence
- [ ] Tester avec une entité exemple (ACOEM France SAS)

---

### Phase 4: Orchestration Parallèle (2-3 jours)

#### Étape 4.1: Créer l'Orchestrateur d'Extraction Détaillée

**Fichier**: `api/company_agents/orchestrator/detailed_extraction_orchestrator.py`

```python
"""
Orchestrateur d'extraction détaillée en parallèle.
Lance N agents d'extraction détaillée simultanément.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime
from company_agents.models import EntityRef, DetailedEntityInfo
from company_agents.subs_agents.detailed_extractor import extract_entity_details
from services.websocket_service import send_websocket_update

logger = logging.getLogger(__name__)


async def orchestrate_detailed_extraction(
    entities: List[EntityRef],
    session_id: str,
    max_concurrent: int = 5,
    use_cache: bool = True
) -> List[DetailedEntityInfo]:
    """
    Orchestre l'extraction détaillée en parallèle avec semaphore.

    Args:
        entities: Liste des entités à enrichir
        session_id: ID de session pour tracking
        max_concurrent: Nombre max d'agents concurrents (éviter rate limits)
        use_cache: Utiliser le cache Redis

    Returns:
        Liste des DetailedEntityInfo extraites (filtrée des None)
    """
    logger.info(f"🔄 Orchestration extraction détaillée: {len(entities)} entités")
    logger.info(f"⚡ Concurrence max: {max_concurrent} agents simultanés")

    # Semaphore pour limiter la concurrence
    semaphore = asyncio.Semaphore(max_concurrent)

    # Compteurs pour tracking
    total = len(entities)
    completed = 0
    errors = 0
    cached = 0

    async def extract_one(entity: EntityRef, index: int) -> Optional[DetailedEntityInfo]:
        """Extrait une entité avec gestion d'erreurs."""
        nonlocal completed, errors, cached

        async with semaphore:
            try:
                logger.info(f"📄 [{index+1}/{total}] Extraction: {entity.legal_name}")

                # Envoyer update WebSocket (démarrage)
                await send_websocket_update(
                    session_id,
                    {
                        "agent_name": "📄 Extracteur Détaillé",
                        "entity_name": entity.legal_name,
                        "status": "running",
                        "progress": f"{index+1}/{total}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                # Extraction
                result = await extract_entity_details(
                    entity_ref=entity,
                    session_id=session_id,
                    use_cache=use_cache
                )

                if result:
                    completed += 1

                    # Détection cache hit
                    if hasattr(result, "_cached_at"):
                        cached += 1
                        logger.info(f"✅ [{index+1}/{total}] Cache HIT: {entity.legal_name}")
                    else:
                        logger.info(f"✅ [{index+1}/{total}] Extraction OK: {entity.legal_name} (confidence: {result.confidence})")

                    # Envoyer update WebSocket (succès)
                    await send_websocket_update(
                        session_id,
                        {
                            "agent_name": "📄 Extracteur Détaillé",
                            "entity_name": entity.legal_name,
                            "status": "completed",
                            "confidence": result.confidence,
                            "cached": hasattr(result, "_cached_at"),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

                    return result
                else:
                    errors += 1
                    logger.warning(f"⚠️ [{index+1}/{total}] Extraction échouée: {entity.legal_name}")

                    # Envoyer update WebSocket (erreur)
                    await send_websocket_update(
                        session_id,
                        {
                            "agent_name": "📄 Extracteur Détaillé",
                            "entity_name": entity.legal_name,
                            "status": "error",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

                    return None

            except Exception as e:
                errors += 1
                logger.error(f"❌ [{index+1}/{total}] Erreur {entity.legal_name}: {e}")

                # Envoyer update WebSocket (erreur)
                await send_websocket_update(
                    session_id,
                    {
                        "agent_name": "📄 Extracteur Détaillé",
                        "entity_name": entity.legal_name,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                return None

    # Lancer toutes les extractions en parallèle
    logger.info("⚡ Démarrage des extractions parallèles...")
    tasks = [extract_one(entity, i) for i, entity in enumerate(entities)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filtrer les None et les exceptions
    detailed_entities = [
        r for r in results
        if r is not None and not isinstance(r, Exception)
    ]

    # Logs finaux
    logger.info(f"✅ Extraction détaillée terminée:")
    logger.info(f"   • Total: {total}")
    logger.info(f"   • Succès: {completed}")
    logger.info(f"   • Erreurs: {errors}")
    logger.info(f"   • Cache hits: {cached}")
    logger.info(f"   • Taux de réussite: {(completed/total)*100:.1f}%")

    # Envoyer update WebSocket final
    await send_websocket_update(
        session_id,
        {
            "agent_name": "📄 Extracteur Détaillé",
            "status": "all_completed",
            "total": total,
            "completed": completed,
            "errors": errors,
            "cached": cached,
            "success_rate": (completed/total)*100 if total > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    return detailed_entities
```

**Tâches**:
- [ ] Créer `detailed_extraction_orchestrator.py`
- [ ] Implémenter `orchestrate_detailed_extraction()` avec semaphore
- [ ] Ajouter logging granulaire par entité
- [ ] Implémenter WebSocket updates granulaires
- [ ] Tester avec 10 entités en parallèle

---

#### Étape 4.2: Intégrer dans le Pipeline Principal

**Fichier**: `api/company_agents/orchestrator/extraction_orchestrator.py`

Modifier la fonction `orchestrate_extraction()` pour intégrer les nouveaux agents:

```python
# Après l'étape Mineur:

# ============================================
# Étape 3: Cartographe Minimal (NOUVEAU)
# ============================================
logger.info("🗺️ Étape 3: Cartographie Minimale des Entités")

from ..subs_agents.minimal_mapper import call_minimal_mapper

search_mode = "thorough" if state.deep_search else "fast"

mapping_result = await call_minimal_mapper(
    company_name=state.target_entity,
    sector=state.info_card.get("sector") if state.info_card else None,
    website=state.analyzer_raw.get("target_domain") if state.analyzer_raw else None,
    context=state.info_card.get("context") if state.info_card else None,
    search_mode=search_mode,
    session_id=session_id
)

state.mapping_result = mapping_result
logger.info(f"✅ Cartographie: {mapping_result.total_found} entités identifiées")

# ============================================
# Étape 4: Extraction Détaillée Parallèle (NOUVEAU)
# ============================================
if mapping_result.entities_identified:
    logger.info(f"📄 Étape 4: Extraction Détaillée Parallèle ({len(mapping_result.entities_identified)} entités)")

    from .detailed_extraction_orchestrator import orchestrate_detailed_extraction

    detailed_entities = await orchestrate_detailed_extraction(
        entities=mapping_result.entities_identified,
        session_id=session_id,
        max_concurrent=5,  # Limite de concurrence
        use_cache=True     # Utiliser cache Redis
    )

    state.detailed_entities = detailed_entities
    logger.info(f"✅ Extraction détaillée: {len(detailed_entities)}/{len(mapping_result.entities_identified)} réussies")
else:
    logger.info("ℹ️ Aucune entité identifiée par le Cartographe Minimal")
    state.detailed_entities = []

# Continuer avec Superviseur et Restructurateur...
```

**Tâches**:
- [ ] Modifier `extraction_orchestrator.py`
- [ ] Intégrer appel `call_minimal_mapper()`
- [ ] Intégrer appel `orchestrate_detailed_extraction()`
- [ ] Adapter ExtractionState pour stocker `mapping_result` et `detailed_entities`
- [ ] Tester le pipeline complet end-to-end

---

### Phase 5: Adaptation des Agents Finaux (2-3 jours)

#### Étape 5.1: Adapter le Superviseur

**Fichier**: `api/company_agents/subs_agents/meta_validator_optimized.py`

Modifier l'input du Superviseur pour accepter la nouvelle structure:

```python
# AVANT (ancien format):
# Input: SubsidiaryReport

# APRÈS (nouveau format):
# Input:
#   - mapping_result: MinimalMappingReport
#   - detailed_entities: List[DetailedEntityInfo]

SUPERVISEUR_INSTRUCTIONS = """
# RÔLE
Tu es le **⚖️ Superviseur**. Ta mission: valider la cohérence globale.

# INPUT NOUVEAU FORMAT
Tu reçois:
1. mapping_result: MinimalMappingReport
   - entities_identified: Liste[EntityRef] (entités brutes identifiées)
   - sources de la cartographie

2. detailed_entities: List[DetailedEntityInfo]
   - Entités enrichies avec toutes les données détaillées
   - Chaque entité a un score de confidence

# MISSION
Valider la cohérence entre:
- L'entreprise principale (company_card)
- Les entités identifiées (mapping_result)
- Les entités enrichies (detailed_entities)

# VALIDATIONS
... (reste inchangé)
"""
```

**Tâches**:
- [ ] Modifier le prompt du Superviseur
- [ ] Adapter la fonction `call_meta_validator()` pour passer les nouveaux inputs
- [ ] Tester avec les nouvelles structures de données

---

#### Étape 5.2: Adapter le Restructurateur

**Fichier**: `api/company_agents/subs_agents/data_validator_optimized.py`

Modifier pour transformer `List[DetailedEntityInfo]` → `List[SubsidiaryDetail]`:

```python
RESTRUCTURATEUR_INSTRUCTIONS = """
# RÔLE
Tu es le **🔄 Restructurateur**. Ta mission: transformer vers CompanyInfo final.

# INPUT NOUVEAU FORMAT
Tu reçois:
1. company_card: CompanyCard (entreprise principale)
2. mapping_result: MinimalMappingReport (cartographie)
3. detailed_entities: List[DetailedEntityInfo] (entités enrichies)
4. meta_validation_report: MetaValidationReport (validations)

# MISSION
Transformer DetailedEntityInfo → SubsidiaryDetail pour le format CompanyInfo.

# TRANSFORMATION
Pour chaque DetailedEntityInfo:
  SubsidiaryDetail {
    legal_name: detailed.legal_name,
    headquarters: LocationInfo {
      line1: detailed.headquarters.line1,
      city: detailed.headquarters.city,
      country: detailed.headquarters.country,
      latitude: detailed.headquarters.latitude,
      longitude: detailed.headquarters.longitude,
      phone: detailed.phone,
      email: detailed.email,
      website: detailed.website
    },
    activity: detailed.sector,
    confidence: detailed.confidence,
    sources: detailed.sources
  }

# ENRICHISSEMENT
- Si detailed.phone manquant → copier depuis headquarters si disponible
- Si detailed.email manquant → copier depuis headquarters si disponible
- Si GPS manquant → enrichir via géocodage (si pas déjà fait)

# OUTPUT
CompanyInfo avec subsidiaries_details rempli.
"""
```

**Tâches**:
- [ ] Modifier le prompt du Restructurateur
- [ ] Implémenter la transformation `DetailedEntityInfo → SubsidiaryDetail`
- [ ] Tester la génération du `CompanyInfo` final

---

### Phase 6: Tests et Validation (3-4 jours)

#### Étape 6.1: Tests Unitaires

```bash
# Tests des nouveaux modèles
pytest api/tests/test_models.py::TestEntityRef
pytest api/tests/test_models.py::TestMinimalMappingReport
pytest api/tests/test_models.py::TestDetailedEntityInfo

# Tests du cache Redis
pytest api/tests/test_entity_cache_service.py

# Tests des outils d'extraction
pytest api/tests/test_entity_identifier_tool.py
pytest api/tests/test_detailed_extraction_tools.py

# Tests des agents
pytest api/tests/test_minimal_mapper.py
pytest api/tests/test_detailed_extractor.py

# Tests de l'orchestration
pytest api/tests/test_detailed_extraction_orchestrator.py
```

#### Étape 6.2: Tests d'Intégration

**Test 1: Entreprise avec filiales (ACOEM Group)**
```bash
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "ACOEM Group",
    "deep_search": true
  }'
```

**Résultats attendus**:
- Cartographe Minimal: 8-12 entités identifiées
- Extraction Détaillée: 8-12 entités enrichies en parallèle
- Temps total: ~60-90s (vs 3-5min avant)
- Coût: ~0.15-0.25€ (vs 0.20-0.30€ avant)

**Test 2: Entreprise sans filiales (Agence Nile)**
```bash
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "https://www.agencenile.com/",
    "deep_search": false
  }'
```

**Résultats attendus**:
- Cartographe Minimal: 0 entités
- Extraction Détaillée: skipped
- Infos entreprise principale enrichies via Plan B

**Test 3: Cache Redis**
```bash
# Extraction 1 (première fois)
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "ACOEM Group"}'

# Extraction 2 (immédiatement après)
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "ACOEM Group"}'
```

**Résultats attendus**:
- Extraction 1: ~0.20€, 60s
- Extraction 2: ~0.05€, 15s (cache hits sur toutes les filiales)

#### Étape 6.3: Tests de Performance

**Test de Parallélisation**
```python
# Script de test: api/tests/performance/test_parallel_extraction.py
import asyncio
from company_agents.orchestrator.detailed_extraction_orchestrator import orchestrate_detailed_extraction

# Créer 20 entités fictives
entities = [EntityRef(legal_name=f"Entity {i}", entity_type="subsidiary", confidence=0.9) for i in range(20)]

# Test avec max_concurrent = 1 (séquentiel)
start = time.time()
results_seq = await orchestrate_detailed_extraction(entities, "test", max_concurrent=1)
duration_seq = time.time() - start

# Test avec max_concurrent = 5 (parallèle)
start = time.time()
results_par = await orchestrate_detailed_extraction(entities, "test", max_concurrent=5)
duration_par = time.time() - start

print(f"Séquentiel (1 agent): {duration_seq:.1f}s")
print(f"Parallèle (5 agents): {duration_par:.1f}s")
print(f"Speedup: {duration_seq/duration_par:.1f}x")
```

**Résultats attendus**:
- Séquentiel: ~300s (20 × 15s)
- Parallèle: ~60s (20 / 5 × 15s)
- Speedup: ~5x

---

### Phase 7: Refonte du Cost Tracking Hiérarchique (3-4 jours)

#### Contexte et Problèmes Actuels

Le système de cost tracking actuel (`api/services/cost_tracking_service.py`) présente des **limitations majeures** pour l'architecture parallèle:

**Problèmes identifiés**:

1. **Structure plate de `models_breakdown`**:
   ```json
   {
     "models_breakdown": [
       {"model": "gpt-4o-mini", "input_tokens": 1000, "cost_usd": 0.01},
       {"model": "gpt-4o-mini", "input_tokens": 1000, "cost_usd": 0.01},
       // ... 10 entrées identiques si 10 agents parallèles
     ]
   }
   ```
   ❌ Impossible de savoir quel agent a consommé quoi
   ❌ Pas de distinction entre agents séquentiels et parallèles

2. **Pas de hiérarchie agent → tool**:
   - Les tools sont trackés séparément
   - Aucun lien: "Agent Extracteur #3 a utilisé `extract_contact_info` avec 300 tokens"

3. **Tracking par entité manquant**:
   - Impossible de savoir: "Coût pour extraire ACOEM France SAS = 0.01€"
   - Important pour facturation ou analyse de performance

4. **Cache non tracké**:
   - Si une entité vient du cache Redis → coût = 0€
   - Mais aucun tracking du "gain réalisé grâce au cache"

5. **Estimation vs Réel**:
   - Système d'estimation complexe (lignes 229-446 du fichier actuel)
   - `ToolTokensTracker` existe mais mal intégré
   - Fallback sur estimations → coûts imprécis

---

#### Étape 7.1: Créer le Context Manager de Tracking

**Fichier**: `api/services/cost_tracking/cost_context.py`

```python
"""
Context Manager pour tracking automatique des coûts d'agents.
Permet un tracking hiérarchique agent → tools.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

# Context variable pour tracking hiérarchique
_cost_context_stack: ContextVar[List["CostContext"]] = ContextVar("cost_context_stack", default=[])


class CostContext:
    """
    Context manager pour tracking automatique des coûts d'un agent.

    Usage:
        async with CostContext(
            phase_name="eclaireur",
            agent_name="🔍 Éclaireur",
            model="gpt-4o-mini",
            session_id="abc-123"
        ) as ctx:
            # Code de l'agent
            result = await agent.run_async(...)

            # Tracker les tokens
            ctx.add_tokens(input_tokens=1000, output_tokens=500)

            # Tracker un tool
            ctx.add_tool_usage(
                tool_name="web_search_identify",
                model="gpt-4o-search-preview",
                input_tokens=500,
                output_tokens=300
            )
    """

    def __init__(
        self,
        phase_name: str,
        agent_name: str,
        model: str,
        session_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        parent_context: Optional["CostContext"] = None
    ):
        self.phase_name = phase_name
        self.agent_name = agent_name
        self.model = model
        self.session_id = session_id
        self.entity_name = entity_name  # Pour agents d'extraction détaillée
        self.parent_context = parent_context

        # Métriques
        self.input_tokens = 0
        self.output_tokens = 0
        self.tools_used: List[Dict[str, Any]] = []
        self.child_contexts: List["CostContext"] = []

        # Timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Cache tracking
        self.cached = False
        self.cache_source: Optional[str] = None

    async def __aenter__(self):
        """Entrée dans le context."""
        self.start_time = time.time()

        # Ajouter au stack de contextes
        stack = _cost_context_stack.get()
        stack.append(self)
        _cost_context_stack.set(stack)

        logger.debug(f"🔍 CostContext START: {self.phase_name} ({self.agent_name})")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Sortie du context."""
        self.end_time = time.time()

        # Retirer du stack
        stack = _cost_context_stack.get()
        if stack and stack[-1] is self:
            stack.pop()
            _cost_context_stack.set(stack)

        # Si on a un parent, s'enregistrer comme enfant
        if self.parent_context:
            self.parent_context.child_contexts.append(self)

        # Calculer et logger le coût
        cost_data = self.get_cost_summary()
        logger.info(
            f"💰 CostContext END: {self.phase_name} - "
            f"{cost_data['cost_eur']:.4f}€ ({cost_data['duration_ms']}ms)"
        )

        return False  # Ne pas supprimer les exceptions

    def add_tokens(self, input_tokens: int, output_tokens: int):
        """Ajoute des tokens consommés par l'agent principal."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def add_tool_usage(
        self,
        tool_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: Optional[int] = None
    ):
        """Ajoute l'usage d'un tool."""
        self.tools_used.append({
            "tool_name": tool_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms
        })

    def mark_cached(self, cache_source: str = "redis", cached_at: Optional[str] = None):
        """Marque l'entité comme extraite depuis le cache."""
        self.cached = True
        self.cache_source = cache_source
        # Si cached, pas de coût
        self.input_tokens = 0
        self.output_tokens = 0
        self.tools_used = []

    def get_cost_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des coûts du contexte."""
        from services.cost_tracking_service import ModelPricing

        # Coût de l'agent principal
        agent_cost_usd = ModelPricing.calculate_cost_usd(
            self.model,
            self.input_tokens,
            self.output_tokens
        )

        # Coûts des tools
        tools_cost_usd = Decimal("0")
        tools_breakdown = []

        for tool in self.tools_used:
            tool_cost = ModelPricing.calculate_cost_usd(
                tool["model"],
                tool["input_tokens"],
                tool["output_tokens"]
            )
            tools_cost_usd += tool_cost

            tools_breakdown.append({
                "tool_name": tool["tool_name"],
                "model": tool["model"],
                "input_tokens": tool["input_tokens"],
                "output_tokens": tool["output_tokens"],
                "cost_usd": float(tool_cost),
                "cost_eur": float(tool_cost * ModelPricing.USD_TO_EUR_RATE),
                "duration_ms": tool.get("duration_ms")
            })

        total_cost_usd = agent_cost_usd + tools_cost_usd
        total_cost_eur = total_cost_usd * ModelPricing.USD_TO_EUR_RATE

        duration_ms = None
        if self.start_time and self.end_time:
            duration_ms = int((self.end_time - self.start_time) * 1000)

        return {
            "phase_name": self.phase_name,
            "agent_name": self.agent_name,
            "entity_name": self.entity_name,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": float(total_cost_usd),
            "cost_eur": float(total_cost_eur),
            "duration_ms": duration_ms,
            "cached": self.cached,
            "cache_source": self.cache_source,
            "tools_used": tools_breakdown,
            "child_contexts": [child.get_cost_summary() for child in self.child_contexts]
        }


def get_current_cost_context() -> Optional[CostContext]:
    """Retourne le contexte de coût actuel (le dernier dans le stack)."""
    stack = _cost_context_stack.get()
    return stack[-1] if stack else None
```

**Tâches**:
- [ ] Créer `api/services/cost_tracking/cost_context.py`
- [ ] Implémenter `CostContext` avec `__aenter__` et `__aexit__`
- [ ] Implémenter `add_tokens()`, `add_tool_usage()`, `mark_cached()`
- [ ] Tester le context manager avec un agent simple

---

#### Étape 7.2: Créer le Tracker Hiérarchique

**Fichier**: `api/services/cost_tracking/hierarchical_tracker.py`

```python
"""
Tracker hiérarchique pour consolider les coûts de tous les agents.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class HierarchicalCostTracker:
    """
    Tracker hiérarchique qui consolide les coûts de tous les agents.
    Construit une structure arborescente des coûts.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.root_phases: List[Dict[str, Any]] = []
        self.cache_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_savings_usd": Decimal("0"),
            "cache_savings_eur": Decimal("0")
        }

    def add_phase(self, cost_summary: Dict[str, Any]):
        """Ajoute une phase d'extraction au tracker."""
        self.root_phases.append(cost_summary)

        # Mettre à jour les stats de cache
        if cost_summary.get("cached"):
            self.cache_stats["cache_hits"] += 1
        else:
            self.cache_stats["cache_misses"] += 1

        # Récursif pour les child_contexts
        self._update_cache_stats_recursive(cost_summary.get("child_contexts", []))

    def _update_cache_stats_recursive(self, children: List[Dict[str, Any]]):
        """Met à jour les stats de cache récursivement."""
        for child in children:
            if child.get("cached"):
                self.cache_stats["cache_hits"] += 1
                # Estimer le coût économisé (coût moyen d'une extraction)
                estimated_savings = Decimal("0.01")  # 0.01€ par entité
                self.cache_stats["cache_savings_usd"] += estimated_savings
                self.cache_stats["cache_savings_eur"] += estimated_savings * Decimal("0.92")
            else:
                self.cache_stats["cache_misses"] += 1

            # Récursif
            self._update_cache_stats_recursive(child.get("child_contexts", []))

    def get_consolidated_costs(self) -> Dict[str, Any]:
        """
        Retourne les coûts consolidés de toute l'extraction.

        Returns:
            {
                "total_cost_usd": float,
                "total_cost_eur": float,
                "total_tokens": int,
                "cache_savings_usd": float,
                "cache_savings_eur": float,
                "phases": List[Dict],
                "summary": Dict
            }
        """
        total_cost_usd = Decimal("0")
        total_cost_eur = Decimal("0")
        total_input_tokens = 0
        total_output_tokens = 0
        total_duration_ms = 0
        agents_executed = 0

        # Parcourir toutes les phases
        for phase in self.root_phases:
            cost_usd, cost_eur, input_tok, output_tok, duration, num_agents = self._sum_costs_recursive(phase)
            total_cost_usd += cost_usd
            total_cost_eur += cost_eur
            total_input_tokens += input_tok
            total_output_tokens += output_tok
            total_duration_ms += duration
            agents_executed += num_agents

        # Calculer cache hit rate
        total_cache_ops = self.cache_stats["cache_hits"] + self.cache_stats["cache_misses"]
        cache_hit_rate = (
            self.cache_stats["cache_hits"] / total_cache_ops
            if total_cache_ops > 0
            else 0.0
        )

        # Phase la plus coûteuse
        most_expensive_phase = max(
            self.root_phases,
            key=lambda p: p.get("cost_usd", 0)
        ) if self.root_phases else None

        return {
            "total_cost_usd": float(total_cost_usd),
            "total_cost_eur": float(total_cost_eur),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "cache_savings_usd": float(self.cache_stats["cache_savings_usd"]),
            "cache_savings_eur": float(self.cache_stats["cache_savings_eur"]),
            "phases": self.root_phases,
            "summary": {
                "agents_executed": agents_executed,
                "cache_hit_rate": cache_hit_rate,
                "cache_hits": self.cache_stats["cache_hits"],
                "cache_misses": self.cache_stats["cache_misses"],
                "most_expensive_phase": most_expensive_phase.get("phase_name") if most_expensive_phase else None,
                "total_duration_ms": total_duration_ms
            }
        }

    def _sum_costs_recursive(self, phase: Dict[str, Any]) -> tuple:
        """
        Somme récursivement les coûts d'une phase et de ses enfants.

        Returns:
            (cost_usd, cost_eur, input_tokens, output_tokens, duration_ms, num_agents)
        """
        cost_usd = Decimal(str(phase.get("cost_usd", 0)))
        cost_eur = Decimal(str(phase.get("cost_eur", 0)))
        input_tokens = phase.get("input_tokens", 0)
        output_tokens = phase.get("output_tokens", 0)
        duration_ms = phase.get("duration_ms", 0)
        num_agents = 1

        # Récursif sur les enfants
        for child in phase.get("child_contexts", []):
            child_cost_usd, child_cost_eur, child_input, child_output, child_duration, child_agents = self._sum_costs_recursive(child)
            cost_usd += child_cost_usd
            cost_eur += child_cost_eur
            input_tokens += child_input
            output_tokens += child_output
            duration_ms += child_duration
            num_agents += child_agents

        return cost_usd, cost_eur, input_tokens, output_tokens, duration_ms, num_agents


# Singleton par session
_session_trackers: Dict[str, HierarchicalCostTracker] = {}

def get_cost_tracker(session_id: str) -> HierarchicalCostTracker:
    """Retourne ou crée un tracker pour une session."""
    if session_id not in _session_trackers:
        _session_trackers[session_id] = HierarchicalCostTracker(session_id)
    return _session_trackers[session_id]

def clear_cost_tracker(session_id: str):
    """Supprime un tracker de session."""
    if session_id in _session_trackers:
        del _session_trackers[session_id]
```

**Tâches**:
- [ ] Créer `hierarchical_tracker.py`
- [ ] Implémenter `HierarchicalCostTracker`
- [ ] Implémenter `add_phase()`, `get_consolidated_costs()`
- [ ] Implémenter calcul du cache hit rate et savings
- [ ] Tester avec plusieurs phases imbriquées

---

#### Étape 7.3: Intégrer dans les Agents

**Modifier**: Tous les agents pour utiliser `CostContext`

**Exemple - Agent Éclaireur**:

```python
# Dans api/company_agents/subs_agents/company_analyzer_optimized.py

from services.cost_tracking.cost_context import CostContext, get_current_cost_context
from services.cost_tracking.hierarchical_tracker import get_cost_tracker

async def call_company_analyzer(
    input_query: str,
    session_id: Optional[str] = None
) -> CompanyLinkage:
    """Appelle l'agent Éclaireur avec tracking des coûts."""

    # Context manager pour tracking automatique
    async with CostContext(
        phase_name="eclaireur",
        agent_name="🔍 Éclaireur",
        model="gpt-4o-mini",
        session_id=session_id
    ) as ctx:
        logger.info(f"🔍 Éclaireur démarré: {input_query}")

        try:
            # Appel de l'agent
            result = await company_analyzer.run_async(input_data={"query": input_query})

            # Tracker les tokens (récupérés depuis le résultat de l'agent)
            # Note: OpenAI Agents SDK devrait fournir ces métriques
            if hasattr(result, "usage"):
                ctx.add_tokens(
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens
                )

            # Enregistrer le contexte dans le tracker de session
            if session_id:
                tracker = get_cost_tracker(session_id)
                tracker.add_phase(ctx.get_cost_summary())

            return result.output

        except Exception as e:
            logger.error(f"❌ Erreur Éclaireur: {e}")
            raise
```

**Exemple - Agent d'Extraction Détaillée** (avec tracking par entité):

```python
# Dans api/company_agents/subs_agents/detailed_extractor.py

async def extract_entity_details(
    entity_ref: EntityRef,
    session_id: Optional[str] = None,
    use_cache: bool = True
) -> Optional[DetailedEntityInfo]:
    """Extrait les détails d'une entité avec tracking des coûts."""

    # Context avec entity_name pour tracking granulaire
    async with CostContext(
        phase_name="extraction_detaillee",
        agent_name="📄 Extracteur Détaillé",
        model="gpt-4o-mini",
        session_id=session_id,
        entity_name=entity_ref.legal_name  # Important!
    ) as ctx:
        logger.info(f"📄 Extraction: {entity_ref.legal_name}")

        # Étape 1: Vérifier cache
        if use_cache:
            cache_service = get_entity_cache_service()
            cached = await cache_service.get(
                legal_name=entity_ref.legal_name,
                country=entity_ref.country
            )
            if cached:
                logger.info(f"✅ Cache HIT: {entity_ref.legal_name}")
                ctx.mark_cached(cache_source="redis")

                # Enregistrer dans le tracker (coût = 0)
                if session_id:
                    tracker = get_cost_tracker(session_id)
                    tracker.add_phase(ctx.get_cost_summary())

                return DetailedEntityInfo(**cached)

        # Étape 2: Extraction via agent
        try:
            result = await detailed_extractor_agent.run_async(...)

            # Tracker les tokens
            if hasattr(result, "usage"):
                ctx.add_tokens(
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens
                )

            # Enregistrer dans le tracker
            if session_id:
                tracker = get_cost_tracker(session_id)
                tracker.add_phase(ctx.get_cost_summary())

            # Mise en cache
            if use_cache:
                await cache_service.set(...)

            return result.output

        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            return None
```

**Tâches**:
- [ ] Modifier `call_company_analyzer()` pour utiliser CostContext
- [ ] Modifier `call_information_extractor()` pour utiliser CostContext
- [ ] Modifier `call_minimal_mapper()` pour utiliser CostContext
- [ ] Modifier `extract_entity_details()` pour utiliser CostContext (avec entity_name)
- [ ] Modifier `call_meta_validator()` pour utiliser CostContext
- [ ] Modifier `call_data_restructurer()` pour utiliser CostContext

---

#### Étape 7.4: Modifier le Modèle `CompanyInfo`

**Fichier**: `api/company_agents/models.py`

Ajouter le nouveau format de `extraction_costs`:

```python
class ExtractionCosts(BaseModel):
    """Coûts d'extraction hiérarchiques."""

    model_config = ConfigDict(extra="forbid", strict=True)

    total_cost_usd: float
    total_cost_eur: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    cache_savings_usd: Optional[float] = None
    cache_savings_eur: Optional[float] = None

    # Structure hiérarchique des phases
    phases: List[Dict[str, Any]] = Field(default_factory=list)

    # Résumé
    summary: Optional[Dict[str, Any]] = None
    exchange_rate: float = Field(default=0.92)


class CompanyInfo(BaseModel):
    """Output final de l'extraction (inchangé sauf extraction_costs)."""

    # ... tous les champs existants ...

    extraction_costs: Optional[ExtractionCosts] = None  # Format mis à jour
```

**Tâches**:
- [ ] Créer le modèle `ExtractionCosts` avec structure hiérarchique
- [ ] Mettre à jour `CompanyInfo.extraction_costs` pour utiliser le nouveau modèle
- [ ] Ajouter tests de validation Pydantic

---

#### Étape 7.5: Modifier l'Orchestrateur Principal

**Fichier**: `api/company_agents/orchestrator/extraction_orchestrator.py`

À la fin de l'orchestration, consolider les coûts:

```python
async def orchestrate_extraction(...) -> Dict[str, Any]:
    """Pipeline d'extraction avec tracking hiérarchique des coûts."""

    # ... Toutes les étapes d'extraction avec CostContext ...

    # À la fin: Consolider les coûts
    if session_id:
        tracker = get_cost_tracker(session_id)
        consolidated_costs = tracker.get_consolidated_costs()

        logger.info(f"💰 Coûts consolidés: {consolidated_costs['total_cost_eur']:.4f}€")
        logger.info(f"💰 Cache savings: {consolidated_costs['cache_savings_eur']:.4f}€")
        logger.info(f"💰 Cache hit rate: {consolidated_costs['summary']['cache_hit_rate']:.1%}")

        # Ajouter au CompanyInfo final
        result_data["extraction_costs"] = ExtractionCosts(**consolidated_costs)

        # Nettoyer le tracker
        clear_cost_tracker(session_id)

    return result_data
```

**Tâches**:
- [ ] Modifier `orchestrate_extraction()` pour consolider les coûts à la fin
- [ ] Ajouter `ExtractionCosts` au `CompanyInfo` retourné
- [ ] Nettoyer le tracker après consolidation

---

#### Étape 7.6: Tests du Système de Coûts

**Tests unitaires**:

```bash
# Test CostContext
pytest api/tests/cost_tracking/test_cost_context.py

# Test HierarchicalCostTracker
pytest api/tests/cost_tracking/test_hierarchical_tracker.py

# Test intégration avec agents
pytest api/tests/test_cost_tracking_integration.py
```

**Test d'intégration complet**:

```bash
# Extraction avec 10 filiales + cache
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "ACOEM Group"}'

# Vérifier la structure de extraction_costs:
{
  "extraction_costs": {
    "total_cost_usd": 0.18,
    "total_cost_eur": 0.17,
    "cache_savings_usd": 0.05,
    "cache_savings_eur": 0.046,
    "phases": [
      {
        "phase_name": "eclaireur",
        "agent_name": "🔍 Éclaireur",
        "cost_usd": 0.01,
        "tools_used": [...]
      },
      {
        "phase_name": "extraction_detaillee",
        "child_contexts": [
          {
            "entity_name": "ACOEM France SAS",
            "cost_usd": 0.01,
            "cached": false
          },
          {
            "entity_name": "ACOEM Germany GmbH",
            "cost_usd": 0.0,
            "cached": true
          }
        ]
      }
    ],
    "summary": {
      "agents_executed": 15,
      "cache_hit_rate": 0.30,
      "cache_hits": 3,
      "cache_misses": 7
    }
  }
}
```

**Tâches**:
- [ ] Écrire tests unitaires pour `CostContext`
- [ ] Écrire tests pour `HierarchicalCostTracker`
- [ ] Tester avec extraction réelle (ACOEM Group)
- [ ] Valider la structure JSON finale
- [ ] Vérifier les calculs de cache savings

---

#### Étape 7.7: Dashboard de Visualisation (Optionnel)

Pour une meilleure observabilité, créer un endpoint dédié aux coûts:

**Fichier**: `api/routers/costs.py`

```python
"""
Endpoints pour visualiser les coûts d'extraction.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/extraction/{session_id}")
async def get_extraction_costs(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retourne les coûts détaillés d'une extraction.

    Format:
    - Breakdown hiérarchique par phase
    - Coûts par entité (si extraction détaillée)
    - Cache hit rate
    - Savings réalisés
    """
    # Récupérer depuis DB
    extraction = await db.get(CompanyExtraction, session_id=session_id)

    if not extraction or not extraction.extraction_costs:
        return {"error": "Extraction not found or no cost data"}

    return {
        "session_id": session_id,
        "company_name": extraction.company_name,
        "extraction_costs": extraction.extraction_costs,
        "created_at": extraction.created_at.isoformat()
    }


@router.get("/organization/summary")
async def get_organization_cost_summary(
    organization_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Résumé des coûts pour une organisation sur une période.

    Métriques:
    - Coût total
    - Coût moyen par extraction
    - Cache savings total
    - Cache hit rate moyen
    - Top phases les plus coûteuses
    """
    # Implémenter l'agrégation
    pass
```

**Tâches** (optionnel):
- [ ] Créer `api/routers/costs.py`
- [ ] Implémenter `GET /costs/extraction/{session_id}`
- [ ] Implémenter `GET /costs/organization/summary`
- [ ] Ajouter graphiques dans le frontend (Chart.js)

---

#### Gains Attendus de la Phase 7

**Visibilité des Coûts**:
- ✅ Breakdown hiérarchique: savoir quel agent coûte quoi
- ✅ Tracking par entité: "ACOEM France SAS = 0.01€"
- ✅ Cache economics: "3€ économisés grâce au cache ce mois-ci"

**Précision**:
- ✅ Tracking réel (pas d'estimations)
- ✅ Consolidation automatique des agents parallèles
- ✅ Distinction coûts agents vs coûts tools

**Observabilité**:
- ✅ Dashboard temps réel via WebSocket
- ✅ Endpoints dédiés aux coûts
- ✅ Analyse de performance (quelle phase est la plus coûteuse?)

**Facturation**:
- ✅ Coût par entité → facturation granulaire possible
- ✅ Cache hit rate → optimisation économique
- ✅ Export des coûts pour comptabilité

---

## 📊 Gains Attendus

### Comparaison: AVANT vs APRÈS

#### Cas 1: Entreprise avec 10 filiales (ex: ACOEM Group)

| Métrique | **AVANT** | **APRÈS** | **Gain** |
|----------|-----------|-----------|----------|
| **Temps d'exécution** | 180-300s | 60-90s | **-67%** |
| **Coût moyen** | 0.20€ | 0.18€ | **-10%** |
| **Recherches redondantes** | Oui (si 2ème extraction) | Non (cache Redis) | **100%** |
| **Modularité** | Non (tout re-chercher) | Oui (enrichir 1 filiale) | ✅ |
| **Parallélisation** | Non (séquentiel) | Oui (5 agents //) | ✅ |

**Détail des Coûts (APRÈS)**:
- Éclaireur: 0.01€
- Mineur: 0.02€
- Cartographe Minimal: 0.03€ (-80% vs 0.15€)
- Extraction Détaillée: 10 × 0.01€ = 0.10€ (nouveau)
- Superviseur: 0.01€
- Restructurateur: 0.01€
- **Total: 0.18€**

#### Cas 2: Entreprise sans filiales (ex: Agence Nile)

| Métrique | **AVANT** | **APRÈS** | **Gain** |
|----------|-----------|-----------|----------|
| **Temps d'exécution** | 60-90s | 30-45s | **-50%** |
| **Coût moyen** | 0.05€ | 0.04€ | **-20%** |

**Détail des Coûts (APRÈS)**:
- Éclaireur: 0.01€
- Mineur: 0.02€
- Cartographe Minimal: 0.01€ (mode fast, pas d'entités)
- Extraction Détaillée: 0€ (skipped)
- Superviseur: 0€ (skipped si pas d'entités)
- Restructurateur: 0€ (skipped si pas d'entités)
- **Total: 0.04€**

#### Cas 3: Extraction multiple (même entreprise 2×)

| Métrique | **AVANT** | **APRÈS** | **Gain** |
|----------|-----------|-----------|----------|
| **Temps 1ère extraction** | 180s | 60s | -67% |
| **Temps 2ème extraction** | 180s | 15s | **-92%** |
| **Coût 1ère extraction** | 0.20€ | 0.18€ | -10% |
| **Coût 2ème extraction** | 0.20€ | 0.05€ | **-75%** |

**Explication**: Cache Redis évite toutes les extractions détaillées (10 filiales en cache).

### Gains Qualitatifs

✅ **Modularité**: Possibilité d'enrichir une seule filiale sans tout re-chercher
✅ **Parallélisation**: 5 filiales extraites simultanément
✅ **Cache intelligent**: TTL 7 jours, évite recherches redondantes
✅ **Scalabilité**: Ajout facile de nouveaux agents spécialisés (ex: agent "ESG", agent "Risques")
✅ **Observabilité**: Updates WebSocket granulaires par entité
✅ **Résilience**: Si 1 agent échoue, les autres continuent

---

## ⚠️ Points d'Attention

### 1. Rate Limits des APIs

**Problème**: Parallélisation de 10+ agents peut déclencher des rate limits (429 errors).

**Solutions**:
- ✅ Semaphore `max_concurrent = 5` (par défaut)
- ✅ Retry exponentiel avec backoff (déjà implémenté dans guardrails)
- ✅ Monitoring des erreurs 429 dans logs

**Configuration recommandée**:
```python
MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "5"))
```

### 2. Gestion d'Erreurs Partielles

**Problème**: Si 3/10 agents échouent, doit-on continuer?

**Solution**:
- ✅ Continuer l'extraction même si certains agents échouent
- ✅ Marquer les entités échouées avec `confidence = 0.0`
- ✅ Logger les erreurs pour monitoring
- ✅ Envoyer WebSocket update par entité (succès ou erreur)

### 3. Cost Tracking Distribué

**Problème**: Le coût est maintenant distribué sur N agents en parallèle.

**Solution**:
- ✅ Modifier `api/services/cost_tracking_service.py` pour consolider les coûts
- ✅ Tracer chaque appel d'agent avec son coût
- ✅ Agréger dans `extraction_costs.models_breakdown`

**Exemple de structure**:
```json
{
  "extraction_costs": {
    "cost_usd": 0.18,
    "models_breakdown": [
      {"model": "gpt-4o-mini", "phase": "minimal_mapper", "cost_usd": 0.03},
      {"model": "gpt-4o-mini", "phase": "detailed_extractor_1", "cost_usd": 0.01},
      {"model": "gpt-4o-mini", "phase": "detailed_extractor_2", "cost_usd": 0.01},
      ...
    ]
  }
}
```

### 4. Cache Invalidation

**Problème**: Si les données d'une entreprise changent, le cache devient obsolète.

**Solution**:
- ✅ TTL par défaut: 7 jours
- ✅ Endpoint admin: `DELETE /cache/entity/{legal_name}` pour invalidation manuelle
- ✅ Header `X-Force-Refresh: true` pour forcer re-extraction
- ✅ Logging des cache hits/misses pour monitoring

### 5. WebSocket Updates Granulaires

**Problème**: L'orchestrateur lance N agents, comment suivre chacun?

**Solution**:
- ✅ Envoyer un update WebSocket par entité:
  - `status: "running"` au démarrage
  - `status: "completed"` au succès (avec confidence)
  - `status: "error"` en cas d'échec
- ✅ Update final avec stats globales (total, succès, erreurs, cache hits)

**Format des updates**:
```json
{
  "agent_name": "📄 Extracteur Détaillé",
  "entity_name": "ACOEM France SAS",
  "status": "completed",
  "confidence": 0.87,
  "cached": false,
  "progress": "3/10",
  "timestamp": "2025-01-27T14:32:15Z"
}
```

---

## 📅 Timeline et Ressources

### Timeline Estimée

| Phase | Durée | Jalons |
|-------|-------|--------|
| **Phase 1**: Fondations | 3-4 jours | Modèles Pydantic + Cache Redis |
| **Phase 2**: Cartographe Minimal | 3-4 jours | Agent + Outil identification |
| **Phase 3**: Extracteur Détaillé | 4-5 jours | 5 outils + Agent |
| **Phase 4**: Orchestration | 2-3 jours | Parallélisation + Intégration pipeline |
| **Phase 5**: Adaptation | 2-3 jours | Superviseur + Restructurateur |
| **Phase 6**: Tests & Validation | 3-4 jours | Tests unitaires + intégration + perf |
| **Phase 7**: Cost Tracking Hiérarchique | 3-4 jours | CostContext + HierarchicalTracker + Intégration agents |
| **Buffer** | 2-3 jours | Imprévus et optimisations |

**Total: 22-30 jours (4-6 semaines)**

### Ressources Nécessaires

**Développement**:
- 1 développeur backend Python (temps plein)
- Accès aux APIs: OpenAI (gpt-4o-mini), Perplexity (sonar-pro)
- Redis instance (dev + prod)

**Infrastructure**:
- Serveur de dev avec 8GB+ RAM (pour tests parallèles)
- Redis: 2GB storage (cache 7 jours)
- Monitoring: Logs structurés + dashboard WebSocket

**Budget API estimé (dev + tests)**:
- OpenAI: ~50-100€ pour tests complets
- Perplexity: ~30-50€ pour tests approfondis
- **Total: ~80-150€**

---

## 🚀 Prochaines Étapes

### Décision GO/NO-GO

Avant de démarrer la migration, valider:

- [ ] **Budget**: 80-150€ API + 3-5 semaines dev OK?
- [ ] **Priorité**: Migration vs nouvelles features?
- [ ] **Ressources**: Développeur disponible temps plein?
- [ ] **Stratégie de déploiement**: Feature flag? Déploiement progressif?

### Si GO: Phase 1 (Quick Wins)

Commencer par les **quick wins** (Phase 1):

1. **Cache Redis** (Étape 1.2): Gain immédiat sur extractions multiples
2. **Nouveaux modèles** (Étape 1.1): Fondations pour le reste

**Durée**: 3-4 jours
**Gain**: Cache opérationnel = -75% coût sur 2ème extraction

### Si NO-GO: Optimisations Alternatives

Si la migration complète est trop lourde, alternatives:

1. **Cache Redis uniquement** (Phase 1.2): Gain immédiat sans refonte
2. **Cartographe Minimal** (Phase 2): Découpler identification/extraction
3. **Parallélisation simple**: `asyncio.gather()` sur cartographie actuelle

---

## 📚 Références

- [OpenAI Agents SDK Documentation](https://github.com/openai/openai-agents-sdk)
- [GPT-4o mini: advancing cost-efficient intelligence](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)
- [Pricing | OpenAI](https://openai.com/api/pricing/)
- [Redis Python Client (redis-py)](https://github.com/redis/redis-py)

---

**Document maintenu par**: @nile
**Dernière mise à jour**: 2025-01-27
**Version**: 1.0
