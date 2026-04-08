---
phase: 04-document-ingestion-and-rag
plan: "00"
subsystem: testing
tags: [pytest, docling, qdrant, llama-index, arq, easyocr, xfail, stubs]

# Dependency graph
requires:
  - phase: 03-tool-system-and-skills
    provides: conftest stub pattern for heavy deps (crewai stub injected at test time)
provides:
  - tests/phase04/ directory with 8 test files covering DOCP-01 through DOCP-07
  - pytest-runnable xfail stubs for all Phase 4 requirements
  - conftest.py with sys.path setup and MagicMock stubs for docling, qdrant, llama_index, arq, redis
affects:
  - 04-01 (docproc service — will implement test_docling_pipeline and test_ocr_processing)
  - 04-02 (indexer — will implement test_qdrant_indexing and test_client_isolation)
  - 04-03 (RAG skill + API — will implement test_rag_query and test_chat_upload)
  - 04-04 (GPU scheduling — will implement test_gpu_scheduling)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xfail stub pattern: each DOCP requirement gets a dedicated test file with xfail-marked stubs"
    - "MagicMock stub pattern: heavy deps (docling, qdrant_client, llama_index, arq, redis) injected via sys.modules in conftest.py"

key-files:
  created:
    - tests/phase04/__init__.py
    - tests/phase04/conftest.py
    - tests/phase04/test_docling_pipeline.py
    - tests/phase04/test_ocr_processing.py
    - tests/phase04/test_qdrant_indexing.py
    - tests/phase04/test_client_isolation.py
    - tests/phase04/test_rag_query.py
    - tests/phase04/test_chat_upload.py
    - tests/phase04/test_gpu_scheduling.py
  modified: []

key-decisions:
  - "xfail stubs reference specific plan numbers (Plan 01-04) so developers know which plan fills each stub"
  - "conftest.py stubs docling, llama_index, qdrant_client, arq, and redis via MagicMock so pytest can collect without heavy deps installed"

patterns-established:
  - "Phase test stub pattern: create xfail stubs in Wave 0 so pytest can verify implementation progress from Plan 01 onward"

requirements-completed: [DOCP-01, DOCP-02, DOCP-03, DOCP-04, DOCP-05, DOCP-06, DOCP-07]

# Metrics
duration: 1min
completed: "2026-04-08"
---

# Phase 4 Plan 00: Wave 0 Test Stubs Summary

**pytest xfail stub suite covering all 7 DOCP requirements (15 stubs) with MagicMock isolation for docling, Qdrant, LlamaIndex, ARQ, and Redis heavy dependencies**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-08T20:52:45Z
- **Completed:** 2026-04-08T20:54:05Z
- **Tasks:** 1
- **Files modified:** 9

## Accomplishments

- Created tests/phase04/ with __init__.py, conftest.py, and 7 xfail stub test files
- All 15 stub tests run as xfail under pytest (0 errors, 0 failures)
- conftest.py stubs docling, easyocr, llama_index, qdrant_client, arq, and redis via MagicMock — pytest collects without any heavy deps installed
- Each DOCP-01 through DOCP-07 requirement maps to at least one dedicated stub file with xfail marker referencing the implementing plan

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/phase04/ directory with conftest and all stub test files** - `f4a7837` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/phase04/__init__.py` - Empty package init
- `tests/phase04/conftest.py` - sys.path setup for src/core_api and src/docproc; MagicMock stubs for heavy deps; sample_pages, test_client_id, sample_file_name fixtures
- `tests/phase04/test_docling_pipeline.py` - DOCP-01 stubs: test_text_pdf_extraction, test_process_endpoint_returns_pages
- `tests/phase04/test_ocr_processing.py` - DOCP-02 stubs: test_scanned_pdf_ocr_enabled, test_easyocr_options_configured
- `tests/phase04/test_qdrant_indexing.py` - DOCP-03/04 stubs: test_semantic_chunking, test_qdrant_vector_upsert, test_init_embed_model_768_dims
- `tests/phase04/test_client_isolation.py` - DOCP-04 stubs: test_collection_naming_per_client, test_query_returns_only_own_docs
- `tests/phase04/test_rag_query.py` - DOCP-05 stubs: test_rag_skill_returns_answer, test_qdrant_search_tool_citations
- `tests/phase04/test_chat_upload.py` - DOCP-06 stubs: test_ingest_endpoint_queues_job, test_ingest_skill_triggers_arq
- `tests/phase04/test_gpu_scheduling.py` - DOCP-07 stubs: test_gpu_lock_acquire_release, test_gpu_lock_serializes_workloads

## Decisions Made

- xfail stubs reference specific plan numbers (Plan 01-04) so developers know exactly which plan will fill each stub
- Heavy deps stubbed via MagicMock in sys.modules (same pattern as Phase 3 crewai stub) — keeps test collection fast and dependency-free

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- tests/phase04/ is ready for Plans 01-04 to fill in stubs as implementation proceeds
- pytest tests/phase04/ -x -q can be used as a verify command in all subsequent Phase 4 plans
- No blockers

---
*Phase: 04-document-ingestion-and-rag*
*Completed: 2026-04-08*
