---
phase: 04-document-ingestion-and-rag
plan: 05
subsystem: testing
tags: [pytest, mocking, qdrant, docling, easyocr, arq, gpu-lock, llamaindex, rag]

# Dependency graph
requires:
  - phase: 04-document-ingestion-and-rag
    provides: Plans 01-04 implementation of docproc, RAG pipeline, tools, and worker
provides:
  - Complete passing test suite for all Phase 4 code (35 tests, 0 xfail stubs)
  - Edge case coverage for docproc, OCR, Qdrant, client isolation, tools, GPU lock, worker
affects: [04-document-ingestion-and-rag, future phases using RAG/ingest]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Patch rag.pipeline.Document to inspect constructor kwargs for metadata assertion"
    - "Use worktree pytest root for isolation from main repo test cache"
    - "AsyncMock + patch for GPU lock acquire/release verification in worker tests"

key-files:
  created: []
  modified:
    - tests/phase04/test_docling_pipeline.py
    - tests/phase04/test_ocr_processing.py
    - tests/phase04/test_qdrant_indexing.py
    - tests/phase04/test_client_isolation.py
    - tests/phase04/test_chat_upload.py
    - tests/phase04/test_gpu_scheduling.py

key-decisions:
  - "Patch rag.pipeline.Document at the pipeline module level to verify metadata kwargs — avoids fragile MagicMock attribute traversal on stubbed llama_index.core.Document"
  - "test_ingest_endpoint_rejects_unsupported_ext asserts mock_create_pool.assert_not_called() — validation must fail before Redis pool is created (validates correct early-return order)"

patterns-established:
  - "Phase 4 test pattern: patch heavy deps in conftest, patch implementation modules in individual tests"
  - "Worker error path tests: patch acquire_gpu_lock and release_gpu_lock separately to isolate the finally-block guarantee"

requirements-completed: [DOCP-01, DOCP-02, DOCP-03, DOCP-04, DOCP-05, DOCP-06, DOCP-07]

# Metrics
duration: 25min
completed: 2026-04-08
---

# Phase 4 Plan 05: Phase 4 Test Hardening Summary

**35-test Phase 4 suite hardened with 9 missing edge cases — full green, zero xfail stubs, all DOCP requirements covered**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-08T17:00:00Z
- **Completed:** 2026-04-08T17:25:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Verified all prior Phase 4 tests (26) passed as a baseline — no regressions
- Added 9 targeted edge-case tests across 6 test files to reach 35 total
- Full `pytest tests/phase04/ -q` reports 35 passed, 0 failed, 0 xfail

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden docproc and RAG pipeline tests** - `795f78e` (test)
2. **Task 2: Harden tools, ingest, and GPU lock tests — full suite green** - `efe8164` (test)

**Plan metadata:** (docs commit — see final commit below)

## Files Created/Modified

- `tests/phase04/test_docling_pipeline.py` — Added test_process_returns_full_text, test_process_returns_total_pages
- `tests/phase04/test_ocr_processing.py` — Added test_ocr_disabled_uses_text_converter
- `tests/phase04/test_qdrant_indexing.py` — Added test_index_document_creates_metadata (patches Document constructor)
- `tests/phase04/test_client_isolation.py` — Added test_different_clients_different_collections
- `tests/phase04/test_chat_upload.py` — Added test_call_ingest_tool_posts_to_ingest, test_ingest_endpoint_rejects_unsupported_ext
- `tests/phase04/test_gpu_scheduling.py` — Added test_worker_max_jobs_is_one, test_worker_releases_lock_on_docproc_error

## Decisions Made

- Patch `rag.pipeline.Document` at module level to assert metadata kwargs, rather than relying on MagicMock attribute traversal from stubbed `llama_index.core.Document` (which returns MagicMock chains that don't equal literal strings)
- `test_ingest_endpoint_rejects_unsupported_ext` asserts `mock_create_pool.assert_not_called()` to verify validation rejects .docx before any Redis I/O — validates the correct early-exit order in the ingest router

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_index_document_creates_metadata assertion strategy**
- **Found during:** Task 1 (test_qdrant_indexing.py)
- **Issue:** Original approach captured Document instances from the splitter call — but Document is stubbed as MagicMock in conftest.py, so `doc.metadata["file_name"]` returns a MagicMock chain, not the literal string
- **Fix:** Changed to patch `rag.pipeline.Document` directly and assert `call_args.kwargs["metadata"]` contains correct literal values
- **Files modified:** tests/phase04/test_qdrant_indexing.py
- **Verification:** Test passes (34/34 → 35/35 after fix)
- **Committed in:** 795f78e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test assertion strategy)
**Impact on plan:** Necessary correction for test correctness. No scope creep.

## Issues Encountered

- pytest was collecting tests from `D:/MAAI Agent Platform/` (main repo) instead of the worktree, showing 26 tests instead of 35. Resolved by running pytest from the worktree root `D:/MAAI Agent Platform/.claude/worktrees/agent-a9971621`.

## Known Stubs

None — all tests exercise real code paths via mocked external services. No hardcoded empty values or placeholders remain in the test suite.

## Next Phase Readiness

- All Phase 4 unit tests pass — Phase 4 implementation is verified at code level
- RAG pipeline, docproc, GPU lock, ingest worker, and tool tests cover success and error paths
- Ready for Phase 5 planning (email integration) or full Docker stack integration testing

---
*Phase: 04-document-ingestion-and-rag*
*Completed: 2026-04-08*
