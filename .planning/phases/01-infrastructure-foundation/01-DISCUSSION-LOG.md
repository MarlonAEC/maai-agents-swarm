# Phase 1: Infrastructure Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 01-infrastructure-foundation
**Areas discussed:** Service topology, Model bootstrapping, Client config layout, GPU/CPU fallback

---

## Service Topology

### Q1: Which services should Phase 1 Docker Compose include?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 1 only | Ollama + LiteLLM + Open WebUI only. Other services added in later phases. | ✓ |
| Full stack with profiles | All services defined now, grouped into Compose profiles. | |
| Core + Redis | Ollama + LiteLLM + Open WebUI + Redis. Redis lightweight, needed by Phase 2. | |

**User's choice:** Phase 1 only
**Notes:** Keeps Phase 1 focused and debuggable.

### Q2: Should services use a shared Docker network or the default Compose network?

| Option | Description | Selected |
|--------|-------------|----------|
| Named network | Explicit named network (e.g., 'maai-net'). Services reference by container name. | ✓ |
| Default Compose network | Let Compose create the default network. | |

**User's choice:** Named network
**Notes:** Clearer, avoids INFRA-06 localhost pitfalls.

### Q3: How should Open WebUI connect to Ollama?

| Option | Description | Selected |
|--------|-------------|----------|
| Open WebUI -> LiteLLM -> Ollama | All LLM traffic goes through LiteLLM proxy. | ✓ |
| Open WebUI -> Ollama directly | Native Ollama integration, LiteLLM only for API consumers. | |
| Both paths available | Direct + proxy paths available simultaneously. | |

**User's choice:** Open WebUI -> LiteLLM -> Ollama
**Notes:** Centralizes model routing for INFRA-05.

### Q4: Should Open WebUI be exposed on a specific host port?

| Option | Description | Selected |
|--------|-------------|----------|
| Port 3000 | Fixed mapping to localhost:3000. | |
| Port 8080 | Fixed mapping to localhost:8080. | |
| Configurable via client.env | Default to 3000, override via WEBUI_PORT. | ✓ |

**User's choice:** Configurable via client.env
**Notes:** Handles port conflicts per client.

---

## Model Bootstrapping

### Q1: How should initial model downloads be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Bootstrap script | Separate bootstrap.sh that pulls models before stack starts. | ✓ |
| Entrypoint hook | Ollama container checks and pulls on startup. | |
| Manual pull instructions | Document commands for user to run manually. | |

**User's choice:** Bootstrap script
**Notes:** Keeps docker-compose.yml clean, user sees download progress.

### Q2: Should the bootstrap script be configurable for which models to pull?

| Option | Description | Selected |
|--------|-------------|----------|
| Config-driven | Read model list from models.yaml. Defaults overridable per client. | ✓ |
| Hardcoded defaults | Always pulls the standard set. | |

**User's choice:** Config-driven
**Notes:** Clients can override for weaker hardware (e.g., Qwen3 7B).

### Q3: Where should downloaded Ollama models be persisted?

| Option | Description | Selected |
|--------|-------------|----------|
| Named Docker volume | Persist in named volume (e.g., 'ollama-models'). | ✓ |
| Host-mounted directory | Mount host directory into container. | |

**User's choice:** Named Docker volume
**Notes:** Survives container rebuilds, managed by Docker.

---

## Client Config Layout

### Q1: How should the per-client config directory be structured?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat structure | Single directory: clients/<client-name>/ with all config files. | ✓ |
| Nested by concern | Subdirectories for config/, prompts/, data/. | |
| Root-level config | Config files at project root, no clients/ subdirectory. | |

**User's choice:** Flat structure
**Notes:** Phase 1 only uses client.env and models.yaml.

### Q2: Should Phase 1 ship a default/example client config?

| Option | Description | Selected |
|--------|-------------|----------|
| Example client included | Ship clients/default/ with working examples. | ✓ |
| Template + setup script | Ship templates and a setup.sh that generates config. | |
| Docs only | Document the structure, user creates manually. | |

**User's choice:** Example client included
**Notes:** Docker Compose references this path by default.

### Q3: What should be configurable in client.env for Phase 1?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: ports + models | WEBUI_PORT, OLLAMA_GPU_ENABLED, model names only. | ✓ |
| Forward-looking | All above plus IMAP_HOST, REDIS_URL, QDRANT_URL placeholders. | |
| You decide | Claude picks the right set. | |

**User's choice:** Minimal: ports + models
**Notes:** Just what Phase 1 services actually need.

---

## GPU/CPU Fallback

### Q1: How should the stack handle GPU detection and fallback?

| Option | Description | Selected |
|--------|-------------|----------|
| Compose profiles | Two profiles: 'gpu' (default, NVIDIA runtime) and 'cpu'. Bootstrap detects GPU. | ✓ |
| Ollama auto-detect | Single config, Ollama auto-detects GPU/CPU at runtime. | |
| Manual toggle | User sets OLLAMA_GPU_ENABLED in client.env manually. | |

**User's choice:** Compose profiles
**Notes:** OLLAMA_GPU_ENABLED in client.env as manual override.

### Q2: When running CPU-only, should bootstrap auto-switch to smaller models?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-switch | CPU profile pulls Qwen3 7B + Gemma 3 1B instead of larger models. | ✓ |
| Warn but keep config | Warn about performance, respect user's models.yaml. | |
| You decide | Claude picks the best approach. | |

**User's choice:** Auto-switch
**Notes:** LiteLLM config updated accordingly. User doesn't need to manually change models.yaml.

---

## Claude's Discretion

- LiteLLM configuration file format and model alias naming
- Docker Compose health check configuration for each service
- Exact Compose file structure and YAML organization
- Bootstrap script implementation details (bash vs Python)

## Deferred Ideas

None — discussion stayed within phase scope.
