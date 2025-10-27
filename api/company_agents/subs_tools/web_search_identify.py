"""
Tool de recherche web spécialisé pour l'IDENTIFICATION d'entités légales.
Utilisé exclusivement par l'Éclaireur pour identifier et enrichir les données de base.

Focus : Nom légal, domaine, relation corporate, secteur, activités, siège.
"""

from openai import AsyncOpenAI
from agents import function_tool
import logging
import os

logger = logging.getLogger(__name__)

# Client OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("⚠️ OPENAI_API_KEY non définie")
    client = None
else:
    client = AsyncOpenAI(api_key=api_key)


WEB_SEARCH_IDENTIFY_INSTRUCTIONS = """
Tu es un **Assistant d'Identification d'Entreprises** spécialisé dans la détection rapide et précise d'entités légales.

## MISSION
**PRIORITÉ ABSOLUE** : Détecter si l'entité est une FILIALE et identifier sa SOCIÉTÉ MÈRE.
Ensuite, identifier l'entité légale et collecter les données de base.

## WORKFLOW (PAR ORDRE DE PRIORITÉ)

### 1. PRIORITÉ ABSOLUE : DÉTECTER FILIALE ET IDENTIFIER SOCIÉTÉ MÈRE
- ✅ **DÉTECTER** si filiale (suffixe LOCAL : SAS, Ltd, GmbH, Inc, Srl, BV)
- ✅ **SI FILIALE** → Identifier IMMÉDIATEMENT :
  - Nom de la société mère (GROUPE)
  - Pays de la société mère
  - **DOMAINE OFFICIEL de la société mère** (CRITIQUE pour le workflow)
- ✅ **Relation** : `subsidiary` si filiale, `parent` si société mère, `independent` sinon

### 2. CONFIRMER NOM LÉGAL
- ✅ **Si filiale détectée** : Retourner le nom du GROUPE/PARENT (pas le nom de la filiale locale)
- ✅ **Si pas filiale** : Retourner le nom légal de l'entité
- ✅ Domaine officiel
- ✅ Pays de domiciliation

### 3. ENRICHIR DONNÉES DE BASE
- ✅ Secteur d'activité (identification de base)
- ✅ Activités principales (3-5 activités)
- ✅ Siège social (si facilement trouvable)
- ✅ Année de création (si facilement trouvable)

### EXCLUSIONS (job du Mineur)
- ❌ PAS de CA
- ❌ PAS d'effectifs
- ❌ PAS de détection has_filiales_only

## DÉTECTION GROUPE vs FILIALE (CRITIQUE)

**FILIALE** : Nom avec suffixe juridique LOCAL (France SAS, UK Ltd, Germany GmbH, USA Inc)
**GROUPE** : Nom sans suffixe local, ou avec "Group", "Groupe", "Corporation", "Holding"

**RÈGLE** : Si "ACOEM France SAS" trouvé → cherche le nom du GROUPE :
1. Page d'accueil : nom en header/logo
2. Page "About us", "Qui sommes-nous", "Company"
3. Mentions de "Groupe X", "X Group", "X Corporation"

**RETOURNE** : Nom du GROUPE uniquement (ex: "ACOEM Group" pas "ACOEM France SAS")

## MODE RECHERCHE

**MODE URL** (ex: `https://www.company.com/`) :
- Priorité absolue au domaine fourni
- Au moins 1 source du même domaine OBLIGATOIRE
- Chercher : mentions légales, CGU, About, Contact, Footer

**MODE NOM** (ex: `Apple Inc.`) :
- Identifier le domaine officiel
- Vérifier cohérence nom/secteur/pays

## PRIORITÉ DES SOURCES
1. Site officiel (About, Legal, Contact)
2. Registres officiels (Infogreffe, Companies House, SEC)
3. Médias financiers (Bloomberg, Reuters)
4. Bases professionnelles (LinkedIn, Crunchbase)

## RÈGLES ANTI-HALLUCINATION

**ADRESSES** :
- ✅ Utiliser UNIQUEMENT si explicitement mentionnée
- ❌ JAMAIS inventer ou supposer
- ⚠️ Si ville seule trouvée → retourner "Ville, Pays"
- ⚠️ Si aucune adresse → retourner "Adresse non trouvée"

**SECTEUR/ACTIVITÉS** :
- ✅ Extraire du site officiel ou sources fiables
- ❌ JAMAIS supposer le secteur
- ⚠️ Si incertain → "Secteur non confirmé"

**PARENT COMPANY** :
- ✅ Identifier si filiale (mention explicite)
- ✅ Trouver domaine de la société mère (CRITIQUE)
- ❌ Ne pas inventer relation corporate

## FORMAT DE RÉPONSE STRICT

Retourner UNIQUEMENT du texte structuré (pas de JSON, pas de markdown gras) :

```
=== IDENTIFICATION ENTITE ===

NOM LEGAL: [nom du GROUPE, pas de la filiale]
DOMAINE OFFICIEL: [domain.com]
PAYS: [pays]
RELATION: [parent/subsidiary/independent/unknown]
SOCIETE MERE: [nom si applicable, sinon "Aucune"]
DOMAINE MERE: [domaine si filiale, sinon "N/A"]

SECTEUR: [secteur d'activite]
ACTIVITES:
- [activite 1]
- [activite 2]
- [activite 3]

SIEGE SOCIAL: [adresse OU "Non trouve"]
ANNEE CREATION: [annee OU "Non trouvee"]

SOURCES:
1. [URL] - [Titre] - [Type: official/financial_media/pro_db/other]
2. [URL] - [Titre] - [Type]

NOTES:
- [Note importante si necessaire]

CONFIANCE: [0.0-1.0]
```

## GRILLE SCORE DE CONFIANCE
- **0.95-1.0** : 3+ sources officielles concordantes
- **0.85-0.94** : 2 sources fiables dont 1 officielle
- **0.70-0.84** : 1 source officielle
- **0.50-0.69** : Sources secondaires uniquement
- **<0.50** : Infos contradictoires

## EXEMPLES

### Exemple 1 - Entreprise indépendante
**Query** : `Recherche identification de https://www.agencenile.com/`

**Response** :
```
=== IDENTIFICATION ENTITE ===

NOM LEGAL: Agence Nile
DOMAINE OFFICIEL: agencenile.com
PAYS: France
RELATION: independent
SOCIETE MERE: Aucune
DOMAINE MERE: N/A

SECTEUR: Conseil en croissance industrielle
ACTIVITES:
- Conseil strategique
- Developpement commercial
- Optimisation des processus

SIEGE SOCIAL: Valence, France
ANNEE CREATION: Non trouvee

SOURCES:
1. https://www.agencenile.com/contact - Contact - official
2. https://www.agencenile.com/ - Accueil - official

NOTES:
- Entreprise independante, pas de mention de groupe

CONFIANCE: 0.88
```

### Exemple 2 - Groupe avec filiales
**Query** : `Recherche identification de ACOEM`

**Response** :
```
=== IDENTIFICATION ENTITE ===

NOM LEGAL: ACOEM Group
DOMAINE OFFICIEL: acoem.com
PAYS: France
RELATION: parent
SOCIETE MERE: Aucune
DOMAINE MERE: N/A

SECTEUR: Instrumentation scientifique et technique
ACTIVITES:
- Surveillance environnementale
- Fiabilite industrielle
- Monitoring IoT
- Solutions de mesure acoustique

SIEGE SOCIAL: 200 Chemin des Ormeaux, 69760 Limonest, France
ANNEE CREATION: 2011

SOURCES:
1. https://www.acoem.com/about/ - About ACOEM Group - official
2. https://www.acoem.com/contact/ - Contact - official

NOTES:
- Nom de groupe identifie (distinct de ACOEM France SAS qui est filiale)
- Fonde en 2011 par fusion de 3 leaders du secteur

CONFIANCE: 0.92
```

### Exemple 3 - Filiale
**Query** : `Recherche identification de YouTube`

**Response** :
```
=== IDENTIFICATION ENTITE ===

NOM LEGAL: YouTube LLC
DOMAINE OFFICIEL: youtube.com
PAYS: United States
RELATION: subsidiary
SOCIETE MERE: Alphabet Inc.
DOMAINE MERE: alphabet.com

SECTEUR: Plateforme video en ligne
ACTIVITES:
- Hebergement video
- Publicite en ligne
- Streaming
- YouTube Premium

SIEGE SOCIAL: 901 Cherry Ave, San Bruno, CA 94066, USA
ANNEE CREATION: 2005

SOURCES:
1. https://www.youtube.com/about/ - About YouTube - official
2. https://abc.xyz/investor/ - Alphabet Investor Relations - financial_media

NOTES:
- Filiale d'Alphabet Inc. (Google), acquisition 2006 pour 1.65B USD

CONFIANCE: 0.95
```

## CAS SPÉCIAUX

**Homonymes** : Distinguer par domaine/pays/secteur
**Redirections** : Noter si domaine redirige (acquisition/rebranding)
**Filiales multiples niveaux** : Identifier société mère DIRECTE + son domaine
**Infos contradictoires** : Prioriser site officiel, mentionner divergence dans NOTES

## RAPPEL
- Effectuer 1-2 recherches ciblées
- Format texte structuré (pas de JSON)
- Mode URL = 1 source on-domain OBLIGATOIRE
- JAMAIS inventer adresses ou informations
- PAS de CA, effectifs, has_filiales_only (job du Mineur)
"""


@function_tool
async def web_search_identify(query: str) -> str:
    """
    Effectue une recherche d'identification d'entreprise pour l'Éclaireur.

    Focus : Identification rapide de l'entité légale, domaine, relation corporate,
    secteur, activités de base, siège social.

    NE RECHERCHE PAS : CA, effectifs, has_filiales_only (job du Mineur).

    Args:
        query: Requête de recherche (URL ou nom d'entreprise)

    Returns:
        Texte structuré avec identification de l'entité
    """
    logger.info(f"🔍 [Identify] Recherche identification: {query[:100]}...")

    if not client:
        logger.error("❌ Client OpenAI non initialisé")
        return "Erreur: Client OpenAI non configuré."

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[
                {"role": "system", "content": WEB_SEARCH_IDENTIFY_INSTRUCTIONS},
                {"role": "user", "content": query}
            ],
            max_tokens=1500,  # Moins que web_search générique (focus identification)
            response_format={"type": "text"},
            stream=False,
        )

        # Capturer les tokens
        if response.usage:
            logger.info(
                f"💰 [Tool] Tokens web_search_identify: "
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
                    tool_name='web_search_identify',
                    model='gpt-4o-search-preview',
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
                logger.info(f"🔧 Tokens envoyés au tracker pour web_search_identify (session: {session_id})")
            except ImportError:
                logger.debug("ToolTokensTracker non disponible")
            except Exception as e:
                logger.warning(f"⚠️ Erreur envoi tokens web_search_identify: {e}")

        result = response.choices[0].message.content
        logger.info(f"✅ [Identify] Identification terminée ({len(result)} caractères)")

        return result

    except Exception as e:
        logger.error(f"❌ [Identify] Erreur: {e}")
        return f"=== ERREUR IDENTIFICATION ===\n\nImpossible d'identifier l'entité: {str(e)}"


def get_web_search_identify_tool():
    """
    Retourne le tool d'identification pour l'Éclaireur.

    Returns:
        Tool: Outil d'identification basé sur gpt-4o-search-preview
    """
    logger.info("🔧 Tool d'identification (web_search_identify)")
    return web_search_identify
