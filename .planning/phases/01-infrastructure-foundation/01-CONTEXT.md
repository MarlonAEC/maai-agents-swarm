# Phase 1: Infrastructure Foundation - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Docker Compose stack that starts the full infrastructure with a single command. Ollama serves local LLMs, LiteLLM proxies and routes model requests, and Open WebUI provides the browser-based chat interface. GPU acceleration confirmed when available, CPU fallback functional. Per-client config folder mounted and loaded.

This phase does NOT include: Core API (FastAPI), CrewAI agents, Redis, Qdrant, or any application logic. Those are Phase 2+.

</domain>

<decisions>
## Implementation Decisions

### Service Topology
- **D-01:** Phase 1 Docker Compose includes only three services: Ollama, LiteLLM, and Open WebUI. No other services (Redis, Qdrant, CrewAI worker, FastAPI) until their respective phases.
- **D-02:** Use an explicit named Docker network (e.g., `maai-net`). Services reference each other by container name. Addresses INFRA-06 (no localhost pitfalls).
- **D-03:** All LLM traffic routes through LiteLLM: Open WebUI -> LiteLLM -> Ollama. Open WebUI is configured with LiteLLM as its OpenAI-compatible endpoint. This centralizes model routing for INFRA-05.
- **D-04:** Open WebUI host port is configurable via `WEBUI_PORT` in client.env, defaulting to 3000.

### Model Bootstrapping
- **D-05:** Separate bootstrap script (bootstrap.sh) pulls required models before the stack starts. Run once on first deploy, not on every container start.
- **D-06:** Model list is config-driven — read from models.yaml in the client config folder. Default set: Qwen3 14B (reasoning), Gemma 3 4B (classification), nomic-embed-text (embeddings).
- **D-07:** Downloaded models persisted in a named Docker volume (e.g., `ollama-models`). Survives container rebuilds.

### Client Config Layout
- **D-08:** Flat directory structure: `clients/<client-name>/` containing client.env, models.yaml, and placeholder files for later phases. Phase 1 only uses client.env and models.yaml.
- **D-09:** Ship a `clients/default/` folder with working client.env.example and models.yaml. Docker Compose references this path by default. User copies and customizes.
- **D-10:** Phase 1 client.env contains minimal vars: WEBUI_PORT, OLLAMA_GPU_ENABLED, REASONING_MODEL, CLASSIFIER_MODEL, EMBEDDING_MODEL. No forward-looking placeholders.

### GPU/CPU Fallback
- **D-11:** Two Docker Compose profiles: `gpu` (default, uses NVIDIA runtime + deploy.resources.reservations) and `cpu` (no GPU config). Bootstrap script detects GPU availability and sets the active profile. OLLAMA_GPU_ENABLED in client.env serves as manual override.
- **D-12:** When CPU profile is active, bootstrap auto-switches to smaller models: Qwen3 7B instead of 14B, Gemma 3 1B instead of 4B. LiteLLM config updated accordingly. User does not need to manually edit models.yaml for CPU-only deployments.

### Claude's Discretion
- LiteLLM configuration file format and model alias naming
- Docker Compose health check configuration for each service
- Exact Compose file structure and YAML organization
- Bootstrap script implementation details (bash vs Python)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Documentation
- `.planning/PROJECT.md` -- Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` -- INFRA-01 through INFRA-06 acceptance criteria
- `.planning/ROADMAP.md` -- Phase 1 success criteria and dependencies
- `CLAUDE.md` -- Technology stack details, version compatibility, model recommendations

### Technology References (from CLAUDE.md)
- LiteLLM >= 1.83.0 required (supply chain attack on 1.82.7/1.82.8)
- Docker Compose V2 plugin (`docker compose` not `docker-compose`)
- Ollama Docker image: `ollama/ollama`
- Open WebUI Docker image: `ghcr.io/open-webui/open-webui`
- nomic-embed-text must be explicitly pulled (not auto-pulled with other models)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code.

### Established Patterns
- None yet — Phase 1 establishes the foundational patterns.

### Integration Points
- Docker Compose is the single entry point for the entire stack
- client.env is the per-client configuration surface
- models.yaml defines which LLMs are available per deployment
- LiteLLM proxy URL is the single LLM endpoint for all consumers (Open WebUI now, Core API in Phase 2)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. All decisions followed recommended defaults.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-infrastructure-foundation*
*Context gathered: 2026-04-07*
