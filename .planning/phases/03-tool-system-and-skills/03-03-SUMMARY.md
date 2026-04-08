---
phase: 03-tool-system-and-skills
plan: "03"
subsystem: core-api
tags: [skill-executor, chat-routing, crewai, lifespan, confirm-first]
dependency_graph:
  requires: ["03-01"]
  provides: ["end-to-end skill execution via chat", "confirm-first flow", "skill listing"]
  affects: ["src/core_api/skills/executor.py", "src/core_api/routers/chat.py", "src/core_api/main.py"]
tech_stack:
  added: []
  patterns:
    - "Direct CrewAI Agent/Task/Crew constructors (not @CrewBase) for runtime YAML-driven assembly"
    - "asyncio.get_running_loop() for async-safe thread-pool offloading"
    - "Stateless confirm-first via **bold** skill name embedded in confirmation message"
key_files:
  created:
    - src/core_api/skills/executor.py
  modified:
    - src/core_api/routers/chat.py
    - src/core_api/main.py
decisions:
  - "Direct Agent/Task/Crew constructors used for skill executor — @CrewBase cannot load arbitrary runtime YAML paths (Research Pitfall 4)"
  - "asyncio.get_running_loop() replaces deprecated get_event_loop() in chat handler (Research Pitfall 5)"
  - "Skill name embedded in **bold** in confirmation message enables stateless confirm-first without server sessions (Research Pitfall 3)"
  - "Tool registry initialized before skill registry in lifespan — dependency order required"
  - "Graceful degradation: missing skills directory logs warning and continues (no crash)"
metrics:
  duration: "2m 18s"
  completed: "2026-04-08T17:02:02Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 3 Plan 03: Skill Executor and Chat Router Wiring Summary

**One-liner:** Skill executor assembles CrewAI crews from matched SkillDef at runtime using direct constructors; chat router routes through matcher before freeform fallback with stateless confirm-first flow.

## What Was Built

Three files that complete the skill system's end-to-end execution path:

**`src/core_api/skills/executor.py`** (new)
- `run_skill(skill, user_message, messages)` — synchronous function for use with `loop.run_in_executor()`
- Resolves tool instances from tool registry by name, instantiating each class
- Builds `Agent` → `Task` → `Crew` from SkillDef fields using direct constructors (no `@CrewBase`)
- Formats `{user_message}` into task description
- Uses same LLM pattern as `freeform_crew.py`: `openai/reasoning-model` via LiteLLM proxy

**`src/core_api/routers/chat.py`** (modified)
- Added skill routing layer before freeform fallback
- `_detect_pending_confirmation()` — parses last assistant message for embedded skill name in `**bold**`
- `_CONFIRM_KEYWORDS` / `_CANCEL_KEYWORDS` — frozensets for yes/no detection
- Handles all four `RoutingDecision` values: `LIST_SKILLS`, `AUTO_RUN`, `CONFIRM_FIRST`, `FREEFORM`
- Replaced deprecated `get_event_loop()` with `get_running_loop()`
- Confirmation message embeds skill name as `**{skill.name}**` for stateless parsing

**`src/core_api/main.py`** (modified)
- Lifespan now initializes tool registry then skill registry at startup
- Reads `CLIENT_ID` env var to locate per-client skills and tools config
- Loads optional `tools.yaml` allowlist from `/app/clients/{CLIENT_ID}/tools.yaml`
- Gracefully handles missing skills directory (warning, no crash)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create skill executor with dynamic crew assembly | 6a144e3 | src/core_api/skills/executor.py |
| 2 | Modify chat router for skill routing and lifespan initialization | 4a97ed8 | src/core_api/routers/chat.py, src/core_api/main.py |

## Verification

- All files parse with `ast.parse()` — valid Python 3.11 syntax
- All 40 phase 2 tests pass after modifications (`python -m pytest tests/phase2/ -x -q`)
- Static analysis confirms all acceptance criteria met:
  - executor.py: `run_skill` function, direct constructors, no `@CrewBase`, no `asyncio.run`
  - chat.py: all four RoutingDecision branches, `get_running_loop()`, confirmation helpers
  - main.py: both registry initializations, CLIENT_ID, yaml.safe_load

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all routing logic is fully wired. Skills directory path (`/app/clients/{CLIENT_ID}/skills`) will be bind-mounted in Plan 04 (Docker wiring).

## Self-Check: PASSED

- `src/core_api/skills/executor.py` exists and defines `run_skill` at line 24
- `src/core_api/routers/chat.py` defines `_detect_pending_confirmation` at line 50
- `src/core_api/main.py` contains `tool_reg.initialize` and `skill_reg.initialize`
- Commits 6a144e3 and 4a97ed8 verified in git log
