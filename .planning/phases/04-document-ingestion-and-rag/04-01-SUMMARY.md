---
phase: 04-document-ingestion-and-rag
plan: "01"
subsystem: docproc
tags: [docling, easyocr, fastapi, document-processing, ocr]
dependency_graph:
  requires: ["04-00"]
  provides: ["docproc-service", "DOCP-01", "DOCP-02"]
  affects: ["04-03", "04-04"]
tech_stack:
  added: ["docling>=2.85.0", "easyocr", "opencv-python-headless", "uvicorn"]
  patterns: ["FastAPI lifespan", "dual-converter pattern", "EasyOCR pre-warming", "stub-based test isolation"]
key_files:
  created:
    - src/docproc/main.py
    - src/docproc/pyproject.toml
    - src/docproc/logging_config.py
    - src/docproc/Dockerfile
    - tests/phase04/__init__.py
    - tests/phase04/conftest.py
    - tests/phase04/test_docling_pipeline.py
    - tests/phase04/test_ocr_processing.py
  modified: []
decisions:
  - "EasyOCR used as Docling OCR backend instead of PaddleOCR — PaddleOCR is not a native Docling backend (RESEARCH.md finding). EasyOCR satisfies DOCP-02."
  - "opencv-python-headless instead of opencv-python — headless variant avoids libGL dependency absent in python:3.11-slim (Research Pitfall 1)"
  - "120s HEALTHCHECK start-period — Docling + EasyOCR model loading is slow on first container boot"
  - "Dual DocumentConverter pattern — converter_ocr and converter_text cached on app.state for fast per-request selection"
  - "EasyOCR pre-warmed in lifespan via Reader instantiation — avoids first-request latency from model download"
  - "Test isolation via sys.modules stubs (conftest.py) — docling/easyocr/cv2 not installed in dev Python 3.14 environment"
metrics:
  duration_seconds: 226
  completed_date: "2026-04-08"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 0
---

# Phase 4 Plan 01: Docproc Sidecar Service Summary

**One-liner:** FastAPI document processing sidecar using Docling text extraction and EasyOCR for scanned PDFs, exposing POST /process on port 8001.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create docproc FastAPI service with Docling + EasyOCR | 0b10f33 | src/docproc/main.py, pyproject.toml, logging_config.py |
| 2 | Create docproc Dockerfile and fill in Wave 0 test stubs | e721314 | src/docproc/Dockerfile, tests/phase04/* (5 files) |

## What Was Built

The docproc sidecar is a self-contained FastAPI microservice that:

1. **Accepts POST /process** with `{file_path, ocr_enabled}` and returns structured text with per-page metadata matching the contract expected by Plan 03's ARQ worker.

2. **Dual converter strategy** — two `DocumentConverter` instances are cached on `app.state` at startup:
   - `converter_ocr`: uses `EasyOcrOptions(lang=["en"], use_gpu=False, force_full_page_ocr=True)` via `PdfPipelineOptions` — for scanned/image PDFs
   - `converter_text`: plain `DocumentConverter()` with no OCR overhead — for digital-native PDFs

3. **EasyOCR pre-warming** in lifespan via `easyocr.Reader(["en"], gpu=False)` to trigger model download before first request (Research Pitfall 4).

4. **Port 8001** (core-api uses 8000 — no collision).

5. **7 unit tests** passing in tests/phase04/ using sys.modules stubs for docling/easyocr/cv2 — no ML dependencies needed in dev environment.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| EasyOCR instead of PaddleOCR | PaddleOCR is not a native Docling OCR backend. EasyOCR is Docling's supported backend and satisfies DOCP-02 (accurate OCR for scanned documents). |
| opencv-python-headless | Avoids libGL requirement absent in python:3.11-slim images (Research Pitfall 1). |
| 120s HEALTHCHECK start-period | Docling + EasyOCR model loading takes longer than core-api's 30s on first boot. |
| Dual converter cached on app.state | Avoids re-initialising pipeline options per request; selection is O(1) based on ocr_enabled flag. |
| sys.modules stub injection in conftest | Dev machine runs Python 3.14 without ML deps; stubs allow full test coverage without installation. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestClient fixture: patch.object(app, "state") approach did not work**
- **Found during:** Task 2 test execution
- **Issue:** `patch.object(app, "state")` creates a MagicMock but the lifespan inside TestClient startup runs and sets real (stubbed) converters on the actual `app.state`, overwriting the patch. The test saw 0 pages because the mock converter's `convert()` was not called.
- **Fix:** Changed test fixtures to let lifespan run (with `easyocr` module patched to skip model download), then mutate `app.state.converter_ocr` and `app.state.converter_text` directly after TestClient starts. Consistent pattern across both test files.
- **Files modified:** tests/phase04/test_docling_pipeline.py, tests/phase04/test_ocr_processing.py
- **Commits:** e721314 (included in Task 2 commit after fix)

## Known Stubs

None — all endpoints are fully wired. The app.state converters are real Docling/EasyOCR objects in production (stubbed only in test context).

## Verification Results

```
7 passed in 0.24s
syntax ok (ast.parse on main.py and logging_config.py)
```

All acceptance criteria met:
- src/docproc/ has Dockerfile, main.py, pyproject.toml, logging_config.py
- POST /process accepts file_path and ocr_enabled, returns structured text with page metadata
- EasyOCR pre-warmed in lifespan
- Dockerfile on python:3.11-slim with 120s health check start-period
- No reference to PaddleOcrOptions (which does not exist in Docling)
- Wave 0 tests for DOCP-01 and DOCP-02 pass with mocked dependencies
