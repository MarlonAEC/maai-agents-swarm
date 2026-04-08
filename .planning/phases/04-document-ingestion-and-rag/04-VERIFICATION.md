---
phase: 04-document-ingestion-and-rag
verified: 2026-04-08T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Upload a PDF in Open WebUI chat and confirm the pipeline saves it to /app/uploads and the document_ingest skill queues an ARQ job"
    expected: "User sees a job ID returned in chat; background worker processes the file and indexes chunks into Qdrant"
    why_human: "Requires a running Docker stack with Ollama, Qdrant, Redis, docproc, ingest-worker, and Open WebUI — cannot verify programmatically"
  - test: "Ask 'what does my document say about X?' in Open WebUI after indexing"
    expected: "ask_documents skill triggers, QdrantSearchTool retrieves chunks, answer includes 'Source: filename.pdf, page N' citations"
    why_human: "Requires live Qdrant collection with indexed data and an LLM via LiteLLM — end-to-end flow cannot be run in a dry check"
  - test: "Start a heavy LLM inference chat request, then immediately upload a document; confirm the ingest worker waits for the lock"
    expected: "GPU lock prevents concurrent VRAM use; ingest worker retries until LLM inference completes before starting EasyOCR"
    why_human: "Requires concurrent workloads on a GPU-enabled host to observe sequencing behavior"
---

# Phase 4: Document Ingestion and RAG — Verification Report

**Phase Goal:** Document ingestion and RAG pipeline — users can upload documents, have them processed and indexed, then query them through chat.
**Verified:** 2026-04-08
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /process accepts a file path and returns extracted text with page metadata | VERIFIED | `src/docproc/main.py` — full implementation: validates path, delegates to Docling converter, builds `PageResult` list, returns `ProcessResponse` with pages + full_text |
| 2 | Scanned PDFs are OCR-processed via EasyOCR (satisfies DOCP-02) | VERIFIED | `EasyOcrOptions` instantiated with `force_full_page_ocr=True`, pre-warm at startup via `easyocr.Reader` — note: EasyOCR used instead of PaddleOCR per RESEARCH.md finding (see Requirements Coverage note) |
| 3 | Text PDFs are extracted without OCR overhead | VERIFIED | Dual converters — `converter_text = DocumentConverter()` (no OCR) and `converter_ocr` — selected by `ocr_enabled` flag |
| 4 | LlamaIndex pipeline chunks documents and stores embeddings in Qdrant | VERIFIED | `src/core_api/rag/pipeline.py` — `SemanticSplitterNodeParser` + `QdrantVectorStore` + `VectorStoreIndex` — complete implementation, 153 lines |
| 5 | Each client gets an isolated Qdrant collection (`maai_{client_id}_documents`) | VERIFIED | `_collection_name(client_id)` returns `f"maai_{client_id}_documents"` — used in both `index_document` and `query_documents` |
| 6 | `Settings.embed_model` set to OllamaEmbedding before any Qdrant operations | VERIFIED | `init_embed_model()` called in `main.py` lifespan before any routes handle requests; function explicitly sets `Settings.embed_model` |
| 7 | ARQ worker processes documents one at a time (`max_jobs=1`) | VERIFIED | `WorkerSettings.max_jobs = 1` in `src/core_api/workers/ingest_worker.py` |
| 8 | GPU lock prevents concurrent GPU workloads | VERIFIED | `acquire_gpu_lock` wraps the docproc HTTP call; `release_gpu_lock` called in `finally` block |
| 9 | User can trigger document ingestion via a skill in chat | VERIFIED | `clients/default/skills/document_ingest.yaml` — triggers include "index this document", uses `call_ingest` tool |
| 10 | User can ask questions about indexed documents via a dedicated RAG skill | VERIFIED | `clients/default/skills/ask_documents.yaml` — triggers include "what do my documents say about", uses `qdrant_search` tool |
| 11 | RAG answers include document name and page number citations | VERIFIED | `QdrantSearchTool._run` formats: `Source: {r['file_name']}, page {r['page_label']}` |
| 12 | Redis, Qdrant, docproc, and ingest-worker services wired in Docker Compose | VERIFIED | All four services present in `docker-compose.yml` with persistent volumes (`qdrant-data`, `redis-data`), health checks, and `maai-net` network |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Notes |
|----------|-----------|--------------|--------|-------|
| `tests/phase04/__init__.py` | — | exists | VERIFIED | Empty package init |
| `tests/phase04/conftest.py` | 30 | 166 | VERIFIED | MagicMock stubs for docling, qdrant_client, llama_index, arq, redis |
| `tests/phase04/test_docling_pipeline.py` | 30 | 200 | VERIFIED | No xfail stubs remain |
| `tests/phase04/test_ocr_processing.py` | 20 | 170 | VERIFIED | No xfail stubs remain |
| `tests/phase04/test_qdrant_indexing.py` | 40 | 181 | VERIFIED | Imports from `rag.pipeline` confirmed |
| `tests/phase04/test_client_isolation.py` | 20 | 92 | VERIFIED | Tests `_collection_name` directly |
| `tests/phase04/test_rag_query.py` | 30 | 77 | VERIFIED | No xfail stubs remain |
| `tests/phase04/test_chat_upload.py` | 30 | 162 | VERIFIED | Imports `CallIngestTool`, `JobStatusTool` |
| `tests/phase04/test_gpu_scheduling.py` | 30 | 133 | VERIFIED | Tests acquire/release/timeout behavior |
| `src/docproc/Dockerfile` | — | exists | VERIFIED | `FROM python:3.11-slim` confirmed |
| `src/docproc/main.py` | 80 | 234 | VERIFIED | Exports `app`, full implementation |
| `src/docproc/pyproject.toml` | — | exists | VERIFIED | Contains `docling>=2.85.0`, `easyocr` |
| `src/docproc/logging_config.py` | — | exists | VERIFIED | Exports `get_logger` |
| `src/core_api/rag/pipeline.py` | 60 | 153 | VERIFIED | Exports `init_embed_model`, `index_document`, `query_documents` |
| `src/core_api/rag/gpu_lock.py` | 20 | 60 | VERIFIED | Exports `acquire_gpu_lock`, `release_gpu_lock` |
| `src/core_api/workers/ingest_worker.py` | 50 | 146 | VERIFIED | Exports `WorkerSettings`, `max_jobs=1` |
| `src/core_api/pyproject.toml` | — | exists | VERIFIED | Contains `arq>=0.27.0` |
| `src/core_api/tools/qdrant_search_tool.py` | 30 | 49 | VERIFIED | Exports `QdrantSearchTool` |
| `src/core_api/tools/job_status_tool.py` | 25 | 68 | VERIFIED | Exports `JobStatusTool` |
| `src/core_api/tools/call_ingest_tool.py` | 25 | 66 | VERIFIED | Exports `CallIngestTool` |
| `src/core_api/routers/ingest.py` | 30 | 86 | VERIFIED | POST /ingest queues ARQ jobs |
| `src/core_api/agents/rag_crew.py` | 40 | 78 | VERIFIED | Exports `run_rag_crew` |
| `clients/default/skills/document_ingest.yaml` | — | exists | VERIFIED | Contains `call_ingest` in tools list |
| `clients/default/skills/ask_documents.yaml` | — | exists | VERIFIED | Contains `qdrant_search` in tools list |
| `docker-compose.yml` (updated) | — | exists | VERIFIED | Contains `qdrant`, `redis`, `docproc`, `ingest-worker` services |
| `clients/default/client.env` (updated) | — | exists | VERIFIED | Contains `REDIS_HOST`, `QDRANT_HOST`, `DOCPROC_URL` |

---

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `src/docproc/main.py` | `Docling DocumentConverter` | import + instantiation | WIRED | Line 24: `from docling.document_converter import DocumentConverter`; Lines 90, 97: two converters created in lifespan |
| `src/docproc/main.py` | `EasyOcrOptions` | OCR configuration | WIRED | Line 23: `from docling.datamodel.pipeline_options import EasyOcrOptions`; Line 84: `EasyOcrOptions(lang=["en"], ...)` |
| `src/core_api/workers/ingest_worker.py` | `src/core_api/rag/pipeline.py` | `index_document` call | WIRED | Line 22: `from rag.pipeline import index_document`; Line 113: `index_document(client_id=..., pages=..., file_name=...)` |
| `src/core_api/rag/pipeline.py` | Qdrant | `QdrantVectorStore` + `VectorStoreIndex` | WIRED | Line 17: import; Lines 96, 129: `QdrantVectorStore` constructed; result returned from `query_documents` |
| `src/core_api/workers/ingest_worker.py` | `src/core_api/rag/gpu_lock.py` | `acquire_gpu_lock` around docproc call | WIRED | Line 21: import; Line 79: `acquired = await acquire_gpu_lock(ctx["redis"])`; Line 102: `release_gpu_lock` in `finally` |
| `src/core_api/tools/qdrant_search_tool.py` | `src/core_api/rag/pipeline.py` | `query_documents` call | WIRED | Line 10: `from rag.pipeline import query_documents`; Line 39: called with `client_id` and `query` |
| `src/core_api/tools/call_ingest_tool.py` | `src/core_api/routers/ingest.py` | HTTP POST to `/ingest` | WIRED | Line 41: `ingest_url = f"http://localhost:{...}/ingest"`; Lines 44-48: `httpx.Client.post(ingest_url, ...)` |
| `src/core_api/routers/ingest.py` | ARQ Redis pool | `enqueue_job("process_document", ...)` | WIRED | Line 69: `job = await redis.enqueue_job("process_document", file_path, client_id, file_name)` |
| `clients/default/skills/document_ingest.yaml` | `call_ingest_tool.py` | `tools` list in YAML | WIRED | Line 13: `- call_ingest`; tool name matches `CallIngestTool.name = "call_ingest"` |
| `clients/default/skills/ask_documents.yaml` | `qdrant_search_tool.py` | `tools` list in YAML | WIRED | Line 16: `- qdrant_search`; tool name matches `QdrantSearchTool.name = "qdrant_search"` |
| `docker-compose.yml (ingest-worker)` | `ingest_worker.py WorkerSettings` | arq CLI command | WIRED | Line 250: `command: ["arq", "workers.ingest_worker.WorkerSettings"]` |
| `docker-compose.yml (docproc)` | `src/docproc/Dockerfile` | build context | WIRED | `build: context: ./src/docproc` confirmed |
| `docker-compose.yml (core-api)` | redis, qdrant | `depends_on` | WIRED | Lines 152-155: `depends_on: redis: condition: service_healthy; qdrant: condition: service_healthy` |
| `src/core_api/main.py` | `rag/pipeline.init_embed_model` | lifespan call before routes | WIRED | Line 28: import; Lines 63-67: `init_embed_model()` called in lifespan |
| `src/core_api/main.py` | `routers/ingest.router` | `include_router` | WIRED | Line 30: import; Line 82: `app.include_router(ingest_router)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `QdrantSearchTool._run` | `results` | `query_documents()` → `QdrantVectorStore` → Qdrant gRPC | Yes — retriever returns live scored nodes from vector DB | FLOWING |
| `ingest_worker.process_document` | `resp_data` | HTTP POST to docproc `/process` → Docling converter | Yes — Docling iterates document elements and builds page list | FLOWING |
| `routers/ingest.py` | `job_id` | `redis.enqueue_job(...)` returns ARQ `Job` | Yes — ARQ assigns UUID job ID from Redis | FLOWING |
| `pipeline.query_documents` | `raw_nodes` | `retriever.retrieve(question)` on `VectorStoreIndex.from_vector_store` | Yes — retrieval against live Qdrant collection | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Method | Result | Status |
|----------|--------|--------|--------|
| `pipeline.py` parses cleanly | `ast.parse()` | No errors | PASS |
| `ingest_worker.py` parses cleanly | `ast.parse()` | No errors | PASS |
| `qdrant_search_tool.py` parses cleanly | `ast.parse()` | No errors | PASS |
| `routers/ingest.py` parses cleanly | `ast.parse()` | No errors | PASS |
| `docproc/main.py` parses cleanly | `ast.parse()` | No errors | PASS |
| `gpu_lock.py` parses cleanly | `ast.parse()` | No errors | PASS |
| `rag_crew.py` parses cleanly | `ast.parse()` | No errors | PASS |
| No xfail stubs in test files | AST decorator scan | 0 xfail decorators found in test_docling_pipeline, test_gpu_scheduling, test_qdrant_indexing, test_chat_upload | PASS |
| All logging via `get_logger` (not print/console) | `grep from logging_config` | All 7 implementation files use `from logging_config import get_logger` | PASS |

---

### Requirements Coverage

| Requirement | Description | Plans | Status | Evidence |
|-------------|-------------|-------|--------|----------|
| DOCP-01 | PDF text extraction via Docling | 00, 01, 05 | SATISFIED | `src/docproc/main.py` — `DocumentConverter` processes PDF/image files, returns page-level text |
| DOCP-02 | OCR for scanned documents | 00, 01, 05 | SATISFIED (with deviation) | Implemented via EasyOCR, not PaddleOCR. RESEARCH.md documents that PaddleOCR is not a native Docling backend. EasyOCR satisfies the functional requirement. REQUIREMENTS.md wording ("via PaddleOCR") is technically stale but the requirement intent is met. |
| DOCP-03 | Document chunking and embedding via LlamaIndex | 00, 02, 03, 05 | SATISFIED | `pipeline.py` — `SemanticSplitterNodeParser` + `OllamaEmbedding(nomic-embed-text)` |
| DOCP-04 | Vector storage in Qdrant with persistent volumes | 00, 02, 04, 05 | SATISFIED | `QdrantVectorStore` in pipeline; `qdrant-data` named volume in docker-compose.yml |
| DOCP-05 | Per-client RAG knowledge base (isolated collections) | 00, 02, 04, 05 | SATISFIED | `_collection_name(client_id)` → `maai_{client_id}_documents`; used consistently in index and query |
| DOCP-06 | User can ask questions about indexed documents via chat | 00, 03, 05 | SATISFIED | `ask_documents.yaml` skill + `qdrant_search` tool + `QdrantSearchTool` chain complete |
| DOCP-07 | GPU workloads sequenced (LLM inference and OCR not concurrent) | 00, 02, 04, 05 | SATISFIED | `gpu_lock.py` Redis semaphore; `acquire_gpu_lock` wraps docproc call in `ingest_worker.py` `finally` block ensures release |

**DOCP-02 Note:** REQUIREMENTS.md states "OCR for scanned documents via PaddleOCR." The implementation uses EasyOCR because PaddleOCR is not a native Docling OCR backend (documented in RESEARCH.md and noted in Plan 01 objective). The functional requirement is met. REQUIREMENTS.md should be updated to reflect "EasyOCR" rather than "PaddleOCR" in a future housekeeping pass — this is a documentation gap, not an implementation gap.

---

### Anti-Patterns Found

| File | Pattern Checked | Result | Severity |
|------|----------------|--------|----------|
| All 7 implementation source files | `TODO`, `FIXME`, `HACK`, `placeholder` | None found | — |
| All 7 implementation source files | `return null`, `return []`, `return {}` empty stubs | None found | — |
| All 7 test files | Remaining `xfail` decorators | 0 found (Wave 0 stubs all replaced) | — |
| All implementation files | `console.log` / `print` used instead of logger | None found — all use `get_logger` | — |
| `src/core_api/tools/call_ingest_tool.py` | Synchronous `httpx.Client` in a tool `_run` method | Uses `httpx.Client` (sync) deliberately — `_run` is a synchronous CrewAI tool method, not an async handler. Acceptable pattern here. | INFO only |

No blockers. No warnings.

---

### Human Verification Required

#### 1. End-to-End Document Upload and Ingest

**Test:** Open the Open WebUI chat interface. Upload a PDF via the file attachment button and then type "index this document". Observe the response.
**Expected:** The `document_ingest` skill triggers, `CallIngestTool` POSTs to `/ingest`, the endpoint returns a job ID, and the user sees a confirmation message with the job ID.
**Why human:** Requires a running Docker stack with all services healthy. Cannot verify HTTP routing through Open WebUI → Pipelines → core-api → Redis without a live environment.

#### 2. RAG Query with Citations

**Test:** After indexing a document (above), type "what does my document say about [topic]?" in chat.
**Expected:** The `ask_documents` skill triggers, `QdrantSearchTool` retrieves chunks, and the response ends with "Source: filename.pdf, page N" citations.
**Why human:** Requires a live Qdrant collection with indexed data and LLM inference via LiteLLM — cannot simulate the full retrieval + generation loop programmatically.

#### 3. GPU Lock Sequencing Under Concurrent Load

**Test:** Start a large LLM reasoning task in chat (to hold the GPU), then immediately trigger document ingestion.
**Expected:** The ingest worker's ARQ job waits for the GPU lock (up to 30 retries × 1s = 30s), then acquires it and runs EasyOCR after the LLM finishes.
**Why human:** Requires a GPU-enabled host with concurrent workloads. The sequencing logic is verified at code level; the temporal behavior needs live observation.

---

## Gaps Summary

No gaps found. All 12 truths are verified, all artifacts are substantive and wired, all key links confirmed present, and both YAML skill files correctly reference tool names that match their respective tool class `name` attributes.

One documentation discrepancy exists: REQUIREMENTS.md DOCP-02 says "PaddleOCR" but implementation uses EasyOCR by documented design choice. This is a requirements doc staleness issue, not an implementation gap, and does not block the phase goal.

---

_Verified: 2026-04-08_
_Verifier: Claude (gsd-verifier)_
