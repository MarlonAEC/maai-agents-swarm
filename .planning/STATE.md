---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: Completed 03-02-PLAN.md
last_updated: "2026-04-08T17:06:04.112Z"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 9
  completed_plans: 7
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Clients can describe what they need in natural language and the system executes it using local AI — no cloud dependencies, no data leaving their machine.
**Current focus:** Phase 03 — tool-system-and-skills

## Current Position

Phase: 03 (tool-system-and-skills) — EXECUTING
Plan: 4 of 4

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-infrastructure-foundation P01 | 4 | 3 tasks | 17 files |
| Phase 01-infrastructure-foundation P02 | 1 | 1 tasks | 1 files |
| Phase 02-core-api-and-end-to-end-chat P02 | 2 | 1 tasks | 1 files |
| Phase 02-core-api-and-end-to-end-chat P01 | 2 | 2 tasks | 10 files |
| Phase 02-core-api-and-end-to-end-chat P03 | 225 | 2 tasks | 11 files |
| Phase 03-tool-system-and-skills P01 | 150 | 2 tasks | 6 files |
| Phase 03-tool-system-and-skills P03 | 138 | 2 tasks | 3 files |
| Phase 03-tool-system-and-skills P02 | 5 | 2 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- LiteLLM MUST be pinned to >=1.83.0 — versions 1.82.7/1.82.8 were backdoored (March 2026 supply chain attack)
- Python 3.11 only — 3.12/3.13 have known packaging issues with PaddleOCR and ML deps
- Docling + PaddleOCR must run in separate containers from Core API (PaddlePaddle vs PyTorch dependency conflict)
- nomic-embed-text must be explicitly pulled in bootstrap — not auto-pulled with Qwen3 or Gemma 3
- [Phase 01-infrastructure-foundation]: LiteLLM image main-latest with inline comment requiring >=1.83.0 (backdoored supply chain attack on 1.82.7/1.82.8)
- [Phase 01-infrastructure-foundation]: ollama-gpu and ollama-cpu share container_name: ollama so LiteLLM always reaches http://ollama:11434 regardless of profile
- [Phase 01-infrastructure-foundation]: Open WebUI configured with ENABLE_OLLAMA_API=false routing all LLM traffic through LiteLLM
- [Phase 01-infrastructure-foundation]: WEBUI_SECRET_KEY placeholder CHANGE_ME_RUN_BOOTSTRAP in client.env — bootstrap.sh Plan 02 will replace with real secret
- [Phase 01-infrastructure-foundation]: Cross-platform sed compatibility: detect GNU vs BSD sed for bootstrap.sh to work on Linux, macOS, and Git Bash
- [Phase 01-infrastructure-foundation]: LiteLLM version check is best-effort: unknown version warns but does not block bootstrap
- [Phase 02-core-api-and-end-to-end-chat]: Pipe plugin uses self.type='pipe' (not filter) so it appears as selectable model in Open WebUI dropdown; filter would forward to LiteLLM which is wrong for this use case
- [Phase 02-core-api-and-end-to-end-chat]: 120s default REQUEST_TIMEOUT in Pipelines plugin — CPU inference for Qwen3 14B is slow especially on model load
- [Phase 02-core-api-and-end-to-end-chat]: openai/reasoning-model LiteLLM alias used for LLM inference; Ollama embedder points directly to http://ollama:11434/api/embeddings; stream=False + max_iter=5 + max_execution_time=60 guardrails; run_in_executor for async safety
- [Phase 02-core-api-and-end-to-end-chat]: OPENAI_API_BASE_URLS and OPENAI_API_KEYS must have same semicolon-separated entry count — mismatch causes silent routing failures in Open WebUI
- [Phase 02-core-api-and-end-to-end-chat]: maai-uploads is a named Docker volume shared between core-api and pipelines — persists across restarts, accessible by both containers
- [Phase 03-tool-system-and-skills]: Use Ollama /api/embed batch endpoint (not /api/embeddings) for skill indexing — correct endpoint per Research Pitfall 6
- [Phase 03-tool-system-and-skills]: L2-normalise skill embeddings at build time so dot product == cosine similarity in matcher — avoids redundant normalisation per query
- [Phase 03-tool-system-and-skills]: Warmup embedding model in initialize() to prevent first-match timeout (Research Pitfall 2)
- [Phase 03-tool-system-and-skills]: Direct Agent/Task/Crew constructors for skill executor — @CrewBase cannot load arbitrary runtime YAML paths
- [Phase 03-tool-system-and-skills]: asyncio.get_running_loop() replaces deprecated get_event_loop() in chat handler
- [Phase 03-tool-system-and-skills]: Skill name embedded in bold in confirmation message enables stateless confirm-first without server sessions
- [Phase 03-tool-system-and-skills]: crewai stub injected in conftest.py (not pytest.importorskip) so Phase 3 tests run in any Python version without crewai installed
- [Phase 03-tool-system-and-skills]: Plain class crewai stub (not Pydantic BaseModel) so EchoTool.name accessible at class level matching real crewai behaviour

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3: Open WebUI Pipelines + Core API integration is sparsely documented at implementation level — may need implementation research before planning
- Phase 5: Gmail OAuth vs IMAP token flows and ARQ DAG depends_on support need validation before planning

## Session Continuity

Last session: 2026-04-08T17:06:04.109Z
Stopped at: Completed 03-02-PLAN.md
Resume file: None
