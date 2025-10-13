"""
Output Guardrail pour l'Éclaireur (Company Analyzer)

Vérifie que la sortie contient :
1. target_domain présent (si détectable)
2. Au moins 1 source on-domain valide (en MODE URL)
3. URLs accessibles (vérification active HTTP)
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from agents import output_guardrail, GuardrailFunctionOutput
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)

# Configuration pour la vérification d'accessibilité
TIMEOUT_SECONDS = 5.0
MAX_CONCURRENT_CHECKS = 5
ALLOWED_STATUS_CODES = {200, 201, 202, 203, 204, 205, 206, 301, 302, 303, 307, 308, 403}  # 403 = Protected but exists


def _extract_domain(url: str) -> Optional[str]:
    """Extrait le domaine d'une URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Enlever 'www.' si présent
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


def _is_url(text: str) -> bool:
    """Vérifie si le texte contient une URL."""
    return text.strip().startswith(("http://", "https://"))


async def _check_url_accessibility(url: str) -> Dict[str, Any]:
    """
    Vérifie l'accessibilité d'une URL via requête HTTP HEAD.
    
    Args:
        url: URL à vérifier
        
    Returns:
        Dict avec status_code, accessible (bool), et error_message
    """
    if not url or not url.startswith("http"):
        return {"url": url, "accessible": False, "status_code": None, "error": "URL invalide"}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FilialeAgentsBot/1.0; +https://agencenile.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            # Essayer HEAD d'abord (plus rapide)
            try:
                response = await client.head(url, headers=headers)
                status_code = response.status_code
            except (httpx.HTTPStatusError, httpx.RequestError):
                # Si HEAD échoue, essayer GET
                response = await client.get(url, headers=headers)
                status_code = response.status_code
            
            accessible = status_code in ALLOWED_STATUS_CODES
            
            return {
                "url": url,
                "accessible": accessible,
                "status_code": status_code,
                "error": None if accessible else f"HTTP {status_code}"
            }
    
    except httpx.TimeoutException:
        return {"url": url, "accessible": False, "status_code": None, "error": "Timeout"}
    except httpx.ConnectError:
        return {"url": url, "accessible": False, "status_code": None, "error": "Connection refused"}
    except httpx.InvalidURL:
        return {"url": url, "accessible": False, "status_code": None, "error": "URL invalide"}
    except Exception as e:
        return {"url": url, "accessible": False, "status_code": None, "error": str(e)[:100]}


async def _check_sources_accessibility(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Vérifie l'accessibilité de toutes les sources en parallèle.
    
    Args:
        sources: Liste des sources avec URLs
        
    Returns:
        Dict avec accessible_sources, dead_links, et vérification summary
    """
    urls_to_check = [src.get("url") for src in sources if src.get("url")]
    
    if not urls_to_check:
        return {"accessible_sources": [], "dead_links": [], "total_checked": 0}
    
    # Vérifier les URLs en parallèle (limité à MAX_CONCURRENT_CHECKS)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    
    async def check_with_semaphore(url: str):
        async with semaphore:
            return await _check_url_accessibility(url)
    
    # Exécuter les vérifications en parallèle
    results = await asyncio.gather(*[check_with_semaphore(url) for url in urls_to_check])
    
    # Séparer les sources accessibles des liens morts
    accessible_sources = []
    dead_links = []
    
    for result in results:
        if result["accessible"]:
            accessible_sources.append(result["url"])
        else:
            dead_links.append({
                "url": result["url"],
                "error": result["error"],
                "status_code": result["status_code"]
            })
    
    logger.info(
        f"🔍 Vérification d'accessibilité: {len(accessible_sources)}/{len(urls_to_check)} URLs accessibles"
    )
    
    return {
        "accessible_sources": accessible_sources,
        "dead_links": dead_links,
        "total_checked": len(urls_to_check)
    }


@output_guardrail
async def eclaireur_output_guardrail(ctx, agent, output: Dict[str, Any]) -> GuardrailFunctionOutput:
    """
    Guardrail de sortie pour l'Éclaireur selon la doc OpenAI.
    
    Vérifie :
    - Présence de target_domain (en MODE URL)
    - Au moins 1 source on-domain valide (en MODE URL)
    - Exclusion des URLs mortes (404, timeout, etc.)
    
    Args:
        ctx: Contexte d'exécution
        agent: Agent en cours
        output: Sortie de l'agent (dict CompanyLinkage)
        
    Returns:
        GuardrailFunctionOutput avec tripwire si violation détectée
    """
    try:
        # Récupérer l'input original depuis le contexte
        # Le contexte OpenAI peut être un RunContextWrapper, pas un dict
        original_input = ""
        
        # Essayer d'accéder aux messages du contexte (format OpenAI SDK)
        if hasattr(ctx, "messages") and ctx.messages:
            # Prendre le premier message utilisateur
            for msg in ctx.messages:
                if hasattr(msg, "content"):
                    original_input = msg.content
                    break
                elif isinstance(msg, dict) and "content" in msg:
                    original_input = msg["content"]
                    break
        
        # Fallback : convertir ctx en string si nécessaire
        if not original_input:
            original_input = str(ctx) if ctx else ""
        
        # Déterminer si on est en MODE URL
        is_url_mode = _is_url(str(original_input))
        
        # Extraire le domaine cible de l'input (si MODE URL)
        input_domain = None
        if is_url_mode:
            input_domain = _extract_domain(str(original_input))
        
        # Convertir l'output en dict si c'est un objet Pydantic
        if hasattr(output, "model_dump"):
            output_dict = output.model_dump()
        elif isinstance(output, dict):
            output_dict = output
        else:
            # Fallback : essayer de le convertir en dict
            output_dict = dict(output) if output else {}
        
        # Extraire les données de la sortie
        target_domain = output_dict.get("target_domain")
        sources = output_dict.get("sources", [])
        
        # Liste des violations
        violations: List[str] = []
        removed_dead_links: List[str] = []
        
        # RÈGLE 1: En MODE URL, target_domain doit être présent
        if is_url_mode and not target_domain:
            violations.append("target_domain manquant en MODE URL")
        
        # RÈGLE 2: En MODE URL, au moins 1 source on-domain
        on_domain_sources = []
        if is_url_mode and input_domain:
            for src in sources:
                src_url = src.get("url", "")
                if src_url:
                    src_domain = _extract_domain(src_url)
                    if src_domain == input_domain:
                        on_domain_sources.append(src)
            
            if not on_domain_sources:
                violations.append(f"Aucune source on-domain trouvée pour {input_domain}")
        
        # RÈGLE 3: Vérifier ACTIVEMENT l'accessibilité des URLs
        logger.info(f"🔍 Vérification active de {len(sources)} sources...")
        accessibility_check = await _check_sources_accessibility(sources)
        
        dead_links_info = accessibility_check.get("dead_links", [])
        accessible_count = len(accessibility_check.get("accessible_sources", []))
        
        # Extraire les URLs mortes avec détails pour le hint de correction
        for dead_link in dead_links_info:
            url = dead_link["url"]
            status_code = dead_link.get("status_code")
            error = dead_link.get("error", "Inaccessible")
            
            # Format : "URL (HTTP 404)" ou "URL (Timeout)" etc.
            if status_code:
                removed_dead_links.append(f"{url} (HTTP {status_code})")
            else:
                removed_dead_links.append(f"{url} ({error})")
        
        # Si des liens morts sont détectés, enregistrer
        if removed_dead_links:
            # Construire le message d'erreur sans f-strings imbriqués
            dead_link_details = [f"{dl['url']} ({dl['error']})" for dl in dead_links_info[:2]]
            violations.append(
                f"URLs inaccessibles détectées ({len(removed_dead_links)}/{len(sources)}): "
                f"{', '.join(dead_link_details)}"
            )
        
        # Décision : déclencher le tripwire si violations critiques
        if violations:
            logger.warning(f"🚨 Guardrail Éclaireur déclenché: {', '.join(violations)}")
            
            # Retourner avec tripwire_triggered=True pour forcer un retry
            return GuardrailFunctionOutput(
                output_info={
                    "violations": violations,
                    "removed_dead_links": removed_dead_links,
                    "input_domain": input_domain,
                    "found_on_domain_sources": len(on_domain_sources),
                    "is_url_mode": is_url_mode,
                },
                tripwire_triggered=True
            )
        
        # Pas de violation : laisser passer
        logger.info(f"✅ Guardrail Éclaireur: validation OK")
        return GuardrailFunctionOutput(
            output_info={"status": "ok"},
            tripwire_triggered=False
        )
    
    except Exception as e:
        # En cas d'erreur dans le guardrail, ne pas bloquer l'agent
        logger.error(f"❌ Erreur dans le guardrail Éclaireur: {e}", exc_info=True)
        return GuardrailFunctionOutput(
            output_info={"error": str(e)},
            tripwire_triggered=False  # Ne pas bloquer sur erreur guardrail
        )

