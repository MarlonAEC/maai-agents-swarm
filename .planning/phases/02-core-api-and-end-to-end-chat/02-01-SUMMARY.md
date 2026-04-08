---
phase: 02-core-api-and-end-to-end-chat
plan: "01"
subsystem: api
tags: [fastapi, crewai, litellm, ollama, python, uvicorn, pydantic, docker]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: Docker Compose stack with LiteLLM proxy at http://litellm:4000/v1 and Ollama at http://ollama:11434

provides:
  - FastAPI Core API service with /health and POST /chat endpoints
  - CrewAI FreeformCrew wired to LiteLLM openai/reasoning-model alias
  - Centralised logging via logging_config.get_logger()
  - Dockerfile for Core API container (python:3.11-slim, uv, uvicorn)

affects:
  - 02-02 (Pipelines plugin that calls POST /chat)
  - 02-03 (Docker Compose wiring for core-api service)

# Tech tracking
tech-stack:
  added:
    - fastapi>=0.115.0
    - uvicorn[standard]
    - crewai>=1.13.0
    - python-dotenv>=1.0
    - pyyaml>=6.0
    - python-multipart
    - httpx>=0.27.0
    - pydantic>=2.0
  patterns:
    - CrewBase decorator pattern for YAML-driven crews
    - Thread-pool executor for blocking CrewAI calls in async FastAPI handlers
    - Centralised get_logger() factory (logging_config.py)
    - LLM instantiated per-crew via _llm() method

key-files:
  created:
    - src/core_api/main.py
    - src/core_api/logging_config.py
    - src/core_api/routers/chat.py
    - src/core_api/agents/freeform_crew.py
    - src/core_api/agents/config/agents.yaml
    - src/core_api/agents/config/tasks.yaml
    - src/core_api/pyproject.toml
    - src/core_api/Dockerfile
    - src/core_api/routers/__init__.py
    - src/core_api/agents/__init__.py
  modified: []

key-decisions:
  - "Agent uses openai/reasoning-model alias via LiteLLM (not direct Ollama) for LLM inference — consistent with D-07"
  - "Embedder uses direct Ollama at http://ollama:11434/api/embeddings — CrewAI ollama provider does not support LiteLLM proxy (D-10 / AGNT-07)"
  - "stream=False on LLM — required by AGNT-08; CrewAI does not support streaming agent responses"
  - "max_iter=5 and max_execution_time=60 guardrails on Agent — prevents runaway inference loops (AGNT-09)"
  - "run_in_executor wraps blocking CrewAI kickoff — keeps FastAPI event loop unblocked (D-11)"
  - "python:3.11-slim base image and uv for dependency installation — matches CLAUDE.md constraints"

patterns-established:
  - "Logging pattern: all modules use get_logger(__name__) from logging_config — never print/console.log"
  - "Crew pattern: @CrewBase class with _llm() factory method, @agent/@task/@crew decorators, YAML configs"
  - "Async pattern: blocking CPU/LLM work runs in thread-pool via asyncio.get_event_loop().run_in_executor"

requirements-completed: [CHAT-04, CHAT-05, CHAT-06, AGNT-07, AGNT-08, AGNT-09]

# Metrics
duration: 2min
completed: "2026-04-08"
---

# Phase 2 Plan 01: Core API — FastAPI + CrewAI Freeform Chat Summary

**FastAPI Core API with POST /chat wired to a CrewAI freeform agent using openai/reasoning-model via LiteLLM proxy, Ollama embedder, and stream=False + guardrail constraints**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T04:41:07Z
- **Completed:** 2026-04-08T04:43:05Z
- **Tasks:** 2
- **Files created:** 10

## Accomplishments

- FastAPI app with /health liveness probe and POST /chat endpoint backed by CrewAI
- FreeformCrew using YAML agent/task configs, openai/reasoning-model alias via LiteLLM, guardrails (stream=False, max_iter=5, max_execution_time=60)
- Dockerfile using python:3.11-slim, uv for fast installation, Python urllib health check

## Task Commits

Each task was committed atomically:

1. **Task 1: Core API scaffold with FastAPI app and CrewAI freeform agent** - `a9a87db` (feat)
2. **Task 2: Core API Dockerfile** - `906fc56` (feat)

## Files Created/Modified

- `src/core_api/main.py` - FastAPI app entrypoint with /health and chat router registration
- `src/core_api/logging_config.py` - Centralised get_logger() factory with LOG_LEVEL env control
- `src/core_api/routers/chat.py` - POST /chat endpoint (ChatRequest/ChatResponse), thread-pool executor
- `src/core_api/agents/freeform_crew.py` - CrewBase FreeformCrew wired to LiteLLM + Ollama embedder
- `src/core_api/agents/config/agents.yaml` - freeform_agent role/goal/backstory
- `src/core_api/agents/config/tasks.yaml` - freeform_task with {messages} and {user_message} inputs
- `src/core_api/pyproject.toml` - Project metadata and pinned dependencies
- `src/core_api/Dockerfile` - python:3.11-slim, uv install, uvicorn CMD, HEALTHCHECK
- `src/core_api/routers/__init__.py` - Package init
- `src/core_api/agents/__init__.py` - Package init

## Decisions Made

- openai/reasoning-model LiteLLM alias used (not direct Ollama) — decouples Core API from model tags
- Ollama embedder points directly to http://ollama:11434/api/embeddings — CrewAI's ollama provider cannot route through LiteLLM proxy
- stream=False mandated by AGNT-08 — CrewAI sequential crews do not stream
- max_iter=5 + max_execution_time=60 prevent runaway inference on local hardware
- asyncio.run_in_executor wraps blocking kickoff() to keep FastAPI event loop responsive

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. All networking uses Docker service names (litellm, ollama) that are wired in Docker Compose (Plan 03).

## Next Phase Readiness

- Core API package at src/core_api/ is complete and ready to be wired into Docker Compose in Plan 03
- POST /chat endpoint accepts `{ messages: [...], user_message: "..." }` and returns `{ response: "..." }`
- Dockerfile ready for `docker compose build core-api`
- Plan 02 (Pipelines plugin) can now target http://core-api:8000/chat as the backend

---
*Phase: 02-core-api-and-end-to-end-chat*
*Completed: 2026-04-08*
