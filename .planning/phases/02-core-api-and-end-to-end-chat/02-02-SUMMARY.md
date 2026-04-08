---
phase: 02-core-api-and-end-to-end-chat
plan: "02"
subsystem: pipelines
tags: [open-webui, pipelines, httpx, pydantic, fastapi, pipe-plugin]

# Dependency graph
requires:
  - phase: 02-core-api-and-end-to-end-chat
    provides: Core API POST /chat endpoint at http://core-api:8000/chat (built in plan 02-01)

provides:
  - Open WebUI pipe-type Pipelines plugin (src/pipelines/maai_pipe.py)
  - "MAAI Agent" selectable model in Open WebUI dropdown
  - Full message history forwarding to Core API via httpx
  - Intermediate status events via __event_emitter__ (Thinking..., Processing..., Done)
  - File upload handling: saves to /app/uploads, acknowledges receipt

affects:
  - 02-03-PLAN (Docker Compose wiring — adds pipelines service with volume mount)
  - Phase 03 and beyond (any plan that changes Core API /chat interface)

# Tech tracking
tech-stack:
  added:
    - httpx (async HTTP client for pipe -> core-api calls)
    - pydantic BaseModel (Valves configuration class)
  patterns:
    - Pipe-type Pipelines plugin pattern (NOT filter) — pipe appears as model in dropdown
    - __event_emitter__ status event protocol for progress feedback
    - Valves pattern for admin-configurable plugin settings

key-files:
  created:
    - src/pipelines/maai_pipe.py
  modified: []

key-decisions:
  - "Use pipe type (self.type='pipe'), NOT filter — pipe appears as selectable model in Open WebUI; filter would forward to LiteLLM (wrong for this use case)"
  - "120s request timeout default — agent inference on CPU can be slow, especially during model load"
  - "File uploads saved to /app/uploads with timestamp prefix to avoid naming collisions; no parsing in Phase 2 (D-16)"

patterns-established:
  - "Pipe plugin pattern: class Pipeline with Valves(BaseModel), __init__ sets self.type='pipe', async pipe() is main handler"
  - "Python logging module for all log output — no print() calls (CLAUDE.md compliance)"
  - "Status events sequence: Thinking... -> Processing your request... -> Done (maps to D-03 protocol)"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03]

# Metrics
duration: 2min
completed: 2026-04-08
---

# Phase 02 Plan 02: MAAI Agent Pipelines Plugin Summary

**Pipe-type Open WebUI Pipelines plugin forwarding full chat history to Core API with status events and file upload acknowledgment**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T04:41:10Z
- **Completed:** 2026-04-08T04:42:11Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Built `src/pipelines/maai_pipe.py` — a pipe-type Pipelines plugin that appears as "MAAI Agent" in Open WebUI's model dropdown
- Plugin forwards full message history to Core API POST /chat endpoint via async httpx call with 120s timeout
- Intermediate status events emitted via `__event_emitter__`: "Thinking...", "Processing your request...", "Done"
- File upload handling: accepts files from Open WebUI body, saves to /app/uploads with timestamp prefix, appends acknowledgment to agent response
- Configurable via Valves: CORE_API_URL and REQUEST_TIMEOUT exposed in Open WebUI admin UI
- Error handling returns user-friendly messages for timeout, HTTP errors, and unexpected exceptions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MAAI Pipelines pipe plugin** - `2d5cbb7` (feat)

**Plan metadata:** (pending — created after this summary)

## Files Created/Modified

- `src/pipelines/maai_pipe.py` - Pipe-type Pipelines plugin for Open WebUI; routes all messages through Core API

## Decisions Made

- Used pipe type (`self.type = "pipe"`) rather than filter — per D-01 and research Pattern 1. A pipe is a model endpoint; a filter forwards to LiteLLM, which is wrong for this use case.
- Set 120s default timeout for REQUEST_TIMEOUT — CPU inference for Qwen3 14B can be slow, especially on model load.
- File data saved with `int(time.time())_` timestamp prefix to avoid collisions when multiple files arrive in quick succession.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - Python syntax verified, all acceptance criteria checks passed on first run.

## User Setup Required

None - no external service configuration required. The pipelines service Docker wiring is handled in Plan 02-03.

## Next Phase Readiness

- `src/pipelines/maai_pipe.py` is ready to be volume-mounted into the Pipelines server container
- Plan 02-03 (Docker Compose wiring) must add the `pipelines` service with `/app/pipelines` volume mount and register it in Open WebUI via `OPENAI_API_BASE_URLS`
- `maai-uploads` shared volume must be defined in docker-compose.yml and mounted in both `pipelines` and `core-api` containers

---
*Phase: 02-core-api-and-end-to-end-chat*
*Completed: 2026-04-08*
