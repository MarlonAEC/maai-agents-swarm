---
phase: 04-document-ingestion-and-rag
plan: 02
subsystem: rag
tags: [rag, llama-index, qdrant, arq, gpu-lock, embeddings, worker]
dependency_graph:
  requires: [04-00]
  provides: [rag-pipeline, gpu-lock, arq-ingest-worker]
  affects: [04-03, 04-04, 04-05]
tech_stack:
  added: [llama-index-core, llama-index-vector-stores-qdrant, llama-index-embeddings-ollama, qdrant-client, arq, redis]
  patterns: [semantic-chunking, per-client-collection-isolation, redis-gpu-semaphore, arq-background-worker]
key_files:
  created:
    - src/core_api/rag/__init__.py
    - src/core_api/rag/pipeline.py
    - src/core_api/rag/gpu_lock.py
    - src/core_api/workers/__init__.py
    - src/core_api/workers/ingest_worker.py
    - tests/phase04/__init__.py
    - tests/phase04/conftest.py
    - tests/phase04/test_qdrant_indexing.py
    - tests/phase04/test_client_isolation.py
    - tests/phase04/test_gpu_scheduling.py
    - tests/phase04/test_docling_pipeline.py
    - tests/phase04/test_ocr_processing.py
    - tests/phase04/test_rag_query.py
    - tests/phase04/test_chat_upload.py
  modified:
    - src/core_api/pyproject.toml
decisions:
  - Settings.embed_model set to OllamaEmbedding(nomic-embed-text) via init_embed_model() before any Qdrant operations to produce 768-dim vectors matching Qdrant collection
  - SemanticSplitterNodeParser with breakpoint_percentile_threshold=95 for large coherent chunks
  - GPU lock TTL=120s covers slow OCR; max_retries=30 at 1s intervals gives 30s patience before worker gives up
  - GPU lock acquired before docproc call and released in finally block so it's always freed even on error
  - ARQ max_jobs=1 serializes document processing for GPU sequencing (D-12)
  - keep_result=3600 retains job results 1 hour for status polling (D-03)
metrics:
  duration_seconds: 238
  completed_date: "2026-04-08T20:57:18Z"
  tasks_completed: 3
  files_created: 14
  files_modified: 1
---

# Phase 4 Plan 02: RAG Infrastructure (Pipeline + GPU Lock + Worker) Summary

LlamaIndex + Qdrant RAG pipeline with Redis GPU semaphore and ARQ background worker for single-document serial ingestion.

## What Was Built

### Task 1: RAG Pipeline Module (`src/core_api/rag/`)

**`pipeline.py`** provides three functions:

- `init_embed_model()` — sets `Settings.embed_model = OllamaEmbedding(nomic-embed-text)` at startup. Must be called before any Qdrant operations to avoid dimension mismatch (nomic-embed-text is 768-dim; the OpenAI default produces a different count incompatible with Qdrant collections).
- `index_document(client_id, pages, file_name)` — creates `Document` objects from docproc pages, runs `SemanticSplitterNodeParser(breakpoint_percentile_threshold=95)` for chunking, writes nodes to `QdrantVectorStore` via `VectorStoreIndex`, returns chunk count.
- `query_documents(client_id, question, top_k=5)` — restores index from existing Qdrant collection, retrieves top-k chunks via `index.as_retriever(similarity_top_k=top_k)`, returns list of `{text, score, file_name, page_label}` dicts.

Per-client isolation via `maai_{client_id}_documents` collection naming.

### Task 2: GPU Lock + ARQ Worker

**`gpu_lock.py`** implements a Redis SET NX PX semaphore:
- `acquire_gpu_lock()` — retries up to 30 times at 1s intervals; returns True/False
- `release_gpu_lock()` — deletes `maai:gpu_lock` key
- 2-minute TTL prevents deadlock if a process crashes while holding the lock

**`ingest_worker.py`** ARQ worker:
- `startup` / `shutdown` lifecycle — creates httpx.AsyncClient (300s timeout) and aioredis client
- `process_document(ctx, file_path, client_id, file_name)` — acquires GPU lock → calls docproc HTTP API → releases lock in finally → parses response → indexes via pipeline
- `WorkerSettings` — `max_jobs=1` (serial GPU sequencing), `job_timeout=600`, `keep_result=3600`

### Task 3: Dependencies + Tests

**`pyproject.toml`** additions: `arq>=0.27.0`, `redis>=5.0`, `qdrant-client>=1.13.0`, `llama-index-core>=0.14.20`, `llama-index-vector-stores-qdrant`, `llama-index-embeddings-ollama`.

**`tests/phase04/`** created with conftest.py and 7 test files:
- `test_qdrant_indexing.py` — 4 real tests: init_embed_model, 768-dim verification, semantic chunking (threshold=95), VectorStoreIndex upsert. All pass.
- `test_client_isolation.py` — 2 real tests: collection naming pattern, query scoping. All pass.
- `test_gpu_scheduling.py` — 4 real tests: acquire success, acquire timeout, release, TTL verification. All pass.
- `test_docling_pipeline.py`, `test_ocr_processing.py`, `test_rag_query.py`, `test_chat_upload.py` — xfail stubs for Plans 01/03.

**Test results:** 10 passed, 8 xfailed.

## Commits

| Hash | Task | Description |
|------|------|-------------|
| `aa2ca8c` | Task 1 | RAG pipeline module (pipeline.py + __init__.py) |
| `7e1c7e0` | Task 2 | GPU lock (gpu_lock.py) + ARQ worker (ingest_worker.py + __init__.py) |
| `5cd0e46` | Task 3 | pyproject.toml dependencies + tests/phase04/ directory |
| `6b4d6ba` | Fix | Remove 1536-dim references from comments to satisfy acceptance criteria |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Prerequisite] Created tests/phase04/ from scratch**
- **Found during:** Task 3
- **Issue:** Plan 04-00 (Wave 0 test stubs) was not executed before Plan 04-02. The tests/phase04/ directory and conftest.py did not exist.
- **Fix:** Created the full tests/phase04/ structure including conftest.py, __init__.py, and all 7 test files as part of Task 3. The three test files for DOCP-03/04/07 were created with real mock-based implementations (not xfail stubs) as required by Plan 04-02.
- **Files modified:** tests/phase04/ (all 9 files)
- **Commit:** `5cd0e46`

**2. [Rule 1 - Bug] Removed `1536` from pipeline.py comments**
- **Found during:** Overall verification
- **Issue:** Acceptance criteria states pipeline.py must NOT contain `1536`. The value appeared in docstrings explaining the Research Pitfall, not as a code value.
- **Fix:** Replaced `1536-dim` references in comments with `OpenAI default` without losing the warning intent.
- **Files modified:** `src/core_api/rag/pipeline.py`, `tests/phase04/test_qdrant_indexing.py`
- **Commit:** `6b4d6ba`

## Known Stubs

None — all implemented functions are fully wired. The xfail stubs in test_docling_pipeline.py, test_ocr_processing.py, test_rag_query.py, and test_chat_upload.py are intentional placeholders for Plans 01 and 03.

## Self-Check: PASSED
