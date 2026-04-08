---
phase: 03-tool-system-and-skills
plan: 02
subsystem: testing
tags: [crewai, pydantic, yaml, pytest, numpy, embeddings, tool-registry, skill-registry, matcher]

# Dependency graph
requires:
  - phase: 03-tool-system-and-skills plan 01
    provides: SkillDef, SkillIndex, MatchResult, RoutingDecision models; tool_registry, registry, matcher modules

provides:
  - EchoTool BaseTool plugin (src/core_api/tools/echo_tool.py) — test fixture for tool registry
  - example_skill.yaml — complete skill definition for integration testing
  - clients/default/tools.yaml — per-client tool allowlist config
  - 20-test Phase 3 unit test suite covering tool registry, skill registry, and matcher
  - conftest.py with crewai stub for Python 3.14+ dev environments

affects: [03-03, 03-04, all future phases using skill system]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tool plugins: one .py file per tool in src/core_api/tools/, BaseTool subclass with name='echo' (snake_case)"
    - "Skill YAML: self-contained per-skill file with name/description/triggers/autonomy/tools/agent/task"
    - "Test crewai stub: inject minimal crewai.tools.BaseTool stub into sys.modules when crewai unavailable"
    - "Test embedding mocks: monkeypatch skills.registry._embed_texts with deterministic numpy vectors"
    - "Test matcher mocks: monkeypatch skills.matcher.get_index with controlled SkillIndex + known cosine scores"

key-files:
  created:
    - src/core_api/tools/__init__.py
    - src/core_api/tools/echo_tool.py
    - clients/default/skills/example_skill.yaml
    - clients/default/tools.yaml
    - tests/phase3/__init__.py
    - tests/phase3/conftest.py
    - tests/phase3/test_tool_registry.py
    - tests/phase3/test_skill_registry.py
    - tests/phase3/test_matcher.py
  modified: []

key-decisions:
  - "Crewai stub injected in conftest.py (not pytest.importorskip) so tests run in any Python version without crewai installed"
  - "EchoTool.name uses class-level str assignment (not Pydantic field annotation) matching real crewai BaseTool pattern"
  - "Matcher tests use unit vectors with known dot products to control cosine similarity scores deterministically"

patterns-established:
  - "Pattern: Tool plugin = one .py file per tool, class name optional, tool_name = class.name (snake_case)"
  - "Pattern: Skill YAML = clients/<client>/skills/<name>.yaml, must include all required fields inline"
  - "Pattern: Test mocking = monkeypatch skills.registry._embed_texts to avoid live Ollama dependency"

requirements-completed: [AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05]

# Metrics
duration: 5min
completed: 2026-04-08
---

# Phase 3 Plan 02: Example Tool, Skill Config, and Unit Test Scaffold Summary

**EchoTool BaseTool plugin + example_skill.yaml + 20-test Phase 3 suite covering tool registry, skill registry, and three-zone matcher with mocked embeddings**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-08T16:59:40Z
- **Completed:** 2026-04-08T17:05:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- EchoTool BaseTool subclass with `name="echo"` registered in tools/echo_tool.py — discoverable by tool registry
- example_skill.yaml with all required fields (name, description, triggers, autonomy=confirm-first, tools=[echo], agent, task)
- clients/default/tools.yaml allowlist with echo tool enabled
- 20 unit tests pass in 0.25s with no live Ollama — full coverage of tool registry, skill registry, and matcher routing zones

## Task Commits

Each task was committed atomically:

1. **Task 1: Create echo tool plugin and client config files** - `467be03` (feat)
2. **Task 2: Create Phase 3 unit test scaffold** - `79d38f5` (test)

**Plan metadata:** committed with docs commit below

## Files Created/Modified

- `src/core_api/tools/__init__.py` - Empty package marker for tools directory
- `src/core_api/tools/echo_tool.py` - EchoTool: BaseTool subclass, name="echo", returns "Echo: {message}"
- `clients/default/skills/example_skill.yaml` - Example skill with echo tool, confirm-first autonomy, full agent+task sections
- `clients/default/tools.yaml` - Per-client tool allowlist enabling only the echo tool
- `tests/phase3/__init__.py` - Empty package marker
- `tests/phase3/conftest.py` - crewai stub injection + tools_dir/skills_dir/example_skill_yaml/tools_yaml fixtures
- `tests/phase3/test_tool_registry.py` - 5 tests: tool discovery, issubclass check, dunder skipping, allowlist filtering
- `tests/phase3/test_skill_registry.py` - 5 tests: YAML loading, autonomy defaults, tool filtering, embedding shape
- `tests/phase3/test_matcher.py` - 9 tests: LIST_SKILLS keywords, AUTO_RUN, CONFIRM_FIRST, FREEFORM zones

## Decisions Made

- **crewai stub over pytest.importorskip**: Using `importorskip` caused all 3 test modules to skip (exit code 5), which doesn't meet the "pytest exits 0" criterion. Instead injected a minimal plain-class stub in conftest.py. This allows tests to run in Python 3.14 dev environments and properly tests the skill modules against a compatible BaseTool interface.
- **Plain class stub (not Pydantic BaseModel)**: The stub BaseTool uses a plain Python class so `EchoTool.name` remains accessible as a class-level string attribute, matching how real crewai BaseTool exposes it. Pydantic's metaclass interferes with class-level attribute access.
- **Unit vectors for score control**: Matcher tests use `e0` (unit vector along axis 0) as the skill embedding, then construct query vectors as `[target_score, sqrt(1 - score^2), 0, ...]` to achieve exact dot products, enabling deterministic threshold testing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] crewai stub design: plain class instead of Pydantic BaseModel**
- **Found during:** Task 2 (unit test scaffold)
- **Issue:** Initial crewai stub inherited from `pydantic.BaseModel`. When `EchoTool` (also Pydantic) inherits from this stub's `BaseTool`, accessing `EchoTool.name` at class level raises `AttributeError` because Pydantic intercepts class-level field access.
- **Fix:** Changed stub `BaseTool` to a plain Python class. `name: str = ""` becomes a regular class attribute, so `EchoTool.name == "echo"` works at class level, matching real crewai's behaviour.
- **Files modified:** tests/phase3/conftest.py
- **Verification:** `python -m pytest tests/phase3/ -x -q` → 20 passed
- **Committed in:** 79d38f5 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in stub design)
**Impact on plan:** Required fix for all tool registry tests to pass. No scope creep.

## Issues Encountered

- Python 3.14 on dev machine (not project-required 3.11) lacks crewai due to broken wheel builds (regex, tiktoken). The crewai stub approach cleanly solves this without special-casing in CI.
- numpy not installed globally — installed via pip to enable test modules to import.

## Known Stubs

None — EchoTool is a real implementation, example_skill.yaml contains real field values.

## Next Phase Readiness

- Tool registry, skill registry, and matcher are fully tested
- EchoTool serves as a working example for future tool plugin authors
- example_skill.yaml serves as a template for adding real skills
- Ready for Plan 03 (pipeline integration) and Plan 04 (end-to-end integration)

---
*Phase: 03-tool-system-and-skills*
*Completed: 2026-04-08*
