# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FilialeAgents** is a multi-agent company extraction system that uses OpenAI Agents SDK to analyze companies and their subsidiaries. The system orchestrates 5 specialized agents through a pipeline to extract, validate, and structure company information from web sources.

### Key Technologies
- **Backend**: FastAPI + OpenAI Agents SDK + Perplexity API + Redis
- **Frontend**: Next.js 14 + React + TypeScript + Tailwind CSS
- **Orchestration**: Custom agent pipeline with real-time WebSocket tracking
- **Package Manager**: `uv` for Python dependencies (NOT pip)

## Essential Commands

### Development Setup
```bash
# Install all dependencies (use uv, not pip)
make setup                    # Installs both API and frontend dependencies
uv sync                       # Sync Python dependencies via pyproject.toml

# Start services locally (recommended for development)
make start                    # Start API on port 8012
make start-frontend           # Start frontend on port 3002

# Check service status
make status                   # Verify API and frontend availability
```

### Docker (Production-like)
```bash
# Build and start all services (API + Frontend + Redis)
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f frontend

# Stop services
docker-compose down
```

### Testing
```bash
# API health check
make test                     # Curl healthcheck to localhost:8000/health

# Frontend tests (if configured)
make test-frontend           # Run npm test in frontend/

# Manual extraction test
curl -X POST "http://localhost:8012/extract" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "https://www.example.com/"}'
```

### Documentation
```bash
make docs                    # Open Swagger UI (http://localhost:8012/docs)
```

## Architecture: 5-Agent Pipeline

The extraction pipeline orchestrates **5 specialized agents** sequentially:

### 1. 🔍 Éclaireur (Company Analyzer)
- **File**: `api/company_agents/subs_agents/company_analyzer_optimized.py`
- **Model**: gpt-4o-mini
- **Purpose**: Identifies legal entity, detects parent/subsidiary relationships, extracts target domain
- **Output**: `CompanyLinkage` (entity_legal_name, target_domain, relationship, parent_company)
- **Guardrails**: Active URL validation (`api/company_agents/guardrails/eclaireur.py`)
  - Validates domain presence
  - Checks URL accessibility (HTTP 200-299)
  - Auto-retries with correction hints on failure (max 3 attempts)

### 2. ⛏️ Mineur (Information Extractor)
- **File**: `api/company_agents/subs_agents/information_extractor_optimized_v2.py`
- **Model**: gpt-4o-mini
- **Purpose**: Extracts key company info (headquarters, sector, revenue, employees)
- **Output**: `CompanyCard`
- **Search Strategy**: Strict on-domain search (`site:{domain}`) to avoid homonyms

### 3. 🗺️ Cartographe (Subsidiary Extractor)
- **File**: `api/company_agents/subs_agents/subsidiary_extractor.py`
- **Models**:
  - **Simple mode** (`deep_search=False`): gpt-4o-search-preview (fast, economical)
  - **Advanced mode** (`deep_search=True`): Perplexity Sonar Pro (thorough, comprehensive)
- **Purpose**: Extracts subsidiaries with locations, contacts (phone/email), GPS coordinates
- **Output**: `SubsidiaryReport`
- **Plan B**: If no subsidiaries found → enriched info about main company in `extraction_summary.main_company_info`

### 4. ⚖️ Superviseur (Meta Validator)
- **File**: `api/company_agents/subs_agents/meta_validator_optimized.py`
- **Model**: gpt-4o-mini
- **Purpose**: Validates global coherence (geographic/business alignment, source quality)
- **Output**: `MetaValidationReport` (scores, conflicts, excluded subsidiaries)

### 5. 🔄 Restructurateur (Data Restructurer)
- **File**: `api/company_agents/subs_agents/data_validator_optimized.py`
- **Model**: gpt-4o-mini
- **Purpose**: Normalizes to final `CompanyInfo` schema, enriches GPS, extracts contacts
- **Output**: `CompanyInfo` (final API response format)

### Orchestration
- **Entry point**: `api/company_agents/extraction_core.py` → `extract_company_data()`
- **Pipeline logic**: `api/company_agents/orchestrator/extraction_orchestrator.py`
- **Agent caller**: `api/company_agents/orchestrator/agent_caller.py` (handles retries, metrics, guardrails)

## Critical Implementation Rules

### 1. Workflow: Plan → Validation → Execution (from `.cursor/rules/my-rules.mdc`)
- **ALWAYS** propose a plan before implementing changes
- **List affected files** with sample diffs
- **Wait for explicit approval** ("OK, execute") before proceeding
- **NEVER** implement without user confirmation

### 2. Minimal Scope
- **FORBIDDEN** without validation: out-of-scope refactoring, mass renaming, opportunistic optimizations
- Only modify what's strictly requested
- Prefer extending existing files over creating new ones

### 3. Agent Development
- Agents are defined in `api/company_agents/subs_agents/`
- Each agent uses OpenAI Agents SDK: `Agent(model=..., instructions=..., tools=[...])`
- Guardrails are registered in `api/company_agents/guardrails/__init__.py` via `load_guardrails()`
- Output schemas are Pydantic models in `api/company_agents/models.py`

### 4. Testing
- **NEVER** create tests without explicit request
- **BEFORE** creating tests: propose plan, conventions, sample diff → wait for "OK, create"
- **AUTO-CLEAN** after test execution: remove `*.test.tmp*`, `.pytest_cache/`, `coverage/`

### 5. Documentation
- All documentation (except root `README.md`) **MUST** go in `docs/` folder
- **BEFORE** creating new `.md`: verify if existing doc can be enriched
- Keep `docs/` clean by removing obsolete files when adding new ones

### 6. Jupyter Notebooks
- **NEVER** create/modify `.ipynb` without explicit request
- Always use `ipynb,py:light` format (Jupytext pairing)
- Strip outputs before commit (`nbstripout`)

### 7. Package Management
- **USE**: `uv` commands (`uv sync`, `uv add <package>`, `uv remove <package>`)
- **DO NOT USE**: `pip install` (breaks `uv` lock file)
- Dependencies are in `pyproject.toml`, lockfile is `uv.lock`

## Key File Locations

### Backend Structure
```
api/
├── main.py                              # ASGI entry point
├── start.py                             # Local dev server
├── routers/
│   ├── extraction.py                    # POST /extract, /extract-async
│   ├── health.py                        # GET /health
│   ├── tracking.py                      # GET /tracking/{session_id}
│   └── websocket.py                     # WS /ws/{session_id}
├── services/
│   ├── extraction_service.py            # Orchestration
│   ├── websocket_service.py             # WebSocket + heartbeat
│   ├── agent_tracking_service.py        # Agent state tracking
│   └── cost_tracking_service.py         # Cost calculation (USD/EUR)
├── company_agents/
│   ├── extraction_core.py               # Main entry: extract_company_data()
│   ├── orchestrator/
│   │   ├── extraction_orchestrator.py   # 5-stage pipeline
│   │   └── agent_caller.py              # Agent execution + retry logic
│   ├── subs_agents/                     # 5 specialized agents
│   ├── guardrails/                      # Output validation
│   ├── metrics/                         # Real-time tracking
│   ├── models.py                        # Pydantic schemas
│   └── config/                          # Agent configuration
└── status/
    ├── manager.py                       # Redis session manager
    └── models.py                        # AgentStatus, AgentState
```

### Frontend Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                     # Search page
│   │   └── results/page.tsx             # Results display
│   ├── components/
│   │   ├── ui/
│   │   │   ├── agent-progress.tsx       # WebSocket progress
│   │   │   └── enhanced-agent-progress.tsx
│   │   ├── company/
│   │   │   ├── company-overview.tsx     # Company info + contacts
│   │   │   ├── subsidiaries-list.tsx    # Subsidiaries list
│   │   │   └── subsidiaries-visualization.tsx
│   │   └── search/
│   │       └── search-page.tsx          # Search form
│   ├── hooks/
│   │   ├── use-company-data.ts          # Fetch results
│   │   └── use-safe-search-params.ts
│   └── lib/
│       └── api.ts                       # TypeScript types
└── public/                              # Static assets
```

## Real-Time Tracking (WebSocket)

### Backend: Heartbeat Implementation
- **Location**: `api/services/websocket_service.py`
- **Ping interval**: 25s (< 30s Nginx timeout)
- **Format**: `{"type": "ping", "timestamp": "..."}`
- **Agent updates**: Sent via `AgentTrackingService` → WebSocket queue

### Frontend: Auto-Reconnect
- **Location**: `frontend/src/components/ui/agent-progress.tsx`
- **Logic**: On `ws.onclose` → retry after 3s delay
- **Pong response**: Client sends `{"type": "pong", "timestamp": "..."}` on ping

### Agent States
- `waiting` → `initializing` → `running` → `finalizing` → `completed` | `error`

## Guardrails System

### Active Guardrails
- **Éclaireur**: URL accessibility validation (`api/company_agents/guardrails/eclaireur.py`)
  - Checks HTTP status codes (200-299 = accessible)
  - Detects errors: 404, 403, 500+, Timeout, ConnectionError, SSLError
  - **Auto-retry**: On failure, sends correction hint with exact dead URLs + HTTP codes

### How Guardrails Work
1. Agent produces output
2. Guardrail validates via `@output_guardrail` decorator
3. If validation fails → raise `OutputGuardrailFailure` with `output_info`
4. System retries agent with correction hint (max 3 attempts)
5. Agent corrects output based on hint

### Example Correction Hint
```
⚠️ URLs NON ACCESSIBLES détectées:
  - https://example.com/mentions-legales (HTTP 404)
  - https://example.com/timeout (Timeout)

Remplace chaque URL ci-dessus par une page on-domain accessible (contact/about/home).
```

## Data Models (Pydantic)

### Final Output: `CompanyInfo`
- **Location**: `api/company_agents/models.py`
- **Key fields**:
  - `company_name`, `headquarters_address`, `headquarters_city`, `headquarters_country`
  - `parent_company`, `sector`, `activities`, `revenue_recent`, `employees`
  - `phone`, `email` (extracted from `main_company_info` if no subsidiaries)
  - `subsidiaries_details: List[SubsidiaryDetail]` (juridical entities)
  - `commercial_presence_details: List[CommercialPresence]` (offices, partners, distributors)
  - `sources: List[SourceRef]`
  - `extraction_costs: Optional[ExtractionCosts]` (USD/EUR breakdown by model)

### Intermediate Models
- `CompanyLinkage` (Éclaireur output)
- `CompanyCard` (Mineur output)
- `SubsidiaryReport` (Cartographe output)
- `MetaValidationReport` (Superviseur output)

## Environment Variables

Required in `.env` file:
```bash
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
REDIS_URL=redis://localhost:6379
API_HOST=0.0.0.0
API_PORT=8012
NEXT_PUBLIC_API_URL=http://localhost:8012
NEXT_PUBLIC_WS_URL=ws://localhost:8012/ws
ENABLE_GUARDRAILS=true
LOG_LEVEL=INFO
```

## Cost Tracking

- **Service**: `api/services/cost_tracking_service.py`
- **Models**: gpt-4o, gpt-4o-mini, gpt-4o-search-preview, sonar-pro (Perplexity)
- **Pricing**: Tracked per 1M tokens (input/output), converted to USD + EUR
- **Output**: `extraction_costs` field in `CompanyInfo` response
- **Endpoints**:
  - `GET /costs/organization/stats` (aggregate stats)
  - `POST /costs/estimate` (pre-extraction estimate)
  - `GET /costs/extraction/{extraction_id}` (detailed breakdown)

## Deep Search Mode

- **Parameter**: `deep_search: bool` (default: `False`)
- **Simple mode** (`False`): Uses `gpt-4o-search-preview` → fast, economical (~0.01-0.05€)
- **Advanced mode** (`True`): Uses Perplexity Sonar Pro → thorough, comprehensive (~0.05-0.20€)
- **Location**: Configured in Cartographe agent (`api/company_agents/subs_agents/subsidiary_extractor.py`)

## API Endpoints

### Core Extraction
- `POST /extract` - Synchronous extraction (company name or URL)
- `POST /extract-async` - Asynchronous extraction (returns 202 Accepted + session_id)
- `POST /extract-from-url-async` - URL-specific async extraction
- `GET /results/{session_id}` - Retrieve extraction results
- `WS /ws/{session_id}` - Real-time progress tracking

### Monitoring
- `GET /health` - Health check
- `GET /tracking/{session_id}` - Extraction status
- `GET /docs` - Swagger UI

## Common Pitfalls

1. **Don't use `pip`**: Always use `uv sync` / `uv add` / `uv remove`
2. **Don't skip plan validation**: NEVER implement without user approval
3. **Don't create files unnecessarily**: Prefer editing existing files
4. **Don't modify out-of-scope code**: Keep changes minimal
5. **Don't commit test outputs**: Auto-clean `.pytest_cache/`, `coverage/`, etc.
6. **Don't push to `main`**: Use feature branches + PRs
7. **Don't hard-code secrets**: Use environment variables only

## Debugging Tips

### View Agent Logs
```bash
# Docker
docker-compose logs -f api | grep "Éclaireur\|Cartographe\|Guardrail"

# Local
# Logs are in stdout when running `make start`
```

### Test Single Agent
```python
# In api/company_agents/subs_agents/
from company_analyzer_optimized import create_company_analyzer_agent

agent = create_company_analyzer_agent()
result = agent.run("https://www.example.com/")
print(result.model_dump_json(indent=2))
```

### Check Guardrail Execution
- Look for log lines: `🚨 Guardrail Éclaireur déclenché`
- Retry messages: `⚠️ Guardrail déclenché (tentative 1/3)`
- Success: `✅ Guardrail Éclaireur: validation OK`

## Code Style & Quality

- **Formatting**: Follow existing style, don't mass-reformat
- **Linting**: Run `black` and `flake8` before PR (configured in `pyproject.toml`)
- **Type hints**: Use type annotations for new functions
- **Error handling**: Explicit try/catch on risky operations (I/O, network, parsing)
- **Logging**: Use structured logs with levels (DEBUG, INFO, WARNING, ERROR)
- **Security**: NEVER commit secrets, use env vars for all credentials

## Git Workflow

- **Protected branch**: `main` (do not push directly)
- **Commit style**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Review required**: All PRs need approval before merge
- **Required checks**: Tests must pass, no red CI status

## References

- **README.md**: High-level project overview
- **docs/**: Technical documentation (create only when needed, keep clean)
- **api/README.md**: API-specific documentation
- **frontend/README.md**: Frontend-specific documentation
- **Swagger UI**: http://localhost:8012/docs (when API running)
- **.cursor/rules/my-rules.mdc**: Development workflow rules (plan → validate → execute)
