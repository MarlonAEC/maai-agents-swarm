---
phase: "04-document-ingestion-and-rag"
plan: "03"
subsystem: "core_api"
tags: ["rag", "tools", "skills", "ingest", "arq", "qdrant"]
dependency_graph:
  requires: ["04-02"]
  provides: ["qdrant_search_tool", "job_status_tool", "call_ingest_tool", "ingest_router", "rag_crew", "document_ingest_skill", "ask_documents_skill"]
  affects: ["core_api", "skill_registry", "tool_registry"]
tech_stack:
  added: ["arq.jobs.Job for status polling"]
  patterns: ["BaseTool subclass pattern (echo_tool.py)", "ARQ enqueue_job via FastAPI router", "skill YAML with tools list"]
key_files:
  created:
    - src/core_api/tools/qdrant_search_tool.py
    - src/core_api/tools/job_status_tool.py
    - src/core_api/tools/call_ingest_tool.py
    - src/core_api/routers/ingest.py
    - src/core_api/agents/rag_crew.py
    - clients/default/skills/document_ingest.yaml
    - clients/default/skills/ask_documents.yaml
  modified:
    - clients/default/tools.yaml
    - src/core_api/main.py
    - tests/phase04/test_rag_query.py
    - tests/phase04/test_chat_upload.py
    - tests/phase04/conftest.py
decisions:
  - "CallIngestTool POSTs to /ingest (same process via localhost) — avoids inter-service dep, enables skill-based job queueing per D-02"
  - "ingest router validates file existence before ARQ enqueue — fail-fast at API layer before worker picks up bad job"
  - "JobStatusTool uses asyncio.run() to bridge sync crewai _run to async arq status check"
  - "Phase 4 conftest adds crewai stub (same as phase3) — allows tests to run without crewai installed"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-08"
  tasks_completed: 3
  files_created: 8
  files_modified: 5
---

# Phase 04 Plan 03: User-Facing RAG Layer Summary

**One-liner:** Three CrewAI BaseTool plugins (qdrant_search, job_status, call_ingest), a POST /ingest FastAPI endpoint queuing ARQ jobs, a RAG crew module, two skill YAML files (document_ingest, ask_documents), and main.py startup wiring — completing the user-facing document Q&A flow.

## What Was Built

This plan connects the RAG pipeline from Plan 02 to the skill system from Phase 3, enabling users to trigger document ingestion and query their document knowledge base through chat.

### Task 1: Tools and Ingest Router

**QdrantSearchTool** (`src/core_api/tools/qdrant_search_tool.py`): CrewAI BaseTool that calls `query_documents()` from the Plan 02 RAG pipeline. Returns formatted results with `Source: filename, page N` citations per DOCP-06.

**JobStatusTool** (`src/core_api/tools/job_status_tool.py`): CrewAI BaseTool that checks ARQ job status using `arq.jobs.Job.info()`. Bridges synchronous `_run` to async ARQ via `asyncio.run()`. Returns human-readable status including chunk count on completion.

**CallIngestTool** (`src/core_api/tools/call_ingest_tool.py`): CrewAI BaseTool that POSTs to the `/ingest` endpoint (same process via localhost) to queue an ARQ `process_document` job. Returns job ID for status tracking. Per D-02: the skill itself triggers the job through this tool.

**Ingest Router** (`src/core_api/routers/ingest.py`): FastAPI POST `/ingest` endpoint that validates file existence and extension, then calls `redis.enqueue_job("process_document", ...)`. Returns immediately with job ID (async pattern per D-01). Supported extensions: PDF, PNG, JPG, JPEG, TIFF, BMP.

### Task 2: RAG Crew and Skill YAMLs

**RAG Crew** (`src/core_api/agents/rag_crew.py`): `run_rag_crew(user_message, context_chunks)` function assembling a minimal single-agent CrewAI crew to synthesize answers from retrieved document context. Not typically called directly — the ask_documents skill uses qdrant_search tool and the executor handles crew creation.

**document_ingest.yaml**: Skill for indexing documents. Uses `call_ingest` and `job_status` tools. `autonomy: auto-execute`. Triggers: "index this document", "ingest this file", "add to knowledge base", etc.

**ask_documents.yaml**: Skill for querying the knowledge base. Uses `qdrant_search` tool. `autonomy: auto-execute`. Instructions include citation format requirements.

**tools.yaml**: Updated allowlist to include `qdrant_search`, `job_status`, `call_ingest` alongside existing `echo`.

### Task 3: main.py Wiring and Tests

**main.py**: Added `init_embed_model()` call in lifespan startup (before yield, after skill registry init). Added `app.include_router(ingest_router)`. Both wrapped safely — embed model failure logs a warning rather than crashing startup.

**Tests**: Replaced all 4 xfail stubs across `test_rag_query.py` and `test_chat_upload.py` with 9 real passing tests covering: citation format, empty results, tool names, skill YAML tool lists, and ingest endpoint job queuing.

**conftest.py**: Added crewai stub injection (same pattern as phase3/conftest.py) so phase4 tests run without crewai installed.

## Verification

All 26 phase 4 tests pass: `python -m pytest tests/phase04/ -q` → `26 passed in 0.30s`

Acceptance criteria verified:
- QdrantSearchTool calls query_documents with `Source:` citation format
- JobStatusTool checks ARQ Job.info()
- CallIngestTool POSTs to `/ingest` and returns job_id
- Ingest router uses `enqueue_job`, validates `/app/uploads/` path
- document_ingest skill lists `call_ingest` in tools (D-02 compliance)
- ask_documents skill lists `qdrant_search` in tools
- tools.yaml has all three new tools
- main.py has `init_embed_model`, `ingest_router`, `app.include_router(ingest_router)`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | cfa831f | feat(04-03): create RAG tools and ingest router |
| Task 2 | 3b5acf3 | feat(04-03): add RAG crew, skill YAMLs, and update tool allowlist |
| Task 3 | 3e1a001 | feat(04-03): wire main.py and fill Wave 0 test stubs |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Phase 4 conftest missing crewai stub**
- **Found during:** Task 3 (test execution)
- **Issue:** `tests/phase04/conftest.py` stubbed arq, docling, llama_index etc. but not `crewai` or `crewai.tools`. All tool imports in tests failed with `ModuleNotFoundError: No module named 'crewai'`.
- **Fix:** Added the same crewai stub injection pattern from `tests/phase3/conftest.py` to `tests/phase04/conftest.py`. The stub provides BaseTool, Agent, Task, Crew, LLM, Process at module level.
- **Files modified:** `tests/phase04/conftest.py`
- **Commit:** 3e1a001

## Known Stubs

None. All tools are fully wired to real implementations (rag/pipeline.py, ARQ, FastAPI). No hardcoded empty values or placeholder responses in the main code paths.
