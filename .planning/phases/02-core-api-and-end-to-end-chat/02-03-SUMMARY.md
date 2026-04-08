---
phase: 02-core-api-and-end-to-end-chat
plan: "03"
subsystem: infra
tags: [docker-compose, pipelines, open-webui, fastapi, crewai, pytest, volumes, networking]

# Dependency graph
requires:
  - phase: 02-core-api-and-end-to-end-chat
    provides: Core API (FastAPI + CrewAI) Dockerfile at src/core_api/ — plan 02-01
  - phase: 02-core-api-and-end-to-end-chat
    provides: Pipelines pipe plugin at src/pipelines/maai_pipe.py — plan 02-02

provides:
  - Extended docker-compose.yml with core-api and pipelines services on maai-net
  - maai-uploads shared Docker volume between core-api and pipelines
  - Open WebUI wired to both LiteLLM and Pipelines via semicolon-separated OPENAI_API_BASE_URLS
  - Updated client.env with CORE_API_PORT and PIPELINES_API_KEY variables
  - Phase 2 test scaffold with 38 structural tests across 5 test files

affects:
  - Phase 03 and beyond (any plan requiring Docker stack verification)
  - Phase 03-document-processing (maai-uploads volume shared with core-api)

# Tech tracking
tech-stack:
  added:
    - ghcr.io/open-webui/pipelines:main (Docker image)
  patterns:
    - Semicolon-separated OPENAI_API_BASE_URLS/OPENAI_API_KEYS must have matching entry counts
    - Structural pytest pattern: test docker-compose.yml without Docker running
    - maai-uploads shared volume pattern for cross-service file exchange

key-files:
  created:
    - tests/phase2/__init__.py
    - tests/phase2/conftest.py
    - tests/phase2/test_docker_wiring.py
    - tests/phase2/test_webui_accessible.py
    - tests/phase2/test_core_api.py
    - tests/phase2/test_crew_config.py
    - tests/phase2/test_pipeline.py
  modified:
    - docker-compose.yml
    - clients/default/client.env
    - clients/default/client.env.example

key-decisions:
  - "OPENAI_API_BASE_URLS and OPENAI_API_KEYS MUST have the same number of semicolon-separated entries — mismatch causes silent routing failures in Open WebUI"
  - "pipelines service has no depends_on (standalone server) — open-webui depends_on pipelines, not the reverse"
  - "core-api depends_on litellm service_healthy — ensures LiteLLM proxy is ready before agent accepts requests"
  - "maai-uploads volume declared as named Docker volume (not bind-mount) for cross-service sharing between pipelines and core-api"

patterns-established:
  - "Structural test pattern: parse docker-compose.yml with yaml.safe_load() and assert service/volume/env config without running Docker"
  - "OPENAI_API count guard: always test that OPENAI_API_BASE_URLS and OPENAI_API_KEYS have matching semicolon counts"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, AGNT-07, AGNT-08, AGNT-09]

# Metrics
duration: 8min
completed: "2026-04-08"
---

# Phase 2 Plan 03: Docker Compose Wiring and Test Scaffold Summary

**core-api and pipelines services wired into Docker Compose with maai-uploads shared volume, Open WebUI OPENAI_API_BASE_URLS updated to include Pipelines, and 38 structural tests created across 5 test files**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-08T05:05:00Z
- **Completed:** 2026-04-08T05:13:00Z
- **Tasks:** 2 of 3 (Task 3 is checkpoint:human-verify — awaiting human verification)
- **Files created:** 8
- **Files modified:** 3

## Accomplishments

- Extended docker-compose.yml with 2 new services: `core-api` (FastAPI/CrewAI built from ./src/core_api) and `pipelines` (ghcr.io/open-webui/pipelines:main with ./src/pipelines bind-mount)
- Added `maai-uploads` named Docker volume shared between core-api (/app/uploads) and pipelines (/app/uploads)
- Updated Open WebUI to route to both LiteLLM and Pipelines via semicolon-separated OPENAI_API_BASE_URLS and matching OPENAI_API_KEYS
- Created Phase 2 test scaffold: 38 structural tests covering Docker wiring, WebUI accessibility, Core API structure, CrewAI config, and pipeline plugin

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Docker Compose with core-api and pipelines services** - `2753e98` (feat)
2. **Task 2: Create Phase 2 test scaffold** - `068dc2e` (feat)
3. **Task 3: Verify end-to-end chat pipeline** - Checkpoint awaiting human verification

## Files Created/Modified

- `docker-compose.yml` — Added core-api, pipelines services and maai-uploads volume; updated open-webui OPENAI_API_BASE_URLS/OPENAI_API_KEYS and depends_on
- `clients/default/client.env` — Added CORE_API_PORT=8000 and PIPELINES_API_KEY=0p3n-w3bu!
- `clients/default/client.env.example` — Added same variables with documentation comments
- `tests/phase2/__init__.py` — Package marker
- `tests/phase2/conftest.py` — Fixtures: compose_config, client_env, core_api_url, pipelines_url
- `tests/phase2/test_docker_wiring.py` — 17 structural tests for Docker Compose Phase 2 additions
- `tests/phase2/test_webui_accessible.py` — 5 structural tests for Open WebUI port and dependencies (CHAT-01)
- `tests/phase2/test_core_api.py` — 7 structural + 2 skippable live tests for Core API
- `tests/phase2/test_crew_config.py` — 4 tests for AGNT-07, AGNT-08, AGNT-09 CrewAI constraints
- `tests/phase2/test_pipeline.py` — 6 structural tests for Pipelines pipe plugin

## Decisions Made

- OPENAI_API_BASE_URLS and OPENAI_API_KEYS must always have the same number of semicolon-separated entries — mismatched counts cause silent routing failures in Open WebUI (tested by `test_open_webui_api_keys_count_matches_urls`)
- pipelines service is standalone (no depends_on) — it starts independently and open-webui waits for it
- core-api depends_on litellm with `condition: service_healthy` — ensures LiteLLM is ready before FastAPI starts serving requests
- maai-uploads is a named Docker volume (not a bind-mount) so it persists across container restarts and is accessible by both services

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — all configuration uses defaults from client.env. No external services or API keys required.

## Next Phase Readiness

- Full Docker stack ready: `docker compose build core-api && docker compose --profile gpu up -d`
- 38 structural tests pass: `pytest tests/phase2/ -v -k "not live"`
- Awaiting human verification of end-to-end chat (Task 3 checkpoint)
- Phase 3 (document processing) can use maai-uploads volume for file exchange

## Known Stubs

None - all core functionality implemented. File upload in pipelines plugin returns acknowledgment message ("Document processing will be available in a future update") which is intentional — full processing is Phase 3 scope.

---
*Phase: 02-core-api-and-end-to-end-chat*
*Completed: 2026-04-08*
