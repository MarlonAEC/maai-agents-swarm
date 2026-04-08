---
phase: 03-tool-system-and-skills
plan: "01"
subsystem: skill-system-core
tags: [skills, routing, embeddings, tool-registry, crewai]
dependency_graph:
  requires: []
  provides:
    - skills.models (SkillDef, RoutingDecision, MatchResult, SkillIndex)
    - skills.tool_registry (load_tools, get_registry, initialize, filter_by_allowlist)
    - skills.registry (load_skills, get_index, initialize, _embed_texts)
    - skills.matcher (route)
  affects:
    - src/core_api/main.py (startup initialization)
    - src/core_api/routers/ (skill-aware chat routing in 03-03)
tech_stack:
  added:
    - numpy>=1.26 (cosine similarity dot products)
  patterns:
    - importlib.util.spec_from_file_location for plugin discovery
    - Ollama /api/embed batch embedding with L2-normalisation
    - Three-zone threshold routing (HIGH=0.7, LOW=0.5)
    - Module-level singleton (_INDEX, _REGISTRY) populated at startup
key_files:
  created:
    - src/core_api/skills/__init__.py
    - src/core_api/skills/models.py
    - src/core_api/skills/tool_registry.py
    - src/core_api/skills/registry.py
    - src/core_api/skills/matcher.py
  modified:
    - src/core_api/pyproject.toml (added numpy>=1.26)
decisions:
  - "Use /api/embed (batch) not /api/embeddings (per Research Pitfall 6) — Ollama batch endpoint is more efficient and correct"
  - "L2-normalise embeddings at index build time so dot product == cosine similarity at match time"
  - "Warmup embedding model at initialize() to prevent first-match timeout (Research Pitfall 2)"
  - "Filter skill tool lists (not skills themselves) when allowed_tools is set — skill stays indexed, tools are filtered"
metrics:
  duration_seconds: 150
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_created: 5
  files_modified: 1
---

# Phase 3 Plan 01: Skill System Core Modules Summary

**One-liner:** Embedding-based three-zone skill matcher with importlib tool plugin registry and Ollama /api/embed batch indexing.

## What Was Built

Five new Python modules in `src/core_api/skills/` implementing the complete skill matching pipeline:

1. **`skills/__init__.py`** — Package init (minimal, makes `skills` importable).

2. **`skills/models.py`** — Pydantic/dataclass data models:
   - `SkillDef(BaseModel)` — validates skill YAML files with `autonomy="confirm-first"` default
   - `RoutingDecision(Enum)` — four states: AUTO_RUN, CONFIRM_FIRST, FREEFORM, LIST_SKILLS
   - `MatchResult` — decision + matched skill + cosine score
   - `SkillIndex` — dataclass holding skills list and L2-normalised numpy embedding matrix

3. **`skills/tool_registry.py`** — Plugin discovery via importlib:
   - Scans `tools/` directory for `.py` files
   - Imports each module and finds non-abstract `BaseTool` subclasses
   - Registers under the class `.name` attribute as key
   - Supports `filter_by_allowlist()` for per-client tool restriction
   - Uses `get_logger(__name__)` throughout (no print statements)

4. **`skills/registry.py`** — YAML discovery and embedding index:
   - `_embed_texts()` — batched Ollama `/api/embed` call, L2-normalises returned vectors
   - `_warmup_embedding_model()` — forces model load before first real call
   - `load_skills()` — reads `*.yaml` files, validates with `SkillDef`, batch-embeds all texts
   - Module-level `_INDEX` singleton populated by `initialize()`

5. **`skills/matcher.py`** — Three-zone routing:
   - LIST_SKILLS keyword short-circuit (frozenset of phrases like "what can you do")
   - Embeds user message via `_embed_texts`, computes dot product against index
   - score >= 0.7: AUTO_RUN (if autonomy=="auto-execute") or CONFIRM_FIRST
   - score >= 0.5: CONFIRM_FIRST
   - score < 0.5: FREEFORM (no skill matched)
   - Thresholds configurable via `SKILL_HIGH_THRESHOLD` / `SKILL_LOW_THRESHOLD` env vars

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The modules are fully implemented with no placeholder logic or hardcoded empty values. The `_embed_texts()` function requires a running Ollama instance — this is expected Docker runtime behavior, not a stub.

## Self-Check: PASSED

Files verified:
- FOUND: src/core_api/skills/__init__.py
- FOUND: src/core_api/skills/models.py
- FOUND: src/core_api/skills/tool_registry.py
- FOUND: src/core_api/skills/registry.py
- FOUND: src/core_api/skills/matcher.py

Commits verified:
- 126d020: feat(03-01): add skill data models and tool plugin registry
- 28beccd: feat(03-01): add skill registry with embedding index and three-zone matcher
