# Phase 2: Core API and End-to-End Chat - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

A user message travels from Open WebUI through a Pipelines plugin to the FastAPI Core API, which invokes a CrewAI freeform agent backed by the local LLM (via LiteLLM), and returns a coherent response. Chat history persists, multi-turn context is maintained, and file uploads are accepted and acknowledged (but not processed until Phase 4).

This phase does NOT include: YAML-defined skills or Skill Matcher (Phase 3), document ingestion/RAG (Phase 4), Redis/ARQ task queuing (Phase 4+), or any business tools (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### WebUI-to-API Integration
- **D-01:** Open WebUI connects to Core API via a **Pipelines plugin** (filter/pipe). The Pipelines server runs as a separate Docker container with the plugin mounted as a volume.
- **D-02:** **ALL chat messages** route through the Pipeline -> Core API -> CrewAI agent. No split routing. The agent handles everything — user never thinks about routing.
- **D-03:** During agent processing, the Pipeline sends **intermediate status messages** ('Thinking...', 'Processing your request...') as partial streaming responses so the user sees progress.
- **D-04:** Open WebUI's existing config stays: `ENABLE_OLLAMA_API=false`, `OPENAI_API_BASE_URLS=http://litellm:4000/v1`. The Pipelines container is registered as a pipeline endpoint in Open WebUI.

### CrewAI Agent Design
- **D-05:** Phase 2 agent is **pure conversational** — no tools. It's a reasoning-capable LLM wrapper with a good system prompt. It gracefully declines tasks it can't do yet.
- **D-06:** **Pipeline passes full message history** to Core API. Open WebUI already tracks chat history — no need for Core API to maintain its own session store. Core API injects the history into CrewAI agent context.
- **D-07:** Agent uses the **`reasoning-model`** alias from LiteLLM (Qwen3 14B / Qwen3 7B on CPU).
- **D-08:** Agent runs with **non-streaming mode** (`stream=False`) per AGNT-08 to prevent tool call drops. Status updates are sent by the Pipeline layer, not by the agent itself.
- **D-09:** **Conservative guardrails**: `max_iter=5`, `max_execution_time=60s` per AGNT-09. Sufficient for conversational use; can be tuned via config later.
- **D-10:** CrewAI embedder explicitly configured for Ollama using `embedding-model` alias (AGNT-07) — not defaulting to OpenAI.

### Service Architecture
- **D-11:** CrewAI runs **in-process** inside the FastAPI service. No Redis or ARQ worker in Phase 2. Add task queuing when async heavy processing is needed (Phase 4+).
- **D-12:** Two new Docker services added: (1) `core-api` (FastAPI + CrewAI, Python 3.11), (2) `pipelines` (Open WebUI Pipelines server with filter plugin). Both join `maai-net`.
- **D-13:** Python code lives at **`src/core_api/`** with Dockerfile at `src/core_api/Dockerfile`. Pipelines plugin at **`src/pipelines/`**.

### File Upload Handling
- **D-14:** Pipeline **accepts files from Open WebUI** and stores them in a shared Docker volume (`maai-uploads`). Responds with: "File received: {filename}. Document processing will be available in a future update."
- **D-15:** Shared volume `maai-uploads` is mounted in both Pipelines and Core API containers. Phase 4 adds Docling processing from the same volume.
- **D-16:** No file parsing, metadata extraction, or content processing in Phase 2. Just receipt acknowledgment.

### Claude's Discretion
- Pipelines plugin implementation details (filter vs pipe type, exact protocol)
- FastAPI endpoint design (routes, request/response schemas)
- CrewAI agent system prompt content
- Docker health check configuration for new services
- Exact Pipelines server image and configuration

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Documentation
- `.planning/PROJECT.md` -- Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` -- CHAT-01 through CHAT-06, AGNT-07 through AGNT-09 acceptance criteria
- `.planning/ROADMAP.md` -- Phase 2 success criteria and dependencies
- `CLAUDE.md` -- Technology stack, version compatibility, model recommendations

### Phase 1 Artifacts
- `.planning/phases/01-infrastructure-foundation/01-CONTEXT.md` -- Phase 1 decisions (service topology, model bootstrapping, client config layout)
- `docker-compose.yml` -- Current 3-service stack (Ollama, LiteLLM, Open WebUI) to extend
- `config/litellm/proxy_config.yaml` -- LiteLLM model aliases (reasoning-model, classifier-model, embedding-model)
- `clients/default/client.env` -- Current client config variables
- `bootstrap.sh` -- Bootstrap script for model pulling and config generation

### Technology References (from CLAUDE.md)
- CrewAI >= 1.13.0 with Pydantic v2, YAML-driven config
- FastAPI >= 0.115.x with Pydantic v2
- Open WebUI Pipelines — filter/pipe plugin system
- LiteLLM >= 1.83.0 (supply chain attack on 1.82.7/1.82.8)
- Python 3.11 only (ML ecosystem compat)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docker-compose.yml` — Extend with 2 new services (core-api, pipelines), add maai-uploads volume
- `config/litellm/proxy_config.yaml` — Model aliases already defined, Core API uses same LiteLLM endpoint
- `clients/default/client.env` — Will need new vars for Core API port, Pipelines config
- `bootstrap.sh` — May need extension to validate Core API + Pipelines services

### Established Patterns
- Docker Compose profiles (gpu/cpu) — new services don't need profiles, they're hardware-agnostic
- Named volumes for persistence (ollama-models, webui-data) — follow same pattern for maai-uploads
- Health checks on all services — add health checks for core-api and pipelines
- LiteLLM as the single LLM gateway — Core API calls LiteLLM, never Ollama directly

### Integration Points
- Open WebUI -> Pipelines -> Core API -> LiteLLM -> Ollama (full message flow)
- Pipeline registered in Open WebUI via OPENAI_API_BASE_URLS or pipeline endpoint config
- Core API joins maai-net, calls LiteLLM at http://litellm:4000/v1
- Shared volume maai-uploads bridges Pipelines (write) and Core API (read) for file handling

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. All decisions followed recommended defaults.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 02-core-api-and-end-to-end-chat*
*Context gathered: 2026-04-07*
