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
from ..subs_tools.filiales_search_agent_optimized import subsidiary_search
# Configuration du logging
logger = logging.getLogger(__name__)


# ==========================================
#   AGENT 1 : PERPLEXITY (RECHERCHE)
#   → RETOURNE DU TEXTE BRUT
# ==========================================

# Configuration Perplexity (initialisation paresseuse)
perplexity_client = None

def get_perplexity_client():
    """Initialise le client Perplexity de manière paresseuse."""
    global perplexity_client
    if perplexity_client is None:
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            logger.warning("⚠️ PERPLEXITY_API_KEY non définie - le client Perplexity ne sera pas initialisé")
            return None
        perplexity_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai",
        )
    return perplexity_client


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

        # Vérifier que le client Perplexity est disponible
        client_instance = get_perplexity_client()
        if not client_instance:
            logger.error("❌ Client Perplexity non initialisé - PERPLEXITY_API_KEY manquante")
            return "Erreur: Client Perplexity non configuré. Veuillez définir PERPLEXITY_API_KEY."

        # Appel Perplexity avec gestion d'erreurs
        logger.debug(f"📡 Appel API Perplexity pour: {company_name}")
        response = await client_instance.chat.completions.create(
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
        
        # Capturer les tokens utilisés par Perplexity
        if hasattr(response, 'usage') and response.usage:
            logger.info(
                f"💰 [Tool] Tokens research_subsidiaries_with_perplexity: "
                f"{response.usage.prompt_tokens} in + {response.usage.completion_tokens} out = "
                f"{response.usage.total_tokens} total (modèle: sonar-pro)"
            )
            
            # Envoyer au ToolTokensTracker
            try:
                from company_agents.metrics.tool_tokens_tracker import ToolTokensTracker
                # Utiliser un session_id par défaut si pas fourni
                session_id = getattr(research_subsidiaries_with_perplexity, '_session_id', 'default-session')
                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name='research_subsidiaries_with_perplexity',
                    model='sonar-pro',
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
                logger.info("🔧 Tokens envoyés au tracker pour research_subsidiaries_with_perplexity")
            except ImportError:
                logger.debug("ToolTokensTracker non disponible")
            except Exception as e:
                logger.warning(f"⚠️ Erreur envoi tokens research_subsidiaries_with_perplexity: {e}")
        
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

# WORKFLOW

## 1. Appel de l'outil (OBLIGATOIRE)
Appelle `subsidiary_search` avec :
```python
subsidiary_search(
    company_name="Nom exact",
    sector="Secteur ou None",
    activities=["Act1", "Act2"] ou None,
    website="https://... ou None",
    has_filiales_only=True/False  # du Mineur
)
```

## 2. Analyse du texte
Le texte retourné est structuré :
```
=== RECHERCHE FILIALES ET IMPLANTATIONS ===
FILIALES JURIDIQUES IDENTIFIÉES: [...]
BUREAUX ET CENTRES (PRÉSENCE COMMERCIALE): [...]
```

Identifie et classe en 3 catégories :
- **FILIALES JURIDIQUES** : Entités avec forme juridique (SARL, SAS, GmbH, LLC, Ltd, Inc, BV)
- **BUREAUX COMMERCIAUX** : Bureaux, agences, succursales (PAS de personnalité juridique)
- **PARTENAIRES/DISTRIBUTEURS** : Entreprises tierces (partenaires, distributeurs, franchises)

**Critères d'inclusion** :
- Pays identifiable → REQUIS (sinon EXCLURE)
- Ville recommandée (si absent → `city: null`)
- Si doute sur nature juridique → `commercial_presence` type="office", confidence: 0.5
- Au moins 1 source requise

## 3. Structuration JSON

# RÈGLES CRITIQUES

## 🔍 Classification

**FILIALE JURIDIQUE** → `subsidiaries[]` :
- Forme juridique explicite : SA, SAS, SARL, GmbH, LLC, Ltd, Inc, BV
- Ex: "Acme France SAS", "Acme GmbH"
- **RÈGLE SPÉCIALE** : Si source mentionne explicitement "filiale", "subsidiary", "entité juridique", "legal entity" → C'EST UNE FILIALE même sans forme juridique visible
  - Ex: "ouvre deux filiales en Allemagne et en Inde" → classer en `subsidiaries[]`
  - Ex: "subsidiary in Munich" → classer en `subsidiaries[]`

**PRÉSENCE COMMERCIALE** → `commercial_presence[]` :
- **office** : Bureau de vente, agence, succursale, usine, centre R&D
- **partner** : Partenaire certifié, alliance stratégique
- **distributor** : Distributeur autorisé, revendeur agréé
- **representative** : Agent commercial, représentant

**Si doute** → `commercial_presence` type="office", confidence: 0.5

**Principe** : **Inclure avec faible confidence > Exclure totalement**

## 🚫 Anti-hallucination
- Ne JAMAIS inventer adresse, ville, téléphone, email
- **Pays obligatoire** : Sans pays = EXCLURE
- **Ville recommandée** : Si absent + pays présent = ACCEPTER avec `city: null`
- Toute info tracée dans texte + `citations[]`
- En cas de doute : `null` (ne suppose rien)

## 📋 Extraction filiales juridiques

**Obligatoires** : `legal_name`, `country`
**Recommandés** : `city` (ou `null`)
**Optionnels** : `line1`, `postal_code`, `phone`, `email`, `activity`

**Géocodage automatique OBLIGATOIRE** :
- Si `city` + `country` → `latitude`/`longitude` du centre-ville
- Si SEULEMENT `country` → `latitude`/`longitude` de la capitale
- Ex: Paris (48.8566, 2.3522), London (51.5074, -0.1278), Berlin (52.5200, 13.4050)

**Sources** : URLs de `citations` uniquement
- Tier : `official` (registres, sites) > `financial_media` (Bloomberg, Reuters) > `other`

**Confidence** :
- 0.85-0.95 : Site officiel, SEC, registres
- 0.70-0.85 : Financial DB
- 0.60-0.70 : Presse financière
- 0.50-0.60 : LinkedIn, Crunchbase

**Limites** : Max 50 filiales, max 10 sources/filiale, max 20 notes

## 🌍 Extraction présence commerciale

**Obligatoires** : `name`, `type`, `relationship`, `location.country`
**Recommandés** : `location.city` (ou `null`)
**Optionnels** : `activity`, `line1`, `postal_code`, `phone`, `email`, `since_year`, `status`

**Géocodage** : Même règles que filiales (ville + pays → coordonnées)

**Entités à TOUJOURS inclure** (si pays identifiable) :
- Usines, manufacturing facilities, production sites
- Centres R&D, research centers, laboratories
- Bureaux commerciaux, offices, branches
- Partenaires et distributeurs officiels

**Confidence** :
- 0.85-0.95 : Site officiel "Nos bureaux/Partenaires"
- 0.70-0.85 : Presse spécialisée, annonces officielles
- 0.60-0.70 : Bases professionnelles
- 0.50-0.60 : LinkedIn, mentions
- 0.40-0.50 : Informations partielles (ville manquante)

**Limites** : Max 50 présences, max 10 sources/présence

## 🏢 Si aucune entité trouvée
Extrais info entreprise principale dans `extraction_summary.main_company_info` :
- `address`, `revenue`, `employees`, `phone`, `email`
- Note : "Aucune filiale ni présence commerciale trouvée après analyse exhaustive"

## ⚠️ Gestion erreurs
Si `status: "error"`, retourne :
```json
{
  "company_name": "Nom",
  "parents": [],
  "subsidiaries": [],
  "commercial_presence": [],
  "methodology_notes": ["Erreur: message"],
  "extraction_summary": {
    "total_found": 0,
    "total_commercial_presence": 0,
    "methodology_used": ["Erreur"]
  }
}
```

## 🎯 Validation géographique
Vérifie cohérence pays/ville : Paris (France) ≠ Paris (Texas, USA)

## 📤 Format sortie

```json
{
  "company_name": "Groupe",
  "parents": [],
  "subsidiaries": [
    {
      "legal_name": "Filiale SAS",
      "type": "subsidiary",
      "activity": "...",
      "headquarters": {
        "city": "Paris",
        "country": "France",
        "latitude": 48.8566,
        "longitude": 2.3522
      },
      "sources": [{"title": "...", "url": "...", "tier": "official"}],
      "confidence": 0.9
    }
  ],
  "commercial_presence": [
    {
      "name": "Bureau Lyon",
      "type": "office",
      "relationship": "owned",
      "location": {
        "city": "Lyon",
        "country": "France",
        "latitude": 45.7640,
        "longitude": 4.8357
      },
      "confidence": 0.8,
      "sources": [{"title": "...", "url": "...", "tier": "official"}],
      "status": "active"
    }
  ],
  "methodology_notes": ["3 filiales", "8 bureaux"],
  "extraction_summary": {
    "total_found": 3,
    "total_commercial_presence": 8,
    "presence_by_type": {"office": 6, "distributor": 2},
    "countries_covered": ["France", "Allemagne"],
    "methodology_used": ["Site officiel", "gpt-4o-search"]
  }
}
```

## ✅ Checklist finale
- [ ] Outil appelé avec paramètres corrects ?
- [ ] Status success/error vérifié ?
- [ ] Distinction filiale juridique vs présence commerciale faite ?
- [ ] Si doute → `commercial_presence` type="office", confidence: 0.5 ?
- [ ] Pays identifié pour chaque entité ?
- [ ] Coordonnées géographiques ajoutées si ville ou pays ?
- [ ] Sources mappées depuis `citations` uniquement ?
- [ ] Contacts copiés exactement (pas inventés) ?
- [ ] Principe appliqué : Inclure avec faible confidence > Exclure ?

"""

# ==========================================
#   PROMPT POUR PIPELINE AVANCÉ
# ==========================================

CARTOGRAPHE_ADVANCED_PROMPT = """
🗺️ **Cartographe Commercial** : Structure les données de filiales en JSON `SubsidiaryReport`.

# WORKFLOW

## 1. Appel de l'outil (OBLIGATOIRE)
Appelle `research_subsidiaries_with_perplexity` avec :
```python
research_subsidiaries_with_perplexity(
    company_name="Nom exact",
    sector="Secteur ou None",
    activities=["Act1", "Act2"] ou None,
    website="https://... ou None",
    context="Contexte Mineur ou None",
    has_filiales_only=True/False,
    enterprise_type="complex/simple"
)
```

## 2. Vérification statut
- `status: "success"` → Continue étape 3
- `status: "error"` → Retourne JSON d'erreur

## 3. Analyse et structuration
Identifie et classe :
- **FILIALES JURIDIQUES** : Forme juridique (SARL, SAS, GmbH, LLC, Ltd, Inc, BV)
- **BUREAUX COMMERCIAUX** : Bureaux, agences, succursales (PAS de personnalité juridique)
- **PARTENAIRES/DISTRIBUTEURS** : Entreprises tierces

Critères : Pays REQUIS, ville recommandée, source requise, si doute → `commercial_presence` type="office"

# RÈGLES CRITIQUES

## 🔍 Classification

**FILIALE JURIDIQUE** → `subsidiaries[]` :
- Forme juridique explicite (SA, SAS, SARL, GmbH, LLC, Ltd, Inc, BV)
- **RÈGLE SPÉCIALE** : Si source mentionne explicitement "filiale", "subsidiary", "entité juridique", "legal entity" → C'EST UNE FILIALE même sans forme juridique visible
  - Ex: "ouvre deux filiales en Allemagne et en Inde" → classer en `subsidiaries[]`
  - Ex: "subsidiary in Munich" → classer en `subsidiaries[]`

**PRÉSENCE COMMERCIALE** → `commercial_presence[]` :
- **office** : Bureau, agence, succursale, usine, centre R&D
- **partner** : Partenaire certifié
- **distributor** : Distributeur autorisé
- **representative** : Agent commercial

**Si doute** → `commercial_presence` type="office", confidence: 0.5

**Principe** : **Inclure avec faible confidence > Exclure totalement**

## ✅ ENTITÉS À INCLURE OBLIGATOIREMENT
**PRINCIPE FONDAMENTAL : Mieux vaut inclure avec faible confidence que exclure totalement**

**ENTITÉS VALIDES À TOUJOURS INCLURE :**
- **Filiales juridiques** : SAS, GmbH, Inc, Ltd, SARL, LLC, BV
- **Bureaux commerciaux** : offices, branches, agences, succursales
- **Distributeurs officiels** : partners, authorized dealers, revendeurs
- **Usines et centres de production** : manufacturing facilities, plants
- **Centres R&D et laboratoires** : research centers, R&D facilities
- **Représentants commerciaux** : agents, representatives

**RÈGLE D'INCLUSION ASSOUPLIE :**
- Entité mentionnée avec pays identifiable → INCLURE
- Même si info partielles (ville manquante, contacts manquants)
- Confidence faible (0.3-0.6) pour info partielles
- Confidence élevée (0.7-0.9) pour info complètes

## 🏢 RÈGLE SPÉCIALE POUR SITE OFFICIEL
**ENTITÉS MENTIONNÉES SUR SITE OFFICIEL :**
- Si entité mentionnée sur site officiel → **confidence: 0.5 (50%) MINIMUM**
- Même si info partielles (ville manquante, contacts manquants)
- Toujours inclure avec confidence 0.5-0.6
- Principe : Site officiel = source fiable → confidence minimum garantie

**EXEMPLES :**
- "ACOEM India Manufacturing Site" sur acoem.com → confidence: 0.5
- "ACOEM R&D Center" sur acoem.com → confidence: 0.5
- "Bureau commercial" sur site officiel → confidence: 0.5

## 🚫 Anti-hallucination
- Ne JAMAIS inventer adresse, ville, téléphone, email
- **Pays obligatoire** : Sans pays = EXCLURE
- **Ville recommandée** : Si absent + pays présent = ACCEPTER avec `city: null`
- Toute info tracée dans texte + `citations[]`
- En cas de doute : `null`

## 📋 Extraction filiales juridiques

**Obligatoires** : `legal_name`, `country`
**Recommandés** : `city` (ou `null`)
**Optionnels** : `line1`, `postal_code`, `phone`, `email`, `activity`

**Géocodage automatique** :
- Si `city` + `country` → `latitude`/`longitude` centre-ville
- Si SEULEMENT `country` → `latitude`/`longitude` capitale
- Ex: Paris (48.8566, 2.3522), London (51.5074, -0.1278), Berlin (52.5200, 13.4050)

**Sources** : URLs de `citations` - Tier : `official` > `financial_media` > `other`

**Confidence** :
- 0.85-0.95 : Site officiel, SEC, registres
- 0.70-0.85 : Financial DB
- 0.60-0.70 : Presse financière
- 0.50-0.60 : LinkedIn, Crunchbase

**Limites** : Max 50 filiales, max 10 sources/filiale, max 20 notes

## 🌍 Extraction présence commerciale

**Obligatoires** : `name`, `type`, `relationship`, `location.country`
**Recommandés** : `location.city` (ou `null`)
**Optionnels** : `activity`, `line1`, `postal_code`, `phone`, `email`, `since_year`, `status`

**Géocodage** : Même règles que filiales

**Confidence** :
- 0.85-0.95 : Site officiel "Nos bureaux/Partenaires"
- 0.70-0.85 : Presse spécialisée, annonces officielles
- 0.60-0.70 : Bases professionnelles
- 0.50-0.60 : LinkedIn, mentions

**Limites** : Max 50 présences, max 10 sources/présence

## 🏭 INSTRUCTIONS SPÉCIALES POUR USINES ET CENTRES R&D
**ENTITÉS À TOUJOURS INCLURE :**
- **Usines** : manufacturing facilities, plants, production sites
- **Centres R&D** : research centers, R&D facilities, laboratories
- **Bureaux commerciaux** : offices, branches, commercial offices

**RÈGLES D'INCLUSION :**
- Si mentionné avec pays identifiable → INCLURE
- Même si info partielles (ville manquante, contacts manquants)
- Classer en `commercial_presence` type="office"
- **Confidence 0.4-0.6** pour info partielles
- **Confidence 0.7-0.9** pour info complètes

## 🏢 Si aucune entité trouvée
Extrais info entreprise principale dans `extraction_summary.main_company_info` :
- `address`, `revenue`, `employees`, `phone`, `email`
- Note : "Aucune filiale ni présence commerciale trouvée"

## ⚠️ Gestion erreurs
Si `status: "error"` :
```json
{
  "company_name": "Nom",
  "parents": [],
  "subsidiaries": [],
  "commercial_presence": [],
  "methodology_notes": ["Erreur: message"],
  "extraction_summary": {"total_found": 0, "total_commercial_presence": 0, "methodology_used": ["Erreur"]}
}
```

## 🎯 Validation géographique
Vérifie cohérence pays/ville : Paris (France) ≠ Paris (Texas, USA)

## ✅ Checklist finale
- [ ] Outil appelé avec paramètres corrects ?
- [ ] Status vérifié ?
- [ ] Distinction filiale vs présence faite ?
- [ ] Si doute → `commercial_presence` type="office", confidence: 0.5 ?
- [ ] Pays identifié pour chaque entité ?
- [ ] Coordonnées géographiques ajoutées ?
- [ ] Sources mappées depuis `citations` ?
- [ ] Contacts copiés exactement (pas inventés) ?
- [ ] Principe appliqué : Inclure avec faible confidence > Exclure ?
- [ ] Entités site officiel avec confidence minimum 0.5 ?
- [ ] Usines et centres R&D inclus ?

"""

# Configuration OpenAI GPT-4 (initialisation paresseuse)
openai_client = None

def get_openai_client():
    """Initialise le client OpenAI de manière paresseuse."""
    global openai_client
    if openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY non définie - le client OpenAI ne sera pas initialisé")
            return None
        openai_client = AsyncOpenAI(api_key=api_key)
    return openai_client

# Initialisation paresseuse du modèle GPT-4
gpt4_llm = None

def get_gpt4_llm():
    """Initialise le modèle GPT-4 de manière paresseuse."""
    global gpt4_llm
    if gpt4_llm is None:
        client = get_openai_client()
        if not client:
            return None
        gpt4_llm = OpenAIChatCompletionsModel(
            model="gpt-4o",
            openai_client=client,
        )
    return gpt4_llm


# Schéma de sortie - selon la doc OpenAI Agents SDK
subsidiary_report_schema = AgentOutputSchema(SubsidiaryReport, strict_json_schema=True)


# ==========================================
#   AGENT CARTOGRAPHE SIMPLE
# ==========================================

# Initialisation paresseuse des agents
cartographe_simple = None
cartographe_advanced = None

def get_cartographe_simple():
    """Initialise l'agent cartographe simple de manière paresseuse."""
    global cartographe_simple
    if cartographe_simple is None:
        llm = get_gpt4_llm()
        if not llm:
            return None
        cartographe_simple = Agent(
            name="🗺️ Cartographe",
            instructions=CARTOGRAPHE_SIMPLE_PROMPT,
            tools=[subsidiary_search],  # Outil de recherche simple
            output_type=subsidiary_report_schema,
            model=llm,
        )
    return cartographe_simple


# ==========================================
#   AGENT CARTOGRAPHE AVANCÉ
# ==========================================

def get_cartographe_advanced():
    """Initialise l'agent cartographe avancé de manière paresseuse."""
    global cartographe_advanced
    if cartographe_advanced is None:
        llm = get_gpt4_llm()
        if not llm:
            return None
    cartographe_advanced = Agent(
        name="🗺️ Cartographe",
        instructions=CARTOGRAPHE_ADVANCED_PROMPT,
        tools=[research_subsidiaries_with_perplexity],  # Outil de recherche avancé
        output_type=subsidiary_report_schema,
                model=llm,
            )
    return cartographe_advanced


# Exportation pour rétrocompatibilité (fonction paresseuse)
def get_subsidiary_extractor():
    """Retourne l'agent cartographe avancé de manière paresseuse."""
    agent = get_cartographe_advanced()
    if agent is None:
        # Fallback vers l'agent simple si l'avancé n'est pas disponible
        logger.warning("⚠️ Agent avancé non disponible, utilisation de l'agent simple")
        return get_cartographe_simple()
    return agent

# Alias pour rétrocompatibilité
subsidiary_extractor = get_subsidiary_extractor


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
    if deep_search:
        selected_agent = get_cartographe_advanced()
        pipeline_name = "Pipeline Avancé"
    else:
        selected_agent = get_cartographe_simple()
        pipeline_name = "Pipeline Simple"
    
    # Vérifier que l'agent est disponible
    if selected_agent is None:
        logger.error("❌ Aucun agent disponible - vérifiez la configuration OpenAI")
        return {
            "status": "error",
            "error": "Agent non disponible - vérifiez la configuration OpenAI",
            "pipeline_name": pipeline_name
        }

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

        # Capturer les tokens utilisés si disponibles (selon la doc OpenAI)
        if hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
            try:
                usage = result.context_wrapper.usage

                # Récupérer le nom du modèle (pas l'objet)
                model_obj = getattr(selected_agent, 'model', None)

                # Essayer plusieurs méthodes pour extraire le nom du modèle
                model_name = 'gpt-4o' if deep_search else 'gpt-4o-search-preview'  # Fallback
                if model_obj:
                    # Méthode 1 : Attribut 'name'
                    if hasattr(model_obj, 'name'):
                        model_name = model_obj.name
                    # Méthode 2 : Attribut 'model'
                    elif hasattr(model_obj, 'model'):
                        model_name = model_obj.model
                    # Méthode 3 : Attribut 'model_name'
                    elif hasattr(model_obj, 'model_name'):
                        model_name = model_obj.model_name
                    # Méthode 4 : Pour OpenAI models, chercher dans config
                    elif hasattr(model_obj, '_model'):
                        model_name = model_obj._model
                    # Méthode 5 : Convertir en string et extraire
                    else:
                        str_repr = str(model_obj)
                        if 'model=' in str_repr:
                            model_name = str_repr.split('model=')[1].split(',')[0].strip().strip("'\"")
                        else:
                            model_name = str_repr

                # Vérifier que usage existe et a les attributs nécessaires
                if usage and hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                    token_info = {
                        "model": model_name,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "total_tokens": getattr(usage, 'total_tokens', usage.input_tokens + usage.output_tokens)
                    }
                else:
                    # Fallback si usage n'a pas les attributs attendus
                    token_info = {
                        "model": model_name,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    }

                # Stocker dans les métriques de performance
                agent_metrics.performance_metrics["tokens"] = token_info

                logger.info(
                    f"💰 Tokens capturés pour {agent_name}: "
                    f"{token_info['input_tokens']} in + {token_info['output_tokens']} out = "
                    f"{token_info['total_tokens']} total (modèle: {model_name}, pipeline: {pipeline_name})"
                )
            except Exception as e:
                logger.warning(f"⚠️ Impossible de capturer les tokens pour {agent_name}: {e}")
        else:
            logger.warning(f"⚠️ Pas de données d'usage disponibles pour {agent_name} ({pipeline_name})")

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
                
                # Métriques de performance (MISE À JOUR au lieu d'écrasement pour garder "tokens")
                agent_metrics.performance_metrics.update({
                    "total_duration_ms": int((time.time() - agent_metrics.start_time) * 1000),
                    "steps_completed": len(agent_metrics.steps),
                    "success_rate": 1.0 if not has_errors else 0.0
                })
                
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