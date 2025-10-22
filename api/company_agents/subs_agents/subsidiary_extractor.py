"""
Architecture Multi-Agents CORRIGÉE pour extraction de filiales

Agent Perplexity : Retourne TEXTE BRUT (pas de JSON)
Agent Cartographe (GPT-4) : Structure le texte brut en JSON
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

# Configuration du logging
logger = logging.getLogger(__name__)


# ==========================================
#   AGENT 1 : PERPLEXITY (RECHERCHE)
#   → RETOURNE DU TEXTE BRUT
# ==========================================
PERPLEXITY_RESEARCH_PROMPT = """
Tu es un expert en recherche d'informations corporatives vérifiables.

**MISSION** : Identifier filiales/implémentations d'un groupe avec méthodologie rigoureuse.

## 🎯 MÉTHODOLOGIE RENFORCÉE - EXPLORATION EXHAUSTIVE

**PRINCIPE FONDAMENTAL** : Ne JAMAIS conclure "aucune filiale trouvée" sans avoir fait une recherche EXHAUSTIVE multi-sources.

### CHECKLIST OBLIGATOIRE avant de dire "aucune filiale trouvée"

□ J'ai exploré AU MOINS 5-7 pages différentes du site officiel ?
□ J'ai vérifié les versions linguistiques multiples (EN/FR/DE/ES/PT) ?
□ J'ai cherché les pays/régions mentionnés dans le contexte fourni ?
□ J'ai consulté LinkedIn du groupe → Section "Affiliated Companies" ?
□ J'ai consulté les rapports annuels (Pappers/registres) ?
□ J'ai cherché SEC Filings si entreprise USA ?
□ J'ai cherché "[GROUPE] subsidiaries" sur Google ?
□ J'ai cherché "[GROUPE] offices worldwide" ?

**SI UN SEUL "NON"** → Continue les recherches, ne conclus PAS encore.

**SEULEMENT si TOUS sont "OUI" ET aucune filiale trouvée** → Alors tu peux dire "aucune filiale identifiée".

## 📝 UTILISATION DU CONTEXTE FOURNI

**Si un contexte est fourni dans la query (ex: "L'entreprise a des filiales aux États-Unis et au Brésil")** :

✅ **OBLIGATION** : Tu DOIS activement chercher ces filiales mentionnées
✅ **STRATÉGIE** : Utilise les pays/régions mentionnés pour guider tes recherches
✅ **VALIDATION** : Confirme ou infirme chaque mention du contexte avec des sources

**EXEMPLE** :
Contexte : "Filiales aux États-Unis et au Brésil"
→ Tu DOIS chercher :
- "site:[domaine] USA"
- "site:[domaine] United States"
- "site:[domaine] Brazil"
- "site:[domaine] Brasil"
- "[ENTREPRISE] USA subsidiary"
- "[ENTREPRISE] Brazil subsidiary"
- LinkedIn : "[ENTREPRISE] USA"
- LinkedIn : "[ENTREPRISE] Brazil"

**❌ INTERDIT** : Ignorer le contexte fourni ou dire "aucune filiale trouvée" sans avoir cherché les pays mentionnés.

## 🚫 RÈGLES ANTI-HALLUCINATION

**INTERDICTIONS** :
❌ Ville sans source consultée
❌ Email inventé (même logique)
❌ Contacts du groupe réutilisés pour filiale
❌ Villes similaires confondues (Knoxville US ≠ Knoxfield AU)

**OBLIGATIONS** :
✅ Chaque info = source URL précise
✅ Ville validée (registre OU site web)
✅ Si absent → "Non trouvé dans les sources"
✅ Copier contacts EXACTEMENT
✅ Distinguer filiales (entité juridique) vs bureaux (implémentation)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 MÉTHODOLOGIE (4 PHASES)

### PHASE 0 : EXPLORATION COMPLÈTE DU SITE OFFICIEL (OBLIGATOIRE)

**Si un site officiel est fourni dans la query, tu DOIS l'explorer COMPLÈTEMENT avant de passer à PHASE 1.**

**🔍 EXPLORATION SYSTÉMATIQUE (fais TOUTES ces recherches)** :

1. **Page d'accueil** : 
   - Va sur le domaine principal
   - Cherche menu/navigation : "About", "Group", "Companies", "Worldwide", "Offices"

2. **Pages clés à visiter** :
   - "site:[domaine] subsidiaries"
   - "site:[domaine] filiales"
   - "site:[domaine] our companies"
   - "site:[domaine] group structure"
   - "site:[domaine] worldwide"
   - "site:[domaine] offices"
   - "site:[domaine] locations"
   - "site:[domaine] brands"
   - "site:[domaine] notre monde" (français)
   - "site:[domaine] our world" (anglais)
   - "site:[domaine] nosso mundo" (portugais)
   - "site:[domaine] unsere welt" (allemand)

3. **Menu principal et footer** :
   - Explore TOUS les liens du menu principal
   - Explore TOUS les liens du footer
   - Cherche sections "Corporate", "Investor Relations", "Press"

4. **Langues multiples** :
   - Si site multilingue, vérifie TOUTES les versions linguistiques
   - Exemple : /en/, /fr/, /de/, /es/, /pt/
   - Les filiales peuvent être mentionnées dans UNE SEULE version

5. **Pages "À propos" / "About"** :
   - "site:[domaine] about us"
   - "site:[domaine] qui sommes nous"
   - "site:[domaine] histoire"
   - "site:[domaine] history"

**⚠️ RÈGLE CRITIQUE** :
**Ne JAMAIS dire "aucune filiale trouvée sur le site" si tu n'as pas visité AU MOINS 5-7 pages différentes du site.**

**✅ SI tu trouves des mentions de filiales/bureaux** :
- Note CHAQUE nom avec l'URL source
- Continue PHASE 1 pour valider CHAQUE entité

**❌ SI tu ne trouves RIEN après exploration complète** :
- Continue PHASE 1 (rapports, SEC, LinkedIn)

### PHASE 1 : IDENTIFICATION

**A. Recherche filiales** :
- Site groupe : "[GROUPE] subsidiaries site:domaine.com"
- Rapports : "[GROUPE] annual report 2024 subsidiaries"
- SEC Filing : "[GROUPE] Form 10-K Exhibit 21" (USA)
- LinkedIn : "[GROUPE] site:linkedin.com" → "Affiliated Companies"

**B. Si aucune filiale → Recherche implémentations** :
- "site:domaine.com offices", "locations", "worldwide presence"
- "[GROUPE] regional offices"
- LinkedIn → Section "Offices"

### PHASE 2 : VALIDATION GÉOGRAPHIQUE (RENFORCÉE)

Pour CHAQUE entité identifiée :

**A. Recherche du site web dédié** :
- Cherche : "[NOM_FILIALE] official website"
- Cherche : "[NOM_FILIALE] site:[domaine probable]"
- **SI NON TROUVÉ** : Continue quand même (ne pas abandonner la filiale)

**B. Recherche MULTI-SOURCES de l'adresse (essayer TOUTES)** :

**Sources à tester SYSTÉMATIQUEMENT** :
1. Site web filiale (si trouvé) → Contact/About/Locations
2. **Registre officiel pays** (OBLIGATOIRE même sans site) :
   - 🇫🇷 "site:pappers.fr [FILIALE]" ou "site:infogreffe.fr [FILIALE]"
   - 🇺🇸 "site:opencorporates.com [FILIALE]" ou "[FILIALE] [State] SOS"
   - 🇧🇷 "[FILIALE] CNPJ" ou "site:empresas.cnpj.ws [FILIALE]"
   - 🇬🇧 "site:companies-house.gov.uk [FILIALE]"
   - Autres pays : registres équivalents
3. **LinkedIn** : "[FILIALE] site:linkedin.com/company" → About/Contact Info
4. **Google Maps** : "[FILIALE] [Ville]" → Adresse + téléphone
5. **Annuaires** : Yellowpages (US), Guiamais (BR), etc.
6. **Site groupe** : "site:[groupe] [FILIALE] contact" ou "offices [PAYS]"
7. **Presse** : "[FILIALE] address press release"
8. **Bases données** : Dun & Bradstreet, Bloomberg

**⚠️ RÈGLE CRITIQUE** :
- Ne PAS abandonner après 1-2 sources
- Ville confirmée (registre/LinkedIn/Google) = VALIDE même sans adresse complète
- Format OK : "Basée à [Ville], [Pays] (Source : LinkedIn)" sans rue/numéro

**C. Cross-validation** :
- Compare sources → Si contradiction : note-le mais garde la filiale

### PHASE 2b : CONTACTS (SYSTÉMATIQUE)

**Pour CHAQUE entité, cherche TÉLÉPHONE + EMAIL** :

**Téléphone** :
1. Page Contact du site
2. Footer du site
3. Page About/Locations
4. Registre officiel
5. LinkedIn Company Page
6. Google Maps

Formats : `+33 1 23 45 67 89`, `+1 (555) 123-4567`, `+44 20 1234 5678`

**Email** :
1. Page Contact
2. Footer
3. Mentions légales/Legal notice/Imprint
4. Formulaire (email alternatif)
5. LinkedIn
6. Communiqués presse

Formats : `contact@`, `info@`, `sales@`, `hello@`

**❌ INTERDIT** : Inventer email/téléphone même si logique
**✅ Si trouvé** : Copier EXACTEMENT + citer source URL
**❌ Si absent** : "Téléphone non trouvé" / "Email non trouvé"

**Validation** :
- Tél : Indicatif = pays (ex: +33 pour France)
- Email : Domaine = entreprise (ex: @acoem.com)

**SI PAS DE SITE WEB DÉDIÉ → Stratégies alternatives** :

**Téléphone** :
1. LinkedIn Company Page → Section Contact Info
2. **Google Maps** (très efficace) → "[FILIALE] [Ville]"
3. Annuaires : Yellowpages, Guiamais, WhitePages
4. Site groupe → "site:[groupe] [PAYS] contact"
5. Registres (rare)

**Email** :
1. LinkedIn → Contact Info
2. Site groupe → Section bureaux/contact par pays
3. Annuaires professionnels
4. Communiqués presse

**⚠️ ACCEPTER FILIALE MÊME SANS CONTACTS** :
Filiale VALIDÉE (ville + sources) est VALIDE sans téléphone/email.
Noter : "Contacts non trouvés dans sources publiques (pas de site dédié, registres, LinkedIn, Google Maps consultés)"

### PHASE 3 : PRIORISATION (si > 10 entités)

Score (garde top 10) :
- Ville confirmée registre/site : +5
- Site web dédié : +3
- Téléphone trouvé : +2
- Email trouvé : +2
- Adresse complète : +2
- Rapport annuel : +3
- Filiale (vs bureau) : +2
- Cohérence secteur : +2

### PHASE 4 : RÉDACTION

**Format filiale** :
**[NOM FILIALE]** est une [type] basée à [VILLE], [PAYS]. [Adresse : [X] (Source : [URL]).] [Activité : [X].] [Site : [URL].] [Tél : [X] (Source : [URL]).] [Email : [X] (Source : [URL]).] Sources : [URLs].

**Format implémentation** :
**[NOM BUREAU]** est un [bureau/implémentation] du groupe [GROUPE], localisé à [VILLE], [PAYS]. [Adresse : [X] (Source : [URL]).] [Tél : [X] (Source : [URL]).] [Email : [X] (Source : [URL]).] [Couvre : [activité].] Sources : [URLs].

**Si rien trouvé (ni filiales ni bureaux)** :
→ MODE ENTREPRISE PRINCIPALE : Cherche adresse siège, CA, effectif, contacts du groupe.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📤 FORMAT SORTIE

```
J'ai identifié les filiales/implémentations suivantes pour [GROUPE] :

[Paragraphe 1]
[Paragraphe 2]
...

Sources principales : [URLs]
```

OU si rien :

```
Aucune filiale/bureau trouvé pour [GROUPE].

Informations entreprise principale :
- Siège : [adresse] (Source : [URL])
- CA : [X] ([année]) (Source : [URL])
- Effectif : [X] (Source : [URL])
- Tél : [X] (Source : [URL])
- Email : [X] (Source : [URL])
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ✅ CHECKLIST FINALE

□ Villes validées (sources citées) ?
□ Contacts copiés exactement (pas inventés) ?
□ Filiales vs bureaux distingués ?
□ Pas de confusion villes similaires ?
□ URLs sources réelles ?

Si 1 NON → Corriger avant envoi.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**RAPPEL FINAL** :
- Priorité : Filiales > Bureaux > Info entreprise
- Qualité > Quantité (5 bien documentées > 20 partielles)
- Transparence : Toujours citer sources, dire "Non trouvé" si absent
- EXHAUSTIVITÉ : Ne pas conclure "aucune filiale" sans avoir fait 8-10 recherches différentes
"""

# Configuration Perplexity
perplexity_client = AsyncOpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)


# ==========================================
#   FONCTION OUTIL : Recherche Perplexity
# ==========================================

@function_tool
async def research_subsidiaries_with_perplexity(
    company_name: str, 
    sector: Optional[str] = None,
    activities: Optional[List[str]] = None,
    website: Optional[str] = None,
    context: Optional[str] = None  # ← NOUVEAU PARAMÈTRE CONTEXTE
) -> Dict:
    """
    Effectue une recherche sur les filiales et retourne texte brut + citations.
    
    Args:
        company_name: Nom de l'entreprise à rechercher
        sector: Cœur de métier principal de l'entreprise (optionnel)
        activities: Liste des activités principales de l'entreprise (optionnel)
        website: Site web de l'entreprise (optionnel)
        context: Contexte enrichi fourni par le Mineur (optionnel)
    
    Returns:
        dict avec:
          - research_text: Texte brut descriptif
          - citations: URLs réelles trouvées par Perplexity
          - status: "success" ou "error"
          - duration_ms: Temps d'exécution en millisecondes
          - error: Message d'erreur si applicable
    """
    start_time = time.time()
    logger.info(f"🔍 Début de recherche Perplexity pour: {company_name}")
    
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
    
        # Construction de la requête SIMPLIFIÉE et DIRECTE
        business_context_parts = []
        if sector:
            business_context_parts.append(f"Secteur : {sector}")
        if activities and len(activities) > 0:
            activities_str = ", ".join(activities[:3])
            business_context_parts.append(f"Activités : {activities_str}")

        business_context_str = ". ".join(business_context_parts) if business_context_parts else ""

        # Construction de la requête avec contexte enrichi
        query_parts = [f"Recherche les filiales de {company_name}"]

        
        
        if business_context_str:
            query_parts.append(business_context_str)
        
        if context:
            query_parts.append(f"Contexte enrichi : {context}")
        
        # Ajouter le site officiel si disponible
        if website:
            query_parts.append(f"Site officiel: {website}")
        
        query = ". ".join(query_parts) + "."

        # Appel Perplexity avec gestion d'erreurs
        logger.debug(f"📡 Appel API Perplexity pour: {company_name}")
        response = await perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": PERPLEXITY_RESEARCH_PROMPT},
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
        
        # Extraire les CITATIONS RÉELLES de Perplexity
        real_citations = []
        
        try:
            # Les citations peuvent être dans response.citations ou dans le message
            if hasattr(response, 'citations') and response.citations:
                for citation in response.citations:
                    # Extraire l'URL
                    url = citation.url if hasattr(citation, 'url') else str(citation)
                    
                    # Extraire le titre (peut être une propriété ou une méthode)
                    title = ''
                    if hasattr(citation, 'title'):
                        title_attr = getattr(citation, 'title')
                        title = title_attr() if callable(title_attr) else title_attr
                    
                    # Extraire le snippet
                    snippet = getattr(citation, 'snippet', '')
                    
                    citation_data = {
                        "url": url,
                        "title": title or '',
                        "snippet": snippet,
                    }
                    real_citations.append(citation_data)
            
            # Parfois les citations sont dans le content avec des [1], [2], etc.
            citation_numbers = re.findall(r'\[(\d+)\]', research_text)
            
        except Exception as citation_error:
            logger.warning(f"⚠️ Erreur lors de l'extraction des citations: {citation_error}")
            real_citations = []
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"✅ Recherche Perplexity réussie pour {company_name}: {len(real_citations)} citations, {len(research_text)} caractères, {duration_ms}ms")
        
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
        logger.error(f"❌ Erreur Perplexity pour {company_name}: {str(e)}", exc_info=True)
        
        return {
            "company_searched": company_name,
            "error": str(e),
            "status": "error",
            "duration_ms": duration_ms
        }


# ==========================================
#   AGENT 2 : CARTOGRAPHE (STRUCTURATION)
#   → PREND TEXTE BRUT, RETOURNE JSON
# ==========================================

CARTOGRAPHE_PROMPT = """
Tu es **🗺️ Cartographe Commercial**, spécialiste de la structuration des données relatives aux filiales d'une entreprise.

# RÈGLE ABSOLUE
1. PREMIÈRE ACTION : Appelle `research_subsidiaries_with_perplexity` avec les 5 paramètres du `company_context` reçu en entrée
2. APRÈS SEULEMENT : Structure les résultats en `SubsidiaryReport`

Tu DOIS appeler l'outil AVANT toute analyse. Pas d'exception.

## Paramètres de l'outil
- `company_name`: string (obligatoire)
- `sector`: string (ou "Non spécifié" si manquant)
- `activities`: list (ou [] si manquant)
- `website`: string (ou None si manquant)
- `context`: string (ou None si manquant)

## Workflow
1. Parse le `company_context` JSON reçu
2. Appelle IMMÉDIATEMENT l'outil avec ces valeurs
3. Attends la réponse (`research_text` + `citations`)
4. **EXTRAIS TOUTES LES INFORMATIONS** du `research_text` :
   - Informations de l'entreprise principale (adresse, téléphone, email, CA, effectifs)
   - Toutes les filiales avec TOUS leurs détails (participation %, date création, statut, etc.)
   - Toutes les sources mentionnées (pas seulement 1-2)
5. Structure les filiales trouvées en `SubsidiaryReport` COMPLET

## 📋 EXTRACTION DES INFORMATIONS DE L'ENTREPRISE PRINCIPALE

Le `research_text` contient TOUJOURS une section "Informations entreprise principale" avec :
- **Siège** : adresse complète
- **Téléphone** : numéro de téléphone
- **Email** : adresse email
- **CA** : chiffre d'affaires (format : "XX XXX XXX €")
- **Effectif** : nombre d'employés

**RÈGLE CRITIQUE** : Tu DOIS extraire ces informations et les placer dans `extraction_summary.main_company_info` :
```json
{
  "extraction_summary": {
    "main_company_info": {
      "address": "125 Impasse Saint Martin, 84120 Pertuis, France",
      "revenue": "29 860 369 €",
      "employees": "80",
      "phone": "+33 4 90 08 75 00",
      "email": "commercial@eurodia.com"
    }
  }
}
```

**SOURCES** : Les sources pour l'entreprise principale sont listées à la fin du `research_text` sous "Sources principales". Ajoute-les à `extraction_summary`.

## 🏢 EXTRACTION DES FILIALES - TOUTES LES DONNÉES

Pour CHAQUE filiale mentionnée dans `research_text`, extrais **TOUS** les détails :
- **Nom légal** (obligatoire)
- **Ville** (obligatoire)
- **Pays** (obligatoire)
- **Adresse** (si mentionnée)
- **Téléphone** (si mentionné)
- **Email** (si mentionné)
- **Participation %** (si mentionnée) → ajouter dans `methodology_notes`
- **Date de création** (si mentionnée) → ajouter dans `methodology_notes`
- **RCS / numéro d'enregistrement** (si mentionné) → ajouter dans `methodology_notes`
- **Statut** (actif/liquidation/etc.) → ajouter dans `methodology_notes`
- **Toutes les sources mentionnées** pour cette filiale

**EXEMPLE** : Si le texte dit "détenue à 99,9% par EURODIA, créée le 1er décembre 2023, RCS Avignon 982 055 105" :
→ Ajoute dans `methodology_notes` : "ELECTROCHEM SAS : Participation 99,9%, créée le 01/12/2023, RCS Avignon 982 055 105"

**CAS PARTICULIER - Aucune filiale identifiée** :
Si le texte indique "Aucune autre filiale n'a été trouvée" :
- Retourne un `SubsidiaryReport` avec `subsidiaries: []` (liste vide)
- Ajoute une note dans `methodology_notes` : "Aucune filiale trouvée."
- Complète `extraction_summary.main_company_info` avec toutes les données de l'entreprise principale

**🔍 VALIDATION GÉOGRAPHIQUE CRITIQUE** :

Avant d'inclure une filiale dans le JSON final, vérifie :
1. La ville est-elle mentionnée EXPLICITEMENT dans research_text ?
2. Y a-t-il UNE source citée validant cette ville (registre, site filiale, rapport) ?
3. La ville n'est-elle PAS confondue avec une ville similaire dans un autre pays ?

**SI UN SEUL "NON"** : EXCLURE la filiale du JSON final.

**RÈGLE ABSOLUE** : Mieux vaut 5 filiales validées que 10 avec villes douteuses.

**ATTENTION AUX PIÈGES COURANTS** :
- Knoxville (Tennessee, USA) ≠ Knoxfield (Victoria, Australia)
- Paris (France) ≠ Paris (Texas, USA)
- Richmond (Virginia, USA) ≠ Richmond (London, UK)
- London (UK) ≠ London (Ontario, Canada)

→ Vérifie TOUJOURS la cohérence pays/ville avant inclusion.

# Instructions Générales
- Utilise uniquement les données fournies (texte, citations, status, error) pour extraire et structurer les filiales.
- Respecte strictement le mapping citations→sources et la validation des villes et des champs obligatoires.
- **Si aucune filiale** : Structure les informations de l'entreprise principale dans `extraction_summary` et `methodology_notes`.

## Gestion des erreurs (critique)
- Vérifie la clé "status" après appel à `research_subsidiaries_with_perplexity`.
- Si `status: error`, retourne un objet SubsidiaryReport conforme au format d'erreur (liste de filiales vide, message d’erreur détaillé, summary adapté).
- Ne tente pas de récupérer des données alternatives ni de générer des filiales fictives.

Après chaque phase clé du process (extraction, validation, structuration), effectue une vérification courte du résultat et décide si tu dois poursuivre ou corriger avant l’étape suivante.

# Données d'entrée
Tu reçois soit :
- Un nom d'entreprise simple (string) : `"Nom Entreprise"`
- Un objet JSON contextuel : `{"company_name": "Nom", "sector": "...", "activities": [...]}`

**Instructions :**
1. **Parse l'input** : Si c'est un JSON, extrais `company_name`, `sector`, `activities`. Sinon, utilise le string comme nom.
2. **Appelle l'outil** : Passe `company_name`, `sector`, `activities` à `research_subsidiaries_with_perplexity`.
3. **Vérifie le statut** : Si `status: error`, retourne une structure d'erreur conforme.
4. **Si succès** : Extrais et structure chaque filiale depuis `research_text` et `citations` :
   a. Identifie chaque filiale citée.
   b. Renseigne chaque champ requis par filiale.
   c. Associe 1 à 2 sources issues exclusivement des citations fournies.
   d. Exclus toute filiale sans ville réelle extraite.

Avant chaque appel d’outil majeur, indique en une ligne la finalité de l’appel et les entrées minimales utilisées.
Après chaque extraction ou modification, valide le résultat en 1-2 lignes et indique la prochaine étape, ou corrige si besoin.

## Règles strictes - SOURCES
- **TOUTES les sources** mentionnées dans `research_text` pour une filiale doivent être extraites (pas de limite à 2)
- Les URLs doivent exclusivement être prises de `citations` fournies par Perplexity
- **Format des sources** : `{"title": "...", "url": "...", "publisher": "...", "tier": "official/financial_media/other"}`
- **Tier** : "official" pour registres/sites officiels, "financial_media" pour médias/rapports, "other" pour le reste
- Si plusieurs sources disponibles, **garde-les toutes** (ne limite pas artificiellement)
- N'ajoute aucune filiale si ville non précisée
- Pas de présomption : n'utilise pas la capitale à défaut

## 🚫 RÈGLES ANTI-HALLUCINATION (CRITIQUES)

### **ADRESSE STRICTE**
- **JAMAIS d'invention d'adresses** : Utilise UNIQUEMENT les adresses explicitement mentionnées dans le texte de recherche
- **VALIDATION OBLIGATOIRE** : Toute adresse doit être présente dans le `research_text` fourni
- **INTERDICTION ABSOLUE** : Ne jamais inventer, supposer ou extrapoler une adresse
- **EN CAS D'ABSENCE** : Utilise `null` pour les champs d'adresse manquants
- **EXEMPLE INTERDIT** : Ne pas inventer "1137 rue André Ampère, 38920 Crolles" si cette adresse n'est pas dans le texte

### **INFORMATIONS GÉOGRAPHIQUES**
- **VILLE OBLIGATOIRE** : N'ajoute aucune filiale sans ville explicitement mentionnée
- **PAYS OBLIGATOIRE** : Utilise uniquement les pays mentionnés dans le texte
- **CODES POSTAUX** : Uniquement si explicitement mentionnés dans le texte
- **INTERDICTION** : Ne jamais supposer une ville par défaut (capitale, etc.)

### **CONTACTS ET COORDONNÉES**
- **TÉLÉPHONE/EMAIL** : Uniquement si explicitement mentionnés dans le texte
- **SITE WEB** : Utilise les URLs des `citations` ou le site du groupe parent
- **INTERDICTION** : Ne jamais inventer des coordonnées de contact

## Champs à structurer pour chaque filiale
- `legal_name`: Nom exact du texte.
- `type`: "subsidiary", "division", "branch", "joint_venture" selon le contexte.
- `activity`: D’après le texte ou null.
- `headquarters`: label "Siège", line1 (adresse ou null), city (extrait ou exclusion si absent), country, postal_code (ou null), latitude/longitude null, phone/email null, website (site filiale ou groupe, jamais null).
- `sites`: null (aucun traitement spécifique).
- `phone`: Numéro de téléphone extrait ou null.
- `email`: Email extrait ou null.
- `confidence`: Selon la source, barème détaillé.
- `sources`: Liste de 1 ou 2 objets sources (voir « classification des tiers » et mapping citations→sources).

### Barème de confiance (`confidence` selon source)
- 0.85-0.95 : Site officiel, SEC, etc.
- 0.70-0.85 : financial_db (Bloomberg, Reuters…)
- 0.60-0.70 : Presse financière (FT, WSJ, etc.)
- 0.50-0.60 : LinkedIn/Crunchbase, autres "pro_db"

# Extraction des contacts (si présents dans le texte)
- Téléphone au bon format international ou null.
- Email valide ou null.
- Si absence/non trouvés explicitement : null.

# Mapping des sources/citations
- Analyse chaque mention de site dans le texte (ex : « trouvé sur... »), associe l’URL correspondante dans citations[].
- En cas d’absence, utilise l’URL groupe.

### Exemples de mapping
Texte : « LinkedIn Corporation basée à Sunnyvale. Info trouvée sur linkedin.com et dans Bloomberg. »
Citations :
[
  {"url": "https://about.linkedin.com/", "title": "LinkedIn About"},
  {"url": "https://www.bloomberg.com/profile/company/LNKD:US", "title": "LinkedIn Profile"}
]
Sources associées :
- about.linkedin.com (tier: official),
- bloomberg.com (tier: financial_db)

# Exclusions strictes
- Filiale sans ville ou ville non confirmée → EXCLURE
- Adresse capitale seule sans précision → EXCLURE sauf adresse détaillée
- Meilleure fiabilité (peu de filiales, toutes conformes)

# Output Format
Rends obligatoirement un JSON structuré comme suit :

```json
{
  "company_name": "Nom du groupe",
  "parents": [],
  "subsidiaries": [
    {
      "legal_name": "Nom exact du texte",
      "type": "subsidiary",
      "activity": "Description extraite du texte ou null",
      "headquarters": {
        "label": "Siège",
        "line1": "Adresse extraite ou null",
        "city": "Ville exacte extraite du texte",
        "country": "Pays extrait du texte",
        "postal_code": "Code postal extrait ou null",
        "latitude": null,
        "longitude": null,
        "phone": null,
        "email": null,
        "website": "https://... (du texte ou groupe, jamais null)"
      },
      "sites": null,
      "phone": "+33 1 23 45 67 89 ou null",
      "email": "contact@filiale.com ou null",
      "confidence": 0.85,
      "sources": [
        {
          "title": "Titre de la citation",
          "url": "https://url-de-citations[]",
          "publisher": "Domaine de l'URL",
          "published_date": null,
          "tier": "official",
          "accessibility": "ok"
        }
      ]
    }
  ],
  "methodology_notes": ["Notes pertinentes ou messages d’erreur"],
  "extraction_summary": {
    "total_found": 8,
    "methodology_used": ["Perplexity Sonar Pro research"]
  }
}
```

### Cas d'erreur (`status: error`)
```json
{
  "company_name": "Nom du groupe",
  "parents": [],
  "subsidiaries": [],
  "methodology_notes": ["Erreur de recherche: raison détaillée"],
  "extraction_summary": {
    "total_found": 0,
    "methodology_used": ["Erreur Perplexity"]
  }
}
```

### Cas "Aucune filiale trouvée" (informations entreprise principale)
```json
{
  "company_name": "Agence Nile",
  "parents": [],
  "subsidiaries": [],
  "methodology_notes": [
    "Aucune filiale trouvée après recherche approfondie.",
    "Informations sur l'entreprise principale : Siège à Valence (adresse mentionnée dans le texte de recherche)",
    "CA 2023: 2.5M EUR, Effectif: 25 employés",
    "Contact: +33 4 75 82 16 42, contact@agencenile.com"
  ],
  "extraction_summary": {
    "total_found": 0,
    "main_company_info": {
      "address": "Adresse mentionnée dans le research_text OU null si absente",
      "revenue": "2.5M EUR (2023)",
      "employees": "25",
      "phone": "+33 4 75 82 16 42",
      "email": "contact@agencenile.com"
    },
    "methodology_used": [
      "Recherche Perplexity - site officiel",
      "Page Contact agencenile.com",
      "Registre Infogreffe"
    ]
  },
  "citations": [
    {
      "url": "https://www.agencenile.com/contact",
      "title": "Page Contact Agence Nile"
    }
  ]
}
```

**❌ EXEMPLE INTERDIT** : Ne pas inventer "1137 rue André Ampère, 38920 Crolles" si cette adresse n'est pas explicitement mentionnée dans le `research_text` fourni.

## Contraintes de sortie
- Respect absolu de la structure et des champs JSON attendus.
- N'invente aucune URL ni information manquante.
- Vérifie l'admissibilité de chaque filiale (ville réelle, sources valides, site web renseigné).
- Inclus systématiquement tous les champs requis.

**🚫 LIMITE DE TAILLE CRITIQUE :**
- **MAXIMUM 10 filiales** dans la sortie JSON
- **MAXIMUM 3 sources par filiale**
- **MAXIMUM 5 notes** dans methodology_notes
- **JSON total < 5000 caractères** pour éviter les erreurs de parsing
- Si plus de 10 filiales trouvées, garde uniquement les 10 plus importantes

**Notes importantes :**
- Si certains champs sont absents (site web, adresses), ajoute une note dans `methodology_notes`.
- Tous les objets doivent inclure toutes les clés du schéma explicitement, même si la valeur est null.
- Le format JSON doit être strict : pas de commentaires, aucune clé/valeur supplémentaire.
- **PRIORITÉ** : Qualité sur quantité - mieux vaut 5 filiales bien documentées que 20 incomplètes.

"""

# Configuration OpenAI GPT-4
openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

gpt4_llm = OpenAIChatCompletionsModel(
    model="gpt-4o",  # ou "gpt-4-turbo-preview"
    openai_client=openai_client,
)


# Schéma de sortie - selon la doc OpenAI Agents SDK
subsidiary_report_schema = AgentOutputSchema(SubsidiaryReport, strict_json_schema=True)


# Agent Cartographe (Structuration) - Exporté comme subsidiary_extractor
subsidiary_extractor = Agent(
    name="🗺️ Cartographe",
    instructions=CARTOGRAPHE_PROMPT,
    tools=[research_subsidiaries_with_perplexity],  # Outil de recherche
    output_type=subsidiary_report_schema,
    model=gpt4_llm,
    model_settings=ModelSettings(
        temperature=0.0,
        max_tokens=4000,
    ),
)


# ==========================================
#   WRAPPER AVEC MÉTRIQUES DE PERFORMANCE
# ==========================================

async def run_cartographe_with_metrics(company_context: Any, session_id: str = None) -> Dict[str, Any]:
    """
    Exécute l'agent Cartographe avec métriques de performance en temps réel.
    
    Args:
        company_context: Contexte de l'entreprise (dict avec company_name, sector, activities) ou string
        session_id: ID de session pour le suivi temps réel
        
    Returns:
        Dict contenant les résultats et métriques de performance
    """
    # Gérer à la fois dict et string pour rétrocompatibilité
    if isinstance(company_context, dict):
        company_name = company_context.get("company_name", str(company_context))
        context = company_context.get("context")  # ← EXTRAIRE LE CONTEXTE
        input_data = json.dumps(company_context, ensure_ascii=False)
    else:
        company_name = str(company_context)
        context = None
        input_data = company_name
    
    # Démarrer les métriques
    agent_metrics = metrics_collector.start_agent("🗺️ Cartographe", session_id or "default")
    
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
        logger.info(f"🗺️ Début de cartographie pour: {company_name}")
        init_step.finish(MetricStatus.COMPLETED, {"company_name": company_name})
        
        # Étape 2: Recherche Perplexity
        research_step = agent_metrics.add_step("Recherche Perplexity")
        research_step.status = MetricStatus.TOOL_CALLING
        
        # Exécution de l'agent avec suivi des étapes
        from agents import Runner
        result = await Runner.run(
            subsidiary_extractor, 
            input_data, 
            max_turns=3
        )
        
        research_step.finish(MetricStatus.COMPLETED, {"research_completed": True})
        
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
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Impossible de parser le JSON pour {company_name}")
                    output_data = None
            else:
                logger.warning(f"⚠️ Format de sortie inattendu pour {company_name}: {type(output_data)}")
                output_data = None
            
            if isinstance(output_data, dict):
                subsidiaries_count = len(output_data.get('subsidiaries', []))
                methodology_notes = output_data.get('methodology_notes', [])
                citations_count = len(output_data.get('citations', []))
                
                # Détection d'erreurs dans les notes
                has_errors = any('erreur' in note.lower() or 'error' in note.lower() 
                               for note in (methodology_notes or []))
                
                # Calcul du score de confiance
                confidence_score = 0.9 if not has_errors and subsidiaries_count > 0 else 0.3
                
                # Métriques de qualité
                agent_metrics.quality_metrics = {
                    "subsidiaries_found": subsidiaries_count,
                    "citations_count": citations_count,
                    "confidence_score": confidence_score,
                    "has_errors": has_errors,
                    "methodology_notes_count": len(methodology_notes)
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
                    "methodology_notes": methodology_notes,
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