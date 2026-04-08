---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to plan
stopped_at: Completed 04-document-ingestion-and-rag 04-05-PLAN.md
last_updated: "2026-04-08T21:20:12.406Z"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 15
  completed_plans: 15
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-07)

**Core value:** Clients can describe what they need in natural language and the system executes it using local AI — no cloud dependencies, no data leaving their machine.
**Current focus:** Phase 04 — document-ingestion-and-rag

## Current Position

Phase: 5
Plan: Not started

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
| Phase 03-tool-system-and-skills P04 | 247 | 2 tasks | 5 files |
| Phase 04-document-ingestion-and-rag P00 | 1 | 1 tasks | 9 files |
| Phase 04-document-ingestion-and-rag P01 | 226 | 2 tasks | 8 files |
| Phase 04-document-ingestion-and-rag P02 | 238 | 3 tasks | 15 files |
| Phase 04-document-ingestion-and-rag P03 | 12 | 3 tasks | 13 files |
| Phase 04-document-ingestion-and-rag P04 | 123 | 2 tasks | 3 files |
| Phase 04-document-ingestion-and-rag P05 | 25 | 2 tasks | 6 files |

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
- [Phase 03-tool-system-and-skills]: Inject caplog.handler directly into skills.executor logger (propagate=False) to capture WARNING records in tests
- [Phase 03-tool-system-and-skills]: Extend crewai stub in conftest with Agent/Task/Crew/LLM/Process/crewai.project for executor and freeform_crew import compatibility
- [Phase 04-document-ingestion-and-rag]: xfail stubs reference specific plan numbers (Plan 01-04) so developers know which plan fills each stub
- [Phase 04-document-ingestion-and-rag]: conftest.py stubs docling, llama_index, qdrant_client, arq, and redis via MagicMock so pytest can collect without heavy deps installed
- [Phase 04-document-ingestion-and-rag]: EasyOCR used as Docling OCR backend instead of PaddleOCR — PaddleOCR is not a native Docling backend (RESEARCH.md finding). Satisfies DOCP-02.
- [Phase 04-document-ingestion-and-rag]: opencv-python-headless instead of opencv-python — avoids libGL dependency absent in python:3.11-slim (Research Pitfall 1)
- [Phase 04-document-ingestion-and-rag]: Settings.embed_model set to OllamaEmbedding(nomic-embed-text) via init_embed_model() before any Qdrant operations to produce 768-dim vectors matching Qdrant collection schema
- [Phase 04-document-ingestion-and-rag]: ARQ max_jobs=1 serializes document ingestion for GPU sequencing; GPU lock (Redis SET NX PX) covers docproc HTTP call where OCR runs; released in finally block
- [Phase 04-document-ingestion-and-rag]: CallIngestTool POSTs to /ingest (same process via localhost) — avoids inter-service dep, enables skill-based job queueing per D-02
- [Phase 04-document-ingestion-and-rag]: Phase 4 conftest adds crewai stub (same as phase3) — allows tests to run without crewai installed
- [Phase 04-document-ingestion-and-rag]: ingest-worker reuses core-api build context (./src/core_api) — shares Dockerfile and all deps, overrides CMD to arq workers.ingest_worker.WorkerSettings
- [Phase 04-document-ingestion-and-rag]: docproc start_period=120s — Docling loads large ML models on cold start, can take 60-90s before /health responds
- [Phase 04-document-ingestion-and-rag]: DOCPROC_USE_GPU defaults to false — EasyOCR GPU requires CUDA; most client desktops are CPU-only
- [Phase 04-document-ingestion-and-rag]: Patch rag.pipeline.Document at module level to assert metadata kwargs — avoids fragile MagicMock chain traversal on stubbed llama_index.core.Document

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3: Open WebUI Pipelines + Core API integration is sparsely documented at implementation level — may need implementation research before planning
- Phase 5: Gmail OAuth vs IMAP token flows and ARQ DAG depends_on support need validation before planning

## Session Continuity

Last session: 2026-04-08T21:12:52.423Z
Stopped at: Completed 04-document-ingestion-and-rag 04-05-PLAN.md
Resume file: None
