---
phase: 01-infrastructure-foundation
plan: 01
subsystem: infra
tags: [docker, docker-compose, ollama, litellm, open-webui, pytest, yaml]

# Dependency graph
requires: []
provides:
  - Docker Compose stack definition with 4 services (ollama-gpu, ollama-cpu, litellm, open-webui)
  - GPU/CPU profiles for Ollama with NVIDIA deploy reservation
  - Named network maai-net with container DNS resolution
  - Client config folder (clients/default/) with env and models files
  - LiteLLM proxy_config.yaml routing 3 model aliases to Ollama
  - Phase 1 pytest scaffold with 19 tests covering all 6 INFRA requirements
affects:
  - 01-02 (bootstrap.sh reads client.env, models.yaml, docker-compose.yml profiles)
  - 02-agent-worker (uses maai-net and LiteLLM routing)
  - all-phases (pytest scaffold establishes test conventions)

# Tech tracking
tech-stack:
  added:
    - pytest>=7.0
    - pytest-asyncio>=0.23
    - httpx>=0.27
    - pyyaml>=6.0
    - docker compose v2 (ghcr.io/berriai/litellm:main-latest, ollama/ollama, ghcr.io/open-webui/open-webui:main)
  patterns:
    - "Docker Compose profiles: gpu/cpu to gate NVIDIA resource reservation"
    - "Client config folder pattern: clients/<name>/client.env + models.yaml"
    - "LiteLLM model aliases: downstream code uses logical names (reasoning-model), never raw Ollama tags"
    - "Wave 0 test scaffold: structural tests validate config files without running Docker"

key-files:
  created:
    - docker-compose.yml
    - .env
    - clients/default/client.env
    - clients/default/client.env.example
    - clients/default/models.yaml
    - config/litellm/proxy_config.yaml
    - pyproject.toml
    - pytest.ini
    - tests/__init__.py
    - tests/phase1/__init__.py
    - tests/phase1/conftest.py
    - tests/phase1/test_stack_startup.py
    - tests/phase1/test_local_only.py
    - tests/phase1/test_client_config.py
    - tests/phase1/test_gpu_active.py
    - tests/phase1/test_litellm_routing.py
    - tests/phase1/test_networking.py
  modified: []

key-decisions:
  - "LiteLLM image tagged as main-latest with inline comment requiring >=1.83.0 due to supply chain attack on 1.82.7/1.82.8"
  - "ollama-gpu and ollama-cpu share container_name: ollama — only one profile active at a time"
  - "Open WebUI configured with ENABLE_OLLAMA_API=false to force all traffic through LiteLLM"
  - "litellm depends_on both ollama variants with required: false so it starts regardless of which profile is active"
  - "WEBUI_SECRET_KEY placeholder CHANGE_ME_RUN_BOOTSTRAP in client.env — bootstrap.sh will replace with openssl rand value"

patterns-established:
  - "Health checks: use wget not curl (curl not installed in ollama image)"
  - "Inter-service URLs: always use container name (http://ollama:11434), never localhost"
  - "Test skip convention: pytest.skip('Requires running Docker stack') for all live tests"
  - "Structural tests: load and validate YAML/env config files without Docker running"

requirements-completed:
  - INFRA-01
  - INFRA-02
  - INFRA-03
  - INFRA-06

# Metrics
duration: 4min
completed: 2026-04-07
---

# Phase 01 Plan 01: Infrastructure Stack Definition Summary

**Docker Compose 4-service stack (ollama-gpu/cpu, litellm, open-webui) on maai-net with client config folder, LiteLLM model-alias routing, and pytest scaffold covering all 6 INFRA requirements**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-07T18:11:20Z
- **Completed:** 2026-04-07T18:14:35Z
- **Tasks:** 3 (Task 0, Task 1, Task 2)
- **Files modified:** 17

## Accomplishments

- pytest scaffold with 19 tests covering INFRA-01 through INFRA-06; 14 structural tests pass without Docker
- Docker Compose stack with GPU/CPU profiles, health checks using wget, named network maai-net, and proper service chain via depends_on + service_healthy
- Client config folder (clients/default/) with documented client.env.example, operational client.env, and models.yaml
- LiteLLM proxy_config.yaml with 3 model aliases (reasoning-model, classifier-model, embedding-model) routing to Ollama container DNS — no cloud endpoints

## Task Commits

Each task was committed atomically:

1. **Task 0: Create test scaffold** - `9531127` (test)
2. **Task 1: Create Docker Compose stack definition** - `71af8db` (feat)
3. **Task 2: Create client config files and LiteLLM proxy config** - `0a31833` (feat)

**Plan metadata:** _(committed after SUMMARY.md)_

## Files Created/Modified

- `docker-compose.yml` - Complete 4-service stack with GPU/CPU profiles, maai-net, health checks
- `.env` - Compose project env setting CLIENT_ENV_PATH for overridable client config
- `clients/default/client.env.example` - Documented template with all 7 required Phase 1 vars
- `clients/default/client.env` - Operational config with CHANGE_ME_RUN_BOOTSTRAP placeholder
- `clients/default/models.yaml` - Config-driven model list (reasoning, classifier, embedding)
- `config/litellm/proxy_config.yaml` - 3 model aliases routing to http://ollama:11434
- `pyproject.toml` - Project metadata and dev dependencies
- `pytest.ini` - Test runner config with testpaths = tests
- `tests/__init__.py`, `tests/phase1/__init__.py` - Package markers
- `tests/phase1/conftest.py` - Shared fixtures: ollama_url, litellm_url, webui_port, async_client
- `tests/phase1/test_stack_startup.py` - INFRA-01 structural + skip tests
- `tests/phase1/test_local_only.py` - INFRA-02 local-only enforcement tests
- `tests/phase1/test_client_config.py` - INFRA-03 client folder and var tests
- `tests/phase1/test_gpu_active.py` - INFRA-04 GPU/CPU profile tests
- `tests/phase1/test_litellm_routing.py` - INFRA-05 model alias and prefix tests
- `tests/phase1/test_networking.py` - INFRA-06 named network and service routing tests

## Decisions Made

- LiteLLM image tagged `main-latest` with inline security comment requiring >=1.83.0 — versions 1.82.7/1.82.8 were backdoored in March 2026 supply chain attack
- Both ollama-gpu and ollama-cpu use `container_name: ollama` — only one profile activates at a time, so LiteLLM always reaches Ollama at `http://ollama:11434` regardless of GPU/CPU selection
- Open WebUI configured with `ENABLE_OLLAMA_API=false` and `OPENAI_API_BASE_URL=http://litellm:4000/v1` — all LLM traffic routes through LiteLLM, centralizing model routing
- `litellm` depends_on both ollama variants with `required: false` — starts correctly whether GPU or CPU profile is active
- WEBUI_SECRET_KEY left as `CHANGE_ME_RUN_BOOTSTRAP` placeholder — bootstrap.sh (Plan 02) will generate and inject the real value

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

- `clients/default/client.env` contains `WEBUI_SECRET_KEY=CHANGE_ME_RUN_BOOTSTRAP` — intentional placeholder. Plan 02 (bootstrap.sh) will replace this with `openssl rand -hex 32` output on first deploy. This does not prevent Plan 01's goal (file structure establishment) but must be resolved before the stack can be safely run.

## Next Phase Readiness

- All config files exist and are correctly formed — bootstrap.sh (Plan 02) can operate on real files
- Test scaffold is ready — structural tests validate config without Docker; live tests skip with clear messages
- INFRA-04 (GPU detection) and INFRA-05/INFRA-06 live tests remain pending running Docker stack (Plan 02 work)
- No blockers for Plan 02

---
*Phase: 01-infrastructure-foundation*
*Completed: 2026-04-07*
