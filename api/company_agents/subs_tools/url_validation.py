"""
Outils de validation et vérification d'URLs
- Deux tools exposés :
  1) validate_urls_accessibility(urls: List[str])                     ← compat
  2) validate_urls_accessibility_payload(payload: UrlsInput)          ← recommandé ({"urls":[...]})
"""

from typing import List, Literal, TypedDict
import asyncio
import json
import logging
import aiohttp

# Pydantic pour un schéma d'entrée strict côté tool objet
from pydantic import BaseModel, Field, ConfigDict

# Import depuis le module openai-agents (pas le package local)
from agents import function_tool

# Import de la configuration simple
from .config import get_aiohttp_config, create_session

logger = logging.getLogger(__name__)


# =========================
#  Modèle d'entrée strict
# =========================
class UrlsInput(BaseModel):
    """
    Schéma d'entrée strict pour un tool qui accepte {"urls":[...]}.
    additionalProperties est implicitement interdit via extra="forbid"
    dans le JSON Schema strict généré par l'Agents SDK.
    """

    model_config = ConfigDict(extra="forbid")
    urls: List[str] = Field(min_items=1, description="Liste d'URLs http/https")


# =========================
#  Session globale (opt.)
# =========================
_global_session = None


# Fonctions de session globale supprimées - non utilisées


# =========================
#  Types & helpers HTTP
# =========================


class UrlCheck(TypedDict, total=False):
    url: str
    final_url: str
    status: int
    classification: Literal["accessible", "protected", "rate_limited", "broken"]


async def _check_url_fast(session: aiohttp.ClientSession, url: str) -> UrlCheck:
    # 1) HEAD rapide
    try:
        async with session.head(url, allow_redirects=True) as r:
            status = r.status
            if status in (405, 501):  # HEAD non supporté -> fallback GET
                raise RuntimeError("HEAD not allowed")
            cls = (
                "accessible"
                if 200 <= status < 400
                else (
                    "protected"
                    if status in (401, 403)
                    else "rate_limited" if status == 429 else "broken"
                )
            )
            return {
                "url": url,
                "status": status,
                "classification": cls,
            }
    except Exception:
        # 2) GET minimal si HEAD échoue / non supporté
        headers = {"Range": "bytes=0-0", "Accept": "*/*"}
        try:

            async with session.get(url, headers=headers, allow_redirects=True) as r:
                status = r.status
                cls = (
                    "accessible"
                    if 200 <= status < 400
                    else (
                        "protected"
                        if status in (401, 403)
                        else "rate_limited" if status == 429 else "broken"
                    )
                )
                return {
                    "url": url,
                    "status": status,
                    "classification": cls,
                }
        except Exception:
            return {
                "url": url,
                "status": 0,
                "classification": "broken",
            }


# =========================
#  Normalisation d'entrée
# =========================
def _normalize_urls(arg: any) -> List[str]:
    """
    Accepte liste, dict {"urls":[...]}, CSV/str JSON (en dernier recours),
    et renvoie une liste http/https dédupliquée (ordre préservé).
    """
    urls: List[str] = []

    # a) déjà une liste
    if isinstance(arg, list):
        urls = [u for u in arg if isinstance(u, str)]
    # b) dict {"urls":[...]}
    elif isinstance(arg, dict) and "urls" in arg:
        val = arg.get("urls")
        if isinstance(val, list):
            urls = [u for u in val if isinstance(u, str)]
        else:
            urls = []
    # c) str → essayer JSON, puis CSV/virgules
    elif isinstance(arg, str):
        s = arg.strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    urls = [u for u in parsed if isinstance(u, str)]
            except Exception:
                pass
        if not urls:
            # CSV simple "a,b,c"
            urls = [p.strip() for p in s.split(",") if p.strip()]

    # Filtre http/https + cap 10 + dédup en préservant l'ordre
    urls = [
        u.strip()
        for u in urls
        if isinstance(u, str) and u.strip().startswith(("http://", "https://"))
    ]
    if len(urls) > 10:
        logger.info("⚡ Limitation à 10 URLs pour performance")
        urls = urls[:10]
    # dédup
    urls = list(dict.fromkeys(urls))
    return urls


# =========================
#  Noyau de validation
# =========================
async def _validate_core(valid: List[str]) -> str:
    if not valid:
        return json.dumps(
            {
                "is_valid": False,
                "reliability_score": 0.0,
                "accessible_urls_count": 0,
                "total_urls_count": 0,
                "broken_urls": [],
                "protected_urls": [],
                "rate_limited_urls": [],
                "validation_errors": ["Aucune URL valide trouvée"],
                "recommendations": [],
            },
            ensure_ascii=False,
        )

    session_config = get_aiohttp_config("fast")

    async with aiohttp.ClientSession(**session_config) as session:
        results = await asyncio.gather(
            *(_check_url_fast(session, u) for u in valid), return_exceptions=True
        )

    typed = [r for r in results if not isinstance(r, Exception)]
    accessible = [r for r in typed if r.get("classification") == "accessible"]
    protected = [r for r in typed if r.get("classification") == "protected"]
    limited = [r for r in typed if r.get("classification") == "rate_limited"]
    broken = [r for r in typed if r.get("classification") == "broken"]

    broken_exc_urls = [
        valid[i] for i, r in enumerate(results) if isinstance(r, Exception)
    ]

    total = len(valid)
    reliability = len(accessible) / total if total else 0.0
    is_valid = reliability >= 0.7

    recos = []
    if limited:
        recos.append(
            "Certaines URLs sont limitées (429). Réessayez plus tard et respectez Retry-After si présent."
        )
    if protected:
        recos.append("Certaines URLs nécessitent une authentification (401/403).")
    if broken or broken_exc_urls:
        recos.append(
            "Des URLs renvoient 5xx/timeout/erreur. Vérifiez la disponibilité ou changez la source."
        )

    return json.dumps(
        {
            "is_valid": is_valid,
            "reliability_score": round(reliability, 2),
            "accessible_urls_count": len(accessible),
            "total_urls_count": total,
            "broken_urls": list(
                dict.fromkeys([r.get("url", "") for r in broken] + broken_exc_urls)
            ),
            "protected_urls": [r["url"] for r in protected],
            "rate_limited_urls": [r["url"] for r in limited],
            "validation_errors": [],
            "recommendations": recos,
        },
        ensure_ascii=False,
    )


# =========================
#  Tools exposés
# =========================


@function_tool
async def validate_urls_accessibility(urls: List[str]) -> str:
    """
    Validation rapide (entrée = liste d'URLs).
    Utiliser ce tool si l'appelant fournit directement une liste JSON (["https://..."]).
    """
    valid = _normalize_urls(urls)
    return await _validate_core(valid)


@function_tool
async def validate_urls_accessibility_payload(payload: UrlsInput) -> str:
    """
    Validation rapide (entrée = objet {"urls":[...]}).
    À privilégier pour la validation directe d'URLs.
    """
    valid = _normalize_urls(payload.urls)
    return await _validate_core(valid)


@function_tool
async def convert_urls_to_json(urls_string: str) -> str:
    """
    Convertit une chaîne CSV d'URLs en liste JSON nettoyée.
    - Gère guillemets/espaces CSV.
    - Filtre http/https plausibles.
    - Supprime les doublons en préservant l'ordre.
    """
    import csv
    import io
    from urllib.parse import urlsplit

    try:
        if not urls_string or not urls_string.strip():
            return json.dumps([])

        rows = list(csv.reader(io.StringIO(urls_string), skipinitialspace=True))
        items = [cell.strip() for row in rows for cell in row if cell and cell.strip()]

        def is_http_url(s: str) -> bool:
            try:
                p = urlsplit(s)
                return p.scheme in ("http", "https") and bool(p.netloc)
            except Exception:
                return False

        cleaned = [s for s in items if is_http_url(s)]
        deduped = list(dict.fromkeys(cleaned))
        logger.info(f"🔄 Conversion de {len(deduped)} URLs en JSON (sur {len(items)})")
        return json.dumps(deduped, ensure_ascii=False)

    except Exception as e:
        logger.error(f"❌ Erreur lors de la conversion des URLs: {e}")
        return json.dumps([])
