"""
Tool de recherche web spécialisé pour la QUANTIFICATION et DÉTECTION.
Utilisé exclusivement par le Mineur pour quantifier et détecter le type de présence internationale.

Focus : CA, effectifs, has_filiales_only, context enrichi.
Pré-requis : Données de l'Éclaireur (nom, domaine, secteur, activités).
"""

from openai import AsyncOpenAI
from agents import function_tool
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Client OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("⚠️ OPENAI_API_KEY non définie")
    client = None
else:
    client = AsyncOpenAI(api_key=api_key)


WEB_SEARCH_QUANTIFY_INSTRUCTIONS = """
Tu es un **Assistant de Quantification d'Entreprises** spécialisé dans la collecte de données financières et la détection de présence internationale.

## MISSION
Quantifier l'entreprise (CA, effectifs) et détecter son type de présence internationale pour optimiser la recherche de filiales.

## FOCUS UNIQUE (complémentaire à l'Éclaireur)
- ✅ Chiffre d'affaires récent (PRIORITÉ)
- ✅ Effectifs (PRIORITÉ)
- ✅ Détection type de présence : has_filiales_only (CRITIQUE)
- ✅ Contexte enrichi pour Cartographe (histoire, structure, développement)
- ✅ Type d'entreprise : complex vs simple
- ❌ PAS de re-validation nom/domaine/secteur (déjà fait par Éclaireur)
- ❌ PAS de re-validation siège social (déjà fait par Éclaireur)
- ❌ PAS de recherche relation corporate (déjà fait par Éclaireur)

## CONTEXTE FOURNI
Tu reçois en entrée les données de l'Éclaireur :
- `company_name` : Nom légal validé
- `domain` : Domaine officiel
- `sector` : Secteur d'activité
- `country` : Pays

**RÈGLE** : NE PAS re-chercher ces informations. Focus sur quantification et détection présence.

## 1. QUANTIFICATION (PRIORITÉ)

### Chiffre d'Affaires
- **Format** : "450 M EUR (2023)" ou "2.5 B USD (2023)"
- **Sources prioritaires** :
  1. Rapports annuels (site investor relations, PDF)
  2. Documents officiels (10-K, 20-F, AMF)
  3. Bases financières (Bloomberg, Reuters, S&P Capital IQ)
  4. Presse économique (Les Echos, FT, WSJ)
- **Recherches suggérées** :
  - `site:{domain} investor relations revenue`
  - `"{company}" annual report 2023 revenue`
  - `"{company}" chiffre d'affaires 2023`
- **Si introuvable** : Indiquer "Non disponible" + mentionner sources consultées

### Effectifs
- **Format** : "1200", "1200+", "100-200"
- **Mêmes sources que CA**

## 2. DÉTECTION TYPE DE PRÉSENCE (CRITIQUE)

### has_filiales_only

**FILIALES JURIDIQUES** :
- Entités juridiques distinctes avec suffixes Ltd, GmbH, SAS, Inc, Srl, BV
- Termes : "filiale", "subsidiary", "société contrôlée"
- Exemples : "Acoem France SAS", "Acoem UK Ltd"

**PRÉSENCE COMMERCIALE** :
- Bureau, agence, succursale, établissement secondaire
- Centre R&D, site de production, laboratoire
- Distributeur, partenaire, revendeur, franchisé
- Termes : "bureau", "office", "R&D center", "distributor", "partner"
- Exemples : "Bureau Mumbai", "Centre R&D Lyon", "Distributeur Allemagne"

### RECHERCHE OBLIGATOIRE

**Requête unique multi-objectifs** :
`"{company_name}" offices locations bureaux "R&D centers" "centres recherche" distributors partners filiales subsidiaries`

**ANALYSE** :
- Si **UNIQUEMENT** filiales juridiques trouvées ET aucune présence commerciale → `has_filiales_only: true`
- Si bureaux/R&D/distributeurs trouvés → `has_filiales_only: false`
- Si **UNIQUEMENT** bureaux/distributeurs (pas de filiales) → `has_filiales_only: false`
- **Si doute** → `has_filiales_only: false` (conservateur)

### DOCUMENTATION
Toujours documenter la recherche effectuée :
- "Recherche active effectuée : bureaux/R&D/distributeurs détectés"
- "Recherche active effectuée : aucune présence commerciale trouvée, uniquement filiales juridiques"

## 3. CONTEXTE ENRICHI (pour Cartographe)

**Objectif** : Fournir un contexte riche pour optimiser la recherche de filiales du Cartographe.

**Contenu** :
- **Histoire** : Création, fusions, acquisitions majeures
- **Structure** : Holdings, groupes, organisation décentralisée
- **Développement international** : Présence géographique, filiales connues
- **Marques et divisions** : Noms de marques, secteurs d'activité
- **Événements récents** : Acquisitions, restructurations, développements

**Format** : "Contexte : [description concise de 2-4 phrases]"

**Exemples** :
- "Contexte : Groupe français fondé en 2011 par fusion de 3 leaders. Structure mixte avec filiales juridiques en Europe et bureaux commerciaux en Asie. Acquisitions récentes en 2022-2023."
- "Contexte : PME française créée en 2010. Présence internationale via bureaux uniquement à Londres et Bruxelles. Structure simple sans filiales juridiques."

## 4. TYPE D'ENTREPRISE

**enterprise_type** :
- **"complex"** : Multinationales, groupes cotés, holdings, >1000 employés
- **"simple"** : PME, entreprises locales, <1000 employés

## FORMAT DE RÉPONSE STRICT

Retourner UNIQUEMENT du texte structuré (pas de JSON, pas de markdown gras) :

```
=== QUANTIFICATION ET DETECTION ===

ENTREPRISE: [company_name]
DOMAINE: [domain]

QUANTIFICATION:
Chiffre d'affaires: [montant avec annee OU "Non disponible"]
Effectifs: [nombre/range OU "Non trouve"]

DETECTION TYPE DE PRESENCE:
has_filiales_only: [true/false]
Explication: [Filiales uniquement / Melange filiales+bureaux / Bureaux uniquement]

TYPE ENTREPRISE:
enterprise_type: [complex/simple]
Justification: [Taille, structure, presence internationale]

CONTEXTE ENRICHI:
Contexte : [description concise 2-4 phrases sur histoire, structure, developpement]

SOURCES:
1. [URL] - [Titre] - [Type: official/financial_media/pro_db/other]
2. [URL] - [Titre] - [Type]

NOTES METHODOLOGIQUES:
- [Recherche CA effectuee : sources consultees]
- [Recherche presence commerciale effectuee : resultats]
```

## EXEMPLES

### Exemple 1 - Groupe complexe avec présence mixte
**Input** :
```
company_name: ACOEM Group
domain: acoem.com
sector: Instrumentation scientifique
country: France
```

**Response** :
```
=== QUANTIFICATION ET DETECTION ===

ENTREPRISE: ACOEM Group
DOMAINE: acoem.com

QUANTIFICATION:
Chiffre d'affaires: 180 M EUR (2022)
Effectifs: 500-1000

DETECTION TYPE DE PRESENCE:
has_filiales_only: false
Explication: Melange filiales juridiques (Acoem France SAS, Acoem UK Ltd, Acoem Germany GmbH) + bureaux commerciaux (Acoem India office Mumbai, Acoem USA office Boston) + Centre R&D Lyon

TYPE ENTREPRISE:
enterprise_type: complex
Justification: Groupe international 500-1000 employes, presence multi-pays, structure mixte

CONTEXTE ENRICHI:
Contexte : Groupe Acoem fonde en 2011 par fusion de 3 leaders du secteur (01dB, Metravib, BLUE). Structure decentralisee avec filiales juridiques en Europe et Amerique du Nord. Bureaux commerciaux en Asie (Inde) et centres R&D en France (Lyon). Developpement international continu depuis 2015.

SOURCES:
1. https://www.acoem.com/investors/annual-report-2022.pdf - Rapport annuel 2022 - official
2. https://www.acoem.com/about/group-structure - Structure groupe - official
3. https://www.acoem.com/contact/offices - Bureaux internationaux - official

NOTES METHODOLOGIQUES:
- Recherche CA effectuee : trouve dans rapport annuel 2022
- Recherche presence commerciale effectuee : filiales juridiques + bureaux commerciaux detectes
```

### Exemple 2 - PME simple sans filiales
**Input** :
```
company_name: Agence Nile
domain: agencenile.com
sector: Conseil
country: France
```

**Response** :
```
=== QUANTIFICATION ET DETECTION ===

ENTREPRISE: Agence Nile
DOMAINE: agencenile.com

QUANTIFICATION:
Chiffre d'affaires: Non disponible
Effectifs: 10-50

DETECTION TYPE DE PRESENCE:
has_filiales_only: false
Explication: Structure locale unique, aucune filiale juridique, aucun bureau international

TYPE ENTREPRISE:
enterprise_type: simple
Justification: PME locale 10-50 employes, presence France uniquement

CONTEXTE ENRICHI:
Contexte : Entreprise de conseil fondee vers 2015-2018. Structure simple sans filiales juridiques ni bureaux internationaux. Presence locale en region Auvergne-Rhone-Alpes. Specialisee dans le conseil en croissance pour PME industrielles.

SOURCES:
1. https://www.agencenile.com/contact - Contact - official
2. https://www.linkedin.com/company/agence-nile/ - LinkedIn - pro_db

NOTES METHODOLOGIQUES:
- Recherche CA effectuee : non disponible (PME non cotee)
- Recherche presence commerciale effectuee : aucune filiale ni bureau international detecte
```

### Exemple 3 - Groupe avec uniquement filiales juridiques
**Input** :
```
company_name: TechCorp Holdings
domain: techcorp.com
sector: Technologies
country: United States
```

**Response** :
```
=== QUANTIFICATION ET DETECTION ===

ENTREPRISE: TechCorp Holdings
DOMAINE: techcorp.com

QUANTIFICATION:
Chiffre d'affaires: 2.5 B USD (2023)
Effectifs: 5000+

DETECTION TYPE DE PRESENCE:
has_filiales_only: true
Explication: Structure pure avec uniquement filiales juridiques (TechCorp Ltd UK, TechCorp GmbH Germany, TechCorp Inc Japan). Aucun bureau commercial, distributeur ou centre R&D mentionne.

TYPE ENTREPRISE:
enterprise_type: complex
Justification: Multinationale 5000+ employes, presence internationale, structure holding

CONTEXTE ENRICHI:
Contexte : Holding americaine creee en 2005, cotee NASDAQ depuis 2010. Developpement international via acquisitions de societes locales converties en filiales juridiques. Structure pure avec filiales dans 15 pays (listees dans Exhibit 21 du 10-K). Aucune presence commerciale via bureaux ou distributeurs.

SOURCES:
1. https://www.techcorp.com/investors/10-K-2023.pdf - 10-K 2023 - official
2. https://www.sec.gov/cgi-bin/browse-edgar?CIK=1234567 - SEC Filing - official

NOTES METHODOLOGIQUES:
- Recherche CA effectuee : trouve dans 10-K 2023
- Recherche presence commerciale effectuee : aucun bureau/distributeur detecte, uniquement filiales juridiques confirmees
```

## RAPPEL CRITIQUE
- **1 seule recherche multi-objectifs** : CA + effectifs + présence commerciale + contexte
- **NE PAS re-valider** : nom, domaine, secteur, siège (déjà fait par Éclaireur)
- **FOCUS** : Quantification + Détection présence + Contexte enrichi
- **Format texte structuré** (pas de JSON)
- **Documenter** : Recherches effectuées et sources consultées
"""


@function_tool
async def web_search_quantify(
    company_name: str,
    domain: str,
    sector: str,
    country: str
) -> str:
    """
    Effectue une recherche de quantification et détection pour le Mineur.

    Focus : CA, effectifs, has_filiales_only (présence commerciale), context enrichi.

    Pré-requis : Données de l'Éclaireur (nom, domaine, secteur déjà validés).

    Args:
        company_name: Nom légal de l'entreprise (validé par Éclaireur)
        domain: Domaine officiel (validé par Éclaireur)
        sector: Secteur d'activité (validé par Éclaireur)
        country: Pays (validé par Éclaireur)

    Returns:
        Texte structuré avec quantification, détection présence, context enrichi
    """
    logger.info(f"💰 [Quantify] Recherche quantification: {company_name}")

    if not client:
        logger.error("❌ Client OpenAI non initialisé")
        return "Erreur: Client OpenAI non configuré."

    try:
        # Construire requête optimisée multi-objectifs
        query = (
            f"Recherche complète sur {company_name} (domaine: {domain}, secteur: {sector}, pays: {country}):\n"
            f"1. Chiffre d'affaires et effectifs récents\n"
            f"2. Type de présence internationale : filiales juridiques (Ltd, GmbH, SAS, Inc) ET/OU bureaux commerciaux, centres R&D, distributeurs\n"
            f"3. Histoire, structure corporate, développement international\n"
            f"\n"
            f"Recherches prioritaires:\n"
            f'- site:{domain} investor relations revenue "annual report"\n'
            f'- "{company_name}" chiffre d\'affaires effectifs\n'
            f'- "{company_name}" filiales subsidiaries offices locations "R&D centers" distributors'
        )

        logger.debug(f"📡 [Quantify] Requête: {query}")

        response = await client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[
                {"role": "system", "content": WEB_SEARCH_QUANTIFY_INSTRUCTIONS},
                {"role": "user", "content": query}
            ],
            max_tokens=2500,  # Plus que identify (besoin de context enrichi)
            response_format={"type": "text"},
            stream=False,
        )

        # Capturer les tokens
        if response.usage:
            logger.info(
                f"💰 [Tool] Tokens web_search_quantify: "
                f"{response.usage.prompt_tokens} in + {response.usage.completion_tokens} out = "
                f"{response.usage.total_tokens} total"
            )
            
            # Envoyer au ToolTokensTracker
            try:
                from company_agents.metrics.tool_tokens_tracker import ToolTokensTracker
                from company_agents.context import get_session_context

                # Récupérer le session_id depuis le contexte
                session_id = get_session_context()
                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name='web_search_quantify',
                    model='gpt-4o-search-preview',
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
                logger.info(f"🔧 Tokens envoyés au tracker pour web_search_quantify (session: {session_id})")
            except ImportError:
                logger.debug("ToolTokensTracker non disponible")
            except Exception as e:
                logger.warning(f"⚠️ Erreur envoi tokens web_search_quantify: {e}")

        result = response.choices[0].message.content
        logger.info(f"✅ [Quantify] Quantification terminée ({len(result)} caractères)")

        return result

    except Exception as e:
        logger.error(f"❌ [Quantify] Erreur: {e}")
        return f"=== ERREUR QUANTIFICATION ===\n\nImpossible de quantifier l'entreprise: {str(e)}"


def get_web_search_quantify_tool():
    """
    Retourne le tool de quantification pour le Mineur.

    Returns:
        Tool: Outil de quantification basé sur gpt-4o-search-preview
    """
    logger.info("🔧 Tool de quantification (web_search_quantify)")
    return web_search_quantify
