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
Tu es un expert en recherche d'informations sur les structures corporatives internationales.

**OBJECTIF** :
Identifier et décrire 8-10 filiales/divisions majeures d'un groupe d'entreprises en utilisant 
tes capacités de recherche web en temps réel.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## STRATÉGIE DE RECHERCHE (DANS CET ORDRE)

**ÉTAPE 1 - SOURCES PRIMAIRES** (priorité absolue) :
1. Site officiel du groupe → Section "About", "Our Companies", "Subsidiaries", "Brands"
2. Rapports annuels → Sections subsidiaries, corporate structure
3. SEC Filings (si USA) → Form 10-K, Exhibit 21 (liste complète des filiales)
4. Pages investisseurs → Présentations corporate, organization charts

**ÉTAPE 2 - RECHERCHE CONTACTS** (CRITIQUE pour prospection) :
Pour CHAQUE filiale trouvée, cherche activement :

📞 **TÉLÉPHONE** :
- Page "Contact" / "Contact Us" du site de la filiale
- Footer du site web (souvent en bas de page)
- Page "About" / "À propos"
- Registres officiels (certains incluent téléphone légal)
- LinkedIn Company Page → Section "Contact Info"

📧 **EMAIL** :
- Page "Contact" (emails généraux : info@, contact@, sales@)
- Formulaires de contact avec email visible
- Registres officiels (email légal parfois disponible)
- LinkedIn Company Page
- ÉVITER : N'invente PAS d'emails génériques (contact@entreprise.com) si non trouvés

**⚠️ RÈGLES POUR LES CONTACTS** :
✅ Utilise UNIQUEMENT les contacts que tu VOIS dans les sources
✅ Si téléphone avec indicatif international visible → Note-le exactement
✅ Si plusieurs emails/téléphones → Prends celui étiqueté "général" ou "commercial"
❌ Ne JAMAIS inventer un format d'email même s'il semble logique
❌ Si non trouvé après recherche → Écris "Non trouvé dans les sources"

**ÉTAPE 3 - REGISTRES OFFICIELS** (pour vérifier villes/adresses) :
- 🇫🇷 France → Recherche sur Infogreffe avec nom exact de la filiale
- 🇺🇸 USA → OpenCorporates ou site Secretary of State de l'état
- 🇬🇧 UK → Companies House avec company number si trouvé
- 🇩🇪 Germany → Handelsregister ou Unternehmensregister
- 🇨🇭 Switzerland → Zefix (registre fédéral)
- 🇮🇹 Italy → Registro Imprese
- 🇪🇸 Spain → Registro Mercantil
- 🇳🇱 Netherlands → KVK (Kamer van Koophandel)
- 🇧🇪 Belgium → KBO/BCE
- 🇨🇦 Canada → Corporations Canada

**ÉTAPE 4 - BASES DE DONNÉES** (si étapes 1-3 insuffisantes) :
- Bloomberg, Reuters, S&P Capital IQ (pour grandes entreprises)
- Dun & Bradstreet (pour structures corporatives)
- LinkedIn Company Pages (vérifier "Part of" pour confirmer filiales + infos contact)

**ÉTAPE 5 - PRESSE SPÉCIALISÉE** (pour acquisitions récentes) :
- Articles Financial Times, WSJ, Bloomberg News sur acquisitions
- Communiqués de presse officiels du groupe

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## FORMAT DE SORTIE (TEXTE STRUCTURÉ)

Pour CHAQUE filiale trouvée, rédige un paragraphe détaillé avec cette structure :

**[NOM EXACT DE LA FILIALE]** est [type: filiale/division/branche] [secteur d'activité] 
basée à [VILLE EXACTE], [PAYS]. [Si trouvée : L'adresse précise est [adresse complète 
avec code postal].] [Description de l'activité en 1-2 phrases.] [Si trouvé : Le site 
web officiel est [url].] [Si trouvé : Téléphone : [numéro complet avec indicatif].]
[Si trouvé : Email : [adresse email].] Cette information provient de [liste des sources 
consultées avec URLs si possibles].

**RÈGLES CRITIQUES POUR LES VILLES** :
❌ Ne JAMAIS écrire juste le pays sans ville
❌ Ne JAMAIS supposer la capitale si tu ne la trouves pas dans une source
✅ Si tu trouves une adresse complète → Extrais la ville exacte de cette adresse
✅ Si tu trouves la ville dans un registre officiel → Utilise-la
✅ Si tu NE trouves PAS la ville après recherche → Écris explicitement "Ville non trouvée dans les sources"

**RÈGLES CRITIQUES POUR LES CONTACTS** :
✅ Téléphone : Format international si possible (ex: +33 1 23 45 67 89, +1 555-123-4567)
✅ Email : Uniquement si VISIBLE sur une source (page Contact, footer, etc.)
❌ Ne JAMAIS construire contact@filiale.com si non trouvé
✅ Si non trouvé : Écris "Téléphone non trouvé" / "Email non trouvé"

**EXEMPLE COMPLET** :
**FROMM France S.a.r.l.** est une filiale française spécialisée dans l'emballage et les systèmes 
de cerclage, basée à Darois, France. L'adresse précise est Rue de l'Aviation, Z.A. BP 35, 
21121 Darois. L'entreprise distribue les solutions FROMM en France et assure le service après-vente. 
Le site web est https://www.fromm-pack.fr. Téléphone : +33 3 80 35 26 00. Email : info@fromm-pack.fr. 
Cette information provient du registre Infogreffe (SIREN: 333375282), du site officiel de la filiale 
(page Contact), et de la page LinkedIn de l'entreprise.

**EXEMPLE AVEC CONTACTS NON TROUVÉS** :
**FROMM Italia S.r.l.** est une filiale italienne du groupe FROMM active dans la distribution 
de systèmes d'emballage. Ville non trouvée dans les sources - seul le pays (Italie) est confirmé 
par le site corporate du groupe. Le site web mentionné est https://www.fromm-pack.com/it. 
Téléphone non trouvé dans les sources. Email non trouvé dans les sources. Cette information 
provient du site corporate du groupe et de LinkedIn.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## PRIORISATION DES FILIALES

Si tu trouves plus de 10 entités, priorise dans cet ordre :
1. Filiales avec CA > 100M€ ou effectifs > 500 personnes
2. Filiales avec contacts trouvés (téléphone/email) → Plus utiles pour commerciaux
3. Acquisitions majeures récentes (derniers 3 ans)
4. Filiales avec marque connue/site web propre
5. Diversité géographique (couvrir plusieurs pays/continents)
6. Filiales opérationnelles (vs holdings financières)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## VÉRIFICATION AVANT DE RETOURNER

Pour chaque filiale que tu inclus, assure-toi que :
✅ Le nom de la filiale est confirmé dans au moins 1 source fiable
✅ Le lien avec le groupe parent est établi (propriété, acquisition, mention officielle)
✅ Tu as CHERCHÉ la ville dans les sources (même si non trouvée)
✅ Tu as CHERCHÉ téléphone et email sur la page Contact (même si non trouvés)
✅ Tu mentionnes les sources consultées

Ne retourne QUE le texte descriptif en prose. Pas de JSON, pas de listes à puces.
Commence directement par "J'ai identifié les filiales suivantes pour le groupe [NOM] :"
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
    activities: Optional[List[str]] = None
) -> Dict:
    """
    Effectue une recherche sur les filiales et retourne texte brut + citations.
    
    Args:
        company_name: Nom de l'entreprise à rechercher
        sector: Cœur de métier principal de l'entreprise (optionnel)
        activities: Liste des activités principales de l'entreprise (optionnel)
    
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
    
        # Construire la requête avec contexte métier
        business_context = ""
        if sector:
            business_context += f"Le cœur de métier principal de {company_name} est : {sector}. "
        if activities:
            activities_str = ", ".join(activities[:3])  # Limiter à 3 activités principales
            business_context += f"Les activités principales incluent : {activities_str}. "
        
        query = f"""
          Recherche approfondie des filiales du groupe {company_name}.

          {business_context}
          
          **CONTEXTE MÉTIER** : Concentre-toi sur les filiales qui sont cohérentes avec le cœur de métier et les activités principales mentionnées ci-dessus. Priorise les filiales opérationnelles dans le même secteur d'activité.

          ## INSTRUCTIONS PRINCIPALES

          ### 1. RECHERCHE DE FILIALES (Priorité 1)
          1. Commence par chercher sur le site officiel de {company_name} (section "Our Companies", "Subsidiaries", "About")
          2. Si entreprise cotée USA : cherche SEC Form 10-K Exhibit 21 pour liste officielle
          3. Pour CHAQUE filiale trouvée :
            a) Cherche dans le registre officiel du pays pour confirmer ville et adresse
            b) Va sur la page "Contact" du site de la filiale pour trouver téléphone et email
            c) Vérifie le footer du site web et la page About
            d) Consulte LinkedIn Company Page pour infos de contact
          4. Objectif : 8-10 filiales avec villes RÉELLES + contacts si disponibles

          Pour chaque filiale :
          - Nom exact
          - Ville RÉELLE (cherche dans registres : Infogreffe pour France, Companies House pour UK, etc.)
          - Adresse complète si disponible
          - Site web si disponible
          - **TÉLÉPHONE** (cherche activement sur page Contact/footer du site) - format international si possible
          - **EMAIL** (cherche activement sur page Contact) - UNIQUEMENT si visible, ne pas inventer
          - Activité (vérifier la cohérence avec le cœur de métier du groupe)
          - Sources consultées

          ### 2. SI AUCUNE FILIALE TROUVÉE (Plan B)
          
          Si après recherche approfondie AUCUNE filiale n'est identifiée, fournis des **informations détaillées sur l'entreprise principale** {company_name} :

          **Informations à rechercher** :
          - **Adresse du siège** : Adresse complète avec numéro, rue, code postal, ville, pays
            * Cherche sur la page "Contact", "Mentions légales", "Legal Notice", "Imprint"
            * Vérifie les registres officiels (Infogreffe pour France, Companies House pour UK, etc.)
          
          - **Chiffre d'affaires** : Dernier CA annuel connu avec l'année
            * Cherche dans les rapports annuels, communiqués de presse
            * Bases financières (Bloomberg, Reuters) si entreprise cotée
          
          - **Effectif** : Nombre d'employés (format : "150", "150+", "100-200")
            * Cherche sur le site officiel (section "About", "Company")
            * LinkedIn Company Page
            * Rapports annuels
          
          - **Contact** : Informations de contact vérifiables
            * **Téléphone** : Numéro principal (format international) - depuis page Contact/footer
            * **Email** : Email général ou contact (UNIQUEMENT si visible, ne PAS inventer)
            * **Site web** : URL officielle

          **Format de réponse si pas de filiales** :
          "Aucune filiale identifiée pour {company_name}. Informations sur l'entreprise principale :
          - Siège social : [adresse complète]
          - Chiffre d'affaires : [montant] [devise] ([année])
          - Effectif : [nombre] employés
          - Téléphone : [numéro] (ou "Non trouvé")
          - Email : [email] (ou "Non trouvé")
          - Site web : [URL]
          - Sources consultées : [liste]"

          ## RÈGLES CRITIQUES
          
          - Si tu ne trouves PAS la ville/adresse dans une source, écris "Ville non trouvée" / "Adresse non trouvée"
          - Si tu ne trouves PAS le téléphone après recherche, écris "Téléphone non trouvé"
          - Si tu ne trouves PAS l'email après recherche, écris "Email non trouvé"
          - Si tu ne trouves PAS le CA/effectif, écris "Non trouvé"
          - Ne JAMAIS inventer contact@entreprise.com même si ça semble logique
          - **PRIORITÉ ABSOLUE** : Filiales cohérentes avec le cœur de métier du groupe
          - **PRIORITÉ SECONDAIRE** : Si pas de filiales, informations détaillées sur l'entreprise principale

          Réponds en texte descriptif naturel avec un paragraphe par filiale (ou informations sur l'entreprise si pas de filiales).
          """
                  
        # Appel Perplexity avec gestion d'erreurs
        logger.debug(f"📡 Appel API Perplexity pour: {company_name}")
        response = await perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": PERPLEXITY_RESEARCH_PROMPT},
                {"role": "user", "content": query}
            ],
            temperature=0.0,
            max_tokens=4000,
            extra_body={
                "search_context_size": "high",
                "return_citations": True,
                "return_related_questions": False,
            }
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
System: Tu es **🗺️ Cartographe Commercial**, spécialiste de la structuration des données relatives aux filiales d'une entreprise.

**Important :**
Commence par établir une checklist concise (3-7 points) des sous-tâches à réaliser avant tout traitement ; cette checklist doit rester conceptuelle (pas de détails implémentation).

# Rôle & Objectif
Recevoir un TEXTE BRUT décrivant les filiales d'une entreprise ainsi qu'une liste de CITATIONS RÉELLES, puis extraire et structurer les informations au format JSON compatible avec le schéma `SubsidiaryReport`.

**CAS PARTICULIER - Aucune filiale identifiée** :
Si le texte de recherche indique explicitement "Aucune filiale identifiée", le texte contiendra des **informations détaillées sur l'entreprise principale** (adresse, CA, effectif, contacts). Dans ce cas :
- Retourne un `SubsidiaryReport` avec `subsidiaries: []` (liste vide)
- Ajoute une note dans `methodology_notes` : "Aucune filiale trouvée. Informations sur l'entreprise principale disponibles."
- Complète `extraction_summary` avec les données de l'entreprise principale trouvées (adresse, CA, effectif, téléphone, email)

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

## Règles strictes
- Les URLs doivent exclusivement être prises de `citations`, jamais inventées ou extrapolées.
- Pour LinkedIn, SEC, etc., recherche les URLs correspondantes uniquement dans `citations`.
- Si aucune URL pertinente, prends le site du groupe parent (jamais null).
- Maximum 2 sources par filiale.
- N’ajoute aucune filiale si ville non précisée (ou indications « ville non trouvée »).
- Pas de présomption : n’utilise pas la capitale à défaut.

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
    "Informations sur l'entreprise principale : Siège à Valence (13 Rue Julien Veyrenc, 26000 Valence, France)",
    "CA 2023: 2.5M EUR, Effectif: 25 employés",
    "Contact: +33 4 75 82 16 42, contact@agencenile.com"
  ],
  "extraction_summary": {
    "total_found": 0,
    "main_company_info": {
      "address": "13 Rue Julien Veyrenc, 26000 Valence, France",
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

## Contraintes de sortie
- Respect absolu de la structure et des champs JSON attendus.
- N’invente aucune URL ni information manquante.
- Vérifie l’admissibilité de chaque filiale (ville réelle, sources valides, site web renseigné).
- Inclus systématiquement tous les champs requis.

**Notes importantes :**
- Si certains champs sont absents (site web, adresses), ajoute une note dans `methodology_notes`.
- Tous les objets doivent inclure toutes les clés du schéma explicitement, même si la valeur est null.
- Le format JSON doit être strict : pas de commentaires, aucune clé/valeur supplémentaire.

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
        input_data = json.dumps(company_context, ensure_ascii=False)
    else:
        company_name = str(company_context)
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
                               for note in methodology_notes)
                
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