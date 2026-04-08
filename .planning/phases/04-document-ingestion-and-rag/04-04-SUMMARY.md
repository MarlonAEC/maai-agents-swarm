---
phase: 04-document-ingestion-and-rag
plan: 04
subsystem: infra
tags: [docker-compose, redis, qdrant, docproc, arq, ingest-worker, vector-database]

# Dependency graph
requires:
  - phase: 04-01
    provides: docproc service Dockerfile and FastAPI app at port 8001
  - phase: 04-02
    provides: ARQ ingest worker (workers/ingest_worker.py) and pipeline.py using REDIS_HOST/QDRANT_HOST
  - phase: 04-03
    provides: RAG crew and skill YAML using Qdrant collections

provides:
  - Complete Docker Compose stack with Redis, Qdrant, docproc, and ingest-worker services
  - Named volumes for qdrant-data, redis-data, easyocr-models
  - client.env Phase 4 connection variables for Redis, Qdrant, and docproc

affects:
  - phase-05 (email integration — any service adding ARQ jobs will use same redis broker)
  - phase-06 (folder watcher — will queue jobs via same ingest-worker pattern)

# Tech tracking
tech-stack:
  added:
    - redis:7-alpine (Docker image)
    - qdrant/qdrant:v1.13.6 (Docker image)
  patterns:
    - ARQ ingest-worker shares core-api build context, overrides CMD to run arq worker
    - All Phase 4 services join maai-net, use restart:unless-stopped, have health checks
    - Health checks use python/python3 urllib.request pattern matching existing services
    - Named volumes for stateful services (qdrant-data, redis-data, easyocr-models)
    - New services added with depends_on:condition:service_healthy for startup ordering

key-files:
  created: []
  modified:
    - docker-compose.yml
    - clients/default/client.env
    - clients/default/client.env.example

key-decisions:
  - "ingest-worker reuses core-api build context (./src/core_api) to share dependencies — no separate Dockerfile needed"
  - "Qdrant port 6333 exposed via QDRANT_PORT env var for local dev access; internal traffic stays on maai-net"
  - "docproc start_period set to 120s — Docling model loading on cold start takes up to 90s"
  - "DOCPROC_USE_GPU defaults to false in both docker-compose.yml and client.env — EasyOCR GPU requires CUDA, most clients are CPU-only"

patterns-established:
  - "Worker services pattern: share base image build context, override command, inject connection env vars"
  - "All connection vars (REDIS_HOST, QDRANT_HOST, DOCPROC_URL) use Docker service names as hostnames"

requirements-completed: [DOCP-04, DOCP-05, DOCP-07]

# Metrics
duration: 10min
completed: 2026-04-08
---

# Phase 4 Plan 04: Docker Compose Integration Summary

**Redis, Qdrant, docproc, and ARQ ingest-worker wired into Docker Compose with named volumes, health checks, and client.env connection variables completing the Phase 4 deployable stack**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-08T21:05:42Z
- **Completed:** 2026-04-08T21:15:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added 4 new services to docker-compose.yml: redis, qdrant, docproc, ingest-worker — all with health checks, maai-net, and restart policies
- Added 3 named volumes: qdrant-data (vector store persistence), redis-data (ARQ queue persistence), easyocr-models (model cache)
- Updated core-api service with REDIS_HOST, QDRANT_HOST, DOCPROC_URL env vars and redis/qdrant depends_on entries
- Appended all Phase 4 connection variables to client.env and client.env.example

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Redis, Qdrant, docproc, and ingest-worker to docker-compose.yml** - `096a813` (feat)
2. **Task 2: Update client.env with Phase 4 connection variables** - `858547b` (feat)

**Plan metadata:** committed with docs commit below

## Files Created/Modified

- `docker-compose.yml` - Added redis, qdrant, docproc, ingest-worker services; new volumes; core-api env/depends_on updates
- `clients/default/client.env` - Appended Phase 4 block: REDIS_HOST, REDIS_PORT, QDRANT_HOST, QDRANT_PORT, DOCPROC_URL, DOCPROC_USE_GPU
- `clients/default/client.env.example` - Same Phase 4 block with descriptive comment for DOCPROC_USE_GPU

## Decisions Made

- `ingest-worker` reuses the `./src/core_api` build context — shares the same Dockerfile and all Python dependencies as core-api. No separate Dockerfile needed; the `command` override runs `arq workers.ingest_worker.WorkerSettings`.
- Qdrant port 6333 exposed via `${QDRANT_PORT:-6333}` for local development access to the Qdrant dashboard/REST API. Internal container-to-container traffic stays on maai-net.
- `docproc` start_period set to 120s because Docling loads large ML models on cold start — can take 60-90 seconds before the /health endpoint becomes responsive.
- `DOCPROC_USE_GPU=false` as default in both compose and client.env — EasyOCR GPU acceleration requires CUDA; most client desktops will use CPU-only inference. GPU-enabled clients can override in client.env.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. All services use Docker images that pull automatically. DOCPROC_USE_GPU can be toggled in client.env if the client has a CUDA-compatible GPU.

## Next Phase Readiness

- `docker compose up` now starts the complete document ingestion and RAG pipeline
- Phase 4 is fully wired: docproc (Plan 01) + ingest pipeline (Plan 02) + RAG crew (Plan 03) + Docker stack (Plan 04)
- ARQ jobs submitted via core-api ingest router will be picked up by ingest-worker which calls docproc, runs the LlamaIndex pipeline, and writes to Qdrant
- Phase 5 (email integration) can add new ARQ job types to the same redis broker using the established worker pattern

---
*Phase: 04-document-ingestion-and-rag*
*Completed: 2026-04-08*
