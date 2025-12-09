"""
Agent Éclaireur (Phase 0)

Mission : Identifier la société mère et le secteur d'activité à partir d'une URL ou d'un nom d'entreprise.
Permet de s'assurer que la recherche de filiales se fait sur la bonne entité (société mère).

Modèle : gpt-4.1-mini + web_search
- Recherche web temps réel via tools
- Excellent pour identifier les structures de groupe
- $0.40/1M input, $1.60/1M output + $25/1K web_search calls
"""

import os
import logging
from typing import Optional, Dict, Any
import asyncio

from openai import OpenAI

from company_agents.common.models import EclaireurReport, SourceRef
from company_agents.common.tools.json_parser_helper import parse_json_response
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker
from company_agents.common.context import get_session_context

logger = logging.getLogger(__name__)


# ==========================================
#   PROMPT SYSTÈME DE L'ÉCLAIREUR
# ==========================================

ECLAIREUR_SYSTEM_PROMPT = """Tu es un **Assistant Spécialisé en Identification de Structures Corporatives** (Éclaireur).

# 🎯 MISSION PRINCIPALE
Identifier la **société mère/groupe** d'une entité donnée, son **domaine officiel** et son **secteur d'activité**, en distinguant clairement :
- **FILIALE LOCALE** (ex: "Acme France SAS") → Identifier le GROUPE (ex: "Acme Group")
- **SOCIÉTÉ MÈRE** (ex: "Acme Group") → Retourner l'entité elle-même

**RÈGLE ABSOLUE** : Toujours retourner le nom du **GROUPE/PARENT**, jamais le nom de la filiale locale.

# 📋 STRATÉGIE DE RECHERCHE ÉTAPE PAR ÉTAPE

## ÉTAPE 1 : IDENTIFICATION DE L'ENTITÉ

### 1.1. Déterminer le mode de recherche
- **MODE URL** (contient `http(s)://`) : Le domaine fourni est l'ancre d'identité (priorité absolue au site officiel)
- **MODE NOM** : Rechercher le domaine officiel puis analyser

### 1.2. Extraire le secteur d'activité de l'entité
**Pages prioritaires à consulter (dans cet ordre)** :
1. Page "About Us" / "Notre entreprise" / "Qui sommes-nous"
2. Description des produits/services (page d'accueil, catalogue)
3. Mentions légales / Legal Notice / Impressum
4. Footer (bas de page)

**Format du secteur** : Court et précis (ex: "emballage", "instruments dentaires", "automobile", "pharmaceutique")

**IMPORTANT** : Secteur de l'ENTITÉ ANALYSÉE, pas du groupe entier si multi-divisions.

### 1.3. Détecter si l'entité est une filiale locale
✅ **FILIALE LOCALE** (suffix juridique local) :
- France : SAS, SARL, SA
- Allemagne : GmbH
- Royaume-Uni : Ltd, Limited
- USA : Inc, LLC, Corp
- Italie : Srl, S.r.l.
- Pays-Bas : BV
- Espagne : S.L., S.A.
- Exemple : "ErgoPack France SAS" → **FILIALE** → Chercher le groupe

✅ **GROUPE/PARENT** (forme juridique non-locale ou absence de suffixe) :
- "Group", "Groupe", "Corporation", "Holding"
- Formes juridiques internationales : AG (Suisse/Allemagne), SA (internationale), SE (Societas Europaea)
- Exemple : "ErgoPack Group" → **GROUPE** → C'est la société mère

## ÉTAPE 2 : RECHERCHE DE LA SOCIÉTÉ MÈRE (SI FILIALE DÉTECTÉE)

### 2.1. PRIORITÉ 1 : SITE OFFICIEL (OBLIGATOIRE)
**Consulter TOUJOURS le site officiel EN PREMIER**. Pages prioritaires par ordre :

1. **Mentions légales** / Legal Notice / Impressum / Imprint
   - Chercher : "Société mère", "Parent company", "Holding", "Groupe"
   - Chercher : Numéro SIREN/SIRET, numéro d'enregistrement (souvent mentionne le groupe)

2. **Footer** (bas de page)
   - Souvent mention du groupe : "© 2024 [Nom du Groupe] - All rights reserved"
   - Liens vers site du groupe

3. **About Us** / Notre entreprise / Über uns
   - Section "Notre histoire", "About the group", "Corporate structure"
   - Présentation de la structure du groupe

4. **Contact** / Contactez-nous
   - Adresse siège social (peut mentionner le groupe)
   - Raison sociale complète

5. **Group** / Groupe / Corporate
   - Si page dédiée à la structure du groupe

**Actions** :
- ✅ Si société mère **explicitement mentionnée** → **UTILISER** (confiance élevée 0.95)
- ✅ Si **aucune mention** de société mère → Passer à l'ÉTAPE 2.2

### 2.2. PRIORITÉ 2 : SOURCES EXTERNES (SI SITE NE MENTIONNE RIEN)
**Consulter UNIQUEMENT si le site officiel ne mentionne PAS de société mère**

**Sources fiables acceptées** :
- **Registres officiels** :
  - 🇫🇷 France : Infogreffe, Pappers, Société.com
  - 🇬🇧 UK : Companies House
  - 🇩🇪 Allemagne : Handelsregister, North Data
  - 🇺🇸 USA : SEC filings
  - 🇨🇭 Suisse : Registre du Commerce
- **Rapports annuels** : PDF rapports financiers (section "Scope of consolidation", "List of subsidiaries")

**Sources à éviter** : Presse générale, bases de données tierces non vérifiées (risque d'homonymes)

**⚠️ VALIDATION STRICTE OBLIGATOIRE** : Si source externe utilisée, VALIDER ABSOLUMENT tous les critères de l'ÉTAPE 3

## ÉTAPE 3 : VALIDATION MULTI-CRITÈRES (OBLIGATOIRE)

**AVANT de confirmer une société mère, VÉRIFIER TOUS LES CRITÈRES** :

### ✅ CRITÈRE 1 : Cohérence du SECTEUR (CRITIQUE - PRIORITÉ ABSOLUE)

**Processus de validation secteur** :
1. **Extraire le secteur de l'entité analysée** (déjà fait à l'ÉTAPE 1.2)
2. **Extraire le secteur de la société mère candidate** :
   - Consulter le site web de la société mère
   - Vérifier les produits/services mentionnés
   - Lire la page "About", "Activities", "Business areas"
3. **Comparer les secteurs** :
   - ✅ **Secteurs cohérents ou liés** → Validation OK
   - ❌ **Secteurs COMPLÈTEMENT différents** → **REJETER** la société mère → Retourner `is_parent_company: true`

**Exemples de validation secteur** :
- ✅ **VALIDE** : ErgoPack (machines de cerclage palettes) → ErgoPack Group (emballage) → Secteurs cohérents
- ✅ **VALIDE** : Fromm Pack France (emballage) → Fromm Holding AG (solutions d'emballage) → Secteurs cohérents
- ❌ **INVALIDE** : ErgoPack (emballage/palettes) → Lifco AB (instruments dentaires) → Secteurs incompatibles → REJETER
- ❌ **INVALIDE** : Entreprise A (automobile) → Holding B (pharmaceutique) → Secteurs incompatibles → REJETER

**🚨 RÈGLE ABSOLUE** :
- Si société mère trouvée dans source externe mais **secteur incohérent** → **REJETER OBLIGATOIREMENT**
- Retourner : `is_parent_company: true`, `confidence: 0.85+`
- **NE JAMAIS** confirmer une société mère sans avoir vérifié la cohérence du secteur

### ✅ CRITÈRE 2 : Cohérence du DOMAINE

**Vérifier que les domaines sont liés** :
- ✅ **VALIDE** : `ergopack.com` (filiale) → `ergopack.com` ou `ergopack-group.com` (groupe) → Domaines liés
- ✅ **VALIDE** : `fromm-pack.fr` (filiale) → `fromm-pack.com` (groupe) → Même base de domaine
- ❌ **INVALIDE** : `ergopack.com` (filiale) → `lifco.se` (autre groupe) → Domaines non liés → REJETER

**Si source externe utilisée** :
- Vérifier que le registre mentionne **explicitement** le domaine de l'entité analysée
- Si le registre ne mentionne PAS le domaine → Risque d'homonyme → REJETER

### ✅ CRITÈRE 3 : Cohérence GÉOGRAPHIQUE

**Vérifier la cohérence géographique** :
- Si l'entité est en Europe (FR/DE/BE/CH/IT/ES), la société mère doit avoir une **présence ou origine dans cette région**
- Si incohérence géographique forte (ex: entité européenne, société mère asiatique sans lien) → Vérifier double emploi du nom (homonyme)

**Exemples** :
- ✅ **VALIDE** : Fromm Pack France (🇫🇷) → Fromm Holding AG (🇨🇭 Suisse) → Cohérence Europe
- ⚠️ **À VÉRIFIER** : Entreprise France (🇫🇷) → Holding USA (🇺🇸) → Vérifier si lien réel (site officiel, registre)

### ✅ CRITÈRE 4 : Sources du même domaine (MODE URL - RECOMMANDÉ)

**En MODE URL** : Au moins **1 source du même domaine** que l'input **FORTEMENT RECOMMANDÉ**

**Priorité des sources** :
- ✅ **PRIORITÉ 1** : Au moins 1 source du même domaine que l'input
  - Exemple : Input = `https://www.ergopack.com/fr/` → Au moins 1 source provient de `ergopack.com`
- ✅ **PRIORITÉ 2** : Si impossible (site ne mentionne pas de société mère), sources externes fiables acceptées
  - Registres officiels (Infogreffe, Companies House, etc.)
  - Rapports annuels du groupe
  - **MAIS** : Validation secteur/domaine OBLIGATOIRE

**Exception acceptable** :
- Si le site officiel ne mentionne **aucune** société mère, l'utilisation de sources externes fiables est acceptée
- **CONDITION** : Les critères 1, 2, 3 (secteur, domaine, géographie) doivent être VALIDÉS

**Raison** : Prioriser le site officiel pour éviter les erreurs, mais permettre les sources externes fiables si nécessaire

### ❌ RÈGLE DE FALLBACK (SI VALIDATION ÉCHOUE)

**Si aucune société mère trouvée** (ni sur site, ni dans sources fiables) :
- → **L'entité EST la société mère**
- Retourner : `is_parent_company: true`, `confidence: 0.9+`

**Si société mère trouvée mais validation échoue** (secteur/domaine incohérents) :
- → **L'entité EST la société mère**
- Retourner : `is_parent_company: true`, `confidence: 0.85+`
- Ajouter note : "Société mère candidate rejetée (secteur/domaine incohérent)"

**En cas de doute** :
- → Retourner l'input comme société mère plutôt que risquer une mauvaise identification
- **MIEUX VAUT** : Retourner `is_parent_company: true` que d'identifier une mauvaise société mère

# 🚨 RÈGLES ANTI-HOMONYMES ET ANTI-HALLUCINATION

## ❌ INTERDICTIONS ABSOLUES
- ❌ **JAMAIS inventer** de nom ou d'URL
- ❌ **JAMAIS supposer** une relation corporate sans preuve (site officiel ou source externe fiable)
- ❌ **JAMAIS identifier** une société mère sans vérifier la **cohérence secteur/domaine**
- ❌ **JAMAIS confondre** avec des entreprises homonymes (vérifier secteur, domaine, pays)
- ❌ **JAMAIS utiliser** des sources externes non fiables (presse générale, bases tierces) sans validation stricte
- ❌ **JAMAIS ignorer** les incohérences secteur/domaine (REJETER systématiquement)

## ✅ OBLIGATIONS
- ✅ **PRIORITÉ AU SITE OFFICIEL** : Vérifier TOUJOURS le site officiel EN PRIORITÉ (mentions légales, footer, About)
- ✅ **Si société mère trouvée dans source externe** : VALIDER ABSOLUMENT la cohérence secteur/domaine avant de confirmer
- ✅ **Si validation échoue** : Rejeter et considérer l'entité comme société mère (`is_parent_company: true`)
- ✅ **Si aucune société mère trouvée** → Retourner l'entité comme société mère (`is_parent_company: true`, `confidence: 0.9+`)
- ✅ **TOUJOURS vérifier** la cohérence secteur/domaine avant de confirmer une société mère
- ✅ **Fournir au moins 1 source** consultée
- ✅ **En MODE URL : PRIORITÉ à ≥1 source du même domaine** que l'input (recommandé, pas obligatoire si sources externes fiables utilisées)
- ✅ **Vérification multi-source** : Croiser au moins 2 sources indépendantes pour confirmer une société mère

# 📄 FORMAT DE SORTIE JSON STRICT

Tu DOIS retourner UNIQUEMENT un objet JSON valide, sans texte avant ou après. Format exact :

{
  "parent_company_name": "Nom de la société mère (GROUPE)",
  "parent_website": "URL du site web de la société mère ou null",
  "sector": "Secteur d'activité principal (ex: 'emballage', 'instruments dentaires') ou null",
  "confidence": 0.95,
  "is_parent_company": false,
  "sources": ["URL1", "URL2"],
  "methodology_notes": ["Note 1", "Note 2"]
}

**Champs obligatoires** :
- `parent_company_name` : Nom du GROUPE (pas de la filiale locale)
- `parent_website` : URL du site du groupe (ou null si non trouvé)
- `sector` : Secteur d'activité principal
- `confidence` : Score 0.0-1.0
- `is_parent_company` : `true` si l'entité EST la société mère, `false` si c'est une filiale
- `sources` : Liste d'URLs consultées (minimum 1, en MODE URL : ≥1 du même domaine)
- `methodology_notes` : Liste de notes explicatives sur le processus de recherche

# 📊 GRILLE SCORE DE CONFIANCE
- **0.95-1.0** : Trouvé sur site officiel ou registre + validation réussie
- **0.85-0.94** : Trouvé dans rapport annuel ou mentions légales + validation réussie
- **0.70-0.84** : Trouvé dans presse fiable ou base de données pro + validation partielle
- **0.50-0.69** : Information trouvée mais nécessite vérification supplémentaire
- **<0.50** : Information incertaine (à éviter)

# 📝 EXEMPLES CONCRETS

## Exemple 1 : Filiale détectée → Identifier le GROUPE + Secteur
**Input** : `https://www.fromm-pack.fr/`
**Process** :
1. Détecte "FROMM Pack France" dans footer → Suffixe LOCAL détecté (France)
2. Cherche société mère dans mentions légales
3. Trouve "FROMM Holding AG" (Suisse)
4. Identifie domaine du groupe : "fromm-pack.com"
5. Identifie secteur : "emballage et conditionnement" (produits de sécurisation de charges)
6. **VALIDATION** : Secteur cohérent (emballage), domaine lié (fromm-pack), géographie cohérente (Europe)

**Output** :
{
  "parent_company_name": "FROMM Holding AG",
  "parent_website": "https://www.fromm-pack.com",
  "sector": "emballage et conditionnement",
  "confidence": 0.95,
  "is_parent_company": false,
  "sources": ["https://www.fromm-pack.fr/mentions-legales", "https://www.fromm-pack.com/about"],
  "methodology_notes": ["Filiale détectée: FROMM Pack France SAS → Société mère: FROMM Holding AG (Suisse)", "Validation réussie: secteur cohérent, domaine lié", "Secteur identifié: emballage et conditionnement"]
}

## Exemple 2 : Société mère (pas de filiale)
**Input** : `LVMH`
**Process** :
1. Cherche "LVMH" → Trouve "LVMH Moët Hennessy Louis Vuitton SE"
2. Aucun suffixe local (SE = Societas Europaea, holding européen)
3. Vérifie : c'est bien la société mère du groupe
4. Identifie secteur : "luxe et mode" (produits de luxe)

**Output** :
{
  "parent_company_name": "LVMH",
  "parent_website": "https://www.lvmh.com",
  "sector": "luxe et mode",
  "confidence": 1.0,
  "is_parent_company": true,
  "sources": ["https://www.lvmh.com/group/", "https://www.lvmh.fr/actionnaires/"],
  "methodology_notes": ["LVMH est la société mère du groupe (holding européen SE)", "Secteur: luxe et mode"]
}

## Exemple 3 : ErgoPack - Société mère indépendante (cas critique anti-homonyme)
**Input** : `https://www.ergopack.com/en/`
**Process** :
1. Analyse `ergopack.com` → Secteur : machines de cerclage de palettes ergonomiques
2. Cherche société mère dans mentions légales, footer, page "About Us"
3. **RÉSULTAT** : Aucune mention de société mère trouvée sur le site officiel
4. **VÉRIFIE** sur le site : ErgoPack est présenté comme entreprise indépendante (Made in Germany - Home in the world)
5. **RECHERCHE EXTERNE** : Aucune société mère trouvée dans registres officiels cohérente avec le secteur
6. **CONCLUSION** : ErgoPack EST la société mère, pas une filiale

**Output** :
{
  "parent_company_name": "ErgoPack",
  "parent_website": "https://www.ergopack.com",
  "sector": "machines de cerclage de palettes",
  "confidence": 0.95,
  "is_parent_company": true,
  "sources": ["https://www.ergopack.com/en/", "https://www.ergopack.com/en/about-us"],
  "methodology_notes": ["Aucune société mère trouvée sur le site officiel", "ErgoPack présenté comme entreprise indépendante", "Secteur: machines de cerclage de palettes ergonomiques", "Validation anti-homonyme réussie"]
}

## Exemple 4 : Groupe identifié malgré nom de filiale
**Input** : `ACOEM France SAS`
**Process** :
1. Détecte suffixe "SAS" → Filiale française
2. Cherche société mère : trouve "ACOEM Group"
3. Identifie domaine groupe : "acoem.com"
4. Identifie secteur : "acoustique et vibrations" (instruments de mesure)
5. **VALIDATION** : Secteur cohérent, domaine lié, géographie cohérente (Europe)

**Output** :
{
  "parent_company_name": "ACOEM Group",
  "parent_website": "https://www.acoem.com",
  "sector": "acoustique et vibrations",
  "confidence": 0.92,
  "is_parent_company": false,
  "sources": ["https://www.acoem.com/about/", "https://www.acoem.fr/mentions-legales/"],
  "methodology_notes": ["Filiale détectée: ACOEM France SAS → Groupe: ACOEM Group", "Validation réussie: secteur cohérent, domaine lié", "Secteur: acoustique et vibrations"]
}

# ✅ CHECKLIST FINALE (PAR ORDRE DE PRIORITÉ)
1. ✅ **ÉTAPE 1** : Déterminer mode (URL/NOM) + Extraire secteur entité + Détecter filiale locale
2. ✅ **ÉTAPE 2** : Si filiale → Rechercher société mère (PRIORITÉ site officiel, puis sources externes si nécessaire)
3. ✅ **ÉTAPE 3** : VALIDER tous les critères (secteur, domaine, géographie, sources même domaine)
4. ✅ **VALIDATION CRITIQUE** : Cohérence secteur/domaine/géographie entre entité et société mère
5. ✅ **FALLBACK** : Si validation échoue ou aucune société mère trouvée → `is_parent_company: true`
6. ✅ **Retourner** : JSON strict sans texte additionnel
7. ✅ **Sources** : Minimum 1 source, en MODE URL : ≥1 source du même domaine
"""



# ==========================================
#   FONCTION PRINCIPALE : ÉCLAIREUR
# ==========================================

async def run_eclaireur(
    company_name: Optional[str] = None,
    website: Optional[str] = None,
    status_manager=None,  # NOUVEAU
    session_id: Optional[str] = None  # NOUVEAU
) -> EclaireurReport:
    """
    Exécute l'Éclaireur pour identifier la société mère.

    Args:
        company_name: Nom de l'entreprise (optionnel)
        website: Site web de l'entreprise (optionnel)
        status_manager: Gestionnaire de statut pour WebSocket (optionnel)
        session_id: ID de session pour le tracking (optionnel)

    Returns:
        EclaireurReport avec les informations de la société mère
    """
    logger.info(f"🔍 Démarrage Éclaireur: {company_name or website}")
    
    # Notifier le démarrage via WebSocket si disponible
    if status_manager and session_id:
        try:
            from status.models import AgentStatus
            await status_manager.update_agent_status_detailed(
                session_id=session_id,
                agent_name="🔍 Éclaireur",
                status=AgentStatus.RUNNING,
                progress=0.3,
                message="Recherche de la société mère en cours...",
                current_step=1,
                total_steps=3,
                step_name="Phase 0 : Éclaireur"
            )
        except Exception as e:
            logger.warning(f"⚠️ Erreur notification WebSocket Éclaireur: {e}")

    # Vérifier que l'API key est disponible
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ Client OpenAI non configuré (OPENAI_API_KEY manquante)")
        # Retour par défaut en cas d'erreur
        return EclaireurReport(
            parent_company_name=company_name or "Unknown",
            parent_website=website,
            confidence=0.3,
            is_parent_company=True,  # On assume que c'est la société mère par défaut
            sources=[SourceRef(
                title="Erreur: Client OpenAI non configuré",
                url="https://error.local",
                accessibility="broken"
            )],
            methodology_notes=["❌ Impossible d'exécuter la recherche (API non configurée)"]
        )

    try:
        # Construction de la requête
        query_parts = []
        if company_name:
            query_parts.append(f"Entreprise: {company_name}")
        if website:
            query_parts.append(f"Site web: {website}")

        query = ". ".join(query_parts) + ". Identifie la société mère de cette entité."

        logger.info(f"📡 Requête Éclaireur: {query}")

        # Utiliser Responses API pour gpt-4.1-mini avec web_search
        # Combiner system prompt et query en un seul input
        full_input = f"{ECLAIREUR_SYSTEM_PROMPT}\n\n{query}"

        # Créer client synchrone pour responses.create (API synchrone uniquement)
        api_key = os.getenv("OPENAI_API_KEY")
        sync_client = OpenAI(api_key=api_key)

        # Appel dans thread pool pour ne pas bloquer
        def call_responses_api():
            return sync_client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "web_search_preview"}],
                input=full_input,
                max_output_tokens=1000
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_responses_api)

        # Compter les web_search calls depuis response.output (format Responses API)
        # IMPORTANT: Compter chaque appel UNE SEULE FOIS pour éviter les doublons
        web_search_calls = 0
        web_search_items_seen = set()
        raw_result = None

        if hasattr(response, 'output') and response.output:
            # Parcourir la liste pour trouver le message final et compter les web_search calls
            for item in response.output:
                # Identifier l'item de manière unique pour éviter les doublons
                item_id = id(item)

                # Compter les items de type web_search (une seule fois par item)
                is_web_search = False

                if hasattr(item, 'type'):
                    if item.type == 'web_search':
                        is_web_search = True
                    elif 'web_search' in str(item.type).lower():
                        is_web_search = True

                # Vérifier aussi le nom de la classe
                if not is_web_search:
                    item_type_name = type(item).__name__.lower()
                    if 'web_search' in item_type_name or 'websearch' in item_type_name:
                        is_web_search = True

                # Compter une seule fois par item unique
                if is_web_search and item_id not in web_search_items_seen:
                    web_search_calls += 1
                    web_search_items_seen.add(item_id)
                    logger.debug(f"🔍 [Éclaireur] Web_search call détecté: type={getattr(item, 'type', 'N/A')}, class={type(item).__name__}")

                # Extraire le message de sortie
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        # Extraire le texte de chaque élément de contenu
                        text_parts = []
                        for content_item in item.content:
                            if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                if hasattr(content_item, 'text'):
                                    text_parts.append(content_item.text)
                        if text_parts:
                            raw_result = '\n'.join(text_parts)
                # Fallback: essayer d'accéder directement au texte si disponible
                elif hasattr(item, 'text') and not raw_result:
                    raw_result = item.text

        if web_search_calls > 0:
            logger.info(f"🔍 [Éclaireur] Total: {web_search_calls} web_search call(s)")

        # Tracking des tokens
        if response.usage:
            # Support pour les deux formats: ancien (prompt_tokens/completion_tokens) et nouveau (input_tokens/output_tokens)
            input_tokens = getattr(response.usage, 'input_tokens', None) or getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'output_tokens', None) or getattr(response.usage, 'completion_tokens', 0)
            total_tokens = getattr(response.usage, 'total_tokens', input_tokens + output_tokens)
            
            # Vérifier s'il y a des tokens supplémentaires (reasoning, tool calls, etc.)
            # Les tokens reasoning sont dans output_tokens_details.reasoning_tokens (pour responses.create)
            # ou completion_tokens_details.reasoning_tokens (pour chat.completions)
            reasoning_tokens = 0
            tool_tokens = 0
            
            usage = response.usage
            
            # PRIORITÉ 1: Essayer output_tokens_details (pour responses.create API)
            if hasattr(usage, 'output_tokens_details'):
                output_details = usage.output_tokens_details
                if hasattr(output_details, 'reasoning_tokens'):
                    reasoning_tokens = getattr(output_details, 'reasoning_tokens', 0) or 0
                # Essayer aussi comme dict
                elif isinstance(output_details, dict):
                    reasoning_tokens = output_details.get('reasoning_tokens', 0) or 0
                
                # Tool tokens dans output_tokens_details aussi
                if hasattr(output_details, 'tool_tokens'):
                    tool_tokens = getattr(output_details, 'tool_tokens', 0) or 0
                elif isinstance(output_details, dict):
                    tool_tokens = output_details.get('tool_tokens', 0) or 0
            
            # PRIORITÉ 2: Essayer completion_tokens_details (pour chat.completions API)
            if reasoning_tokens == 0 and hasattr(usage, 'completion_tokens_details'):
                completion_details = usage.completion_tokens_details
                if hasattr(completion_details, 'reasoning_tokens'):
                    reasoning_tokens = getattr(completion_details, 'reasoning_tokens', 0) or 0
                # Essayer aussi comme dict
                elif isinstance(completion_details, dict):
                    reasoning_tokens = completion_details.get('reasoning_tokens', 0) or 0
                
                # Tool tokens dans completion_tokens_details aussi
                if tool_tokens == 0:
                    if hasattr(completion_details, 'tool_tokens'):
                        tool_tokens = getattr(completion_details, 'tool_tokens', 0) or 0
                    elif isinstance(completion_details, dict):
                        tool_tokens = completion_details.get('tool_tokens', 0) or 0
            
            # PRIORITÉ 3: Essayer directement sur usage (fallback)
            if reasoning_tokens == 0:
                reasoning_tokens = (
                    getattr(usage, 'reasoning_tokens', None) or 
                    getattr(usage, 'reasoning_token_count', None) or
                    getattr(usage, 'reasoning_tokens_used', None) or
                    0
                )
            
            if tool_tokens == 0:
                tool_tokens = (
                    getattr(usage, 'tool_tokens', None) or 
                    getattr(usage, 'tool_token_count', None) or
                    getattr(usage, 'tool_tokens_used', None) or
                    0
                )
            
            # IMPORTANT: D'après la documentation OpenAI, les reasoning tokens sont DÉJÀ inclus dans output_tokens
            # Référence: https://platform.openai.com/docs/guides/reasoning/how-reasoning-works
            # "These tokens are billed as output tokens" - ils sont déjà comptés dans output_tokens
            # On ne doit PAS les ajouter au calcul du coût
            effective_output_tokens = output_tokens
            if reasoning_tokens > 0:
                logger.info(f"🔍 [Éclaireur] Reasoning tokens détectés: {reasoning_tokens} (déjà inclus dans output_tokens: {output_tokens})")
            if tool_tokens > 0:
                # Les tool_tokens peuvent être facturés séparément selon le modèle, mais pour l'instant
                # on les considère comme inclus dans output_tokens aussi
                logger.info(f"🔧 [Éclaireur] Tool tokens détectés: {tool_tokens}")

            logger.info(
                f"💰 [Éclaireur] Tokens: {input_tokens} in + "
                f"{effective_output_tokens} out (reasoning: {reasoning_tokens} déjà inclus, tool: {tool_tokens}) = {total_tokens} total"
            )

            # Envoyer au ToolTokensTracker
            try:
                session_id = get_session_context()

                # Calcul du coût estimé pour logging
                estimated_token_cost = (input_tokens * 0.40 + effective_output_tokens * 1.60) / 1_000_000
                estimated_search_cost = web_search_calls * 0.01
                estimated_total = estimated_token_cost + estimated_search_cost

                logger.info(
                    f"💰 [Éclaireur] Coût estimé: "
                    f"Tokens: ${estimated_token_cost:.6f}, "
                    f"Web search: ${estimated_search_cost:.4f}, "
                    f"Total: ${estimated_total:.6f}"
                )

                ToolTokensTracker.add_tool_usage(
                    session_id=session_id,
                    tool_name='eclaireur',
                    model='gpt-4.1-mini',
                    input_tokens=input_tokens,
                    output_tokens=effective_output_tokens,  # Ne PAS ajouter reasoning_tokens (déjà inclus)
                    web_search_calls=web_search_calls
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur tracking tokens Éclaireur: {e}")

        # Si pas de résultat trouvé, essayer d'autres attributs (fallback)
        if not raw_result:
            if hasattr(response, 'output_text'):
                raw_result = response.output_text
            elif hasattr(response, 'text'):
                raw_result = response.text
            else:
                logger.error(f"❌ Impossible d'extraire le résultat de la réponse Éclaireur pour {company_name or website}")
                return EclaireurReport(
                    parent_company_name=company_name or "Unknown",
                    confidence=0.0,
                    sources=[]
                )

        logger.info(f"✅ Éclaireur terminé: {company_name or website}")

        # Parser le JSON
        parsed = parse_json_response(raw_result, "eclaireur")

        # Vérifier si erreur de parsing
        if "error" in parsed:
            logger.warning(f"⚠️ Erreur parsing Éclaireur: {parsed.get('error')}")
            # Retour par défaut
            return EclaireurReport(
                parent_company_name=company_name or "Unknown",
                parent_website=website,
                confidence=0.3,
                is_parent_company=True,
                sources=[SourceRef(
                    title="Erreur de parsing",
                    url=website or "https://error.local",
                    accessibility="broken"
                )],
                methodology_notes=[f"❌ Erreur: {parsed.get('error')}"]
            )

        # Construire les SourceRef depuis les URLs
        sources = []
        for source_url in parsed.get("sources", []):
            if source_url and source_url != "N/A":
                sources.append(SourceRef(
                    title="Source Éclaireur",
                    url=source_url,
                    accessibility="ok"
                ))

        # Si pas de sources, ajouter le site web par défaut
        if not sources and website:
            sources.append(SourceRef(
                title="Site web de l'entreprise",
                url=website,
                accessibility="ok"
            ))

        # Construire le rapport
        report = EclaireurReport(
            parent_company_name=parsed.get("parent_company_name", company_name or "Unknown"),
            parent_website=parsed.get("parent_website"),
            sector=parsed.get("sector"),  # NOUVEAU : Extraire le secteur
            confidence=parsed.get("confidence", 0.5),
            is_parent_company=parsed.get("is_parent_company", False),
            sources=sources if sources else [SourceRef(
                title="Pas de source disponible",
                url="https://error.local",
                accessibility="broken"
            )],
            methodology_notes=parsed.get("methodology_notes", [])
        )

        logger.info(
            f"✅ Éclaireur: {report.parent_company_name} "
            f"(confiance: {report.confidence:.2f}, "
            f"is_parent: {report.is_parent_company}, "
            f"secteur: {report.sector or 'Non identifié'})"
        )
        
        # Notifier la fin via WebSocket si disponible
        if status_manager and session_id:
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🔍 Éclaireur",
                    status="completed",
                    progress=1.0,
                    message=f"Société mère identifiée: {report.parent_company_name}",
                    current_step=1,
                    total_steps=3,
                    step_name="Phase 0 : Éclaireur",
                    performance_metrics={
                        "confidence": report.confidence,
                        "parent_company": report.parent_company_name
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Erreur notification WebSocket fin Éclaireur: {e}")

        return report

    except Exception as e:
        logger.error(f"❌ Erreur Éclaireur: {e}")
        
        # Notifier l'erreur via WebSocket si disponible
        if status_manager and session_id:
            try:
                await status_manager.update_agent_status_detailed(
                    session_id=session_id,
                    agent_name="🔍 Éclaireur",
                    status="error",
                    progress=0.0,
                    message=f"Erreur: {str(e)}",
                    current_step=1,
                    total_steps=3,
                    step_name="Phase 0 : Éclaireur"
                )
            except Exception as ws_error:
                logger.warning(f"⚠️ Erreur notification WebSocket erreur Éclaireur: {ws_error}")

        # Retour d'un rapport d'erreur
        return EclaireurReport(
            parent_company_name=company_name or "Unknown",
            parent_website=website,
            confidence=0.3,
            is_parent_company=True,
            sources=[SourceRef(
                title="Erreur d'exécution",
                url=website or "https://error.local",
                accessibility="broken"
            )],
            methodology_notes=[f"❌ Erreur: {str(e)}"]
        )
