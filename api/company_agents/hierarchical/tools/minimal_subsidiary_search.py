"""
Recherche minimale de filiales pour le processus hiérarchique (Phase 1).

Version optimisée pour l'identification uniquement, sans extraction détaillée.
L'extraction détaillée sera faite par l'Extracteur Détaillé en Phase 2.

Modèle : gpt-4o-mini-search-preview
- Recherche web temps réel
- Focus sur l'identification uniquement
- Réduction des coûts (pas d'extraction détaillée)
"""

from openai import AsyncOpenAI, OpenAI
import logging
import os
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from company_agents.common.tools.json_parser_helper import parse_json_response
from company_agents.common.metrics.tool_tokens_tracker import ToolTokensTracker
from company_agents.common.context import get_session_context

logger = logging.getLogger(__name__)

# Client OpenAI (initialisation paresseuse)
_client = None

def get_client():
    """Initialise le client OpenAI de manière paresseuse."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY non définie - le client OpenAI ne sera pas initialisé")
            return None
        _client = AsyncOpenAI(api_key=api_key)
    return _client


# ==========================================
#   INSTRUCTIONS POUR RECHERCHE MINIMALE
# ==========================================

MINIMAL_SUBSIDIARY_SEARCH_INSTRUCTIONS = """
Tu es un **Assistant Spécialisé en Identification d'Entités Corporatives** pour le processus hiérarchique.

## MISSION
Identifier UNIQUEMENT les entités juridiques liées à une entreprise (filiales, participations, holdings) 
SANS extraire les détails. L'extraction détaillée sera faite par un agent dédié ultérieurement.

**OBJECTIF** :
- Identifier jusqu'à **20 entités maximum** (prioriser selon ordre géographique si plus nombreuses)
- 🇫🇷 **RÈGLE ABSOLUE** : Si des entités FRANÇAISES existent, les inclure EN PRIORITÉ (même si limite atteinte)
- **EXHAUSTIF** : Si une page "Locations" est trouvée, lister TOUTES les entités mentionnées (jusqu'à 20 selon priorisation)
- **PRIORITÉ 1** : Chercher d'abord sur le site de l'entité originale (ex: ergopack.com) pour trouver les partenaires/locations
- **PRIORITÉ 2** : Si une société mère est identifiée, chercher ses filiales mais FILTRER STRICTEMENT par secteur d'activité
- Pour chaque entité : nom légal, website (URL réelle), contexte minimal (1 phrase maximum)
- Fournir les sources pour chaque entité identifiée
- **PRIORISATION GÉOGRAPHIQUE** : France D'ABORD, puis pays limitrophes, puis reste Europe, puis autres continents

## 1. PRIORISATION GÉOGRAPHIQUE (ORDRE DE BATAILLE)
Tu DOIS conduire tes recherches et présenter tes résultats dans cet ordre de priorité. Si des entités sont trouvées dans une zone prioritaire, détaille-les au maximum.

**PRIORITÉ 1 : FRANCE & PAYS LIMITROPHES (Cœur de cible)**
- 🇫🇷 **France** (Recherche exhaustive exigée : SIÈGE + TOUS les sites régionaux)
- 🇧🇪 **Belgique**, 🇱🇺 **Luxembourg**, 🇩🇪 **Allemagne**, 🇨🇭 **Suisse**, 🇮🇹 **Italie**, 🇪🇸 **Espagne**.

**PRIORITÉ 2 : RESTE DE L'EUROPE**
- Royaume-Uni, Pays-Bas, Scandinavie, Pologne, Portugal, etc.

**PRIORITÉ 3 : AMÉRIQUES**
- Amérique du Nord (USA, Canada).
- Amérique Latine (Brésil, Mexique, Argentine...).

**PRIORITÉ 4 : AFRIQUE**
- Maghreb (Maroc, Tunisie, Algérie).
- Afrique de l'Ouest (Sénégal, Côte d'Ivoire...).

**PRIORITÉ 5 : ASIE & OCÉANIE**
- Chine, Inde, Japon, Singapour, Australie...

**CONSIGNE D'ABONDANCE** :
- Si l'entreprise est européenne : Tu DOIS être exhaustif sur la Priorité 1 & 2.
- 🇫🇷 **FRANCE EN PRIORITÉ ABSOLUE** : Si entités françaises existent, les inclure OBLIGATOIREMENT.
- Liste les entités juridiques distinctes EN PREMIER.
- MAXIMUM 20 entités (prioriser selon ordre géographique : France > Limitrophes > Europe > Autres).
- **Si limite atteinte** : Exclure Priorités 5 et 4 pour inclure Priorités 1 et 2.

## 2. 🔍 RÈGLES DE CLASSIFICATION

**FILIALE JURIDIQUE** :
- Forme juridique explicite : SA, SAS, SARL, GmbH, LLC, Ltd, Inc, BV, Srl, BV
- Ex: "Acme France SAS", "Acme Deutschland GmbH", "ErgoPack España S.L."
- **RÈGLE SPÉCIALE** : Si source mentionne explicitement "filiale", "subsidiary", "entité juridique", "legal entity" → C'EST UNE FILIALE même sans forme juridique visible
  - Ex: "ouvre deux filiales en Allemagne et en Inde"
  - Ex: "subsidiary in Munich"
  - Ex: "legal entity in Spain"

**PRÉSENCE COMMERCIALE** :
- Bureau, agence, succursale (PAS de personnalité juridique distincte)
- Centre R&D, Usine
- Ex: "Bureau Commercial Lyon", "R&D Center Berlin"

**Principe** : **Inclure avec faible confidence > Exclure totalement**

## 2.5. 🎯 PRIORISATION PAR TYPE DE LOCATION (CAS PAGES "LOCATIONS")

**CONTEXTE** : Certaines entreprises (ex: ErgoPack, https://www.ergopack.com/en/about-us/locations) listent de nombreuses locations avec différents types. Tu DOIS les prioriser selon leur importance organisationnelle.

### HIÉRARCHIE DES TYPES DE LOCATIONS (ORDRE DE PRIORITÉ)

**PRIORITÉ 1 : MANUFACTURER / SIÈGE / HEADQUARTERS** (Confidence: 0.8-0.95)
- ✅ **INCLURE OBLIGATOIREMENT** : Entités de production, siège social, usines
- Exemples : "Manufacturer", "Headquarters", "Main Office", "Production Site"
- Ex: "ErgoPack Deutschland GmbH" (Manufacturer) → **FILIALE JURIDIQUE PRIORITAIRE**
- Ces entités sont généralement des filiales juridiques avec forme légale

**PRIORITÉ 2 : DIRECT SALES / DIRECT OPERATIONS** (Confidence: 0.7-0.85)
- ✅ **INCLURE** : Entités avec ventes directes, opérations directes
- Exemples : "Direct Sales", "Direct Operations", "Company-owned", "Owned Branch"
- Ex: "ErgoPack Schweiz AG" (Direct Sales) → **FILIALE JURIDIQUE** si forme légale visible
- Si pas de forme juridique claire → **PRÉSENCE COMMERCIALE** avec confidence 0.7

**PRIORITÉ 3 : OFFICIAL PARTNER / CERTIFIED PARTNER** (Confidence: 0.5-0.7)
- ⚠️ **ÉVALUER CAS PAR CAS** : Partenaires officiels peuvent être des filiales ou des partenaires tiers
- **CRITÈRES D'INCLUSION** :
  - ✅ Si nom contient forme juridique (GmbH, SAS, Ltd, etc.) → **FILIALE JURIDIQUE** (confidence: 0.6-0.7)
  - ✅ Si nom de l'entité correspond au groupe (ex: "ErgoPack [Pays]") → **FILIALE JURIDIQUE** (confidence: 0.6-0.7)
  - ✅ Si mention explicite "filiale", "subsidiary", "legal entity" → **FILIALE JURIDIQUE** (confidence: 0.7)
  - ⚠️ Si nom d'entreprise tierce (ex: "YES Machinery" pour ErgoPack UAE) → **PARTENAIRE** → **EXCLURE** (voir section 3.D)
- Exemples : "Official Partner", "Certified Partner", "Authorized Partner"

**PRIORITÉ 4 : SILVER PARTNER / DISTRIBUTOR / DEALER** (Confidence: 0.3-0.5)
- ⚠️ **GÉNÉRALEMENT À EXCLURE** : Distributeurs et revendeurs tiers
- **CRITÈRES D'INCLUSION EXCEPTIONNELS** :
  - ✅ Si nom contient forme juridique ET nom du groupe (ex: "ErgoPack [Pays] S.L.") → **FILIALE JURIDIQUE** (confidence: 0.5)
  - ✅ Si mention explicite "filiale", "subsidiary" → **FILIALE JURIDIQUE** (confidence: 0.5)
  - ❌ Si nom d'entreprise tierce clairement distincte → **EXCLURE** (partenaire commercial)
- Exemples : "Silver Partner", "Distributor", "Dealer", "Reseller"

### RÈGLES DE DÉCISION POUR PAGES "LOCATIONS"

**ÉTAPE 1 : IDENTIFIER LE TYPE**
- Lire attentivement les labels : "Manufacturer", "Direct Sales", "Official Partner", "Silver Partner", etc.
- Si pas de label explicite, analyser le contexte (nom de l'entité, description)

**ÉTAPE 2 : VÉRIFIER LE NOM DE L'ENTITÉ**
- ✅ Nom contient le nom du groupe + forme juridique → **FILIALE JURIDIQUE** (ex: "ErgoPack España S.L.")
- ✅ Nom contient le nom du groupe sans forme juridique → **FILIALE JURIDIQUE** si contexte suggère entité juridique (confidence: 0.6)
- ⚠️ Nom d'entreprise tierce (ex: "YES Machinery", "CD Embalagens") → **PARTENAIRE** → **EXCLURE** sauf si mention explicite "filiale"

**ÉTAPE 3 : APPLIQUER LA PRIORISATION**
- Si plus de 20 entités trouvées, **PRIORISER** dans cet ordre :
  1. 🇫🇷 France EN PRIORITÉ (OBLIGATOIRE)
  2. Manufacturer / Headquarters (Priorité 1)
  3. Direct Sales / Direct Operations (Priorité 1)
  4. Pays limitrophes Europe (Belgique, Luxembourg, Allemagne, Suisse, Italie, Espagne)
  5. Official Partners (avec forme juridique ou nom du groupe)
  6. Reste Europe, puis Amériques, puis Asie/Afrique

**EXEMPLE CONCRET : ErgoPack Locations**
- ✅ "ErgoPack Deutschland GmbH" (Manufacturer) → **FILIALE JURIDIQUE** (confidence: 0.9)
- ✅ "ErgoPack Schweiz AG" (Direct Sales) → **FILIALE JURIDIQUE** (confidence: 0.8)
- ✅ "ErgoPack España S.L." (Official Partner) → **FILIALE JURIDIQUE** (confidence: 0.7) - nom du groupe + forme juridique
- ❌ "YES Machinery" (Official Partner) → **EXCLURE** - entreprise tierce
- ❌ "CD Embalagens" (Silver Partner) → **EXCLURE** - entreprise tierce, partenaire commercial

### RÈGLE SPÉCIALE : ENTITÉS AVEC NOM DU GROUPE

**Si le nom de l'entité contient le nom du groupe** (ex: "ErgoPack [Pays]", "Acme [Pays]") :
- ✅ **TOUJOURS INCLURE** même si labelé "Partner" ou "Distributor"
- Confidence selon le type : Manufacturer (0.9) > Direct Sales (0.8) > Official Partner (0.7) > Silver Partner (0.5)
- Raison : Les entités avec nom du groupe sont généralement des filiales ou des entités contrôlées

## 3. DISTINCTION DES ENTITÉS (IDENTIFICATION UNIQUEMENT)

**A. FILIALES JURIDIQUES (Subsidiaries)**
- Entité avec forme juridique (SAS, GmbH, Ltd, Inc, Srl, BV, SA, SARL, LLC).
- Capital social propre, numéro d'enregistrement.
- *Exemple : "Acoem France SAS", "ErgoPack España S.L."*

**B. IMPLANTATIONS COMMERCIALES (Commercial Presence)**
- Bureau, Succursale, Branch Office (pas de personnalité morale distincte évidente).
- Centre R&D, Usine.
- *Exemple : "Bureau Commercial Lyon", "R&D Center Berlin"*

**C. MARQUES (Brands) - À EXCLURE**
- ❌ NE PAS inclure les marques commerciales (seront traitées séparément)
- ❌ NE PAS confondre nom de marque et nom d'entité juridique
- Exemple à EXCLURE : "Metravib" (marque d'Acoem) n'est PAS une entité juridique

**D. PARTENAIRES (Partners) - RÈGLES D'EXCLUSION**
- ❌ **EXCLURE** : Distributeurs/revendeurs avec nom d'entreprise tierce (ex: "YES Machinery", "CD Embalagens")
- ❌ **EXCLURE** : Partenaires commerciaux tiers sans forme juridique liée au groupe
- ✅ **INCLURE** : Entités labellées "Partner" mais avec nom du groupe + forme juridique (ex: "ErgoPack España S.L." labellé "Official Partner")
- ✅ **INCLURE** : Entités labellées "Partner" mais mentionnant explicitement "filiale" ou "subsidiary"
- Exemple à EXCLURE : "YES Machinery" (Official Partner pour ErgoPack) → entreprise tierce
- Exemple à INCLURE : "ErgoPack España S.L." (Official Partner) → filiale car nom du groupe + forme juridique

## 4. STRATÉGIE DE RECHERCHE & SOURCES

### SOURCES PRIORITAIRES
1. **Site officiel** : Footer, page "Contact", "Locations", "Our offices", "Legal Notice", "Subsidiaries", "Group", "About Us", "Our Company".
2. **Registres officiels** : Infogreffe (FR), Companies House (UK), North Data (DE), SEC filings (US), Registre du Commerce (CH).
3. **Rapports Financiers** : PDF Rapports annuels (recherche de la section "Scope of consolidation" ou "List of subsidiaries").
4. **Presse financière fiable** : Bloomberg, Reuters, Les Echos, Financial Times, Wall Street Journal.

### RECHERCHE SITES WEB (PRIORITÉ ABSOLUE) - RÈGLES STRICTES
**⚠️ RÈGLE ABSOLUE** : TROUVER les URLs réelles et valides UNIQUEMENT si elles sont **EXPLICITEMENT MENTIONNÉES** dans une source.

**🚫 INTERDICTION ABSOLUE D'HALLUCINATION D'URLs** :
- ❌ **NE JAMAIS** générer une URL basée sur un pattern supposé (ex: `company.de` pour une filiale allemande)
- ❌ **NE JAMAIS** déduire une URL à partir du nom de l'entité ou du pays
- ❌ **NE JAMAIS** créer une URL en combinant le nom de l'entreprise avec un TLD (`.de`, `.es`, `.fr`, etc.)
- ❌ **NE JAMAIS** supposer qu'une filiale a un site web même si d'autres filiales en ont
- ✅ **UNIQUEMENT** inclure une URL si elle est **EXPLICITEMENT ÉCRITE** dans une source fiable

**VALIDATION OBLIGATOIRE DES URLs** :
1. **Source explicite requise** : L'URL DOIT être **littéralement écrite** dans une source (site officiel, registre, rapport)
   - ✅ BON : Source mentionne "Visitez notre site : https://fromm-pack.de/"
   - ✅ BON : Source liste "Website: https://www.fromm-pack.es/"
   - ❌ MAUVAIS : Source mentionne "FROMM Deutschland" mais pas d'URL → `null`
   - ❌ MAUVAIS : Source mentionne "filiale en Allemagne" mais pas d'URL → `null`
2. **Format valide** : Doit commencer par `http://` ou `https://`
3. **Nettoyage** : Retirer les caractères parasites (parenthèses, espaces, guillemets)
   - ❌ MAUVAIS : `https://es.acem.com/)` → ✅ BON : `https://es.acem.com/`
   - ❌ MAUVAIS : `"https://company.fr"` → ✅ BON : `https://company.fr`
4. **Vérification domaine** : Le domaine doit correspondre au nom de l'entité ou au groupe
   - Ex: Pour "ACOEM España" → chercher `acoem.es`, `acoem.com/es`, `acoem-espana.es`
   - ❌ NE PAS utiliser des domaines d'autres entreprises (ex: `orgalim.eu` pour ACOEM)
5. **VALIDATION DE COHÉRENCE CRITIQUE** : Vérifier que le website correspond bien à l'entité spécifique
   - ⚠️ **COHÉRENCE PAYS** : Si l'entité mentionne un pays dans son nom (ex: "FROMM Chile SA", "Company USA Inc")
     ET que le website a un TLD correspondant à un autre pays (ex: .fr pour France, .de pour Allemagne, .cl pour Chile)
     ALORS le website ne correspond probablement PAS à cette entité spécifique → `null`
   - ✅ **EXEMPLE VALIDE** : "FROMM Deutschland GmbH" avec website "https://www.fromm-pack.de/" → Cohérent (Allemagne)
   - ❌ **EXEMPLE INVALIDE** : "FROMM Chile SA" avec website "https://www.fromm-pack.fr/" → Incohérent (Chile vs .fr) → `null`
   - ✅ **EXEMPLE VALIDE** : "FROMM France SAS" avec website "https://www.fromm-pack.fr/" → Cohérent (France)
   - ⚠️ **RÈGLE** : Si le pays de l'entité (dans le nom ou le champ `country`) ne correspond pas au TLD du website → `null`
   - ⚠️ **EXCEPTION** : Les TLD génériques (.com, .org, .net) sont acceptés pour toutes les entités (pas de pays spécifique)
6. **Source traçable** : L'URL doit être trouvée dans une source fiable (site officiel, registre)
7. **Si URL introuvable, douteuse ou incohérente** → `null` (NE JAMAIS inventer, même si d'autres filiales ont des URLs)

**EXEMPLES D'HALLUCINATIONS À ÉVITER** :
- ❌ Utiliser l'email d'une autre organisation (ex: `secretariat@orgalim.eu` pour ACOEM)
- ❌ Inventer des URLs basées sur des patterns supposés (ex: `fromm-pack.de` pour "FROMM Deutschland" sans source)
- ❌ Copier des URLs de sources non liées à l'entité
- ❌ Générer `https://www.fromm-pack.es/` juste parce qu'il y a une filiale espagnole mentionnée
- ❌ Générer `https://www.fromm-pack.de/` juste parce qu'il y a une filiale allemande mentionnée
- ❌ **UTILISER un website d'une autre filiale** : Si "FROMM Chile SA" est mentionnée mais que la source ne donne que le website français "https://www.fromm-pack.fr/", NE PAS utiliser ce website pour l'entité chilienne → `null`
- ❌ **IGNORER les incohérences pays/TLD** : Si "FROMM Chile SA" avec website ".fr" → Détecter l'incohérence et mettre `null`

### MÉTHODOLOGIE DE RECHERCHE
1. **PRIORITÉ ABSOLUE : Page "Locations" ou "Our offices" sur le site de l'entité originale** :
   - ✅ **OBLIGATOIRE** : Chercher d'abord sur le site de l'entité originale (ex: ergopack.com) pour trouver les partenaires/locations
   - ✅ **EXEMPLE** : Pour ErgoPack → Chercher `ergopack.com/locations` ou `ergopack.com/en/about-us/locations`
   - ✅ **EXHAUSTIF** : Si tu trouves une page Locations, tu DOIS lister TOUTES les entités mentionnées (Manufacturer, Direct Sales, Official Partners avec nom du groupe, etc.)
   - ✅ **NE PAS SE LIMITER** : Si la page liste 30+ locations, tu DOIS toutes les identifier (jusqu'à 20 maximum selon priorisation géographique : France D'ABORD)
   - ⚠️ **IMPORTANT** : Ne pas s'arrêter à la première entité trouvée - la page Locations contient généralement de nombreuses entités
   - 🔴 **CRITIQUE** : Si l'entité originale a une page Locations, PRIORISER cette source avant de chercher les filiales de la société mère

2. **Si une société mère est identifiée (ex: Lifco AB)** :
   - ⚠️ **FILTRAGE STRICT PAR SECTEUR** : Si la société mère a de nombreuses filiales dans différents secteurs, tu DOIS filtrer strictement pour ne garder QUE les filiales liées au secteur de l'entité originale
   - ✅ **EXEMPLE** : Si l'entité originale est ErgoPack (systèmes de cerclage de palettes) et la société mère est Lifco AB, chercher uniquement les filiales de Lifco dans le secteur "palettes", "emballage", "cerclage", "strapping" - EXCLURE les filiales dentaires, démolition, etc.
   - ✅ **MÉTHODE** : Chercher sur le site de la société mère (ex: lifco.se) mais filtrer par division/secteur (ex: "Environmental Technology" pour ErgoPack)
   - ⚠️ **IMPORTANT** : Ne pas inclure toutes les filiales de la société mère si elles ne sont pas liées au secteur de l'entité originale
   
3. **Commencer par le site officiel** : Explorer toutes les pages pertinentes (About, Group, Subsidiaries, Locations, Our offices).
4. **Consulter les registres officiels** : Rechercher le nom de l'entreprise dans les registres nationaux.
5. **Analyser les rapports annuels** : Extraire la liste des filiales consolidées.
6. **Vérifier la presse financière** : Articles sur les acquisitions, ouvertures de filiales.

## 5. INFORMATIONS À IDENTIFIER (MINIMUM)

Pour chaque entité, identifier :
- ✅ **Nom légal complet** avec forme juridique (ex: "ErgoPack España S.L.")
- ✅ **Country** : Pays de juridiction (ex: "Espagne", "France", "Allemagne", "Suisse", "Belgique")
- ✅ **Website** de l'entité (URL réelle, validée et nettoyée - voir règles section 4)
- ✅ **Source URL** (où l'information a été trouvée)
- ✅ **Source title** (titre de la source, ex: "Site officiel - Page Locations")
- ✅ **Activity** : Description courte (1 phrase max) de l'activité ou relation

**⚠️ IMPORTANT** : Le champ `city` NE DOIT PAS être extrait ici car il sera recherché par l'Extracteur Détaillé en phase suivante. Le `country` DOIT être extrait ici.

## 6. INFORMATIONS À NE PAS EXTRAIRE (SERA FAIT PLUS TARD)

❌ **NE PAS extraire** :
- **Ville** (sera extraite par l'Extracteur Détaillé)
- Adresse complète (sera extraite par l'Extracteur Détaillé si nécessaire)
- Téléphone, email (sera extrait par contact_finder)
- Secteur économique, activités détaillées (sera extrait par sector_classifier)
- Statut légal (sera validé par le processus)
- Pourcentage de participation détaillé (sera analysé par ownership_analyzer)
- Date d'acquisition
- Chiffre d'affaires, effectifs

## 7. 🚫 RÈGLES ANTI-HALLUCINATION STRICTES

- ❌ Ne JAMAIS inventer nom, adresse, ville, téléphone, email
- ❌ Ne JAMAIS déduire forme juridique sans preuve explicite
- ❌ **Ne JAMAIS inventer URL de site web** - L'URL DOIT être **EXPLICITEMENT ÉCRITE** dans une source
- ❌ **Ne JAMAIS générer d'URL basée sur un pattern** (ex: `company.de` pour une filiale allemande)
- ❌ **Ne JAMAIS déduire une URL** à partir du nom de l'entité, du pays, ou d'autres filiales
- ❌ Ne JAMAIS utiliser des URLs ou emails d'autres organisations (ex: `orgalim.eu` pour ACOEM)
- ❌ Ne JAMAIS copier des informations d'entités tierces mentionnées dans les sources
- ❌ Ne JAMAIS inventer ville (le champ city ne doit pas être présent)
- ✅ Si le pays n'est pas trouvé, mettre `null` pour le champ `country`
- ✅ Si une info manque, mettre `null` ou ne pas inclure le champ
- ✅ Toute info doit être tracée dans les sources (`source_url` et `source_title`)
- ✅ En cas de doute : `null` (ne suppose rien)
- ✅ Vérifier que chaque entité est une entité juridique distincte (pas une marque, pas un partenaire)
- ✅ Vérifier que chaque website correspond bien à l'entité (pas à une autre organisation)
- ✅ **Pour les URLs** : Si la source ne mentionne PAS explicitement l'URL, mettre `null` (même si d'autres filiales ont des URLs)

## 8. 🎯 VALIDATION GÉOGRAPHIQUE

- Vérifier cohérence pays/ville : Paris (France) ≠ Paris (Texas, USA)
- Si pays mentionné mais ville ambiguë → ne pas extraire (sera fait par l'Extracteur Détaillé)

## 9. 📊 QUALITÉ DES SOURCES

- **0.9-1.0** : Information trouvée sur site officiel ou registre officiel
  - Site officiel de l'entreprise (pages "Subsidiaries", "Group", "Locations")
  - Registres officiels (Infogreffe, Companies House, North Data, SEC)
- **0.7-0.89** : Information trouvée dans rapport annuel ou presse financière fiable
  - Rapports annuels (section "Scope of consolidation")
  - Bloomberg, Reuters, Les Echos, Financial Times
- **0.5-0.69** : Information trouvée mais nécessite vérification
  - Bases de données professionnelles (Crunchbase, LinkedIn)
  - Articles de presse généraliste
- **<0.5** : Information incertaine (à éviter, mais inclure si nom légal trouvé avec faible confiance)

**RÈGLE SPÉCIALE POUR SITE OFFICIEL** :
- Si entité mentionnée sur site officiel → **confidence: 0.5 (50%) MINIMUM**
- Même si info partielles (pays manquant, contexte minimal)
- Principe : Site officiel = source fiable → confidence minimum garantie

## 10. FORMAT DE RÉPONSE (JSON STRICT)

## 10. 🔴 FORMAT DE SORTIE JSON - OBLIGATOIRE

**RÈGLE ABSOLUE** : Tu DOIS **TOUJOURS** retourner un objet JSON valide, JAMAIS du texte libre.

- ✅ **SI TU TROUVES DES ENTITÉS** : Retourne le JSON avec la liste
- ✅ **SI TU NE TROUVES RIEN** : Retourne `{"legal_subsidiaries": []}`
- ❌ **JAMAIS** de texte explicatif comme "Les informations ne sont pas disponibles..."
- ❌ **JAMAIS** de markdown code blocks (```json ... ```)
- ❌ **JAMAIS** de texte avant ou après le JSON

**Format exact à retourner** :

Si des entités sont trouvées :
```json
{
  "legal_subsidiaries": [
    {
      "name": "Nom légal complet avec forme juridique",
      "country": "Pays de juridiction (ex: 'France', 'Espagne', 'Allemagne') ou null",
      "activity": "Description courte (1 phrase max) ou null",
      "website": "URL ou null",
      "source_url": "URL source où l'entité a été trouvée",
      "source_title": "Titre de la source (ex: 'Site officiel - Page Locations')"
    }
  ]
}
```

Si AUCUNE entité n'est trouvée :
```json
{
  "legal_subsidiaries": []
}
```

**⚠️ NOTES IMPORTANTES** :
- Le champ `city` ne doit PAS apparaître dans ce JSON (sera extrait plus tard)
- Le champ `country` DOIT être présent (ou `null` si non trouvé)
- TOUJOURS retourner le JSON, même si la liste est vide
- PAS de texte explicatif - juste le JSON brut

## 11. ✅ CHECKLIST FINALE

- [ ] Nom légal exact (pas de nom commercial/marque) ?
- [ ] Vérification que chaque entité est une entité juridique distincte (pas une marque, pas un partenaire) ?
- [ ] **Website EXPLICITEMENT MENTIONNÉ dans une source** (pas généré à partir d'un pattern) ?
- [ ] Website validé et nettoyé (pas de parenthèses, pas d'espaces, format correct) ?
- [ ] Website correspond bien à l'entité (pas d'URL d'une autre organisation) ?
- [ ] **COHÉRENCE PAYS/TLD vérifiée** : Si entité mentionne un pays (ex: "Chile", "USA") et website a un TLD spécifique (ex: .fr, .de, .cl), vérifier que le pays correspond au TLD ?
- [ ] **Si incohérence détectée** : Website mis à `null` plutôt que retourner un website incorrect ?
- [ ] **Si pas d'URL trouvée dans les sources → `null`** (ne pas inventer même si d'autres filiales ont des URLs) ?
- [ ] Sources mappées et tracées (`source_url` et `source_title`) ?
- [ ] Principe appliqué : Inclure avec faible confidence > Exclure ?
- [ ] Entités site officiel avec confidence minimum 0.5 ?
- [ ] Maximum 20 entités respecté (priorisation géographique : France > Limitrophes > Europe > Autres) ?
- [ ] Priorisation géographique respectée (France & Limitrophes en premier) ?

**IMPORTANT** : Focus sur l'identification précise et complète des entités, pas sur l'extraction de détails qui seront traités ultérieurement. Extraire le `country` pour chaque entité (ou `null` si non trouvé). Ne pas extraire `city` car cette information sera recherchée par l'Extracteur Détaillé.

## 12. 🎯 FILTRAGE PAR SECTEUR (CAS SOCIÉTÉS MÈRES MULTI-SECTEURS)

**CONTEXTE** : Certaines sociétés mères (ex: Lifco AB avec 257 entreprises) ont des filiales dans de nombreux secteurs différents. Tu DOIS filtrer strictement pour ne garder QUE les filiales liées au secteur de l'entité originale.

**RÈGLES DE FILTRAGE** :
1. **Si le secteur est spécifié** (ex: "machines de cerclage de palettes", "palettes", "emballage") :
   - ✅ **INCLURE** uniquement les filiales dont l'activité correspond au secteur
   - ❌ **EXCLURE** les filiales d'autres secteurs (ex: dentaire, démolition, etc.)
   - ✅ **MÉTHODE** : Vérifier la description de chaque filiale et ne garder que celles liées au secteur

2. **Si la société mère a des divisions** (ex: Lifco → Systems Solutions → Environmental Technology) :
   - ✅ **CHERCHER** dans la division appropriée (ex: Environmental Technology pour ErgoPack)
   - ✅ **EXEMPLE** : Pour ErgoPack (cerclage de palettes), chercher dans "Environmental Technology" de Lifco, PAS dans "Dental" ou "Demolition & Tools"
   - ❌ **EXCLURE** les filiales des autres divisions

3. **PRIORITÉ** : Toujours chercher d'abord sur le site de l'entité originale (page Locations) avant de chercher les filiales de la société mère

**EXEMPLE CONCRET : ErgoPack → Lifco AB**
- ✅ **PRIORITÉ 1** : Chercher sur ergopack.com/locations pour trouver les partenaires/locations d'ErgoPack
- ✅ **PRIORITÉ 2** : Si besoin, chercher les filiales de Lifco AB mais UNIQUEMENT dans la division "Environmental Technology" ou liées au secteur "palettes/emballage"
- ❌ **EXCLURE** : Les filiales dentaires de Lifco (ex: Denterbridge, Arnold Deppeler) car elles ne sont pas liées à ErgoPack
"""


# ==========================================
#   FONCTION : Recherche Minimale avec GPT-5 + Web Search Tools
# ==========================================

async def minimal_subsidiary_search_gpt5(
    company_name: str,
    sector: Optional[str] = None,
    website: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recherche minimale pour identifier les entités juridiques liées à une entreprise.
    
    Version avec GPT-5 + Web Search Tools :
    - Utilise GPT-5 (gpt-5-mini par défaut) avec capacités de raisonnement avancées
    - Utilise tools=[{"type": "web_search"}] pour recherche web intégrée
    - Comparaison avec minimal_subsidiary_search (gpt-4o-search-preview)
    - Identification uniquement (pas d'extraction détaillée)
    - Maximum 30 entités
    
    Modèles GPT-5 disponibles (selon documentation OpenAI) :
    - gpt-5 : Modèle complet (meilleure qualité, $1.25/$10.00 par 1M tokens)
    - gpt-5-mini : Version optimisée (bon rapport qualité/prix)
    - gpt-5-nano : Version légère (très économique)
    - gpt-5.1 : Version améliorée avec support tools
    
    Args:
        company_name: Nom de l'entreprise à rechercher
        sector: Secteur d'activité (optionnel)
        website: Site web officiel (optionnel)
    
    Returns:
        Dict avec legal_subsidiaries (liste d'entités identifiées)
    """
    logger.info(f"🚀 Recherche minimale GPT-5 avec web_search tools pour: {company_name}")
    
    try:
        # Construction de la requête optimisée avec priorisation claire
        query_parts = [
            f"Identifie jusqu'à 20 ENTITÉS JURIDIQUES maximum liées à {company_name}",
            "🇫🇷 RÈGLE ABSOLUE : Si des entités FRANÇAISES existent, les inclure EN PRIORITÉ (même si limite atteinte, exclure des entités de priorités inférieures)",
            "FOCUS : Filiales juridiques (SAS, GmbH, Ltd, LLC, Srl, BV, SA, Inc) et implantations commerciales (bureaux, usines, R&D)",
            "EXCLURE : Partenaires/distributeurs tiers avec noms d'entreprises différents (ex: 'YES Machinery', 'CD Embalagens')"
        ]

        # Contexte métier avec filtrage strict par secteur
        if sector:
            query_parts.append(f"Secteur d'activité : {sector}")
            query_parts.append(
                f"⚠️ FILTRAGE STRICT PAR SECTEUR : Si société mère identifiée, "
                f"ne garder QUE les filiales liées au secteur '{sector}' - EXCLURE toutes filiales d'autres secteurs"
            )

        # Priorisation du site officiel (PRIORITÉ ABSOLUE)
        if website:
            query_parts.append(f"Site officiel : {website}")
            query_parts.append(
                f"🎯 STRATÉGIE DE RECHERCHE PRIORITAIRE : "
                f"1) Chercher d'ABORD sur {website} (pages : Locations, Our offices, About us, Contact, Subsidiaries) "
                f"2) Si société mère trouvée, rechercher ses filiales (mais filtrer par secteur)"
            )

            # Instruction pour page Locations (avec extraction du domaine)
            try:
                parsed_url = urlparse(website)
                base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                query_parts.append(
                    f"📍 RECHERCHE SPÉCIFIQUE : Chercher la page 'Locations' sur {base_domain} "
                    f"(URLs possibles : {base_domain}/locations, {base_domain}/en/about-us/locations, {base_domain}/contact, etc.)"
                )
                query_parts.append(
                    "Si page Locations trouvée, PRIORISER dans cet ordre : "
                    "1) Manufacturer/Headquarters (filiales juridiques avec production) "
                    "2) Direct Sales/Operations (entités avec ventes directes) "
                    "3) Official Partners AVEC nom du groupe (ex: 'ErgoPack España S.L.') "
                    "4) EXCLURE : Silver Partners/Distributeurs tiers (entreprises avec noms différents)"
                )
            except:
                pass

        # Hiérarchie géographique complète avec système de quotas
        query_parts.append(
            "🌍 PRIORISATION GÉOGRAPHIQUE STRICTE (APPLIQUER DANS CET ORDRE) :\n"
            "1) 🇫🇷 PRIORITÉ 1 - FRANCE (OBLIGATOIRE si existe) : Chercher d'ABORD toutes entités françaises\n"
            "2) 🇪🇺 PRIORITÉ 1 - PAYS LIMITROPHES (si place restante) : Belgique, Luxembourg, Allemagne, Suisse, Italie, Espagne\n"
            "3) 🇪🇺 PRIORITÉ 2 - RESTE EUROPE (si place restante) : UK, Pays-Bas, Scandinavie, Pologne, Portugal, Bulgarie, Tchéquie\n"
            "4) 🌎 PRIORITÉ 3 - AMÉRIQUES (si place restante) : USA, Canada, Brésil, Mexique, Costa Rica, Chili\n"
            "5) 🌍 PRIORITÉ 4 - AFRIQUE (si place restante) : Maghreb, Afrique de l'Ouest\n"
            "6) 🌏 PRIORITÉ 5 - ASIE/OCÉANIE (dernière priorité) : Chine, Inde, Japon, Singapour, Australie, Vietnam, UAE\n"
            "\n"
            "⚠️ RÈGLE D'ALLOCATION : Si limite de 20 atteinte, EXCLURE les entités de Priorité 5 et 4 pour inclure les Priorités 1 et 2"
        )

        # Instructions de classification et format de sortie
        query_parts.append(
            "📋 FORMAT ATTENDU : Pour chaque entité trouvée, extraire : "
            "1) Nom légal exact (avec forme juridique si présente), "
            "2) Website (URL réelle UNIQUEMENT si explicitement mentionnée - NE PAS inventer d'URL), "
            "3) Pays et ville, "
            "4) Activité/contexte (1 phrase max), "
            "5) Source URL où l'information a été trouvée"
        )

        query_parts.append(
            "✅ RÈGLE D'INCLUSION : Inclure entité avec faible confiance > Exclure totalement. "
            "Si doute entre filiale juridique ou présence commerciale, INCLURE avec note explicative"
        )

        query_parts.append(
            "🔍 UTILISER web_search pour recherche fiable sur : "
            "site officiel, registres commerciaux (Infogreffe, Companies House, North Data), rapports annuels, presse financière"
        )
        
        query = ". ".join(query_parts) + "."
        
        logger.debug(f"📡 Requête GPT-5: {query}")
        
        # Vérifier que la clé API est disponible
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Client OpenAI non initialisé - OPENAI_API_KEY manquante")
            return {"error": "Client OpenAI non configuré."}
        
        # Sélection du modèle GPT-5
        # GPT-5.1 optimisé : 20% plus rapide + meilleure qualité (20 entités max, France en priorité)
        # Si non disponible, essayer gpt-5-mini, puis gpt-5
        models_to_try = [
            "gpt-5.1",         # Version optimale (rapide + qualité)
            "gpt-5-mini",      # Version économique
            "gpt-5"            # Modèle complet
        ]

        model = models_to_try[0]  # Par défaut, utiliser gpt-5.1
        logger.info(f"🔍 Utilisation du modèle: {model}")
        
        # Construire l'input avec le prompt système et la requête
        # GPT-5 utilise responses.create() avec un input textuel unique
        # OPTIMISATION COÛT: Limiter le nombre de recherches web (coût principal = web_search calls)
        web_search_optimization = """
⚠️ CONTRAINTE WEB_SEARCH (CRITIQUE - COÛT):
- LIMITE STRICTE: Maximum 3-5 recherches web (chaque recherche coûte cher)
- PRIORISER dans cet ordre:
  1. Site officiel du groupe (1 recherche)
  2. Registre officiel principal (1 recherche si nécessaire)
  3. Rapport annuel ou page "Subsidiaries" (1 recherche si nécessaire)
- INTERDICTION: Pas de recherche par pays/entité individuelle
- STRATÉGIE: Analyser en profondeur les résultats obtenus avant toute nouvelle recherche
- Si les 3 premières recherches donnent assez d'infos → STOP
"""
        system_instruction = MINIMAL_SUBSIDIARY_SEARCH_INSTRUCTIONS + web_search_optimization
        full_input = f"{system_instruction}\n\n{query}"
        
        # Appel avec GPT-5 + web_search tools
        # Note: GPT-5 utilise responses.create() (API synchrone)
        # Documentation: https://platform.openai.com/docs/api-reference/responses/create
        # Format: client.responses.create(model="gpt-5", tools=[{"type": "web_search"}], input="...")
        # On utilise OpenAI() (synchrone) car responses.create() n'est pas disponible dans AsyncOpenAI
        sync_client = OpenAI(api_key=api_key)
        
        # Exécuter l'appel de manière asynchrone pour ne pas bloquer
        
        # Créer une fonction wrapper pour l'exécution dans le thread pool
        def call_responses_api():
            return sync_client.responses.create(
                model=model,
                tools=[{"type": "web_search"}],  # Type correct pour GPT-5/GPT-5.1 (web_search_preview = legacy)
                input=full_input
                # Note: reasoning_effort retiré car causait une erreur
                # L'API utilise "medium" par défaut pour GPT-5
            )
        
        # Exécuter dans un thread pool pour ne pas bloquer la boucle d'événements
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_responses_api)
        
        # Extraire le résultat de la réponse
        # D'après la doc OpenAI, responses.create() retourne un objet Response avec un attribut 'output'
        # qui est une liste d'objets (ResponseReasoningItem, ResponseFunctionWebSearch, ResponseOutputMessage)
        # Il faut extraire le texte final depuis ResponseOutputMessage
        raw_result = None
        
        # Compter les web_search calls depuis response.output
        # IMPORTANT: Compter chaque appel UNE SEULE FOIS pour éviter les doublons
        web_search_calls = 0
        web_search_items_seen = set()  # Pour éviter les doublons
        
        if hasattr(response, 'output') and response.output:
            # Parcourir la liste pour trouver le message final et compter les web_search calls
            for item in response.output:
                # Identifier l'item de manière unique pour éviter les doublons
                item_id = id(item)  # Utiliser l'ID de l'objet pour éviter les doublons
                
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
                
                # Vérifier aussi si l'item a des attributs qui indiquent un web_search
                if not is_web_search:
                    # Vérifier les attributs communs des web_search items
                    if hasattr(item, 'tool_call_id') or hasattr(item, 'tool_call'):
                        # Peut être un résultat de tool call, vérifier plus en détail
                        if hasattr(item, 'tool_name') and 'web_search' in str(item.tool_name).lower():
                            is_web_search = True
                
                # Compter une seule fois par item unique
                if is_web_search and item_id not in web_search_items_seen:
                    web_search_calls += 1
                    web_search_items_seen.add(item_id)
                    logger.debug(f"🔍 [MinimalSearchGPT5] Web_search call détecté: type={getattr(item, 'type', 'N/A')}, class={type(item).__name__}")
                
                # Vérifier si c'est un message de sortie
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
                            break
                # Fallback: essayer d'accéder directement au texte si disponible
                elif hasattr(item, 'text'):
                    raw_result = item.text
                    break
            
            if web_search_calls > 0:
                logger.info(f"🔍 [MinimalSearchGPT5] {web_search_calls} web_search call(s) détecté(s) dans response.output")
            else:
                # Logger pour debug si aucun web_search call n'est détecté mais que le modèle en fait
                logger.debug(f"🔍 [MinimalSearchGPT5] Aucun web_search call détecté dans response.output (length: {len(response.output) if hasattr(response.output, '__len__') else 'N/A'})")
        
        # Si pas de résultat trouvé, essayer d'autres attributs
        if not raw_result:
            if hasattr(response, 'output_text'):
                raw_result = response.output_text
            elif hasattr(response, 'text'):
                raw_result = response.text
            else:
                # Dernier recours: convertir en string
                raw_result = str(response) if response else None
        
        if not raw_result:
            logger.warning("⚠️ Aucun contenu dans la réponse GPT-5")
            logger.debug(f"Response structure: {type(response)}, attributes: {[a for a in dir(response) if not a.startswith('_')][:10]}")
            if hasattr(response, 'output'):
                logger.debug(f"Output items: {[type(item).__name__ for item in response.output] if response.output else 'None'}")
            return {"legal_subsidiaries": []}
        
        logger.info(f"✅ Recherche minimale GPT-5 terminée: {company_name}")
        
        # Capturer les tokens utilisés si disponibles
        # L'API responses.create() peut avoir une structure différente pour usage
        input_tokens = 0
        output_tokens = 0
        
        # Essayer différents chemins pour accéder à usage
        usage = None
        if hasattr(response, 'usage'):
            usage = response.usage
        elif hasattr(response, 'usage_stats'):
            usage = response.usage_stats
        elif hasattr(response, 'token_usage'):
            usage = response.token_usage
        
        # Logger la structure de la réponse pour debug
        response_attrs = [a for a in dir(response) if not a.startswith('_')]
        logger.info(f"🔍 [MinimalSearchGPT5] Response attributes: {response_attrs[:20]}")
        
        # Vérifier s'il y a des tokens dans response.output ou ailleurs
        if hasattr(response, 'output') and response.output:
            logger.info(f"🔍 [MinimalSearchGPT5] Response.output type: {type(response.output)}, length: {len(response.output) if hasattr(response.output, '__len__') else 'N/A'}")
        
        if usage:
            # Support pour les deux formats: ancien (prompt_tokens/completion_tokens) et nouveau (input_tokens/output_tokens)
            input_tokens = getattr(usage, 'input_tokens', None) or getattr(usage, 'prompt_tokens', 0) or 0
            output_tokens = getattr(usage, 'output_tokens', None) or getattr(usage, 'completion_tokens', 0) or 0
            total_tokens_from_usage = getattr(usage, 'total_tokens', None)
            
            # Extraire les cached tokens depuis input_tokens_details
            cached_tokens = 0
            if hasattr(usage, 'input_tokens_details'):
                input_details = usage.input_tokens_details
                if hasattr(input_details, 'cached_tokens'):
                    cached_tokens = getattr(input_details, 'cached_tokens', 0) or 0
                elif isinstance(input_details, dict):
                    cached_tokens = input_details.get('cached_tokens', 0) or 0
            
            if cached_tokens > 0:
                logger.info(f"💾 [MinimalSearchGPT5] Cached tokens détectés: {cached_tokens}")
            
            # Si total_tokens n'est pas fourni, calculer depuis input + output
            if total_tokens_from_usage is None:
                total_tokens = input_tokens + output_tokens
            else:
                total_tokens = total_tokens_from_usage
            
            # Vérifier s'il y a des tokens supplémentaires (reasoning, tool calls, etc.)
            # Les tokens reasoning sont dans output_tokens_details.reasoning_tokens (pour responses.create)
            # ou completion_tokens_details.reasoning_tokens (pour chat.completions)
            reasoning_tokens = 0
            tool_tokens = 0
            
            # PRIORITÉ 0: Essayer d'abord via usage.model_dump() (méthode la plus fiable)
            # On sait que cette méthode fonctionne car on voit les données dans les logs
            if reasoning_tokens == 0 and hasattr(usage, 'model_dump'):
                try:
                    usage_dict = usage.model_dump()
                    logger.info(f"🔍 [MinimalSearchGPT5] Tentative extraction depuis usage.model_dump()...")
                    if 'output_tokens_details' in usage_dict:
                        output_dict = usage_dict.get('output_tokens_details', {})
                        logger.info(f"🔍 [MinimalSearchGPT5] output_tokens_details depuis model_dump: {output_dict}, type: {type(output_dict)}")
                        # output_dict peut être un dict ou un objet Pydantic
                        if isinstance(output_dict, dict):
                            reasoning_tokens = output_dict.get('reasoning_tokens', 0) or 0
                            tool_tokens = output_dict.get('tool_tokens', 0) or 0
                        elif hasattr(output_dict, 'reasoning_tokens'):
                            reasoning_tokens = getattr(output_dict, 'reasoning_tokens', 0) or 0
                            tool_tokens = getattr(output_dict, 'tool_tokens', 0) or 0
                        elif hasattr(output_dict, 'model_dump'):
                            # Si c'est un objet Pydantic, utiliser model_dump()
                            output_dict_dumped = output_dict.model_dump()
                            reasoning_tokens = output_dict_dumped.get('reasoning_tokens', 0) or 0
                            tool_tokens = output_dict_dumped.get('tool_tokens', 0) or 0
                        
                        if reasoning_tokens > 0:
                            logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens extraits depuis usage.model_dump(): {reasoning_tokens}")
                        else:
                            logger.warning(f"⚠️ [MinimalSearchGPT5] Reasoning tokens non trouvés dans output_dict: {output_dict}")
                    else:
                        logger.warning(f"⚠️ [MinimalSearchGPT5] 'output_tokens_details' non trouvé dans usage_dict")
                except Exception as e:
                    logger.error(f"❌ Erreur usage.model_dump(): {e}", exc_info=True)
            
            # PRIORITÉ 1: Essayer output_tokens_details (pour responses.create API)
            if reasoning_tokens == 0 and hasattr(usage, 'output_tokens_details'):
                output_details = usage.output_tokens_details
                logger.info(f"🔍 [MinimalSearchGPT5] output_tokens_details type: {type(output_details)}")
                
                # Essayer toutes les méthodes jusqu'à trouver les reasoning tokens
                # Méthode 1: Attribut direct
                if hasattr(output_details, 'reasoning_tokens'):
                    reasoning_tokens = getattr(output_details, 'reasoning_tokens', 0) or 0
                    if reasoning_tokens > 0:
                        logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens extraits via attribut: {reasoning_tokens}")
                
                # Méthode 2: Comme dict
                if reasoning_tokens == 0 and isinstance(output_details, dict):
                    reasoning_tokens = output_details.get('reasoning_tokens', 0) or 0
                    if reasoning_tokens > 0:
                        logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens extraits via dict: {reasoning_tokens}")
                
                # Méthode 3: Via model_dump (objet Pydantic)
                if reasoning_tokens == 0 and hasattr(output_details, 'model_dump'):
                    try:
                        output_dict = output_details.model_dump()
                        reasoning_tokens = output_dict.get('reasoning_tokens', 0) or 0
                        if reasoning_tokens > 0:
                            logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens extraits via output_details.model_dump(): {reasoning_tokens}")
                    except Exception as e:
                        logger.debug(f"⚠️ Erreur output_details.model_dump(): {e}")
                
                # Méthode 4: Via __dict__
                if reasoning_tokens == 0 and hasattr(output_details, '__dict__'):
                    reasoning_tokens = output_details.__dict__.get('reasoning_tokens', 0) or 0
                    if reasoning_tokens > 0:
                        logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens extraits via __dict__: {reasoning_tokens}")
                
                # Tool tokens dans output_tokens_details aussi (même logique)
                if tool_tokens == 0:
                    if hasattr(output_details, 'tool_tokens'):
                        tool_tokens = getattr(output_details, 'tool_tokens', 0) or 0
                    elif isinstance(output_details, dict):
                        tool_tokens = output_details.get('tool_tokens', 0) or 0
                    elif hasattr(output_details, 'model_dump'):
                        try:
                            output_dict = output_details.model_dump()
                            tool_tokens = output_dict.get('tool_tokens', 0) or 0
                        except Exception:
                            pass
                    elif hasattr(output_details, '__dict__'):
                        tool_tokens = output_details.__dict__.get('tool_tokens', 0) or 0
            
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
            
            # Logger les détails pour debug
            if hasattr(usage, 'output_tokens_details'):
                logger.debug(f"🔍 [MinimalSearchGPT5] output_tokens_details: {usage.output_tokens_details}")
            if hasattr(usage, 'input_tokens_details'):
                logger.debug(f"🔍 [MinimalSearchGPT5] input_tokens_details: {usage.input_tokens_details}")
            
            # Si total_tokens > input + output + reasoning + tool, la différence pourrait être d'autres tokens
            calculated_total = input_tokens + output_tokens + reasoning_tokens + tool_tokens
            if total_tokens > calculated_total:
                missing_tokens = total_tokens - calculated_total
                logger.info(f"🔍 [MinimalSearchGPT5] Différence détectée: total_tokens ({total_tokens}) > input+output+reasoning+tool ({calculated_total}) = {missing_tokens} tokens manquants")
                # Si on n'a pas encore trouvé de reasoning tokens, ils pourraient être dans cette différence
                if reasoning_tokens == 0 and missing_tokens > 0:
                    reasoning_tokens = missing_tokens
                    logger.info(f"🔍 [MinimalSearchGPT5] Tokens reasoning estimés depuis différence: {reasoning_tokens}")
            
            # Logger tous les tokens disponibles pour debug
            logger.info(
                f"💰 [MinimalSearchGPT5] Tokens: {input_tokens} in + "
                f"{output_tokens} out = {total_tokens} total"
            )
            if reasoning_tokens > 0:
                logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens: {reasoning_tokens}")
            if tool_tokens > 0:
                logger.info(f"🔧 [MinimalSearchGPT5] Tool tokens: {tool_tokens}")
            
            # Logger tous les attributs de usage pour debug (seulement si reasoning_tokens n'est pas trouvé)
            if reasoning_tokens == 0:
                usage_attrs = [a for a in dir(usage) if not a.startswith('_')]
                logger.debug(f"🔍 [MinimalSearchGPT5] Usage attributes: {usage_attrs}")
                
                # Essayer d'accéder à usage comme un dict aussi
                if hasattr(usage, '__dict__'):
                    logger.debug(f"🔍 [MinimalSearchGPT5] Usage __dict__: {usage.__dict__}")
                # Essayer de convertir en dict si possible
                try:
                    if hasattr(usage, 'model_dump'):
                        usage_dict = usage.model_dump()
                        logger.debug(f"🔍 [MinimalSearchGPT5] Usage dict (model_dump): {usage_dict}")
                        # Essayer d'extraire depuis le dict si pas encore trouvé
                        if reasoning_tokens == 0 and 'output_tokens_details' in usage_dict:
                            output_dict = usage_dict.get('output_tokens_details', {})
                            if isinstance(output_dict, dict):
                                reasoning_tokens = output_dict.get('reasoning_tokens', 0) or 0
                                tool_tokens = output_dict.get('tool_tokens', 0) or 0
                                if reasoning_tokens > 0:
                                    logger.info(f"🔍 [MinimalSearchGPT5] Reasoning tokens extraits depuis model_dump: {reasoning_tokens}")
                    elif hasattr(usage, 'dict'):
                        usage_dict = usage.dict()
                        logger.debug(f"🔍 [MinimalSearchGPT5] Usage dict: {usage_dict}")
                except Exception as e:
                    logger.debug(f"⚠️ Impossible de convertir usage en dict: {e}")
            
            # Si reasoning_tokens ou tool_tokens existent, les ajouter au total
            if reasoning_tokens > 0:
                total_tokens = total_tokens + reasoning_tokens
                logger.info(f"📊 [MinimalSearchGPT5] Total avec reasoning: {total_tokens}")
            if tool_tokens > 0:
                total_tokens = total_tokens + tool_tokens
                logger.info(f"📊 [MinimalSearchGPT5] Total avec tool tokens: {total_tokens}")

            # Envoyer au ToolTokensTracker
            # IMPORTANT: D'après la documentation OpenAI, les reasoning tokens sont DÉJÀ inclus dans output_tokens
            # et sont facturés comme tokens de sortie. On ne doit PAS les ajouter au calcul du coût.
            # Les reasoning tokens sont juste une information de détail pour savoir combien de tokens
            # ont été utilisés pour le raisonnement interne.
            # 
            # Référence: https://platform.openai.com/docs/guides/reasoning/how-reasoning-works
            # "These tokens are billed as output tokens"
            
            # Calculer les input_tokens effectifs (non-cached + cached à 50%)
            effective_input_tokens = input_tokens
            if cached_tokens > 0:
                # Les cached tokens sont facturés à 50% du prix
                # On sépare les tokens: non-cached (plein prix) + cached (50% prix)
                non_cached_input = input_tokens - cached_tokens
                effective_input_tokens = non_cached_input + (cached_tokens * 0.5)  # Pour le calcul, on multiplie par 0.5
                logger.info(f"💾 [MinimalSearchGPT5] Input tokens: {non_cached_input} non-cached + {cached_tokens} cached (50% prix)")
            
            # IMPORTANT: Les reasoning tokens sont DÉJÀ inclus dans output_tokens selon la documentation OpenAI
            # Référence: https://platform.openai.com/docs/guides/reasoning/how-reasoning-works
            # "These tokens are billed as output tokens" - ils sont déjà comptés dans output_tokens
            # On ne doit PAS les ajouter au calcul du coût, juste les logger pour information
            effective_output_tokens = output_tokens
            if reasoning_tokens > 0:
                logger.info(f"📊 [MinimalSearchGPT5] Reasoning tokens détectés: {reasoning_tokens} (déjà inclus dans output_tokens: {output_tokens})")
            if tool_tokens > 0:
                # Les tool_tokens peuvent être facturés séparément selon le modèle, mais pour l'instant
                # on les considère comme inclus dans output_tokens aussi
                logger.info(f"📊 [MinimalSearchGPT5] Tool tokens détectés: {tool_tokens}")
            
            if input_tokens > 0 or effective_output_tokens > 0:
                try:
                    session_id = get_session_context()
                    
                    # IMPORTANT: On track output_tokens tel quel (les reasoning tokens sont déjà inclus)
                    # Le calcul du coût dans hierarchical_cost_tracking gérera les cached tokens
                    ToolTokensTracker.add_tool_usage(
                        session_id=session_id,
                        tool_name='minimal_subsidiary_search_gpt5',
                        model=model,
                        input_tokens=input_tokens,  # Valeur brute (le calcul du coût gérera les cached tokens)
                        output_tokens=effective_output_tokens,  # Ne PAS ajouter reasoning_tokens (déjà inclus)
                        web_search_calls=web_search_calls,
                        cached_tokens=cached_tokens
                    )
                    log_msg = f"✅ [MinimalSearchGPT5] Tokens trackés: {input_tokens} in + {effective_output_tokens} out"
                    if reasoning_tokens > 0:
                        log_msg += f" (reasoning: {reasoning_tokens} déjà inclus)"
                    if tool_tokens > 0:
                        log_msg += f" (tool: {tool_tokens})"
                    if cached_tokens > 0:
                        log_msg += f" (cached: {cached_tokens})"
                    logger.info(log_msg)
                except Exception as e:
                    logger.warning(f"⚠️ Erreur tracking tokens: {e}")
            else:
                logger.warning(f"⚠️ [MinimalSearchGPT5] Aucun token détecté dans usage (input={input_tokens}, output={output_tokens})")
        else:
            # Logger la structure de la réponse pour debug
            logger.warning(
                f"⚠️ [MinimalSearchGPT5] Pas d'usage détecté dans la réponse. "
                f"Attributs disponibles: {[a for a in dir(response) if not a.startswith('_')][:10]}"
            )

        # Logger les données brutes pour debug
        logger.info(f"📋 [MinimalSearchGPT5] Données brutes ({len(raw_result)} caractères):\n{raw_result[:800]}")

        # Parser le JSON retourné
        parsed = parse_json_response(raw_result, "minimal_subsidiary_search_gpt5")

        # Vérifier si erreur de parsing
        if "error" in parsed:
            logger.warning(f"⚠️ Erreur parsing recherche minimale GPT-5: {parsed.get('error')}")
            return {"legal_subsidiaries": []}

        # Vérifier si la clé legal_subsidiaries existe
        if "legal_subsidiaries" not in parsed:
            logger.warning(f"⚠️ Champ 'legal_subsidiaries' manquant dans la réponse (reçu: {list(parsed.keys())})")
            logger.warning(f"⚠️ Le modèle a probablement retourné du texte explicatif au lieu de JSON")
            return {"legal_subsidiaries": []}

        return parsed
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Erreur recherche minimale GPT-5 pour {company_name}: {error_str}")
        
        # Si erreur liée au modèle non disponible, suggérer un fallback
        if "model" in error_str.lower() and ("not found" in error_str.lower() or "does not exist" in error_str.lower()):
            logger.warning(f"💡 Le modèle GPT-5 n'est pas disponible.")
            return {
                "error": f"Modèle GPT-5 non disponible: {error_str}",
                "legal_subsidiaries": []
            }
        
        return {"error": error_str, "legal_subsidiaries": []}

