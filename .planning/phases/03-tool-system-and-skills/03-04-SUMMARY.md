---
phase: 03-tool-system-and-skills
plan: "04"
subsystem: docker-wiring-and-tests
tags: [docker, testing, skill-executor, chat-router, crewai]
dependency_graph:
  requires: [03-02, 03-03]
  provides: [phase-3-complete, docker-skill-wiring, executor-tests, chat-router-tests]
  affects: [docker-compose.yml, tests/phase3/]
tech_stack:
  added: []
  patterns:
    - Inject caplog handler directly into propagate=False loggers to capture warnings in tests
    - Extend crewai stub in conftest with all executor/project symbols for import-time resolution
    - Use __str__ override on MagicMock to control str(result) assertions in executor tests
key_files:
  created:
    - tests/phase3/test_executor.py
    - tests/phase3/test_chat_router.py
  modified:
    - docker-compose.yml
    - clients/default/client.env
    - clients/default/client.env.example
    - tests/phase3/conftest.py
decisions:
  - Inject caplog.handler directly into skills.executor logger (propagate=False) to capture WARNING records in test_run_skill_missing_tool_warning
  - Extend crewai stub (conftest) with Agent/Task/Crew/LLM/Process and crewai.project to unblock executor and freeform_crew imports
  - Use mock_kickoff_result.__str__ override so str(result) in run_skill returns the expected string
metrics:
  duration: 4m
  completed: "2026-04-08"
  tasks: 2
  files: 5
---

# Phase 3 Plan 4: Docker Wiring and Integration Tests Summary

**One-liner:** Docker Compose wired with clients/ bind mount and CLIENT_ID env var; 13 new tests cover executor crew assembly and all four chat routing decisions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update Docker Compose and client.env for skill system | dc3b7c5 | docker-compose.yml, clients/default/client.env, clients/default/client.env.example |
| 2 | Create executor and chat router integration tests | 1595baa | tests/phase3/test_executor.py, tests/phase3/test_chat_router.py, tests/phase3/conftest.py |

## What Was Built

### Task 1: Docker Compose Wiring
- Added `./clients:/app/clients:ro` bind mount to `core-api` service — enables per-client skill YAML and tools.yaml access at `/app/clients/{CLIENT_ID}/`
- Added `CLIENT_ID=${CLIENT_ID:-default}` env var for runtime skill/tool config lookup
- Added `OLLAMA_BASE_URL=http://ollama:11434` env var for direct Ollama access during skill matcher embedding warmup
- Added `ollama-gpu` and `ollama-cpu` `depends_on` entries (`required: false`) so core-api waits for Ollama to be healthy before starting (prevents embedding warmup timeout on startup)
- Added `CLIENT_ID=default` to `clients/default/client.env` and `clients/default/client.env.example`

### Task 2: Integration Tests
**test_executor.py (4 tests):**
- `test_run_skill_assembles_crew` — Crew is constructed and kickoff() called; result string returned
- `test_run_skill_resolves_tools` — Agent receives instantiated tool instances from the registry
- `test_run_skill_missing_tool_warning` — Missing tool logs WARNING; Crew.kickoff still executes (graceful degradation)
- `test_run_skill_formats_user_message` — `{user_message}` placeholder in task description is replaced correctly

**test_chat_router.py (9 tests):**
- `test_detect_pending_confirmation_found` — Parses skill name from bold in assistant confirm message
- `test_detect_pending_confirmation_none` — Returns None when no confirmation pending
- `test_detect_pending_confirmation_empty` — Returns None on empty messages
- `test_chat_list_skills` — LIST_SKILLS returns skill names in response
- `test_chat_freeform_fallback` — FREEFORM routes to run_freeform_crew
- `test_chat_auto_run` — AUTO_RUN routes to run_skill immediately
- `test_chat_confirm_first_prompt` — CONFIRM_FIRST returns bold skill name and "confirm" in response
- `test_chat_confirm_yes` — User "yes" after confirm prompt executes skill
- `test_chat_cancel` — User "no" after confirm prompt returns "cancelled" message

## Test Results

```
73 passed in 5.33s
  - Phase 2: 40 tests (no regressions)
  - Phase 3: 33 tests (plans 01-04 combined)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] caplog does not capture from propagate=False loggers**
- **Found during:** Task 2 — `test_run_skill_missing_tool_warning`
- **Issue:** `get_logger()` sets `logger.propagate = False`, so pytest's caplog fixture (which hooks into root logger) never receives records from `skills.executor`
- **Fix:** Injected `caplog.handler` directly into `skills.executor` logger for the test duration using try/finally to clean up
- **Files modified:** tests/phase3/test_executor.py
- **Commit:** 1595baa

**2. [Rule 1 - Bug] MagicMock __str__ returns default repr, not expected value**
- **Found during:** Task 2 — `test_run_skill_assembles_crew`
- **Issue:** `run_skill` returns `str(crew.kickoff(...))`. With a MagicMock, `str()` returns the default `<MagicMock name=... id=...>` repr, not "mocked result"
- **Fix:** Set `mock_kickoff_result.__str__ = lambda self: "mocked result"` to control the string conversion
- **Files modified:** tests/phase3/test_executor.py
- **Commit:** 1595baa

**3. [Rule 3 - Blocking] crewai stub missing Agent/Task/Crew/LLM/Process/crewai.project symbols**
- **Found during:** Task 2 — importing `skills.executor` and `agents.freeform_crew` for patching
- **Issue:** The existing conftest crewai stub only defined `BaseTool`. The `executor.py` imports `from crewai import LLM, Agent, Crew, Process, Task` and `freeform_crew.py` imports `from crewai.project import CrewBase, agent, crew, task`. These raised `AttributeError`/`ModuleNotFoundError` at import time.
- **Fix:** Extended the crewai stub in conftest with all needed symbols including `crewai.project` module with `CrewBase`, `agent`, `task`, `crew` identity decorators
- **Files modified:** tests/phase3/conftest.py
- **Commit:** 1595baa

**4. [Rule 3 - Blocking] fastapi not installed in test environment**
- **Found during:** Task 2 — importing `routers.chat` for TestClient tests
- **Issue:** `fastapi` is listed in pyproject.toml dependencies but was not installed in the dev Python environment
- **Fix:** Installed `fastapi>=0.115.0`, `uvicorn[standard]`, `pyyaml`, `python-dotenv`, `python-multipart`, `numpy` via pip
- **Commit:** N/A (environment fix, not code change)

## Known Stubs

None — all routing decisions are fully implemented and tested with real code paths.

## Self-Check: PASSED

All created files exist and commits verified:
- FOUND: tests/phase3/test_executor.py
- FOUND: tests/phase3/test_chat_router.py
- FOUND: docker-compose.yml (modified)
- FOUND: commit dc3b7c5 (Task 1)
- FOUND: commit 1595baa (Task 2)
