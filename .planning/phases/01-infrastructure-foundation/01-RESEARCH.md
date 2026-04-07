# Phase 1: Infrastructure Foundation - Research

**Researched:** 2026-04-07
**Domain:** Docker Compose, Ollama, LiteLLM, Open WebUI — local LLM infrastructure
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 1 Docker Compose includes only three services: Ollama, LiteLLM, and Open WebUI. No other services (Redis, Qdrant, CrewAI worker, FastAPI) until their respective phases.
- **D-02:** Use an explicit named Docker network (e.g., `maai-net`). Services reference each other by container name. Addresses INFRA-06 (no localhost pitfalls).
- **D-03:** All LLM traffic routes through LiteLLM: Open WebUI -> LiteLLM -> Ollama. Open WebUI is configured with LiteLLM as its OpenAI-compatible endpoint. This centralizes model routing for INFRA-05.
- **D-04:** Open WebUI host port is configurable via `WEBUI_PORT` in client.env, defaulting to 3000.
- **D-05:** Separate bootstrap script (bootstrap.sh) pulls required models before the stack starts. Run once on first deploy, not on every container start.
- **D-06:** Model list is config-driven — read from models.yaml in the client config folder. Default set: Qwen3 14B (reasoning), Gemma 3 4B (classification), nomic-embed-text (embeddings).
- **D-07:** Downloaded models persisted in a named Docker volume (e.g., `ollama-models`). Survives container rebuilds.
- **D-08:** Flat directory structure: `clients/<client-name>/` containing client.env, models.yaml, and placeholder files for later phases. Phase 1 only uses client.env and models.yaml.
- **D-09:** Ship a `clients/default/` folder with working client.env.example and models.yaml. Docker Compose references this path by default. User copies and customizes.
- **D-10:** Phase 1 client.env contains minimal vars: WEBUI_PORT, OLLAMA_GPU_ENABLED, REASONING_MODEL, CLASSIFIER_MODEL, EMBEDDING_MODEL. No forward-looking placeholders.
- **D-11:** Two Docker Compose profiles: `gpu` (default, uses NVIDIA runtime + deploy.resources.reservations) and `cpu` (no GPU config). Bootstrap script detects GPU availability and sets the active profile. OLLAMA_GPU_ENABLED in client.env serves as manual override.
- **D-12:** When CPU profile is active, bootstrap auto-switches to smaller models: Qwen3 7B instead of 14B, Gemma 3 1B instead of 4B. LiteLLM config updated accordingly. User does not need to manually edit models.yaml for CPU-only deployments.

### Claude's Discretion

- LiteLLM configuration file format and model alias naming
- Docker Compose health check configuration for each service
- Exact Compose file structure and YAML organization
- Bootstrap script implementation details (bash vs Python)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Platform deploys via single `docker compose up` command per client | Docker Compose V2 `docker compose up` command with env_file, named network, and named volumes; bootstrap.sh run separately once. |
| INFRA-02 | All processing runs locally — no data leaves the client's machine | Ollama runs entirely local; LiteLLM config points only to local Ollama; no cloud API keys required for Phase 1. |
| INFRA-03 | Each client has isolated config folder (agents.yaml, workflows.yaml, prompts/, client.env) | `clients/<client-name>/` flat structure; env_file in Compose points to client path; COMPOSE_PROJECT_NAME env can scope volumes. |
| INFRA-04 | Ollama serves local LLMs with GPU acceleration when available | NVIDIA Container Toolkit + `deploy.resources.reservations.devices` in Compose; CPU fallback via profiles; GPU confirmed via `ollama logs` device line. |
| INFRA-05 | LiteLLM proxy routes requests to different models per task type | LiteLLM `proxy_config.yaml` model_list with named aliases (e.g., `reasoning`, `classifier`, `embedder`) pointing to `ollama_chat/` prefixed models at Ollama container URL. |
| INFRA-06 | Docker Compose networking resolves service names correctly (no localhost pitfalls) | Named network `maai-net`; services reference each other by container_name; Ollama internal URL is `http://ollama:11434`. |
</phase_requirements>

---

## Summary

Phase 1 establishes a three-service Docker Compose stack — Ollama, LiteLLM, and Open WebUI — that starts with `docker compose up` and provides a browser-accessible chat interface backed by locally-running LLMs. The deployment environment is confirmed: Docker 28.5.1 and Docker Compose v2.40.3 are present and current; an NVIDIA RTX 4090 (24GB VRAM) is available, making the GPU profile the default path.

The primary architectural risk is service startup ordering: Open WebUI must wait for LiteLLM to be ready, and LiteLLM must wait for Ollama to be serving. Docker Compose `depends_on` with `condition: service_healthy` solves this, but requires careful health check configuration — Ollama's Docker image does not include `curl`, so health checks must use `/dev/tcp` or `wget`. LiteLLM exposes dedicated `/health/readiness` and `/health/liveliness` endpoints that work well for this purpose.

A bootstrap.sh script handles the one-time model pull (via `ollama pull` inside the running container), GPU detection, and profile selection — separating first-run setup from the normal `docker compose up` path. LiteLLM's `proxy_config.yaml` uses named model aliases (e.g., `reasoning-model`, `classifier-model`) so downstream consumers always reference stable names regardless of which actual Ollama model is active on a given deployment.

**Primary recommendation:** Use Docker Compose `profiles` to gate GPU vs CPU service configuration for Ollama; use `depends_on` with `service_healthy` throughout; define LiteLLM model aliases as logical names so bootstrap.sh can write the actual model tag without affecting downstream config.

---

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md are binding on planning and implementation:

| Directive | Impact on This Phase |
|-----------|---------------------|
| `docker compose` (no hyphen) — standalone binary deprecated | All scripts and docs must use `docker compose up`, not `docker-compose up` |
| `litellm>=1.83.0` — 1.82.7/1.82.8 backdoored | Pin exact image tag or version in Compose file; do NOT use `latest` without verifying |
| Python 3.11 only — 3.12/3.13 have ML packaging issues | Not directly applicable to Phase 1 (no Python services), but noted for bootstrap.sh if Python is used |
| No paid third-party APIs — local only | LiteLLM config must NOT include any cloud model endpoints or API keys |
| Ollama Docker image: `ollama/ollama` | Use this image, not alternatives |
| Open WebUI Docker image: `ghcr.io/open-webui/open-webui` | Use this image, not alternatives |
| `nomic-embed-text` must be explicitly pulled | bootstrap.sh must include this pull step; it is not auto-pulled |
| Docker Compose V2 — Compose spec 5.0 | Use `name:` top-level key (Compose spec 3.x is EOL) |
| No `console.log()` — use logger service | Not applicable to Phase 1 (YAML/shell only) |

---

## Standard Stack

### Core Services

| Service | Docker Image | Version Pin | Purpose | Why Standard |
|---------|-------------|-------------|---------|--------------|
| Ollama | `ollama/ollama` | `0.20.x` (latest stable) | Local LLM serving | Official image; GPU/CPU auto-detection; OpenAI-compatible REST API |
| LiteLLM | `ghcr.io/berriai/litellm:main-latest` | `>=1.83.0` (REQUIRED — see supply chain note) | LLM routing proxy | Single YAML config for all model routing; OpenAI-compatible API |
| Open WebUI | `ghcr.io/open-webui/open-webui` | `0.8.x` | Chat interface | Pre-built UI with Ollama + OpenAI API support; no custom frontend needed |

### Supporting Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| Docker Compose V2 | v2.40.3 (confirmed installed) | Stack orchestration |
| Named Docker volume `ollama-models` | — | Persists downloaded LLM weights across rebuilds |
| Named Docker network `maai-net` | — | Service-name DNS resolution between containers |
| NVIDIA Container Toolkit | Host-installed | GPU passthrough to Ollama container |

### LLM Models (Default Deployment — GPU Profile)

| Model | Ollama Tag | Alias in LiteLLM | Purpose |
|-------|-----------|-----------------|---------|
| Qwen3 14B | `qwen3:14b` | `reasoning-model` | Agent reasoning, task planning |
| Gemma 3 4B | `gemma3:4b` | `classifier-model` | File classification, fast tagging |
| nomic-embed-text | `nomic-embed-text` | `embedding-model` | Text embeddings for RAG (Phase 4) |

### LLM Models (CPU Profile Overrides)

| Model | Ollama Tag | Notes |
|-------|-----------|-------|
| Qwen3 7B | `qwen3:7b` | Replaces 14B when CPU-only detected |
| Gemma 3 1B | `gemma3:1b` | Replaces 4B when CPU-only detected |

---

## Architecture Patterns

### Recommended Project Structure

```
.
├── docker-compose.yml          # Main Compose file (all three services)
├── docker-compose.cpu.yml      # CPU profile override (Ollama without GPU config)
├── clients/
│   └── default/
│       ├── client.env          # Runtime config (generated by bootstrap from client.env.example)
│       ├── client.env.example  # Template with documented defaults
│       └── models.yaml         # Model list for bootstrap to pull
├── config/
│   └── litellm/
│       └── proxy_config.yaml   # LiteLLM model routing config (written by bootstrap)
└── bootstrap.sh                # First-run: GPU detect, model pull, config generate
```

### Pattern 1: Docker Compose Named Network

**What:** All services declare `networks: [maai-net]`; the top-level `networks:` block creates it as a bridge network. Services reference each other by their `container_name` value.

**When to use:** Required — this is D-02 (INFRA-06 compliance). Never use `host` networking or `localhost` references across containers.

```yaml
# Source: Docker Compose official docs + D-02 decision
networks:
  maai-net:
    driver: bridge

services:
  ollama:
    container_name: ollama
    networks: [maai-net]

  litellm:
    container_name: litellm
    networks: [maai-net]
    # Ollama is reachable at http://ollama:11434

  open-webui:
    container_name: open-webui
    networks: [maai-net]
    # LiteLLM is reachable at http://litellm:4000
```

### Pattern 2: GPU / CPU Compose Profiles

**What:** Docker Compose `profiles` assign services to named activation groups. The Ollama service is defined twice: a `gpu` variant with NVIDIA deploy config, and a `cpu` variant without it. Only one runs at a time.

**When to use:** D-11 requires this. The bootstrap script selects the active profile by checking `nvidia-smi`.

**Approach — Two service definitions with profiles:**

```yaml
# Source: Docker Compose profiles docs + D-11 decision
services:
  ollama-gpu:
    container_name: ollama
    image: ollama/ollama
    profiles: [gpu]
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    networks: [maai-net]
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags > /dev/null 2>&1 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped

  ollama-cpu:
    container_name: ollama
    image: ollama/ollama
    profiles: [cpu]
    volumes:
      - ollama-models:/root/.ollama
    networks: [maai-net]
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags > /dev/null 2>&1 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
```

**Bootstrap profile selection:**
```bash
# Source: Bash best practice for nvidia-smi check
if nvidia-smi &>/dev/null && [ "$(cat clients/default/client.env | grep OLLAMA_GPU_ENABLED | cut -d= -f2)" != "false" ]; then
    COMPOSE_PROFILE="gpu"
else
    COMPOSE_PROFILE="cpu"
fi
docker compose --profile "$COMPOSE_PROFILE" up -d
```

### Pattern 3: LiteLLM Model Alias Routing

**What:** `proxy_config.yaml` defines `model_name` as a logical alias (e.g., `reasoning-model`) that maps to a specific Ollama model. Open WebUI and future consumers always request the alias — bootstrap.sh controls which actual model each alias points to.

**When to use:** Required for INFRA-05 (model routing per task type) and D-12 (CPU auto-switch).

```yaml
# Source: docs.litellm.ai/docs/providers/ollama + docs.litellm.ai/docs/proxy/configs
model_list:
  - model_name: reasoning-model
    litellm_params:
      model: ollama_chat/qwen3:14b
      api_base: http://ollama:11434
      api_key: none

  - model_name: classifier-model
    litellm_params:
      model: ollama_chat/gemma3:4b
      api_base: http://ollama:11434
      api_key: none

  - model_name: embedding-model
    litellm_params:
      model: ollama/nomic-embed-text
      api_base: http://ollama:11434
      api_key: none

general_settings:
  master_key: ${LITELLM_MASTER_KEY}

litellm_settings:
  drop_params: true
```

**Note on model prefix:**
- Use `ollama_chat/` prefix for chat models — routes to Ollama's `/api/chat` endpoint (recommended over `/api/generate`)
- Use `ollama/` prefix for embedding models — routes to `/api/embeddings`

### Pattern 4: Open WebUI Pointed at LiteLLM

**What:** Open WebUI's OpenAI-compatible API connection is pointed at LiteLLM, not directly at Ollama. This is D-03.

```yaml
# Source: docs.openwebui.com/reference/env-configuration + community examples
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    environment:
      - ENABLE_OLLAMA_API=false       # Disable direct Ollama connection
      - ENABLE_OPENAI_API=true
      - OPENAI_API_BASE_URL=http://litellm:4000/v1
      - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - WEBUI_AUTH=true
    ports:
      - "${WEBUI_PORT:-3000}:8080"
    volumes:
      - webui-data:/app/backend/data
    depends_on:
      litellm:
        condition: service_healthy
    networks: [maai-net]
    restart: unless-stopped
```

**Critical:** Set `WEBUI_SECRET_KEY` to a stable generated value. If unset, it randomizes on each restart, invalidating all sessions and breaking tool tokens.

### Pattern 5: Health Checks and depends_on Chain

**What:** Compose `depends_on` with `condition: service_healthy` ensures services start in the correct order: Ollama → LiteLLM → Open WebUI.

**Ollama health check — IMPORTANT PITFALL:** The `ollama/ollama` image does NOT include `curl`. Use `wget` instead (available in the base image), or use `/dev/tcp` shell redirection.

```yaml
# Ollama health check (wget-based, since curl is absent)
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags > /dev/null 2>&1 || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s   # Ollama takes 30-60s to initialize GPU context

# LiteLLM health check (uses /health/liveliness — no auth required)
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:4000/health/liveliness > /dev/null 2>&1 || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 40s

# Open WebUI depends_on chain
depends_on:
  litellm:
    condition: service_healthy
# Note: Open WebUI itself has a built-in healthcheck in its Dockerfile
```

### Pattern 6: Bootstrap Script Logic

**What:** bootstrap.sh is the first-run setup script. It handles: GPU detection, profile selection, config file generation, and model pulling via `ollama pull` inside the running container.

**Sequence:**
1. Source `clients/<CLIENT>/client.env`
2. Detect GPU: `nvidia-smi &>/dev/null`; compare with `OLLAMA_GPU_ENABLED` override
3. If CPU: rewrite `proxy_config.yaml` with smaller model tags (D-12)
4. Start only the Ollama service: `docker compose --profile $PROFILE up -d ollama`
5. Wait for Ollama to be ready: poll `http://localhost:11434/api/tags`
6. Pull each model from `models.yaml`: `docker exec ollama ollama pull <model>`
7. Stop Ollama: `docker compose stop ollama`
8. Full stack start: `docker compose --profile $PROFILE up -d`

**Why stop-and-restart Ollama:** Starting the full stack with `up -d` before models are pulled means LiteLLM's health check against `/health/readiness` may succeed before models are available, causing Open WebUI to show models that fail on first inference.

### Anti-Patterns to Avoid

- **Referencing `localhost` for inter-container communication:** `localhost` inside a container refers to that container, not the host or another service. Use container names via the named network (`http://ollama:11434`).
- **Using `docker-compose` (standalone binary):** Deprecated. Use `docker compose` (V2 plugin).
- **Pinning `litellm:latest` without version verification:** Versions 1.82.7/1.82.8 were backdoored. Always verify the image tag resolves to `>=1.83.0`.
- **Omitting `WEBUI_SECRET_KEY`:** Causes sessions to invalidate on every container restart. Generate once with `openssl rand -hex 32` and persist in client.env.
- **Using `curl` in Ollama health checks:** The `ollama/ollama` Docker image does not include `curl`. Health checks fail silently. Use `wget` instead.
- **Pulling models on every `docker compose up`:** Models are stored in the named volume and survive rebuilds. Re-pulling wastes bandwidth and blocks startup. Bootstrap.sh runs once; subsequent starts skip the pull.
- **Setting `ENABLE_OLLAMA_API=true` in Open WebUI alongside LiteLLM:** This creates two LLM backends visible to users. Disable the direct Ollama connection; keep only the OpenAI (LiteLLM) connection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM request routing to multiple models | Custom proxy/router | LiteLLM `proxy_config.yaml` model_list | LiteLLM handles auth, fallback chains, rate limiting, model aliasing out of the box |
| Chat interface | Custom React/Vue frontend | Open WebUI | Months of work; Open WebUI has file upload, conversation history, tool calling already |
| Model format compatibility (OpenAI ↔ Ollama) | Custom adapter layer | LiteLLM `ollama_chat/` prefix | LiteLLM translates OpenAI chat format to Ollama's `/api/chat` natively |
| GPU passthrough in containers | Custom CUDA/driver config | NVIDIA Container Toolkit + Compose `deploy.resources.reservations` | Toolkit handles all driver exposure; Compose YAML is the complete config |
| Service startup ordering | Sleep-based delays or custom polling | `depends_on: condition: service_healthy` | Native Compose feature; eliminates race conditions without fragile `sleep` calls |

---

## Common Pitfalls

### Pitfall 1: `curl` Absent from Ollama Docker Image

**What goes wrong:** Docker Compose health checks using `curl -f http://localhost:11434/api/tags` fail immediately with "command not found", marking the container perpetually unhealthy. Services depending on Ollama health never start.

**Why it happens:** The `ollama/ollama` image is built on a minimal base without standard utilities. This is a known open issue (GitHub #9781, reported March 2025; may still be unresolved in 0.20.x).

**How to avoid:** Use `wget -qO-` in health check commands instead of `curl`. Alternatively, use the `/dev/tcp` bash trick: `bash -c 'echo > /dev/tcp/localhost/11434'`.

**Warning signs:** Container status shows `unhealthy` immediately; `docker inspect ollama` health log shows "wget: not found" or "curl: not found".

### Pitfall 2: LiteLLM Image Version and Supply Chain

**What goes wrong:** Using an older pinned tag or `latest` without checking resolves to a backdoored version. The 1.82.7 and 1.82.8 releases were compromised via a TeamPCP/Trivy CI/CD attack in March 2026.

**Why it happens:** Docker image caches may serve yanked versions. `latest` tags are mutable.

**How to avoid:** Pin to a specific image tag that maps to `>=1.83.0`. Verify with `docker run --rm ghcr.io/berriai/litellm:main-latest litellm --version`. Document the verified version in a comment in `docker-compose.yml`.

**Warning signs:** Unexpected outbound network calls from the LiteLLM container; abnormal process behavior.

### Pitfall 3: Ollama Slow Cold Start with GPU

**What goes wrong:** Ollama takes 30-90 seconds to initialize when loading a large model into VRAM on first start. Health checks with short `start_period` mark it unhealthy, blocking LiteLLM and Open WebUI from starting.

**Why it happens:** GPU context initialization and CUDA library loading are slow on first container start. The health check endpoint (`/api/tags`) only becomes responsive once the HTTP server is ready.

**How to avoid:** Set `start_period: 60s` on the Ollama health check. This delays the first health check evaluation without counting initial failures. Increase to `90s` on slower hardware or with larger models.

**Warning signs:** Stack starts slowly; LiteLLM container cycles between starting and unhealthy.

### Pitfall 4: Open WebUI Session Invalidation

**What goes wrong:** Users are logged out on every `docker compose restart` or rebuild. Tool tokens become invalid with "Error decrypting tokens" errors.

**Why it happens:** `WEBUI_SECRET_KEY` defaults to a randomly-generated value when not set. It changes on each container start, invalidating all JWT tokens issued under the previous key.

**How to avoid:** Generate once (`openssl rand -hex 32`) and set in `client.env`. Mount the same secret on every start.

**Warning signs:** Users repeatedly logged out; tool connection errors after container restart.

### Pitfall 5: LiteLLM proxy_config.yaml Not Present at Startup

**What goes wrong:** Docker Compose mounts `./config/litellm/proxy_config.yaml:/app/config.yaml`. If the file doesn't exist at mount time, Docker creates it as a directory (`proxy_config.yaml/`) instead of a file. LiteLLM fails to start with a confusing error.

**Why it happens:** Docker volume bind mounts create missing paths as directories by default.

**How to avoid:** Ensure bootstrap.sh generates `proxy_config.yaml` before `docker compose up` is called. Alternatively, ship a default `proxy_config.yaml` in the repository (not generated — just committed).

**Warning signs:** LiteLLM container exits immediately; error mentions "IsADirectoryError" or config parsing failure.

### Pitfall 6: Both Ollama API and OpenAI API Enabled in Open WebUI

**What goes wrong:** Open WebUI shows duplicate model lists — one from direct Ollama connection, one from LiteLLM. Users see confusing duplicate entries; some models bypass LiteLLM routing.

**Why it happens:** `ENABLE_OLLAMA_API` defaults to `true` in Open WebUI. When LiteLLM is also configured as an OpenAI endpoint, both backends are active.

**How to avoid:** Set `ENABLE_OLLAMA_API=false` in Open WebUI environment. All traffic flows through LiteLLM (D-03).

---

## Code Examples

### Complete docker-compose.yml Skeleton

```yaml
# Source: Docker Compose V2 spec + official images + D-01 through D-12
name: maai-platform

networks:
  maai-net:
    driver: bridge

volumes:
  ollama-models:
  webui-data:

services:
  # ── GPU variant (active when --profile gpu) ──────────────────────────────
  ollama-gpu:
    container_name: ollama
    image: ollama/ollama
    profiles: [gpu]
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags > /dev/null 2>&1 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks: [maai-net]
    restart: unless-stopped

  # ── CPU variant (active when --profile cpu) ───────────────────────────────
  ollama-cpu:
    container_name: ollama
    image: ollama/ollama
    profiles: [cpu]
    volumes:
      - ollama-models:/root/.ollama
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags > /dev/null 2>&1 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks: [maai-net]
    restart: unless-stopped

  # ── LiteLLM proxy ─────────────────────────────────────────────────────────
  litellm:
    container_name: litellm
    image: ghcr.io/berriai/litellm:main-latest  # MUST resolve to >=1.83.0
    command: ["--config", "/app/config.yaml"]
    volumes:
      - ./config/litellm/proxy_config.yaml:/app/config.yaml:ro
    env_file:
      - ${CLIENT_ENV_PATH:-clients/default/client.env}
    ports:
      - "4000:4000"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:4000/health/liveliness > /dev/null 2>&1 || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 40s
    depends_on:
      ollama-gpu:
        condition: service_healthy
        required: false
      ollama-cpu:
        condition: service_healthy
        required: false
    networks: [maai-net]
    restart: unless-stopped

  # ── Open WebUI ─────────────────────────────────────────────────────────────
  open-webui:
    container_name: open-webui
    image: ghcr.io/open-webui/open-webui:main
    environment:
      - ENABLE_OLLAMA_API=false
      - ENABLE_OPENAI_API=true
      - OPENAI_API_BASE_URL=http://litellm:4000/v1
      - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - WEBUI_AUTH=true
      - PORT=8080
    env_file:
      - ${CLIENT_ENV_PATH:-clients/default/client.env}
    ports:
      - "${WEBUI_PORT:-3000}:8080"
    volumes:
      - webui-data:/app/backend/data
    depends_on:
      litellm:
        condition: service_healthy
    networks: [maai-net]
    restart: unless-stopped
```

**Note on `depends_on` with profiles:** When using profiles, `depends_on` with `required: false` is needed because the non-active Ollama service does not exist. The LiteLLM service depends on whichever Ollama variant is active.

### client.env (Phase 1 Minimal)

```bash
# Source: D-10 decision

# Open WebUI
WEBUI_PORT=3000
WEBUI_SECRET_KEY=             # REQUIRED: generate with: openssl rand -hex 32

# LiteLLM
LITELLM_MASTER_KEY=sk-maai-local   # Used by Open WebUI to authenticate to LiteLLM

# GPU control (auto-detected by bootstrap.sh; override here if needed)
OLLAMA_GPU_ENABLED=true       # Set to false to force CPU profile

# Model selection (bootstrap.sh reads these; do not change after first pull)
REASONING_MODEL=qwen3:14b
CLASSIFIER_MODEL=gemma3:4b
EMBEDDING_MODEL=nomic-embed-text
```

### models.yaml (Phase 1 Default)

```yaml
# Source: D-06, D-12 decisions + CLAUDE.md model recommendations
models:
  reasoning: qwen3:14b        # Overridden to qwen3:7b by bootstrap on CPU
  classifier: gemma3:4b       # Overridden to gemma3:1b by bootstrap on CPU
  embedding: nomic-embed-text  # Same on both profiles
```

### proxy_config.yaml (GPU Profile — Generated by bootstrap.sh)

```yaml
# Source: docs.litellm.ai/docs/providers/ollama + docs.litellm.ai/docs/proxy/configs
model_list:
  - model_name: reasoning-model
    litellm_params:
      model: ollama_chat/qwen3:14b
      api_base: http://ollama:11434
      api_key: none

  - model_name: classifier-model
    litellm_params:
      model: ollama_chat/gemma3:4b
      api_base: http://ollama:11434
      api_key: none

  - model_name: embedding-model
    litellm_params:
      model: ollama/nomic-embed-text
      api_base: http://ollama:11434
      api_key: none

general_settings:
  master_key: sk-maai-local

litellm_settings:
  drop_params: true
```

### bootstrap.sh Core Logic

```bash
#!/usr/bin/env bash
# Source: D-05, D-11, D-12 decisions

set -euo pipefail

CLIENT="${1:-default}"
ENV_FILE="clients/${CLIENT}/client.env"
MODELS_FILE="clients/${CLIENT}/models.yaml"
PROXY_CONFIG="config/litellm/proxy_config.yaml"

# Source client config
set -a; source "$ENV_FILE"; set +a

# GPU detection with manual override
detect_profile() {
    if [ "${OLLAMA_GPU_ENABLED:-true}" = "false" ]; then
        echo "cpu"
    elif nvidia-smi &>/dev/null; then
        echo "gpu"
    else
        echo "cpu"
    fi
}

PROFILE=$(detect_profile)
echo "Using profile: $PROFILE"

# On CPU profile, downgrade models
if [ "$PROFILE" = "cpu" ]; then
    REASONING_MODEL="qwen3:7b"
    CLASSIFIER_MODEL="gemma3:1b"
fi

# Generate proxy_config.yaml
mkdir -p "$(dirname $PROXY_CONFIG)"
cat > "$PROXY_CONFIG" << EOF
model_list:
  - model_name: reasoning-model
    litellm_params:
      model: ollama_chat/${REASONING_MODEL}
      api_base: http://ollama:11434
      api_key: none
  - model_name: classifier-model
    litellm_params:
      model: ollama_chat/${CLASSIFIER_MODEL}
      api_base: http://ollama:11434
      api_key: none
  - model_name: embedding-model
    litellm_params:
      model: ollama/${EMBEDDING_MODEL}
      api_base: http://ollama:11434
      api_key: none
general_settings:
  master_key: ${LITELLM_MASTER_KEY}
litellm_settings:
  drop_params: true
EOF

# Start Ollama only, wait for ready
docker compose --profile "$PROFILE" up -d ollama-gpu ollama-cpu 2>/dev/null || true
echo "Waiting for Ollama to be ready..."
until wget -qO- http://localhost:11434/api/tags &>/dev/null; do
    sleep 2
done
echo "Ollama ready"

# Pull models
for MODEL in "$REASONING_MODEL" "$CLASSIFIER_MODEL" "$EMBEDDING_MODEL"; do
    echo "Pulling $MODEL..."
    docker exec ollama ollama pull "$MODEL"
done

# Start full stack
docker compose --profile "$PROFILE" up -d
echo "Stack started. Open WebUI: http://localhost:${WEBUI_PORT:-3000}"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose` standalone binary | `docker compose` V2 plugin | 2022 (deprecated), EOL 2024 | Scripts must use new syntax; standalone binary not guaranteed installed |
| Ollama `ollama/` prefix for chat | `ollama_chat/` prefix for chat | LiteLLM ~1.70.x | Use `ollama_chat/` for chat completions to hit `/api/chat`; `ollama/` routes to `/api/generate` |
| LiteLLM 1.82.x | LiteLLM >=1.83.0 | March 24, 2026 | Supply chain attack; 1.82.7/1.82.8 backdoored and yanked |
| Compose `version: "3.x"` top-level key | `name:` top-level key (Compose spec) | Compose spec 3.x deprecated | Use `name:` instead of `version:` in Compose files |

**Deprecated/outdated:**
- `version: "3.8"` in docker-compose.yml: The `version` key is obsolete in Compose spec V2. Use `name:` instead. Docker Compose V2 ignores it but prints a warning.
- `OPENAI_API_BASE` (singular, old): Use `OPENAI_API_BASE_URL` in Open WebUI environment variables.

---

## Open Questions

1. **LiteLLM `depends_on` with mutual-exclusive profiles**
   - What we know: Docker Compose `depends_on` with `required: false` skips the dependency if the service doesn't exist. This should handle the gpu/cpu mutual-exclusion.
   - What's unclear: Whether `required: false` is supported in all Docker Compose V2 versions, or only recent ones. Compose v2.40.3 (confirmed installed) should support it.
   - Recommendation: Planner should include a task to verify `required: false` behavior in Compose v2.40.3 before relying on it. Fallback: Use a single Ollama service with conditional environment variables instead of profiles.

2. **LiteLLM image tag that guarantees >=1.83.0**
   - What we know: `ghcr.io/berriai/litellm:main-latest` is the standard tag, but `latest` is mutable and may not always reflect a specific version.
   - What's unclear: Whether to pin to a specific SHA digest or a version-tagged release like `ghcr.io/berriai/litellm:main-v1.83.x`.
   - Recommendation: Planner should include a verification task that runs `docker run --rm ghcr.io/berriai/litellm:main-latest litellm --version` and asserts `>=1.83.0`. Add this to bootstrap.sh as a pre-flight check.

3. **Open WebUI `depends_on` for profiles (gpu vs cpu Ollama variants)**
   - What we know: Open WebUI depends on LiteLLM (not directly on Ollama), so the profile complexity is isolated to LiteLLM's `depends_on`.
   - What's unclear: LiteLLM's `depends_on` with two `required: false` entries (one per Ollama profile) — whether Compose correctly waits for whichever one actually starts.
   - Recommendation: Test this specifically. If behavior is unreliable, simplify by having bootstrap.sh start the stack in two phases (Ollama first, then `docker compose up` for the rest).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All services | Yes | 28.5.1 | — |
| Docker Compose V2 | Stack orchestration | Yes | v2.40.3-desktop.1 | — |
| NVIDIA GPU | GPU profile | Yes | RTX 4090, 24GB VRAM | CPU profile (auto-detected) |
| nvidia-smi | bootstrap.sh GPU detection | Yes (implied by GPU) | — | Assume CPU if absent |
| bash | bootstrap.sh | Yes | 5.2.37 | — |
| wget | Health checks inside containers | Assumed present in Ollama/LiteLLM base images | — | /dev/tcp fallback |
| openssl | WEBUI_SECRET_KEY generation | Available on host | — | Any hex generator |
| Python 3.11 | Not needed for Phase 1 | Available (3.14.3 on host — Phase 1 is shell/YAML only) | 3.14.3 | N/A |

**Note on Python version:** Host Python is 3.14.3 but CLAUDE.md mandates 3.11 for project services. Phase 1 has no Python services — this is only relevant from Phase 2 onward. Bootstrap.sh is pure bash.

**Missing dependencies with no fallback:** None identified for Phase 1.

**Missing dependencies with fallback:** None identified (GPU has CPU fallback by design).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (per CLAUDE.md stack) |
| Config file | `pytest.ini` — Wave 0 gap (doesn't exist yet) |
| Quick run command | `pytest tests/phase1/ -x -q` |
| Full suite command | `pytest tests/phase1/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INFRA-01 | `docker compose up` starts all three services | smoke | `pytest tests/phase1/test_stack_startup.py -x` | No — Wave 0 |
| INFRA-02 | No outbound traffic to external APIs during inference | smoke/manual | `pytest tests/phase1/test_local_only.py -x` (network intercept) | No — Wave 0 |
| INFRA-03 | client.env changes are reflected after restart | integration | `pytest tests/phase1/test_client_config.py -x` | No — Wave 0 |
| INFRA-04 | Ollama logs show GPU device on gpu profile | smoke | `pytest tests/phase1/test_gpu_active.py -x` | No — Wave 0 |
| INFRA-05 | LiteLLM routes `reasoning-model` to Qwen3 and `classifier-model` to Gemma3 | integration | `pytest tests/phase1/test_litellm_routing.py -x` | No — Wave 0 |
| INFRA-06 | Services resolve each other by container name | unit/integration | `pytest tests/phase1/test_networking.py -x` | No — Wave 0 |

**Note on test approach:** Phase 1 tests are integration/smoke tests against a running stack — not unit tests. They require Docker and the stack to be up. pytest with `httpx` or `requests` can query live endpoints. `pytest-asyncio` not needed for Phase 1 (sync HTTP calls sufficient).

### Sampling Rate

- **Per task commit:** `pytest tests/phase1/ -x -q --co` (collect-only, verify test structure exists)
- **Per wave merge:** `pytest tests/phase1/ -v` (requires running stack)
- **Phase gate:** Full suite green (all 6 INFRA requirements verified against live stack) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/phase1/__init__.py` — package marker
- [ ] `tests/phase1/test_stack_startup.py` — covers INFRA-01
- [ ] `tests/phase1/test_local_only.py` — covers INFRA-02
- [ ] `tests/phase1/test_client_config.py` — covers INFRA-03
- [ ] `tests/phase1/test_gpu_active.py` — covers INFRA-04
- [ ] `tests/phase1/test_litellm_routing.py` — covers INFRA-05
- [ ] `tests/phase1/test_networking.py` — covers INFRA-06
- [ ] `tests/conftest.py` — shared fixtures (stack health wait, httpx client)
- [ ] `pytest.ini` — test runner config
- [ ] Framework install: `uv pip install pytest httpx pytest-asyncio` (for future phases)

---

## Sources

### Primary (HIGH confidence)
- [docs.litellm.ai/docs/providers/ollama](https://docs.litellm.ai/docs/providers/ollama) — Ollama model prefix (`ollama_chat/` vs `ollama/`), api_base, keep_alive
- [docs.litellm.ai/docs/proxy/configs](https://docs.litellm.ai/docs/proxy/configs) — proxy_config.yaml structure, model_list, general_settings, master_key
- [docs.litellm.ai/docs/proxy/health](https://docs.litellm.ai/docs/proxy/health) — `/health/readiness`, `/health/liveliness` endpoints
- [docs.litellm.ai/docs/proxy/docker_quick_start](https://docs.litellm.ai/docs/proxy/docker_quick_start) — Docker image name, volume mount, startup command
- [docs.openwebui.com/reference/env-configuration/](https://docs.openwebui.com/reference/env-configuration/) — WEBUI_SECRET_KEY, OPENAI_API_BASE_URL, ENABLE_OLLAMA_API, PORT
- [docs.docker.com/compose/how-tos/gpu-support/](https://docs.docker.com/compose/how-tos/gpu-support/) — `deploy.resources.reservations.devices` YAML syntax
- [docs.docker.com/compose/how-tos/profiles/](https://docs.docker.com/compose/how-tos/profiles/) — Docker Compose profiles feature
- CLAUDE.md — Technology stack, image names, version requirements, model recommendations

### Secondary (MEDIUM confidence)
- [github.com/ollama/ollama/issues/9781](https://github.com/ollama/ollama/issues/9781) — curl absence in Ollama Docker image (reported March 2025, status unconfirmed in 0.20.x)
- [dev.to/rosgluk/ollama-in-docker-compose-with-gpu-and-persistent-model-storage-224h](https://dev.to/rosgluk/ollama-in-docker-compose-with-gpu-and-persistent-model-storage-224h) — Ollama GPU Compose pattern
- [github.com/open-webui/open-webui/discussions/5908](https://github.com/open-webui/open-webui/discussions/5908) — Open WebUI unhealthy status discussion

### Tertiary (LOW confidence)
- [dt.in.th/OpenWebUILiteLLM](https://dt.in.th/OpenWebUILiteLLM) — Composite Open WebUI + LiteLLM Docker Compose example (community blog, unverified against latest versions)
- Community examples for `depends_on` with `required: false` and profiles — behavior should be verified against Compose v2.40.3

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — images and versions confirmed from official docs and CLAUDE.md
- Architecture patterns: HIGH — Compose syntax from official Docker docs; LiteLLM config from official LiteLLM docs; Open WebUI env vars from official Open WebUI docs
- Pitfalls: HIGH (curl absence, WEBUI_SECRET_KEY) / MEDIUM (depends_on + profiles interaction) — curl issue confirmed via GitHub; WEBUI_SECRET_KEY from official docs; profile + depends_on interaction is inferred from Compose docs but needs runtime verification
- Validation architecture: MEDIUM — test structure is standard; specific test commands assume `pytest` + `httpx` which are reasonable but not yet installed

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable stack; LiteLLM and Open WebUI release frequently but core config patterns are stable)
