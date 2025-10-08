"""
Orchestrateur multi-agents pour l'extraction d'informations d'entreprise.

Ce module coordonne l'exécution séquentielle des agents spécialisés :
1. 🔍 Company Analyzer : Identification de l'entité légale
2. ⛏️ Information Extractor : Consolidation des informations clés
3. 🗺️ Subsidiary Extractor : Extraction des filiales
4. ⚖️ Meta Validator : Validation de cohérence
5. 🔄 Data Restructurer : Normalisation finale

Fonctionnalités :
- Gestion des sessions et tracking en temps réel
- Validation et filtrage des sources
- Gestion des erreurs et retry automatique
- Cache d'accessibilité des URLs
"""

# flake8: noqa
from __future__ import annotations
from agents import Runner
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import asyncio
import json
import logging
import os
from company_agents.models import CompanyInfo
import httpx
from pydantic import ValidationError


from .subs_agents import (
    company_analyzer,
    information_extractor,
    meta_validator,
    subsidiary_extractor,
)
from .subs_agents.data_validator import data_restructurer

from status import status_manager
from services.agent_tracking_service import agent_tracking_service
import time

logger = logging.getLogger(__name__)

# Configuration pour la validation des URLs
_URL_STATUS_CACHE: Dict[str, bool] = {}  # Cache d'accessibilité des URLs
_URL_TIMEOUT_S = 5.0  # Timeout pour les requêtes HTTP
_URL_ALLOWED_STATUSES = {
    403
}  # Codes de statut acceptés (403 = accès restreint mais valide)
_URL_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
}

# Feature flag: activer/désactiver les filtres post-extraction (accessibilité & fraîcheur)
ENABLE_SUBS_FILTERS = False


async def _check_url_accessible(url: str) -> bool:
    if not url:
        return False
    cached = _URL_STATUS_CACHE.get(url)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(
            timeout=_URL_TIMEOUT_S,
            follow_redirects=True,
            headers=_URL_REQUEST_HEADERS,
        ) as client:
            response = await client.head(url)
            if (
                response.status_code >= 400
                and response.status_code not in _URL_ALLOWED_STATUSES
            ):
                response = await client.get(url)
        ok = response.status_code < 400 or response.status_code in _URL_ALLOWED_STATUSES
    except Exception:
        logger.debug("URL accessibility check failed for %s", url, exc_info=True)
        ok = False

    _URL_STATUS_CACHE[url] = ok
    return ok


async def _filter_sources_list(
    state: "ExtractionState",
    sources: Optional[Iterable[Any]],
) -> Tuple[List[Any], List[str]]:
    filtered: List[Any] = []
    removed: List[str] = []

    if not sources:
        return filtered, removed

    for entry in sources:
        if isinstance(entry, dict):
            url = entry.get("url")
        elif isinstance(entry, str):
            url = entry
        else:
            url = None

        if not url:
            filtered.append(entry)
            continue

        if await _check_url_accessible(url):
            filtered.append(entry)
        else:
            removed.append(url)
            logger.info(
                "URL exclue (inaccessible) pour session=%s agent=%s : %s",
                getattr(state, "session_id", "unknown"),
                getattr(state, "current_agent", "unknown"),
                url,
            )

    return filtered, removed


async def _filter_agent_sources(
    state: "ExtractionState",
    payload: Optional[Dict[str, Any]],
    *,
    agent_label: str,
) -> Optional[Dict[str, Any]]:
    if not payload:
        return payload

    filtered_sources, removed = await _filter_sources_list(
        state, payload.get("sources")
    )
    if not removed:
        return payload

    updated = dict(payload)
    updated["sources"] = filtered_sources
    _append_warning(
        state,
        f"{agent_label}: {len(removed)} source(s) inaccessibles ignorées",
    )
    return updated


async def _filter_inaccessible_sources(
    state: "ExtractionState", report: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    if not report:
        return report

    filtered_report = dict(report)
    removed_urls: List[str] = []

    subsidiaries: List[Dict[str, Any]] = []
    for sub in report.get("subsidiaries", []):
        filtered_sources, removed = await _filter_sources_list(
            state, sub.get("sources")
        )
        new_sub = dict(sub)
        if removed:
            new_sub["sources"] = filtered_sources
            removed_urls.extend(removed)
        subsidiaries.append(new_sub)
    filtered_report["subsidiaries"] = subsidiaries

    parents: List[Dict[str, Any]] = []
    for parent in report.get("parents", []):
        filtered_sources, removed = await _filter_sources_list(
            state, parent.get("sources")
        )
        new_parent = dict(parent)
        if removed:
            new_parent["sources"] = filtered_sources
            removed_urls.extend(removed)
        parents.append(new_parent)
    if parents:
        filtered_report["parents"] = parents

    if removed_urls:
        _append_warning(
            state,
            f"URLs inaccessibles écartées ({len(removed_urls)}): "
            + ", ".join(sorted(set(removed_urls))[:3])
            + ("…" if len(set(removed_urls)) > 3 else ""),
        )

    return filtered_report


def _parse_yyyy_mm_dd(date_str: Optional[str]) -> Optional[tuple[int, int, int]]:
    if not date_str or not isinstance(date_str, str):
        return None
    parts = date_str.split("-")
    try:
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return (y, m, d)
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            return (y, m, 1)
        if len(parts) == 1:
            y = int(parts[0])
            return (y, 1, 1)
    except Exception:
        return None
    return None


def _months_diff_from_now(ymd: tuple[int, int, int]) -> Optional[int]:
    try:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        y, m, _ = ymd
        months = (now.year - y) * 12 + (now.month - m)
        return months
    except Exception:
        return None


def _is_official_domain(url: Optional[str]) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False


def _filter_fresh_sources(
    state: "ExtractionState", report: Optional[Dict[str, Any]], max_age_months: int = 24
) -> Optional[Dict[str, Any]]:
    if not report:
        return report

    filtered_report = dict(report)
    kept_subs: List[Dict[str, Any]] = []
    removed_names: List[str] = []

    for sub in report.get("subsidiaries", []):
        sources = sub.get("sources") or []
        has_recent_official = False
        has_any_date = False

        for src in sources:
            if not isinstance(src, dict):
                continue
            published = _parse_yyyy_mm_dd(src.get("published_date"))
            if published:
                has_any_date = True
                diff = _months_diff_from_now(published)
                if (
                    diff is not None
                    and diff <= max_age_months
                    and (src.get("tier") == "official")
                ):
                    has_recent_official = True

        if has_recent_official:
            kept_subs.append(sub)
            continue

        if has_any_date:
            # toutes les dates étaient > max_age_months ou non officielles
            removed_names.append(sub.get("legal_name") or "(unknown)")
            continue

        # Aucune date: garder seulement si au moins une URL officielle https du domaine légitime
        any_official_https = any(
            isinstance(src, dict)
            and src.get("tier") == "official"
            and _is_official_domain(src.get("url"))
            for src in sources
        )
        if any_official_https:
            kept_subs.append(sub)
        else:
            removed_names.append(sub.get("legal_name") or "(unknown)")

    if removed_names:
        _append_warning(
            state,
            f"Filiales exclues (sources > {max_age_months} mois ou sans date/official): "
            + ", ".join(removed_names[:5])
            + ("…" if len(removed_names) > 5 else ""),
        )

    filtered_report["subsidiaries"] = kept_subs
    return filtered_report


def _normalize_site(
    site: Optional[Dict[str, Any]], *, label_hint: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    if not isinstance(site, dict):
        return None

    result: Dict[str, Any] = {}
    label = site.get("label") or label_hint
    if label:
        result["label"] = _normalize_text(label)

    address = site.get("address") if isinstance(site.get("address"), dict) else None
    for field in ["line1", "city", "country", "postal_code"]:
        value = site.get(field)
        if not value and address:
            value = address.get(field)
        normalized_value = _normalize_text(value)
        if field == "country":
            normalized_value = _normalize_country(value) or normalized_value
        if normalized_value:
            result[field] = normalized_value

    for field in ["phone", "email", "website", "notes"]:
        value = _normalize_text(site.get(field))
        if value:
            result[field] = value

    # ✅ PRÉSERVER LES COORDONNÉES GPS
    for coord_field in ["latitude", "longitude"]:
        coord_value = site.get(coord_field)
        if isinstance(coord_value, (int, float)) and not (
            coord_value != coord_value
        ):  # Check for NaN
            result[coord_field] = float(coord_value)

    if site.get("sources"):
        result["sources"] = [
            src for src in site["sources"] if isinstance(src, dict) and src.get("url")
        ][:2]

    if any(
        result.get(k)
        for k in ["line1", "city", "country", "phone", "email", "website", "notes"]
    ):
        if "label" not in result and label_hint:
            result["label"] = label_hint
        return result
    return None


def _normalize_sites(items: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not items:
        return normalized
    for idx, raw in enumerate(items):
        site = _normalize_site(raw)
        if site:
            if "label" not in site:
                site["label"] = site.get("label") or f"Site {idx + 1}"
            normalized.append(site)
    return normalized


def _dedupe_sites(
    sites: Optional[Iterable[Dict[str, Any]]], max_items: int = 7
) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: Set[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]] = set()
    if not sites:
        return deduped
    for site in sites:
        if not isinstance(site, dict):
            continue
        key = (
            site.get("label"),
            site.get("line1"),
            site.get("city"),
            site.get("country"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(site)
        if len(deduped) >= max_items:
            break
    return deduped


# Fonction _normalize_contact supprimée - non utilisée


# Fonction _dedupe_contacts supprimée - non utilisée


# Schéma supprimé - non utilisé

# Configuration des tours maximum (sera resserrée côté orchestrateur)
MAX_TURNS = {"analyze": 2, "info": 2, "subs": 3, "meta": 1}


def _append_warning(state: "ExtractionState", message: str) -> None:
    if message not in state.warnings and len(state.warnings) < 10:
        state.warnings.append(message)


@dataclass(slots=True)
class ExtractionState:
    """
    État partagé entre les agents lors de l'extraction.

    Stocke les résultats intermédiaires de chaque agent et permet
    le passage de données entre les étapes du pipeline d'extraction.
    """

    session_id: str
    raw_input: str
    include_subsidiaries: bool = True

    # Résultats de l'agent Company Analyzer
    analyzer: Optional[Dict[str, Any]] = None
    analyzer_raw: Optional[str] = None
    target_entity: Optional[str] = None

    # Résultats de l'agent Information Extractor
    info_card: Optional[Dict[str, Any]] = None
    info_raw: Optional[str] = None

    # Résultats de l'agent Subsidiary Extractor
    subs_report: Optional[Dict[str, Any]] = None
    subs_raw: Optional[str] = None

    # Résultats de l'agent Meta Validator
    meta_report: Optional[Dict[str, Any]] = None
    meta_raw: Optional[str] = None

    warnings: List[str] = field(default_factory=list)

    def log(self, step: str, payload: Any) -> None:
        logger.debug("[state:%s] %s → %s", self.session_id, step, payload)


async def orchestrate_extraction(
    raw_input: str,
    *,
    session_id: str,
    include_subsidiaries: bool = True,
) -> Dict[str, Any]:
    """
    Orchestrateur principal du pipeline d'extraction multi-agents.

    Séquence d'exécution :
    1. 🔍 Company Analyzer : Identification de l'entité légale
    2. ⛏️ Information Extractor : Consolidation des informations clés
    3. 🗺️ Subsidiary Extractor : Extraction des filiales (si demandé)
    4. ⚖️ Meta Validator : Validation de cohérence (si nécessaire)
    5. 🔄 Data Restructurer : Normalisation finale
    """

    state = ExtractionState(
        session_id=session_id,
        raw_input=raw_input,
        include_subsidiaries=include_subsidiaries,
    )

    # Étape 1: Identification de l'entité légale
    analyzer_data = await _call_company_analyzer(state)
    state.target_entity = _resolve_target_entity(raw_input, analyzer_data)

    # Étape 2: Consolidation des informations clés
    info_data = await _call_information_extractor(state)

    # Étape 3: Extraction des filiales (conditionnelle)
    if state.include_subsidiaries:
        await _call_subsidiary_extractor(state)

    # Étape 4: Validation de cohérence (conditionnelle)
    if _should_run_meta_validation(state):
        await _call_meta_validator(state)

    # Restructuration des données pour garantir la qualité
    restructured_company_info = await _call_data_restructurer(state)

    if restructured_company_info:
        # Utiliser les données restructurées directement
        try:
            validated = CompanyInfo.model_validate(
                restructured_company_info
            ).model_dump()
            return validated
        except ValidationError as exc:  # type: ignore[name-defined]
            logger.error(
                "Validation CompanyInfo restructuré échouée",
                extra={"errors": exc.errors(), "data": restructured_company_info},
            )
            # Fallback vers la construction manuelle
            company_info = _build_company_info(state, analyzer_data, info_data)
            validated = CompanyInfo.model_validate(company_info).model_dump()
            return validated
    else:
        # Fallback vers la construction manuelle si le restructurateur échoue
        logger.warning(
            "Restructurateur échoué, utilisation de la construction manuelle"
        )
        company_info = _build_company_info(state, analyzer_data, info_data)
        try:
            validated = CompanyInfo.model_validate(company_info).model_dump()
        except ValidationError as exc:  # type: ignore[name-defined]
            logger.error(
                "Validation CompanyInfo échouée",
                extra={"errors": exc.errors(), "data": company_info},
            )
            raise
        return validated


def _resolve_target_entity(raw_input: str, analyzer_data: Dict[str, Any]) -> str:
    parent = analyzer_data.get("parent_company")
    relationship = analyzer_data.get("relationship")
    entity = analyzer_data.get("entity_legal_name") or raw_input

    if relationship == "subsidiary" and parent:
        return parent
    return entity


# ========== 1) Planning supprimé - plan fixe intégré dans l'orchestrateur ===============


# ========== 2) Helpers anti-EOF & JSON-safe ===================================


def _repair_truncated_json(json_str: str) -> str:
    """Tente de réparer un JSON tronqué en fermant les structures ouvertes"""
    if not json_str or not json_str.strip():
        return json.dumps({"error": "JSON vide"})

    try:
        # Stratégie 1: Essayer de parser tel quel
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass

    try:
        # Stratégie 2: Compter les accolades et crochets ouverts
        open_braces = json_str.count("{") - json_str.count("}")
        open_brackets = json_str.count("[") - json_str.count("]")

        # Fermer les structures ouvertes
        repaired = json_str
        if open_braces > 0:
            repaired += "}" * open_braces
        if open_brackets > 0:
            repaired += "]" * open_brackets

        # Tester si le JSON réparé est valide
        json.loads(repaired)
        logger.info("JSON tronqué réparé avec succès (stratégie 2)")
        return repaired

    except json.JSONDecodeError:
        pass

    try:
        # Stratégie 3: Trouver la dernière accolade fermante et tronquer là
        last_brace = json_str.rfind("}")
        if last_brace > 0:
            truncated = json_str[: last_brace + 1]
            json.loads(truncated)
            logger.info("JSON tronqué réparé avec succès (stratégie 3)")
            return truncated
    except json.JSONDecodeError:
        pass

    try:
        # Stratégie 4: Essayer de trouver un objet JSON valide dans la chaîne
        for i in range(len(json_str), 0, -1):
            try:
                candidate = json_str[:i]
                if candidate.strip().endswith(("}", "]")):
                    json.loads(candidate)
                    logger.info("JSON tronqué réparé avec succès (stratégie 4)")
                    return candidate
            except json.JSONDecodeError:
                continue
    except Exception:
        pass

    # Stratégie 5: Si tout échoue, retourner un JSON minimal mais valide
    logger.warning("Impossible de réparer le JSON tronqué, retour d'un JSON minimal")
    return json.dumps(
        {
            "error": "JSON tronqué non réparable",
            "original_length": len(json_str),
            "truncated_content": (
                json_str[:200] + "..." if len(json_str) > 200 else json_str
            ),
        }
    )


def _unwrap_message_content(res: Any) -> Optional[str]:
    """Tente d'extraire une charge utile JSON depuis des wrappers de messages.

    Cas gérés:
    - Dictionnaire avec clé 'content' contenant une chaîne JSON
    - Liste de messages, dernier ayant role='assistant' et 'content' JSON
    """
    try:
        # Dict: {"content": "{...}"}
        if isinstance(res, dict):
            content = res.get("content")
            if isinstance(content, str) and ("{" in content or "[" in content):
                return content

        # List of messages
        if isinstance(res, list) and res:
            last = res[-1]
            if (
                isinstance(last, dict)
                and last.get("role") in {"assistant", "tool"}
                and isinstance(last.get("content"), str)
            ):
                return last["content"]
    except Exception:  # noqa: B902
        pass
    return None


def _final_json(res) -> str:
    # Tenter de déballer du contenu JSON encapsulé dans 'content'
    unwrapped = _unwrap_message_content(res)
    if isinstance(unwrapped, str):
        return unwrapped
    if isinstance(res, str):
        return res
    if hasattr(res, "final_output_json") and res.final_output_json:
        return res.final_output_json
    if hasattr(res, "final_output") and res.final_output is not None:
        fo = res.final_output
        if hasattr(fo, "model_dump"):
            return json.dumps(fo.model_dump(), ensure_ascii=False)
        try:
            s = json.dumps(fo, ensure_ascii=False)
            json.loads(s)
            return s
        except Exception:  # noqa: B902
            s = str(fo)
            try:
                json.loads(s)
                return s
            except Exception:  # noqa: B902
                return _repair_truncated_json(s)
    try:
        dumped = json.dumps(res, ensure_ascii=False)
        json.loads(dumped)
        return dumped
    except Exception:  # noqa: B902
        return _repair_truncated_json(str(res))


def _safe_json_loads(s: str) -> dict:
    if isinstance(s, dict):
        return s
    if not isinstance(s, str):
        return {}
    # Nettoyage basique des fences et extraction de la région JSON principale
    stripped = s.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        # Supprimer fences ```json ... ``` ou ```
        stripped = stripped.strip("`")
    # Extraire entre le premier '{' ou '[' et la dernière '}' ou ']'
    if ("{" in stripped or "[" in stripped) and ("}" in stripped or "]" in stripped):
        try:
            start_candidates = [
                idx for idx in [stripped.find("{"), stripped.find("[")] if idx != -1
            ]
            end_candidates = [
                idx for idx in [stripped.rfind("}"), stripped.rfind("]")] if idx != -1
            ]
            if start_candidates and end_candidates:
                start = min(start_candidates)
                end = max(end_candidates)
                candidate = stripped[start : end + 1]
                return json.loads(candidate)
        except json.JSONDecodeError:
            # On tombera sur la réparation ci-dessous
            pass
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(stripped)
        try:
            return json.loads(repaired)
        except Exception:
            return {}


# =======================================================
# 🔁 Exécution résiliente (retry + backoff + timeout)
# =======================================================


async def _run_agent_with_retry(
    agent,
    *,
    input: str,
    max_turns: int,
    retries: int = 2,
    initial_backoff_s: float = 1.5,
    timeout_s: float = 180.0,  # 3 minutes pour GPT-5 Nano avec tâches complexes
):
    """Exécute Runner.run avec retry exponentiel et timeout par tentative.

    - Retries: 2 par défaut (3 tentatives au total)
    - Backoff: 1.5^n secondes
    - Timeout: coupe les tentatives trop longues
    """
    attempt = 0
    last_error: Exception | None = None
    while True:
        attempt += 1
        try:
            logger.info(
                "▶️ Run agent %s (attempt=%d, max_turns=%d)",
                getattr(agent, "name", "unknown"),
                attempt,
                max_turns,
            )
            res = await asyncio.wait_for(
                Runner.run(agent, input=input, max_turns=max_turns),
                timeout=timeout_s,
            )
            logger.info(
                "✅ Agent %s réussi (attempt=%d)",
                getattr(agent, "name", "unknown"),
                attempt,
            )
            return res
        except asyncio.TimeoutError as e:
            logger.warning(
                "⏳ Timeout agent %s (attempt=%d)",
                getattr(agent, "name", "unknown"),
                attempt,
            )
            last_error = e
        except Exception as e:
            logger.warning(
                "⚠️ Échec agent %s: %s (attempt=%d)",
                getattr(agent, "name", "unknown"),
                e,
                attempt,
            )
            last_error = e

        if attempt > retries:
            logger.error(
                "❌ Abandon agent %s après %d tentatives",
                getattr(agent, "name", "unknown"),
                attempt,
            )
            if last_error is not None:
                raise last_error
            raise RuntimeError("Agent failed without captured exception")

        # Backoff exponentiel
        delay = initial_backoff_s**attempt
        await asyncio.sleep(delay)


# =======================================================
# 🧠 Cache Redis SUPPRIMÉ - Toujours calculer de nouvelles données
# =======================================================

# Variable DISABLE_CACHE supprimée - non utilisée


# Fonctions de cache supprimées - non utilisées


# ========== 3) Outils (avec cache) ============================================


# =================== Filiales: contexte supprimé - OPTIMISATION ===========================


def _apply_subsidiary_confidence(
    company_info: Dict[str, Any], meta_validation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applique les scores de confiance calculés par le ⚖️ Superviseur aux filiales.
    """
    if not meta_validation.get("subsidiaries_confidence"):
        return company_info

    # Créer un mapping nom -> confidence
    confidence_map = {
        sub_conf["subsidiary_name"]: sub_conf["confidence"]
        for sub_conf in meta_validation["subsidiaries_confidence"]
    }

    # Appliquer les scores de confiance aux filiales
    if "subsidiaries_details" in company_info:
        for subsidiary in company_info["subsidiaries_details"]:
            subsidiary_name = subsidiary.get("subsidiary_name")
            if subsidiary_name and subsidiary_name in confidence_map:
                subsidiary["confidence"] = confidence_map[subsidiary_name]

    return company_info


# === 3bis) Helpers pour la nouvelle orchestration =============================


async def _call_company_analyzer(state: ExtractionState) -> Dict[str, Any]:
    # Toujours effectuer une nouvelle analyse (cache supprimé)

    t0 = time.perf_counter()
    res = await _run_agent_with_retry(
        company_analyzer,
        input=state.raw_input,
        max_turns=MAX_TURNS["analyze"],
    )
    raw_output = _final_json(res)
    data = _safe_json_loads(raw_output)
    if not data:
        logger.error("JSON analyzer invalide ou vide: %s", raw_output)
        raise ValueError("company_analyzer returned empty payload")

    filtered = await _filter_agent_sources(state, data, agent_label="Éclaireur")
    state.analyzer = filtered or data
    state.analyzer_raw = json.dumps(state.analyzer, ensure_ascii=False)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "🔍 Éclaireur",
        message="Statut corporate déterminé",
        progress=1.0,
        metrics={"elapsed_ms": elapsed_ms},
    )
    state.log("analyzer", state.analyzer)
    if state.analyzer.get("relationship") == "unknown" and not state.analyzer.get(
        "sources"
    ):
        _append_warning(state, "Statut corporate non déterminé (sources absentes)")
    return state.analyzer


async def _call_information_extractor(state: ExtractionState) -> Dict[str, Any]:
    target = state.target_entity or state.raw_input
    # Toujours effectuer une nouvelle extraction (cache supprimé)

    t0 = time.perf_counter()
    res = await _run_agent_with_retry(
        information_extractor,
        input=target,
        max_turns=MAX_TURNS["info"],
    )
    raw_output = _final_json(res)
    data = _safe_json_loads(raw_output)
    if not data:
        logger.error("JSON info invalide ou vide: %s", raw_output)
        raise ValueError("information_extractor returned empty payload")

    filtered = await _filter_agent_sources(state, data, agent_label="Mineur")
    state.info_card = filtered or data
    state.info_raw = json.dumps(state.info_card, ensure_ascii=False)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "⛏️ Mineur",
        message="Fiche entreprise consolidée",
        progress=1.0,
        metrics={"elapsed_ms": elapsed_ms},
    )
    state.log("info", state.info_card)
    return state.info_card


async def _call_subsidiary_extractor(state: ExtractionState) -> Dict[str, Any]:
    target = state.target_entity or state.raw_input
    # Toujours effectuer une nouvelle extraction (cache supprimé)

    t0 = time.perf_counter()
    res = await _run_agent_with_retry(
        subsidiary_extractor,
        input=target,
        max_turns=MAX_TURNS["subs"],
    )
    raw_output = _final_json(res)
    data = _safe_json_loads(raw_output)
    if not data:
        logger.error("JSON subs invalid: %s", raw_output)
        raise ValueError("subsidiary_extractor returned empty payload")

    logger.info(
        "🔍 RAW subsidiary_extractor output: %s",
        json.dumps(data, indent=2, ensure_ascii=False)[:2000],
    )
    if ENABLE_SUBS_FILTERS:
        filtered = await _filter_inaccessible_sources(state, data)
        # Appliquer un filtre de fraîcheur pour supprimer les filiales obsolètes
        fresh = _filter_fresh_sources(state, filtered or data, max_age_months=24)
        state.subs_report = fresh or filtered or data
    else:
        # Filtres désactivés: utiliser la sortie brute de l'agent
        state.subs_report = data
    state.subs_raw = json.dumps(state.subs_report, ensure_ascii=False)
    logger.info(
        "🔍 AFTER filter, subs_report subsidiaries count: %d",
        len(state.subs_report.get("subsidiaries", [])),
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "🗺️ Cartographe",
        message="Filiales principales extraites",
        progress=1.0,
        metrics={"elapsed_ms": elapsed_ms},
    )
    state.log("subs", state.subs_report)
    if not state.subs_report.get("subsidiaries"):
        state.warnings.append("Aucune filiale fiable trouvée")
    return state.subs_report


def _should_run_meta_validation(state: ExtractionState) -> bool:
    if not state.subs_report:
        return False
    if state.meta_report:
        return False
    if not state.subs_report.get("subsidiaries"):
        return False
    if (
        state.analyzer
        and state.analyzer.get("relationship") == "subsidiary"
        and not state.analyzer.get("parent_company")
    ):
        return True
    if any(not sub.get("sources") for sub in state.subs_report.get("subsidiaries", [])):
        return True
    return False


async def _call_meta_validator(state: ExtractionState) -> Dict[str, Any]:
    agents_results: Dict[str, Any] = {}
    if state.analyzer:
        agents_results["company_analyzer"] = state.analyzer
    if state.info_card:
        agents_results["information_extractor"] = state.info_card
    if state.subs_report:
        agents_results["subsidiary_extractor"] = state.subs_report

    payload = json.dumps({"agents_results": agents_results}, ensure_ascii=False)
    t0 = time.perf_counter()
    res = await _run_agent_with_retry(
        meta_validator,
        input=payload,
        max_turns=MAX_TURNS["meta"],
    )
    raw_output = _final_json(res)
    data = _safe_json_loads(raw_output)
    if not data:
        logger.error("JSON meta invalid: %s", raw_output)
        raise ValueError("meta_validator returned empty payload")

    filtered_meta = data
    if "conflicts" in data or "section_scores" in data:
        filtered_meta = dict(data)
        if "conflicts" in data:
            filtered_conflicts: List[Dict[str, Any]] = []
            for conflict in data.get("conflicts", []):
                filtered_conflict = dict(conflict)
                candidates: List[Dict[str, Any]] = []
                for candidate in conflict.get("candidates", []):
                    filtered_sources, removed = await _filter_sources_list(
                        state, candidate.get("sources")
                    )
                    candidate_copy = dict(candidate)
                    candidate_copy["sources"] = filtered_sources
                    candidates.append(candidate_copy)
                filtered_conflict["candidates"] = candidates
                resolution = conflict.get("resolution")
                if isinstance(resolution, dict):
                    filtered_sources, removed = await _filter_sources_list(
                        state, resolution.get("sources")
                    )
                    filtered_conflict["resolution"] = dict(resolution)
                    filtered_conflict["resolution"]["sources"] = filtered_sources
                filtered_conflicts.append(filtered_conflict)
            filtered_meta["conflicts"] = filtered_conflicts
        if "subsidiaries_confidence" in data:
            entries: List[Dict[str, Any]] = []
            for entry in data.get("subsidiaries_confidence", []):
                entry_copy = dict(entry)
                filtered_sources, removed = await _filter_sources_list(
                    state,
                    entry.get("sources") if isinstance(entry, dict) else None,
                )
                if filtered_sources:
                    entry_copy["sources"] = filtered_sources
                entries.append(entry_copy)
            filtered_meta["subsidiaries_confidence"] = entries

    state.meta_report = filtered_meta
    state.meta_raw = raw_output

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "⚖️ Superviseur",
        message="Validation de cohérence réalisée",
        progress=1.0,
        metrics={"elapsed_ms": elapsed_ms},
    )
    state.log("meta", data)
    for warning in data.get("warnings", [])[:5]:
        if warning not in state.warnings:
            state.warnings.append(warning)
    return data


async def _call_data_restructurer(state: ExtractionState) -> Optional[Dict[str, Any]]:
    """Appel de l'agent restructurateur pour normaliser et valider les données."""
    if not state.subs_report:
        return None

    t0 = time.perf_counter()

    # Préparer les données à restructurer
    data_to_restructure = {
        "company_info": state.info_card,
        "company_info_raw": state.info_raw,
        "subsidiaries": state.subs_report,
        "subsidiaries_raw": state.subs_raw,
        "analyzer_raw": state.analyzer_raw,
        "meta_validation": state.meta_report,
    }

    res = await _run_agent_with_retry(
        data_restructurer,
        input=json.dumps(data_to_restructure, ensure_ascii=False),
        max_turns=3,  # Limite pour éviter les boucles infinies
    )

    raw_output = _final_json(res)
    company_info = _safe_json_loads(raw_output)
    if not company_info:
        logger.warning("JSON restructurer invalid: %s", raw_output)
        return None

    # Vérifier que company_info est un dictionnaire
    if not isinstance(company_info, dict):
        logger.warning("Restructurer output is not a dict: %s", type(company_info))
        return None

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    await _safe_tracking(
        state.session_id,
        "🔄 Restructurateur",
        message="Données restructurées et normalisées",
        progress=1.0,
        metrics={"elapsed_ms": elapsed_ms},
    )

    state.log("restructurer", company_info)
    return company_info


def _parse_headquarters(headquarters: Optional[str]) -> Tuple[str, str, str]:
    """
    Parse headquarters string to extract address, city, country.
    Expected format: "Address, City, Country" or "Address, City PostalCode, Country"
    Returns: (address, city, country)
    """
    if not headquarters or not headquarters.strip():
        return ("Unknown", "Unknown", "Unknown")

    # Try to split by commas (common format)
    parts = [p.strip() for p in headquarters.split(",")]

    if len(parts) >= 3:
        # "Address, City, Country" or "Address, City PostalCode, Country"
        address = parts[0]
        city = parts[-2]  # penultimate part
        country = parts[-1]  # last part
        return (address, city, country)
    elif len(parts) == 2:
        # "City, Country" (no specific address)
        return (parts[0], parts[0], parts[1])
    elif len(parts) == 1:
        # Just a single string, use as address
        return (headquarters, "Unknown", "Unknown")
    else:
        return (headquarters, "Unknown", "Unknown")


def _build_company_info(
    state: ExtractionState,
    analyzer_data: Dict[str, Any],
    info_data: Dict[str, Any],
) -> Dict[str, Any]:
    # info_data est maintenant un CompanyCard (pas CompanyInfo), on doit mapper les champs
    company_info: Dict[str, Any] = {}

    target = (
        state.target_entity or analyzer_data.get("entity_legal_name") or state.raw_input
    )
    company_info["company_name"] = target

    # Mapper CompanyCard → CompanyInfo
    # headquarters (string) → headquarters_address, headquarters_city, headquarters_country
    headquarters_str = info_data.get("headquarters")
    address, city, country = _parse_headquarters(headquarters_str)
    company_info["headquarters_address"] = address
    company_info["headquarters_city"] = city
    company_info["headquarters_country"] = country

    # sector → industry_sector
    company_info["industry_sector"] = info_data.get("sector") or "Non spécifié"

    # activities → core_business (join des activités)
    activities = info_data.get("activities") or []
    company_info["core_business"] = (
        "; ".join(activities) if activities else "Non spécifié"
    )

    # revenue_recent → revenue
    company_info["revenue"] = info_data.get("revenue_recent")

    # employees → employee_count
    company_info["employee_count"] = info_data.get("employees")

    # founding_year (int) → founding_year (str)
    founding_year = info_data.get("founded_year")
    company_info["founding_year"] = str(founding_year) if founding_year else None

    # legal_status (pas dans CompanyCard, on met None)
    company_info["legal_status"] = None

    # confidence_score (pas dans CompanyCard, on met 0.8 par défaut)
    company_info["confidence_score"] = 0.8

    # sources (List[SourceRef dict]) → sources (List[str])
    sources_refs = info_data.get("sources") or []
    logger.info("🔍 DEBUG info_data sources_refs count: %d", len(sources_refs))
    company_info["sources"] = [
        src.get("url") if isinstance(src, dict) else src
        for src in sources_refs
        if (isinstance(src, dict) and src.get("url")) or isinstance(src, str)
    ]
    logger.info(
        "🔍 DEBUG company_info sources after info_data: %s", company_info["sources"]
    )

    relationship = analyzer_data.get("relationship")
    parent_company = analyzer_data.get("parent_company")
    if relationship == "subsidiary" and parent_company:
        company_info["parent_company"] = parent_company
    elif relationship in {"parent", "independent"}:
        # conserver valeur déjà présente le cas échéant
        company_info["parent_company"] = info_data.get("parent_company")

    # Collecter et fusionner les sources AVANT de merger les subsidiaires
    extra_sources = _collect_sources(analyzer_data, state.subs_report)
    logger.info("🔍 DEBUG extra_sources collected: %s", extra_sources)
    company_info["sources"] = _merge_urls(
        company_info.get("sources", []), extra_sources
    )
    logger.info(
        "🔍 DEBUG company_info sources after merge: %s", company_info["sources"]
    )

    # Maintenant on peut merger les subsidiaires avec les sources comme fallback
    details = _merge_subsidiaries(
        [],
        state,
        analyzer_data,
        fallback_sources=company_info.get("sources", []),
    )
    company_info["subsidiaries_details"] = details
    company_info["total_subsidiaries"] = len(details)
    company_info["detailed_subsidiaries"] = len(details)

    # Note: CompanyCard (output de information_extractor) n'a plus de champs
    # global_headquarters ou regional_sites. Ces données sont maintenant dans
    # les filiales via subsidiary_extractor (headquarters + sites par filiale).

    if state.meta_report:
        company_info = _apply_subsidiary_confidence(company_info, state.meta_report)
        scores = state.meta_report.get("section_scores") or {}
        coherence = {
            "geographic_score": scores.get("geographic"),
            "structure_score": scores.get("structure"),
            "sources_score": scores.get("sources"),
            "overall_score": scores.get("overall"),
            "conflicts": [
                c.get("description")
                for c in state.meta_report.get("conflicts", [])[:10]
                if isinstance(c, dict)
            ],
        }
        company_info["coherence_analysis"] = coherence
        if scores.get("overall") is not None:
            company_info["confidence_score"] = float(scores["overall"])

    if state.warnings:
        warning_label = "; ".join(state.warnings[:2])
        quality = list(company_info.get("quality_indicators", []))
        quality.append(
            {
                "indicator_name": "WorkflowWarnings",
                "score": 0.0,
                "description": warning_label,
            }
        )
        company_info["quality_indicators"] = quality

    return company_info


def _merge_subsidiaries(
    existing_details: List[Dict[str, Any]],
    state: ExtractionState,
    analyzer_data: Dict[str, Any],
    *,
    fallback_sources: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    logger.info(
        "🔍 _merge_subsidiaries START: fallback_sources=%s, subs_report has %d subsidiaries",
        fallback_sources,
        len(state.subs_report.get("subsidiaries", []) if state.subs_report else []),
    )
    details_by_name: Dict[str, Dict[str, Any]] = {}
    for item in existing_details:
        name = item.get("subsidiary_name")
        if name:
            details_by_name[name] = {
                "subsidiary_name": name,
                "type": item.get("type"),
                "activity": item.get("activity"),
                "sources": item.get("sources", []),
                "confidence": item.get("confidence"),
                "headquarters_site": item.get("headquarters_site"),
                "operational_sites": item.get("operational_sites", []),
            }

    if state.subs_report:
        for sub in state.subs_report.get("subsidiaries", []):
            name = sub.get("legal_name")
            if not name:
                continue
            entry = details_by_name.get(
                name,
                {
                    "subsidiary_name": name,
                    "type": None,
                    "activity": None,
                    "sources": [],
                    "confidence": None,
                    "headquarters_site": None,
                    "operational_sites": [],
                },
            )
            entry.update(
                {
                    "subsidiary_name": name,
                    "type": sub.get("type"),
                    "activity": sub.get("activity"),
                    "confidence": sub.get("confidence"),
                }
            )

            def _extract_sources(sub_entry: Dict[str, Any]) -> List[str]:
                urls: List[str] = []
                for src in sub_entry.get("sources", []):
                    if isinstance(src, str):
                        urls.append(src)
                    elif isinstance(src, dict):
                        url = src.get("url")
                        if url:
                            urls.append(url)
                return urls

            sources = _extract_sources(sub)

            headquarters = _normalize_site(
                sub.get("headquarters"), label_hint="Headquarters"
            )
            sites = _normalize_sites(sub.get("sites"))

            entry["headquarters_site"] = headquarters or entry.get("headquarters_site")
            entry["operational_sites"] = _dedupe_sites(
                (entry.get("operational_sites") or []) + sites, max_items=7
            )

            # ✅ EXTRACTION DES COORDONNÉES GPS du headquarters vers le niveau racine
            logger.info(
                f"🔍 DEBUG GPS extraction pour {name}: headquarters={type(headquarters)}, data={headquarters}"
            )
            if headquarters and isinstance(headquarters, dict):
                headquarters_lat = headquarters.get("latitude")
                headquarters_lng = headquarters.get("longitude")
                logger.info(
                    f"🔍 DEBUG GPS coords pour {name}: lat={headquarters_lat}, lng={headquarters_lng}"
                )
                if isinstance(headquarters_lat, (int, float)) and isinstance(
                    headquarters_lng, (int, float)
                ):
                    entry["latitude"] = float(headquarters_lat)
                    entry["longitude"] = float(headquarters_lng)
                    logger.info(
                        f"🗺️ Coordonnées GPS extraites pour {name}: {entry['latitude']}, {entry['longitude']}"
                    )
                else:
                    entry["latitude"] = None
                    entry["longitude"] = None
                    logger.info(
                        f"❌ Coordonnées GPS invalides pour {name}: lat={headquarters_lat}, lng={headquarters_lng}"
                    )
            else:
                entry["latitude"] = None
                entry["longitude"] = None
                logger.info(
                    f"❌ Pas de headquarters valide pour {name}: headquarters={headquarters}"
                )

            if not sources and headquarters:
                website = headquarters.get("website")
                if website and isinstance(website, str) and website.startswith("http"):
                    sources.append(website)
            if not sources and sub.get("phone"):
                pass

            existing_sources = entry.get("sources", [])
            entry["sources"] = _merge_urls(existing_sources, sources)

            if not entry["sources"]:
                fallback_website = None
                for contact in entry.get("operational_sites") or []:
                    site_url = (
                        contact.get("website") if isinstance(contact, dict) else None
                    )
                    if isinstance(site_url, str) and site_url.startswith("http"):
                        fallback_website = site_url
                        break
                if (
                    not fallback_website
                    and isinstance(entry.get("headquarters_site"), dict)
                    and isinstance(entry["headquarters_site"].get("website"), str)
                    and entry["headquarters_site"]["website"].startswith("http")
                ):
                    fallback_website = entry["headquarters_site"]["website"]
                if fallback_website:
                    entry["sources"] = [fallback_website]

            if not entry["sources"] and fallback_sources:
                entry["sources"] = [u for u in fallback_sources if u][:1]
                _append_warning(
                    state,
                    f"Source générique appliquée pour {name}",
                )

            details_by_name[name] = entry

    result = list(details_by_name.values())[:10]

    # 🎯 Enrichissement GPS par le Superviseur
    logger.info("📍 Enrichissement GPS des filiales par le Superviseur...")
    # enrich_subsidiaries_gps supprimé - Les modèles GPT peuvent fournir les coordonnées directement

    logger.info(
        "🔍 _merge_subsidiaries END: returning %d subsidiaries, first sources sample: %s",
        len(result),
        [s.get("sources", []) for s in result[:3]],
    )
    return result


def _collect_sources(
    analyzer_data: Dict[str, Any], subs_report: Optional[Dict[str, Any]]
) -> List[str]:
    urls: List[str] = []
    for source in analyzer_data.get("sources", []):
        url = source.get("url") if isinstance(source, dict) else None
        if url:
            urls.append(url)

    if subs_report:
        for sub in subs_report.get("subsidiaries", []):
            if sub.get("sources"):
                src = sub["sources"][0]
                url = src.get("url") if isinstance(src, dict) else None
                if url:
                    urls.append(url)
        for parent in subs_report.get("parents", []):
            for src in parent.get("sources", []):
                url = src.get("url") if isinstance(src, dict) else None
                if url:
                    urls.append(url)
    return urls


def _merge_urls(existing: List[str], additional: List[str]) -> List[str]:
    seen = set()
    merged: List[str] = []
    for url in existing + additional:
        if url and url not in seen:
            seen.add(url)
            merged.append(url)
    return merged


async def _safe_tracking(
    session_id: str,
    step_name: str,
    *,
    message: str,
    progress: float,
    metrics: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        await agent_tracking_service.update_step_progress(
            session_id=session_id,
            step_name=step_name,
            progress=progress,
            message=message,
            performance_metrics=metrics or {},
        )
    except Exception:  # noqa: B902
        logger.debug("Tracking update failed", exc_info=True)


# === 3) Exposition orchestrateur & métadonnées ==============================
_DEFAULT_TOOL_NAMES: List[str] = [
    "run_analyze_and_info",
    "information_extractor",
    "subsidiary_extractor",
    "meta_validator",
    "data_restructurer",
]

_DEFAULT_EXTRACTION_STEPS: List[Dict[str, Any]] = [
    {
        "name": "Identification de l'entité légale",
        "agent": "🔍 Éclaireur",
        "duration": 6,
    },
    {
        "name": "Consolidation des informations clés",
        "agent": "⛏️ Mineur",
        "duration": 10,
        "conditional": True,
    },
    {
        "name": "Extraction des filiales",
        "agent": "🗺️ Cartographe",
        "duration": 12,
    },
    {
        "name": "Validation de cohérence",
        "agent": "⚖️ Superviseur",
        "duration": 4,
        "conditional": True,
    },
    {
        "name": "Restructuration des données",
        "agent": "🔄 Restructurateur",
        "duration": 3,
    },
]

_DEFAULT_SUB_AGENTS: Dict[str, Dict[str, Any]] = {
    "company_analyzer": {"max_turns": MAX_TURNS["analyze"]},
    "information_extractor": {"max_turns": MAX_TURNS["info"]},
    "subsidiary_extractor": {"max_turns": MAX_TURNS["subs"]},
    "meta_validator": {"max_turns": MAX_TURNS["meta"]},
    "data_restructurer": {"max_turns": 3},
}


# Fonctions d'information supprimées - non utilisées


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    val = value.strip()
    return val or None


def _normalize_country(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = " ".join(
        part for part in value.lower().replace(".", " ").split() if part
    )
    mapped = COUNTRY_NORMALIZATION.get(normalized)
    if mapped:
        return mapped
    return " ".join(part.capitalize() for part in normalized.split()) or None


COUNTRY_NORMALIZATION: Dict[str, str] = {
    # États-Unis
    "usa": "États-Unis",
    "u s a": "États-Unis",
    "us": "États-Unis",
    "united states": "États-Unis",
    "united states of america": "États-Unis",
    "etats unis": "États-Unis",
    "états unis": "États-Unis",
    # Royaume-Uni
    "uk": "Royaume-Uni",
    "u k": "Royaume-Uni",
    "united kingdom": "Royaume-Uni",
    "royaume uni": "Royaume-Uni",
    # Corée du Sud
    "south korea": "Corée du Sud",
    "republic of korea": "Corée du Sud",
    "korea": "Corée du Sud",
    # Autres alias fréquents
    "russia": "Russie",
    "russian federation": "Russie",
    "china": "Chine",
    "peoples republic of china": "Chine",
    "people's republic of china": "Chine",
    "hong kong": "Hong Kong",
    "hong kong sar": "Hong Kong",
    "czech republic": "Tchéquie",
    "czechia": "Tchéquie",
    "the netherlands": "Pays-Bas",
    "netherlands": "Pays-Bas",
    "kingdom of the netherlands": "Pays-Bas",
    "france": "France",
    "french republic": "France",
    "mexico": "Mexique",
    "canada": "Canada",
    "germany": "Allemagne",
    "federal republic of germany": "Allemagne",
    "australia": "Australie",
    "new zealand": "Nouvelle-Zélande",
}


# Fonction _aggregate_country_counts supprimée - non utilisée


# =======================================================
# 🔧 Fonctions pour le webhook de suivi en temps réel
# =======================================================


def get_all_tools_names() -> List[str]:
    """Retourne la liste des noms d'outils disponibles"""
    return [
        "run_analyze_and_info",
        "information_extractor",
        "subsidiary_extractor",
        "meta_validator",
        "data_restructurer",
    ]


def get_agent_info() -> Dict[str, Any]:
    """Retourne les informations sur l'orchestrateur principal"""
    return {
        "name": "Extraction Orchestrator",
        "model": "gpt-4o-mini",
        "tools_count": len(get_all_tools_names()),
        "max_turns": 8,
    }


def get_extraction_steps() -> List[Dict[str, Any]]:
    """Retourne les étapes d'extraction avec leurs agents"""
    return [
        {
            "name": "Identification de l'entité légale",
            "agent": "🔍 Éclaireur",
            "duration": 6,
        },
        {
            "name": "Consolidation des informations clés",
            "agent": "⛏️ Mineur",
            "duration": 10,
            "conditional": True,
        },
        {
            "name": "Extraction des filiales",
            "agent": "🗺️ Cartographe",
            "duration": 12,
        },
        {
            "name": "Validation de cohérence",
            "agent": "⚖️ Superviseur",
            "duration": 4,
            "conditional": True,
        },
        {
            "name": "Restructuration des données",
            "agent": "🔄 Restructurateur",
            "duration": 3,
            "conditional": True,
        },
    ]


def get_sub_agents_info() -> Dict[str, Dict[str, Any]]:
    """Retourne les informations sur les sous-agents"""
    return {
        "company_analyzer": {"max_turns": 2, "model": "gpt-4.1-mini"},
        "information_extractor": {"max_turns": 2, "model": "gpt-5-nano"},
        "subsidiary_extractor": {"max_turns": 3, "model": "sonar"},
        "meta_validator": {"max_turns": 1, "model": "gpt-4o-mini"},
        "data_restructurer": {"max_turns": 1, "model": "gpt-4.1-mini"},
    }
