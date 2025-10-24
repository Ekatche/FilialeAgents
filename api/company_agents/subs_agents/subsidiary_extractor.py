"""
Architecture Multi-Agents CORRIGÉE pour extraction de filiales

DEUX PIPELINES DISPONIBLES :
1. Pipeline Simple : Recherche rapide et économique
2. Pipeline Avancé : Recherche approfondie et exhaustive

Agent de recherche : Retourne TEXTE BRUT (pas de JSON)
Agent Cartographe : Structure le texte brut en JSON
"""

import os
import json
import re
import time
import logging
import asyncio
from typing import List, Optional, Dict, Any
from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool
from agents.model_settings import ModelSettings
from agents.agent_output import AgentOutputSchema
from company_agents.models import SubsidiaryReport
from company_agents.metrics import metrics_collector, MetricStatus, RealTimeTracker
from .perplexity_prompt_w_subs import PERPLEXITY_RESEARCH_SUBS_PROMPT
from .perplexity_prompt_wo_subs import PERPLEXITY_RESEARCH_WO_SUBS_PROMPT
from ..subs_tools.filiales_search_agent import subsidiary_search
# Configuration du logging
logger = logging.getLogger(__name__)


# ==========================================
#   AGENT 1 : PERPLEXITY (RECHERCHE)
#   → RETOURNE DU TEXTE BRUT
# ==========================================

# Configuration Perplexity
perplexity_client = AsyncOpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)


# ==========================================
#   SÉLECTION DYNAMIQUE DU PROMPT PERPLEXITY
# ==========================================
#
# LOGIQUE DE SÉLECTION :
# 1. Le Mineur analyse l'entreprise et détermine has_filiales_only (true/false)
# 2. Le Cartographe passe has_filiales_only directement à research_subsidiaries_with_perplexity
# 3. Perplexity effectue la recherche avec la stratégie optimisée (pas de re-analyse)
#
# **STRATÉGIES DE RECHERCHE** :
# - **has_filiales_only=True** → FILIALES_UNIQUEMENT (focus filiales juridiques uniquement)
# - **has_filiales_only=False** → RECHERCHE_COMPLETE (filiales + présence commerciale: bureaux, R&D, distributeurs)
#
# **EXEMPLES** :
# - ACOEM Group (has_filiales_only=False) → Recherche complète (filiales + bureaux India/centres R&D)
# - Holding Pure (has_filiales_only=True) → Filiales juridiques uniquement
# - PME locale (has_filiales_only=False) → Recherche complète (bureaux/distributeurs)
#
# Cette approche centralise l'analyse dans le Mineur et évite la duplication.

# ==========================================
#   FONCTION OUTIL : Recherche Perplexity
# ==========================================

@function_tool
async def research_subsidiaries_with_perplexity(
    company_name: str,
    sector: Optional[str] = None,
    activities: Optional[List[str]] = None,
    website: Optional[str] = None,
    context: Optional[str] = None,
    has_filiales_only: Optional[bool] = None,  # ← NOUVEAU : has_filiales_only direct du Mineur
    enterprise_type: Optional[str] = None  # ← NOUVEAU : enterprise_type direct du Mineur
) -> Dict:
    """
    Effectue une recherche Perplexity adaptée selon le type de présence internationale.

    Args:
        company_name: Nom de l'entreprise à rechercher
        sector: Secteur d'activité principal (optionnel)
        activities: Liste des activités (optionnel)
        website: Site web officiel (optionnel)
        context: Contexte enrichi du Mineur (optionnel)
        has_filiales_only: True si uniquement filiales juridiques, False si mélange ou bureaux uniquement (optionnel)
        enterprise_type: Type d'entreprise déterminé par le Mineur (optionnel)
    
    Returns:
        dict avec:
          - research_text: Texte brut de recherche
          - citations: URLs sources trouvées
          - status: "success" ou "error"
          - duration_ms: Temps d'exécution
          - error: Message d'erreur si applicable
    """
    start_time = time.time()
    logger.info(f"🔍 Recherche Perplexity pour: {company_name}")
    
    try:
        # Vérification de la clé API
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            logger.error("❌ PERPLEXITY_API_KEY non configurée")
            return {
                "company_searched": company_name,
                "error": "API key not configured",
                "status": "error",
                "duration_ms": 0
            }
    
        # 🎯 UTILISATION DIRECTE de has_filiales_only du Mineur
        # Le Mineur a déjà analysé l'entreprise et déterminé has_filiales_only
        # - True = entreprise avec UNIQUEMENT des filiales juridiques
        # - False = mélange (filiales + bureaux/distributeurs) OU bureaux uniquement
        use_filiales_only = has_filiales_only if has_filiales_only is not None else False

        # 🎯 SÉLECTION DU PROMPT ADAPTÉ
        if use_filiales_only:
            selected_prompt = PERPLEXITY_RESEARCH_SUBS_PROMPT
            logger.info(f"🎯 Stratégie: FILIALES_UNIQUEMENT pour {company_name} (has_filiales_only=True)")
        else:
            selected_prompt = PERPLEXITY_RESEARCH_WO_SUBS_PROMPT
            logger.info(f"🎯 Stratégie: RECHERCHE_COMPLETE pour {company_name} (has_filiales_only=False)")

        # Construction de la requête optimisée
        query_parts = [f"Recherche les filiales de {company_name}"]
        
        # Ajouter le contexte métier
        if sector:
            query_parts.append(f"Secteur : {sector}")
        if activities and len(activities) > 0:
            activities_str = ", ".join(activities[:3])
            query_parts.append(f"Activités : {activities_str}")
        
        # Ajouter le contexte enrichi du Mineur
        if context:
            query_parts.append(f"Contexte : {context}")
        
        # Ajouter le site officiel
        if website:
            query_parts.append(f"Site officiel: {website}")
        
        query = ". ".join(query_parts) + "."

        # Appel Perplexity avec gestion d'erreurs
        logger.debug(f"📡 Appel API Perplexity pour: {company_name}")
        response = await perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": selected_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0,
            max_tokens=6000,  # Augmenté pour recherches approfondies
            extra_body={
                "search_context_size": "high",
                "return_citations": True,
                "return_related_questions": False,
            },
            timeout=120.0,  # 2 minutes max
        )
        
        # Vérification de la réponse
        if not response or not response.choices:
            logger.error(f"❌ Réponse vide de Perplexity pour: {company_name}")
            return {
                "company_searched": company_name,
                "error": "Empty response from Perplexity",
                "status": "error",
                "duration_ms": int((time.time() - start_time) * 1000)
            }
        
        # Récupérer le TEXTE BRUT (pas de JSON)
        research_text = response.choices[0].message.content
        
        if not research_text or len(research_text.strip()) < 50:
            logger.warning(f"⚠️ Texte de recherche trop court pour: {company_name}")
            return {
                "company_searched": company_name,
                "error": "Research text too short",
                "status": "error",
                "duration_ms": int((time.time() - start_time) * 1000)
            }
        
        # 🔧 GESTION D'ERREUR : Perplexity retourne du texte, pas du JSON
        logger.info(f"✅ Perplexity a retourné du texte brut ({len(research_text)} caractères) pour: {company_name}")
        logger.debug(f"📝 Début du texte: {research_text[:200]}...")
        
        # Extraction des citations Perplexity
        real_citations = []
        
        try:
            # Citations dans response.citations
            if hasattr(response, 'citations') and response.citations:
                for citation in response.citations:
                    url = citation.url if hasattr(citation, 'url') else str(citation)
                    title = ''
                    if hasattr(citation, 'title'):
                        title_attr = getattr(citation, 'title')
                        title = title_attr() if callable(title_attr) else title_attr
                    
                    real_citations.append({
                        "url": url,
                        "title": title or '',
                        "snippet": getattr(citation, 'snippet', ''),
                    })
            
        except Exception as citation_error:
            logger.warning(f"⚠️ Erreur extraction citations: {citation_error}")
            real_citations = []
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"✅ Recherche réussie: {len(real_citations)} citations, {len(research_text)} chars, {duration_ms}ms")
        
        return {
            "company_searched": company_name,
            "research_text": research_text,
            "citations": real_citations,
            "citation_count": len(real_citations),
            "status": "success",
            "duration_ms": duration_ms,
            "text_length": len(research_text)
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"❌ Erreur Perplexity pour {company_name}: {str(e)}")
        
        return {
            "company_searched": company_name,
            "error": str(e),
            "status": "error",
            "duration_ms": duration_ms
        }


# ==========================================
#   AGENTS CARTOGRAPHES (STRUCTURATION)
#   → PREND TEXTE BRUT, RETOURNE JSON
# ==========================================

# ==========================================
#   PROMPT POUR PIPELINE SIMPLE
# ==========================================

CARTOGRAPHE_SIMPLE_PROMPT = """
🗺️ **Cartographe Commercial** : Structure les données de filiales en JSON `SubsidiaryReport`.

# WORKFLOW OBLIGATOIRE

## Étape 1 : Appel de l'outil (CRITIQUE)
**PREMIÈRE ACTION** : Appelle `subsidiary_search` avec ces paramètres :

```python
subsidiary_search(
    company_name="Nom exact de l'entreprise",  # OBLIGATOIRE
    sector="Secteur d'activité",               # ou None
    activities=["Activité 1", "Activité 2"],   # ou None
    website="https://example.com",             # ou None
    has_filiales_only=True                     # du Mineur (true si uniquement filiales, false si mélange/bureaux)
)
```

## Étape 2 : Analyse du texte de recherche
Après l'appel, analyse le texte retourné par `subsidiary_search` qui est au format :
```
=== RECHERCHE FILIALES ET IMPLANTATIONS ===
FILIALES JURIDIQUES IDENTIFIÉES: [...]
BUREAUX ET CENTRES (PRÉSENCE COMMERCIALE): [...]
```

Continue à l'étape 3 pour structurer ces données en JSON.

## Étape 3 : Extraction des données (AVEC RÉFLEXION)

**🧠 PHASE DE RÉFLEXION INTERNE** (avant structuration JSON) :
1. Lis `research_text` en entier
2. Identifie et classe en 3 catégories :
   - **FILIALES JURIDIQUES** : entités avec personnalité juridique propre (SARL, SAS, GmbH, LLC, etc.)
   - **BUREAUX COMMERCIAUX** : bureaux de vente, agences, succursales sans personnalité juridique
   - **PARTENAIRES/DISTRIBUTEURS** : entreprises tierces (partenaires, distributeurs autorisés, franchises)
3. Pour chaque entité, évalue :
   - Pays identifiable ? → REQUIS (sinon EXCLURE)
   - Ville identifiable ? → RECOMMANDÉ (si absent, utiliser `city: null`)
   - Type de présence clair ? → Si doute, classer en `commercial_presence` type="office"
   - Source traçable dans `citations[]` ? → Au moins 1 source requise
4. N'exclus que si **pays absent** OU **aucune source**
5. PUIS passe à la structuration JSON

# RÈGLES CRITIQUES (NON-NÉGOCIABLES)

## 🔍 Distinction filiale vs présence commerciale

**FILIALE JURIDIQUE** (→ `subsidiaries[]`) :
- Entité avec personnalité juridique propre
- Forme juridique explicite : SA, SAS, SARL, GmbH, LLC, Ltd, Inc, BV, etc.
- Exemple : "Acme France SAS", "Acme GmbH", "Acme Inc."

**BUREAU COMMERCIAL** (→ `commercial_presence[]` type="office") :
- Bureau de vente, agence, succursale
- PAS de personnalité juridique propre
- Exemple : "Bureau commercial de Paris", "Acme - Agence Lyon"

**PARTENAIRE** (→ `commercial_presence[]` type="partner") :
- Entreprise tierce avec accord de partenariat
- Exemple : "Partenaire certifié XYZ", "Alliance stratégique avec ABC"

**DISTRIBUTEUR** (→ `commercial_presence[]` type="distributor") :
- Distributeur autorisé, revendeur agréé
- Exemple : "Distributeur exclusif pour l'Italie", "Authorized dealer"

**REPRÉSENTANT** (→ `commercial_presence[]` type="representative") :
- Agent commercial, représentant
- Exemple : "Agent commercial pour l'Espagne"

## 🚫 Anti-hallucination (RÈGLES ASSOUPLIES)
- **Copie exacte** : Ne JAMAIS inventer adresse, ville, téléphone, email
- **Localisation flexible** : 
  * **Pays obligatoire** : Sans pays identifiable = EXCLURE l'entité
  * **Ville recommandée** : Si absente mais pays présent = ACCEPTER avec `city: null`
- **Validation source** : Toute info doit être tracée dans le texte
- **En cas de doute** : Utilise `null`, ne suppose rien
- **Classification par défaut** : Si nature juridique incertaine → `commercial_presence` type="office", confidence: 0.5
- **Usines et centres R&D** : Toujours inclure en `commercial_presence` type="office" si mentionnés
- **Bureaux commerciaux** : Toujours inclure en `commercial_presence` type="office" si mentionnés

## 📋 Extraction filiales juridiques (CRITÈRES ASSOUPLIS)
Pour chaque filiale dans `research_text` :
- **Obligatoires** : `legal_name`, `country` (ville peut être `null`)
- **Recommandés** : `city` (si absent, utiliser `null`)
- **Optionnels** : `line1` (adresse), `postal_code`, `phone`, `email`, `activity`
- **Géocodage automatique OBLIGATOIRE** :
  * Si `city` ET `country` présents → ajouter `latitude` et `longitude` basées sur tes connaissances géographiques
  * Si SEULEMENT `country` présent (ville absente) → ajouter `latitude` et `longitude` de la capitale du pays
  * Exemples : France sans ville → Paris (48.8566, 2.3522), Germany sans ville → Berlin (52.5200, 13.4050)
- **Sources** : URLs de `citations` uniquement
  - Tier : `official` (registres, sites officiels), `financial_media` (Bloomberg, Reuters), `other`
- **Confidence** :
  - 0.85-0.95 : Site officiel, SEC, registres
  - 0.70-0.85 : Financial DB (Bloomberg, Reuters)
  - 0.60-0.70 : Presse financière (FT, WSJ)
  - 0.50-0.60 : LinkedIn, Crunchbase
- **Limites** : Max 50 filiales, max 10 sources/filiale, max 20 notes

## 🌍 Extraction présence commerciale (CRITÈRES ASSOUPLIS)

Pour chaque bureau/partenaire/distributeur dans `research_text` :

**Obligatoires** :
- `name` : Nom du bureau/partenaire/distributeur
- `type` : "office", "partner", "distributor", "representative" (si doute → "office")
- `relationship` : "owned" (bureau propre), "partnership", "authorized_distributor", "franchise" (si doute → "owned")
- `location.country` : Pays obligatoire

**Recommandés** :
- `location.city` : Si absent, utiliser `null` (pays suffit)

**Optionnels** :
- `activity` : Activité spécifique
- `location.line1` : Adresse complète
- `location.postal_code`, `phone`, `email`
- `since_year` : Année d'établissement
- `status` : "active", "inactive", "unverified"

## 🌍 Géocodage automatique OBLIGATOIRE (NOUVEAU)
**RÈGLES DE GÉOCODAGE** :
- **Si `city` ET `country` présents** → Ajouter `latitude` et `longitude` du centre de la ville
- **Si SEULEMENT `country` présent (ville absente)** → Ajouter `latitude` et `longitude` de la capitale du pays
- **Exemples avec ville** :
  * Paris, France → latitude: 48.8566, longitude: 2.3522
  * London, UK → latitude: 51.5074, longitude: -0.1278
  * New York, USA → latitude: 40.7128, longitude: -74.0060
  * Berlin, Germany → latitude: 52.5200, longitude: 13.4050
- **Exemples sans ville (pays seul)** :
  * France (ville inconnue) → Paris: latitude: 48.8566, longitude: 2.3522
  * UK (ville inconnue) → London: latitude: 51.5074, longitude: -0.1278
  * Germany (ville inconnue) → Berlin: latitude: 52.5200, longitude: 13.4050
- **Précision** : Utilise les coordonnées du centre-ville principal ou de la capitale

**Sources** : URLs de `citations` uniquement
- Tier : `official` > `financial_media` > `other`

**Confidence** :
- 0.85-0.95 : Site officiel avec page "Nos bureaux/Partenaires"
- 0.70-0.85 : Presse spécialisée, annonces officielles
- 0.60-0.70 : Bases de données professionnelles
- 0.50-0.60 : LinkedIn, mentions dans articles

**Limites** :
- Max 50 présences commerciales
- Max 10 sources/présence

## 🎯 CLASSIFICATION PAR DÉFAUT (NOUVEAU - CRITICAL)

**En cas de doute sur la nature juridique** :
- **Par défaut** : Classer en `commercial_presence[]` avec `type="office"`
- **Confidence** : 0.5 (indique incertitude)
- **Exemples** :
  * "OneProd" sans forme juridique → `commercial_presence`, type="office", confidence: 0.5
  * "JCTM Ltda" → `subsidiaries` (Ltda = forme juridique), confidence: 0.9
  * "Acoem USA" → `commercial_presence`, type="office", confidence: 0.6
  * "Benchmark Services" → `commercial_presence`, type="office", confidence: 0.5

**Principe** : Mieux vaut **inclure** avec faible confidence que **exclure** totalement.

## 🏢 Si aucune filiale ET aucune présence commerciale
Extrais info entreprise principale dans `extraction_summary.main_company_info` :
- `address`, `revenue`, `employees`, `phone`, `email` (depuis `research_text`)
- Ajoute note : "Aucune filiale ni présence commerciale trouvée après analyse exhaustive"

## ⚠️ Gestion erreurs
Si `status: "error"` dans réponse outil, retourne :
```json
{
  "company_name": "Nom",
  "parents": [],
  "subsidiaries": [],
  "commercial_presence": [],
  "methodology_notes": ["Erreur: message détaillé"],
  "extraction_summary": {
    "total_found": 0,
    "total_commercial_presence": 0,
    "methodology_used": ["Erreur Perplexity"]
  }
}
```

## 🎯 Validation géographique
Vérifie cohérence pays/ville AVANT inclusion :
- Paris (France) ≠ Paris (Texas, USA)
- London (UK) ≠ London (Ontario, Canada)
- Knoxville (Tennessee, USA) ≠ Knoxfield (Victoria, Australia)

## 📤 Format sortie (succès avec filiales + présence commerciale)

```json
{
  "company_name": "Nom du groupe",
  "parents": [],
  "subsidiaries": [
    {
      "legal_name": "Filiale SAS",
      "type": "subsidiary",
      "activity": "...",
      "headquarters": { "city": "Paris", "country": "France", ... },
      "sources": [...]
    }
  ],
  "commercial_presence": [
    {
      "name": "Bureau commercial de Lyon",
      "type": "office",
      "relationship": "owned",
      "activity": "Vente et support technique",
      "location": {
        "label": "Bureau commercial",
        "line1": "10 rue de la République",
        "city": "Lyon",
        "country": "France",
        "postal_code": "69002",
        "phone": "+33 4 XX XX XX XX",
        "email": "lyon@example.com",
        "website": "https://example.com/contact/lyon"
      },
      "confidence": 0.85,
      "sources": [
        {
          "title": "Nos bureaux - Example.com",
          "url": "https://example.com/contact/offices",
          "tier": "official",
          "accessibility": "ok"
        }
      ],
      "since_year": 2018,
      "status": "active"
    },
    {
      "name": "Distributeur autorisé ABC GmbH",
      "type": "distributor",
      "relationship": "authorized_distributor",
      "activity": "Distribution exclusive pour l'Allemagne",
      "location": {
        "city": "Berlin",
        "country": "Allemagne",
        "website": "https://abc-distributor.de"
      },
      "confidence": 0.75,
      "sources": [
        {
          "title": "Nos distributeurs - Example.com",
          "url": "https://example.com/partners/distributors",
          "tier": "official"
        }
      ],
      "since_year": 2020,
      "status": "active"
    }
  ],
  "methodology_notes": [
    "3 filiales juridiques identifiées",
    "8 bureaux commerciaux répertoriés (France, Allemagne, Espagne)",
    "5 distributeurs autorisés en Europe"
  ],
  "extraction_summary": {
    "total_found": 3,
    "total_commercial_presence": 13,
    "presence_by_type": {
      "office": 8,
      "partner": 0,
      "distributor": 5,
      "representative": 0
    },
    "countries_covered": ["France", "Allemagne", "Espagne", "Italie", "Royaume-Uni"],
    "methodology_used": ["Perplexity Sonar Pro", "Site officiel", "Pages Contact/Bureaux"]
  }
}
```

## ✅ Checklist finale (OBLIGATOIRE avant output)
- [ ] Phase de réflexion interne effectuée ?
- [ ] Outil appelé avec 5 paramètres corrects ?
- [ ] Status vérifié (success/error) ?
- [ ] **Distinction filiale juridique vs présence commerciale faite ?**
- [ ] **Si doute sur nature juridique → Classé en `commercial_presence` type="office" ?**
- [ ] Pays identifié pour chaque entité ? (ville peut être `null`)
- [ ] **Coordonnées géographiques ajoutées** si `city` ET `country` présents ?
- [ ] Sources mappées depuis `citations` uniquement ?
- [ ] Contacts copiés exactement (pas inventés) ?
- [ ] Tous champs présents dans JSON (null si manquant) ?
- [ ] **`commercial_presence[]` peuplée si bureaux/partenaires trouvés ?**
- [ ] Si texte long : traité par sections ?
- [ ] **Principe appliqué : Inclure avec faible confidence plutôt qu'exclure ?**
- [ ] **Usines et centres R&D inclus** même avec informations partielles ?
- [ ] **Bureaux commerciaux inclus** même avec informations partielles ?

## 🏭 INSTRUCTIONS SPÉCIALES POUR USINES ET CENTRES R&D
**ENTITÉS À TOUJOURS INCLURE :**
- **Usines** : manufacturing facilities, plants, production sites
- **Centres R&D** : research centers, R&D facilities, laboratories
- **Bureaux commerciaux** : offices, branches, commercial offices

**RÈGLES D'INCLUSION :**
- Si mentionné dans `research_text` avec pays identifiable → INCLURE
- Même si informations partielles (ville manquante, contacts manquants)
- Classer en `commercial_presence` type="office"
- Utiliser `confidence` 0.4-0.6 pour informations partielles
- Utiliser `confidence` 0.7-0.9 pour informations complètes

"""

# ==========================================
#   PROMPT POUR PIPELINE AVANCÉ
# ==========================================

CARTOGRAPHE_ADVANCED_PROMPT = """
🗺️ **Cartographe Commercial** : Structure les données de filiales en JSON `SubsidiaryReport`.

# WORKFLOW OBLIGATOIRE

## Étape 1 : Appel de l'outil (CRITIQUE)
**PREMIÈRE ACTION** : Appelle `research_subsidiaries_with_perplexity` avec ces paramètres :

```python
research_subsidiaries_with_perplexity(
    company_name="Nom exact de l'entreprise",  # OBLIGATOIRE
    sector="Secteur d'activité",               # ou None
    activities=["Activité 1", "Activité 2"],   # ou None
    website="https://example.com",             # ou None
    context="Contexte enrichi du Mineur",      # ou None
    has_filiales_only=True,                   # du Mineur (true si uniquement filiales, false si mélange/bureaux)
    enterprise_type="complex"                  # du Mineur (complex/simple)
)
```

## Étape 2 : Vérification du statut
Après l'appel, vérifie `status` dans la réponse :
- Si `status: "success"` → Continue à l'étape 3
- Si `status: "error"` → Retourne JSON d'erreur (voir format ci-dessous)

## Étape 3 : Extraction des données (AVEC RÉFLEXION)

**🧠 PHASE DE RÉFLEXION INTERNE** (avant structuration JSON) :
1. Lis `research_text` en entier
2. Identifie et classe en 3 catégories :
   - **FILIALES JURIDIQUES** : entités avec personnalité juridique propre (SARL, SAS, GmbH, LLC, etc.)
   - **BUREAUX COMMERCIAUX** : bureaux de vente, agences, succursales sans personnalité juridique
   - **PARTENAIRES/DISTRIBUTEURS** : entreprises tierces (partenaires, distributeurs autorisés, franchises)
3. Pour chaque entité, évalue :
   - Pays identifiable ? → REQUIS (sinon EXCLURE)
   - Ville identifiable ? → RECOMMANDÉ (si absent, utiliser `city: null`)
   - Type de présence clair ? → Si doute, classer en `commercial_presence` type="office"
   - Source traçable dans `citations[]` ? → Au moins 1 source requise
4. N'exclus que si **pays absent** OU **aucune source**
5. PUIS passe à la structuration JSON

# RÈGLES CRITIQUES (NON-NÉGOCIABLES)

## 🔍 Distinction filiale vs présence commerciale

**FILIALE JURIDIQUE** (→ `subsidiaries[]`) :
- Entité avec personnalité juridique propre
- Forme juridique explicite : SA, SAS, SARL, GmbH, LLC, Ltd, Inc, BV, etc.
- Exemple : "Acme France SAS", "Acme GmbH", "Acme Inc."

**BUREAU COMMERCIAL** (→ `commercial_presence[]` type="office") :
- Bureau de vente, agence, succursale
- PAS de personnalité juridique propre
- Exemple : "Bureau commercial de Paris", "Acme - Agence Lyon"

**PARTENAIRE** (→ `commercial_presence[]` type="partner") :
- Entreprise tierce avec accord de partenariat
- Exemple : "Partenaire certifié XYZ", "Alliance stratégique avec ABC"

**DISTRIBUTEUR** (→ `commercial_presence[]` type="distributor") :
- Distributeur autorisé, revendeur agréé
- Exemple : "Distributeur exclusif pour l'Italie", "Authorized dealer"

**REPRÉSENTANT** (→ `commercial_presence[]` type="representative") :
- Agent commercial, représentant
- Exemple : "Agent commercial pour l'Espagne"

## ✅ ENTITÉS À INCLURE OBLIGATOIREMENT
**PRINCIPE FONDAMENTAL : Mieux vaut inclure avec faible confidence que exclure totalement**

**ENTITÉS VALIDES À TOUJOURS INCLURE :**
- **Filiales juridiques** : SAS, GmbH, Inc, Ltd, SARL, LLC, BV, etc.
- **Bureaux commerciaux** : offices, branches, agences, succursales
- **Distributeurs officiels** : partners, authorized dealers, revendeurs
- **Usines et centres de production** : manufacturing facilities, plants
- **Centres R&D et laboratoires** : research centers, R&D facilities
- **Représentants commerciaux** : agents, representatives

**RÈGLE D'INCLUSION ASSOUPLIE :**
- Si entité mentionnée dans `research_text` avec pays identifiable → INCLURE
- Même si informations partielles (ville manquante, contacts manquants, etc.)
- Utiliser `confidence` faible (0.3-0.6) pour informations partielles
- Utiliser `confidence` élevée (0.7-0.9) pour informations complètes

## 🏢 RÈGLE SPÉCIALE POUR SITE OFFICIEL
**ENTITÉS MENTIONNÉES SUR SITE OFFICIEL :**
- Si entité mentionnée sur site officiel du groupe → confidence: 0.5 (50%) MINIMUM
- Même si informations partielles (ville manquante, contacts manquants)
- Toujours inclure avec confidence 0.5-0.6
- Principe : Site officiel = source fiable, donc confidence minimum garantie

**EXEMPLES :**
- "ACOEM India Manufacturing Site" mentionné sur acoem.com → confidence: 0.5
- "ACOEM R&D Center" mentionné sur acoem.com → confidence: 0.5
- "Bureau commercial" mentionné sur site officiel → confidence: 0.5

## 🚫 Anti-hallucination (RÈGLES ASSOUPLIES)
- **Copie exacte** : Ne JAMAIS inventer adresse, ville, téléphone, email
- **Localisation flexible** :
  * **Pays obligatoire** : Sans pays identifiable = EXCLURE l'entité
  * **Ville recommandée** : Si absente mais pays présent = ACCEPTER avec `city: null`
- **Validation source** : Toute info doit être tracée dans le texte
- **En cas de doute** : Utilise `null`, ne suppose rien
- **Classification par défaut** : Si nature juridique incertaine → `commercial_presence` type="office", confidence: 0.5
- **Usines et centres R&D** : Toujours inclure en `commercial_presence` type="office" si mentionnés
- **Bureaux commerciaux** : Toujours inclure en `commercial_presence` type="office" si mentionnés

## 📋 Extraction filiales juridiques (CRITÈRES ASSOUPLIS)
Pour chaque filiale dans `research_text` :
- **Obligatoires** : `legal_name`, `country` (ville peut être `null`)
- **Recommandés** : `city` (si absent, utiliser `null`)
- **Optionnels** : `line1` (adresse), `postal_code`, `phone`, `email`, `activity`
- **Géocodage automatique** : Si `city` ET `country` présents, ajouter `latitude` et `longitude` basées sur tes connaissances géographiques
- **Sources** : URLs de `citations` uniquement
  - Tier : `official` (registres, sites officiels), `financial_media` (Bloomberg, Reuters), `other`
- **Confidence** :
  - 0.85-0.95 : Site officiel, SEC, registres
  - 0.70-0.85 : Financial DB (Bloomberg, Reuters)
  - 0.60-0.70 : Presse financière (FT, WSJ)
  - 0.50-0.60 : LinkedIn, Crunchbase
- **Limites** : Max 50 filiales, max 10 sources/filiale, max 20 notes

## 🌍 Extraction présence commerciale (CRITÈRES ASSOUPLIS)

Pour chaque bureau/partenaire/distributeur dans `research_text` :

**Obligatoires** :
- `name` : Nom du bureau/partenaire/distributeur
- `type` : "office", "partner", "distributor", "representative" (si doute → "office")
- `relationship` : "owned" (bureau propre), "partnership", "authorized_distributor", "franchise" (si doute → "owned")
- `location.country` : Pays obligatoire

**Recommandés** :
- `location.city` : Si absent, utiliser `null` (pays suffit)

**Optionnels** :
- `activity` : Activité spécifique
- `location.line1` : Adresse complète
- `location.postal_code`, `phone`, `email`
- `since_year` : Année d'établissement
- `status` : "active", "inactive", "unverified"

## 🌍 Géocodage automatique OBLIGATOIRE (NOUVEAU)
**RÈGLES DE GÉOCODAGE** :
- **Si `city` ET `country` présents** → Ajouter `latitude` et `longitude` du centre de la ville
- **Si SEULEMENT `country` présent (ville absente)** → Ajouter `latitude` et `longitude` de la capitale du pays
- **Exemples avec ville** :
  * Paris, France → latitude: 48.8566, longitude: 2.3522
  * London, UK → latitude: 51.5074, longitude: -0.1278
  * New York, USA → latitude: 40.7128, longitude: -74.0060
  * Berlin, Germany → latitude: 52.5200, longitude: 13.4050
- **Exemples sans ville (pays seul)** :
  * France (ville inconnue) → Paris: latitude: 48.8566, longitude: 2.3522
  * UK (ville inconnue) → London: latitude: 51.5074, longitude: -0.1278
  * Germany (ville inconnue) → Berlin: latitude: 52.5200, longitude: 13.4050
- **Précision** : Utilise les coordonnées du centre-ville principal ou de la capitale

**Sources** : URLs de `citations` uniquement
- Tier : `official` > `financial_media` > `other`

**Confidence** :
- 0.85-0.95 : Site officiel avec page "Nos bureaux/Partenaires"
- 0.70-0.85 : Presse spécialisée, annonces officielles
- 0.60-0.70 : Bases de données professionnelles
- 0.50-0.60 : LinkedIn, mentions dans articles

**Limites** :
- Max 50 présences commerciales
- Max 10 sources/présence

## 🎯 CLASSIFICATION PAR DÉFAUT (NOUVEAU - CRITICAL)

**En cas de doute sur la nature juridique** :
- **Par défaut** : Classer en `commercial_presence[]` avec `type="office"`
- **Confidence** : 0.5 (indique incertitude)
- **Exemples** :
  * "OneProd" sans forme juridique → `commercial_presence`, type="office", confidence: 0.5
  * "JCTM Ltda" → `subsidiaries` (Ltda = forme juridique), confidence: 0.9
  * "Acoem USA" → `commercial_presence`, type="office", confidence: 0.6
  * "Benchmark Services" → `commercial_presence`, type="office", confidence: 0.5

**Principe** : Mieux vaut **inclure** avec faible confidence que **exclure** totalement.

## 🏢 Si aucune filiale ET aucune présence commerciale
Extrais info entreprise principale dans `extraction_summary.main_company_info` :
- `address`, `revenue`, `employees`, `phone`, `email` (depuis `research_text`)
- Ajoute note : "Aucune filiale ni présence commerciale trouvée après analyse exhaustive"

## ⚠️ Gestion erreurs
Si `status: "error"` dans réponse outil, retourne :
```json
{
  "company_name": "Nom",
  "parents": [],
  "subsidiaries": [],
  "commercial_presence": [],
  "methodology_notes": ["Erreur: message détaillé"],
  "extraction_summary": {
    "total_found": 0,
    "total_commercial_presence": 0,
    "methodology_used": ["Erreur Perplexity"]
  }
}
```

## 🎯 Validation géographique
Vérifie cohérence pays/ville AVANT inclusion :
- Paris (France) ≠ Paris (Texas, USA)
- London (UK) ≠ London (Ontario, Canada)
- Knoxville (Tennessee, USA) ≠ Knoxfield (Victoria, Australia)

## ✅ Checklist finale (OBLIGATOIRE avant output)
- [ ] Phase de réflexion interne effectuée ?
- [ ] Outil appelé avec paramètres corrects ?
- [ ] Status vérifié (success/error) ?
- [ ] **Distinction filiale juridique vs présence commerciale faite ?**
- [ ] **Si doute sur nature juridique → Classé en `commercial_presence` type="office" ?**
- [ ] Pays identifié pour chaque entité ? (ville peut être `null`)
- [ ] **Coordonnées géographiques ajoutées** si `city` ET `country` présents ?
- [ ] Sources mappées depuis `citations` uniquement ?
- [ ] Contacts copiés exactement (pas inventés) ?
- [ ] Tous champs présents dans JSON (null si manquant) ?
- [ ] **`commercial_presence[]` peuplée si bureaux/partenaires trouvés ?**
- [ ] Si texte long : traité par sections ?
- [ ] **Principe appliqué : Inclure avec faible confidence plutôt qu'exclure ?**
- [ ] **Usines et centres R&D inclus** même avec informations partielles ?
- [ ] **Bureaux commerciaux inclus** même avec informations partielles ?

## 🏭 INSTRUCTIONS SPÉCIALES POUR USINES ET CENTRES R&D
**ENTITÉS À TOUJOURS INCLURE :**
- **Usines** : manufacturing facilities, plants, production sites
- **Centres R&D** : research centers, R&D facilities, laboratories
- **Bureaux commerciaux** : offices, branches, commercial offices

**RÈGLES D'INCLUSION :**
- Si mentionné dans `research_text` avec pays identifiable → INCLURE
- Même si informations partielles (ville manquante, contacts manquants)
- Classer en `commercial_presence` type="office"
- Utiliser `confidence` 0.4-0.6 pour informations partielles
- Utiliser `confidence` 0.7-0.9 pour informations complètes

"""

# Configuration OpenAI GPT-4
openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

gpt4_llm = OpenAIChatCompletionsModel(
    model="gpt-4o",
    openai_client=openai_client,
)


# Schéma de sortie - selon la doc OpenAI Agents SDK
subsidiary_report_schema = AgentOutputSchema(SubsidiaryReport, strict_json_schema=True)


# ==========================================
#   AGENT CARTOGRAPHE SIMPLE
# ==========================================

cartographe_simple = Agent(
    name="🗺️ Cartographe",
    instructions=CARTOGRAPHE_SIMPLE_PROMPT,
    tools=[subsidiary_search],  # Outil de recherche simple
    output_type=subsidiary_report_schema,
    model=gpt4_llm,
)


# ==========================================
#   AGENT CARTOGRAPHE AVANCÉ
# ==========================================

cartographe_advanced = Agent(
    name="🗺️ Cartographe",
    instructions=CARTOGRAPHE_ADVANCED_PROMPT,
    tools=[research_subsidiaries_with_perplexity],  # Outil de recherche avancé
    output_type=subsidiary_report_schema,
    model=gpt4_llm,
)


# Exportation pour rétrocompatibilité
subsidiary_extractor = cartographe_advanced  # Par défaut, utilise le pipeline avancé


# ==========================================
#   WRAPPER AVEC MÉTRIQUES DE PERFORMANCE
# ==========================================

async def run_cartographe_with_metrics(
    company_context: Any,
    session_id: str = None,
    deep_search: bool = False
) -> Dict[str, Any]:
    """
    Exécute l'agent Cartographe avec métriques de performance en temps réel.

    Args:
        company_context: Contexte de l'entreprise (dict avec company_name, sector, activities) ou string
        session_id: ID de session pour le suivi temps réel
        deep_search: Si True, utilise le pipeline avancé (Perplexity). Si False, utilise le pipeline simple (gpt-4o-search)

    Returns:
        Dict contenant les résultats et métriques de performance
    """
    # Sélectionner l'agent selon deep_search
    selected_agent = cartographe_advanced if deep_search else cartographe_simple
    pipeline_name = "Pipeline Avancé" if deep_search else "Pipeline Simple"

    logger.info(f"🎯 Sélection pipeline: {pipeline_name}")

    # Gérer à la fois dict et string pour rétrocompatibilité
    if isinstance(company_context, dict):
        company_name = company_context.get("company_name", str(company_context))
        input_data = json.dumps(company_context, ensure_ascii=False)
    else:
        company_name = str(company_context)
        input_data = company_name

    # Démarrer les métriques
    agent_name = "🗺️ Cartographe"
    agent_metrics = metrics_collector.start_agent(agent_name, session_id or "default")
    
    # Démarrer le suivi temps réel
    from status.manager import status_manager
    real_time_tracker = RealTimeTracker(status_manager)
    
    try:
        # Démarrer le suivi temps réel en arrière-plan
        tracking_task = asyncio.create_task(
            real_time_tracker.track_agent_realtime("🗺️ Cartographe", session_id or "default", agent_metrics)
        )
        
        # Étape 1: Initialisation
        init_step = agent_metrics.add_step("Initialisation")
        logger.info(f"🗺️ Début de cartographie pour: {company_name} ({pipeline_name})")
        init_step.finish(MetricStatus.COMPLETED, {
            "company_name": company_name,
            "pipeline": pipeline_name,
            "deep_search": deep_search
        })

        # Étape 2: Recherche (nom adapté selon le pipeline)
        research_name = "Recherche approfondie" if deep_search else "Recherche rapide"
        research_step = agent_metrics.add_step(research_name)
        research_step.status = MetricStatus.TOOL_CALLING

        # Exécution de l'agent avec suivi des étapes
        from agents import Runner
        result = await Runner.run(
            selected_agent,  # ← Utiliser l'agent sélectionné selon deep_search
            input_data,
            max_turns=3
        )

        research_step.finish(MetricStatus.COMPLETED, {
            "research_completed": True,
            "pipeline_used": pipeline_name
        })
        
        # Étape 3: Structuration des données
        struct_step = agent_metrics.add_step("Structuration des données")
        struct_step.status = MetricStatus.PROCESSING
        
        # Extraction des métriques - selon la doc OpenAI Agents SDK
        if hasattr(result, 'final_output') and result.final_output:
            output_data = result.final_output
            
            # Selon la doc OpenAI Agents SDK, final_output peut être :
            # 1. Un objet Pydantic directement
            # 2. Un dictionnaire
            # 3. Une chaîne JSON
            
            if hasattr(output_data, 'model_dump'):
                # Cas 1: Objet Pydantic (SubsidiaryReport)
                try:
                    output_data = output_data.model_dump()
                    logger.info(f"✅ Objet Pydantic converti en dictionnaire pour {company_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible de convertir l'objet Pydantic pour {company_name}: {e}")
                    output_data = None
            elif isinstance(output_data, dict):
                # Cas 2: Dictionnaire déjà structuré
                logger.info(f"✅ Données déjà en format dictionnaire pour {company_name}")
                
                # Validation de taille pour éviter les JSON trop volumineux
                json_str = json.dumps(output_data, ensure_ascii=False)
                if len(json_str) > 10000:  # Limite à 10KB
                    logger.warning(f"⚠️ JSON trop volumineux ({len(json_str)} caractères) pour {company_name}, limitation appliquée")
                    # Limiter le nombre de filiales
                    if 'subsidiaries' in output_data and len(output_data['subsidiaries']) > 10:
                        output_data['subsidiaries'] = output_data['subsidiaries'][:10]
                        output_data['methodology_notes'] = (output_data.get('methodology_notes', []) or [])[:5]
                        logger.info(f"✅ Limitation appliquée: 10 filiales max pour {company_name}")
            elif isinstance(output_data, str):
                # Cas 3: Chaîne JSON à parser
                try:
                    output_data = json.loads(output_data)
                    logger.info(f"✅ JSON parsé en dictionnaire pour {company_name}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Erreur JSON pour {company_name}: {e}")
                    logger.error(f"📝 Contenu reçu: {output_data[:500]}...")
                    # 🔧 FALLBACK : Créer un objet vide en cas d'échec JSON
                    output_data = {
                        "company_name": company_name,
                        "subsidiaries": [],
                        "commercial_presence": [],
                        "methodology_notes": [f"Erreur de parsing JSON: {str(e)}"]
                    }
                    logger.warning(f"⚠️ Fallback appliqué pour {company_name}")
            else:
                logger.warning(f"⚠️ Format de sortie inattendu pour {company_name}: {type(output_data)}")
                output_data = None
            
            if isinstance(output_data, dict):
                subsidiaries_count = len(output_data.get('subsidiaries', []))
                commercial_presence_count = len(output_data.get('commercial_presence', []))
                methodology_notes = output_data.get('methodology_notes', [])
                
                # 🔧 FIX: Mapper les citations depuis les sources des entités
                all_sources = []
                for sub in output_data.get('subsidiaries', []):
                    all_sources.extend(sub.get('sources', []))
                for pres in output_data.get('commercial_presence', []):
                    all_sources.extend(pres.get('sources', []))
                
                # Compter les URLs uniques
                unique_urls = set([s.get('url') for s in all_sources if s.get('url')])
                citations_count = len(unique_urls)
                
                logger.info(f"📊 Cartographie {company_name}: {subsidiaries_count} filiales, {commercial_presence_count} présences commerciales, {citations_count} sources uniques")
                
                # Détection d'erreurs dans les notes
                has_errors = any('erreur' in note.lower() or 'error' in note.lower() 
                               for note in (methodology_notes or []))
                
                # Calcul du score de confiance amélioré
                total_entities = subsidiaries_count + commercial_presence_count
                if total_entities > 0 and not has_errors:
                    confidence_score = 0.9
                elif total_entities > 0 and has_errors:
                    confidence_score = 0.6
                else:
                    confidence_score = 0.3
                
                # Métriques de qualité enrichies
                agent_metrics.quality_metrics = {
                    "subsidiaries_found": subsidiaries_count,
                    "commercial_presence_found": commercial_presence_count,
                    "total_entities": total_entities,
                    "citations_count": citations_count,
                    "confidence_score": confidence_score,
                    "has_errors": has_errors,
                    "methodology_notes_count": len(methodology_notes) if methodology_notes else 0
                }
                
                # Métriques de performance
                agent_metrics.performance_metrics = {
                    "total_duration_ms": int((time.time() - agent_metrics.start_time) * 1000),
                    "steps_completed": len(agent_metrics.steps),
                    "success_rate": 1.0 if not has_errors else 0.0
                }
                
                struct_step.finish(MetricStatus.COMPLETED, {
                    "subsidiaries_count": subsidiaries_count,
                    "citations_count": citations_count,
                    "confidence_score": confidence_score
                })
                
                # Finalisation
                final_step = agent_metrics.add_step("Finalisation")
                final_step.finish(MetricStatus.COMPLETED)
                
                # Terminer les métriques
                agent_metrics.finish(MetricStatus.COMPLETED if not has_errors else MetricStatus.ERROR)
                
                # Annuler le suivi temps réel et envoyer les métriques finales
                tracking_task.cancel()
                try:
                    await tracking_task
                except asyncio.CancelledError:
                    pass
                
                await real_time_tracker.send_final_metrics("🗺️ Cartographe", session_id or "default", agent_metrics)
                
                logger.info(f"✅ Cartographie terminée pour {company_name}: {subsidiaries_count} filiales, {agent_metrics.total_duration_ms}ms")
                
                return {
                    "result": output_data,
                    "status": "success" if not has_errors else "error",
                    "duration_ms": agent_metrics.total_duration_ms,
                    "subsidiaries_count": subsidiaries_count,
                    "has_errors": has_errors,
                    "methodology_notes": methodology_notes or [],
                    "metrics": agent_metrics.to_dict()
                }
            else:
                # Cas où final_output n'est pas un dict ou est None après parsing
                struct_step.finish(MetricStatus.COMPLETED, {"output_type": type(output_data).__name__ if output_data else "None"})
                
                # Finalisation
                final_step = agent_metrics.add_step("Finalisation")
                final_step.finish(MetricStatus.COMPLETED)
                
                # Terminer les métriques avec succès (on a un résultat, même si format inattendu)
                agent_metrics.finish(MetricStatus.COMPLETED)
                
                # Annuler le suivi temps réel et envoyer les métriques finales
                tracking_task.cancel()
                try:
                    await tracking_task
                except asyncio.CancelledError:
                    pass
                
                await real_time_tracker.send_final_metrics("🗺️ Cartographe", session_id or "default", agent_metrics)
                
                if output_data is None:
                    logger.info(f"ℹ️ Aucune donnée parsée pour {company_name} - format OpenAI Agents SDK standard")
                else:
                    logger.warning(f"⚠️ Format de sortie inattendu pour {company_name}: {type(output_data).__name__}")
                
                return {
                    "result": result.final_output,
                    "status": "success",
                    "duration_ms": agent_metrics.total_duration_ms,
                    "subsidiaries_count": 0,
                    "has_errors": False,
                    "methodology_notes": ["Format de sortie traité avec succès"],
                    "metrics": agent_metrics.to_dict()
                }
        else:
            struct_step.finish(MetricStatus.ERROR, {"error": "Pas de résultat final"})
            agent_metrics.finish(MetricStatus.ERROR, "Pas de résultat final")
            
            # Annuler le suivi temps réel et envoyer les métriques finales
            tracking_task.cancel()
            try:
                await tracking_task
            except asyncio.CancelledError:
                pass
            
            await real_time_tracker.send_final_metrics("🗺️ Cartographe", session_id or "default", agent_metrics)
            
            logger.error(f"❌ Pas de résultat final pour {company_name}")
            return {
                "result": None,
                "status": "error",
                "duration_ms": agent_metrics.total_duration_ms,
                "subsidiaries_count": 0,
                "has_errors": True,
                "methodology_notes": ["Pas de résultat final"],
                "metrics": agent_metrics.to_dict()
            }
            
    except Exception as e:
        # Marquer l'étape en erreur
        current_step = agent_metrics.get_current_step()
        if current_step:
            current_step.finish(MetricStatus.ERROR, {"error": str(e)})
        
        agent_metrics.finish(MetricStatus.ERROR, str(e))
        
        # Annuler le suivi temps réel et envoyer les métriques finales
        tracking_task.cancel()
        try:
            await tracking_task
        except asyncio.CancelledError:
            pass
        
        await real_time_tracker.send_final_metrics("🗺️ Cartographe", session_id or "default", agent_metrics)
        
        logger.error(f"❌ Erreur lors de la cartographie pour {company_name}: {str(e)}", exc_info=True)
        
        return {
            "result": None,
            "status": "error",
            "duration_ms": agent_metrics.total_duration_ms,
            "subsidiaries_count": 0,
            "has_errors": True,
            "methodology_notes": [f"Erreur d'exécution: {str(e)}"],
            "error": str(e),
            "metrics": agent_metrics.to_dict()
        }