# Output Guardrails - Documentation

## 🎯 Objectif

Les **output guardrails** valident les sorties des agents selon la documentation OpenAI Agents SDK, en déclenchant des **retries automatiques** sans bloquer le suivi temps réel WebSocket.

## 📋 Architecture

### 1. Guardrail Function (@output_guardrail)

Chaque guardrail est une fonction async décorée avec `@output_guardrail` :

```python
from agents import output_guardrail, GuardrailFunctionOutput

@output_guardrail
async def my_guardrail(ctx, agent, output: Dict[str, Any]) -> GuardrailFunctionOutput:
    # Validation logic
    if violation_detected:
        return GuardrailFunctionOutput(
            output_info={"violations": [...], "details": {...}},
            tripwire_triggered=True  # Déclenche un retry
        )
    
    return GuardrailFunctionOutput(
        output_info={"status": "ok"},
        tripwire_triggered=False  # Validation OK
    )
```

### 2. Retry Mechanism (agent_wrappers.py)

Le wrapper `run_agent_with_metrics` gère les retries **sans bloquer le tracking** :

- **Tentative 1** : Exécution normale
- **Tentative 2** (si guardrail déclenché) : Ajout d'un `[CORRECTION_HINT]` avec les liens morts détectés
- **Tentative 3** (si échec) : Ajout d'un `[CORRECTION_HINT_FINAL]` avec instructions strictes

**Paramètres** :
- `max_retries=2` : Nombre de retries (par défaut 2)
- Le tracking WebSocket **continue en arrière-plan** pendant tous les retries

### 3. Lifecycle Hooks (agent_hooks.py)

Les hooks notifient le frontend via WebSocket des événements guardrail :

```python
class RealtimeAgentHooks(AgentHooks):
    async def on_output_guardrail_tripwire_triggered(self, context, guardrail_result):
        # Notifie le frontend : "⚠️ Validation échouée - Retry en cours..."
        await self.status_manager.update_agent_status_detailed(...)
```

## 🔧 Configuration

### Activer un guardrail pour un agent

**Fichier** : `api/company_agents/config/agent_config.py`

```python
DEFAULT_AGENT_GUARDRAILS: Dict[str, List[str]] = {
    "company_analyzer": [
        "company_agents.guardrails.eclaireur:eclaireur_output_guardrail",
    ],
    "information_extractor": [
        "company_agents.guardrails.mineur:mineur_output_guardrail",
    ],
}
```

**Format** : `"module.path:function_name"`

### Charger les guardrails dynamiquement

**Fichier** : `api/company_agents/subs_agents/company_analyzer.py`

```python
from company_agents.config.agent_config import load_guardrails

company_analyzer = Agent(
    name="🔍 Éclaireur",
    # ... config ...
)

# Charger les guardrails déclarés en config
company_analyzer.output_guardrails = load_guardrails("company_analyzer")
```

## 📊 Suivi Temps Réel

### Flow d'exécution

```
1. Agent démarre
   └─> Hook: on_agent_start() → WebSocket: "initializing"

2. Exécution de l'agent
   └─> Tracking en arrière-plan (boucle asyncio)

3. Si guardrail déclenché
   ├─> Hook: on_output_guardrail_tripwire_triggered()
   ├─> WebSocket: "⚠️ Validation échouée - Retry en cours..."
   └─> Retry avec correction hint (tracking continue)

4. Si succès
   └─> Hook: on_agent_end() → WebSocket: "completed"
```

### Métriques transmises

- `guardrail_triggered: bool` : Indique si un guardrail a été déclenché
- `violations: List[str]` : Liste des violations détectées (max 3)
- `retry_attempt: int` : Numéro de la tentative (1, 2, 3)

## 🚨 Exemple Complet : Éclaireur

### Guardrail (eclaireur.py)

Vérifie :
1. ✅ `target_domain` présent (en MODE URL)
2. ✅ Au moins 1 source on-domain valide
3. ✅ Exclusion des URLs mortes (404, timeout)

```python
@output_guardrail
async def eclaireur_output_guardrail(ctx, agent, output: Dict[str, Any]):
    # Détection MODE URL
    is_url_mode = _is_url(ctx.get("original_input", ""))
    
    # Validation
    if is_url_mode and not output.get("target_domain"):
        return GuardrailFunctionOutput(
            output_info={"violations": ["target_domain manquant"]},
            tripwire_triggered=True
        )
    
    # ... autres validations ...
```

### Workflow avec Retry

**Tentative 1** :
```json
Input: "https://www.agencenile.com/"
Output: {"target_domain": null, "sources": [...]}
→ Guardrail: TRIPWIRE (target_domain manquant)
```

**Tentative 2** (avec correction) :
```json
Input: "https://www.agencenile.com/
[CORRECTION_HINT]: Corrige la sortie pour respecter:
1) target_domain présent si détectable
2) ≥1 source on-domain valide
3) exclure/remplacer toute URL morte"

Output: {"target_domain": "agencenile.com", "sources": [{"url": "https://www.agencenile.com/mentions-legales", ...}]}
→ Guardrail: ✅ OK
```

## ⚙️ Best Practices

1. **Guardrails légers** : Validation rapide (<100ms) pour ne pas ralentir le workflow
2. **Exceptions gracieuses** : Si le guardrail plante, ne pas bloquer l'agent (`tripwire_triggered=False`)
3. **Logs détaillés** : Logger les violations pour debug
4. **Max retries limité** : 2-3 retries max pour éviter les boucles infinies
5. **WebSocket continu** : Le tracking ne doit **jamais** être annulé pendant les retries

## 🔗 Références

- [OpenAI Agents SDK - Guardrails](https://platform.openai.com/docs/guides/agents/guardrails)
- [OpenAI Agents SDK - Lifecycle Hooks](https://platform.openai.com/docs/guides/agents/lifecycle-hooks)
- [OutputGuardrailTripwireTriggered Exception](https://github.com/openai/agents-sdk/blob/main/agents/exceptions.py)

