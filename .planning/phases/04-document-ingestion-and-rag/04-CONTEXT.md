# Phase 4: Document Ingestion and RAG - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Full document ingestion pipeline: users upload PDFs (text and scanned/image-only) in chat, the system processes them via Docling + PaddleOCR in a background queue, chunks and embeds the content via LlamaIndex, and stores vectors in a per-client Qdrant collection. Users can then ask questions about their indexed documents via a dedicated RAG skill and receive answers with document + page citations. GPU workloads (LLM inference and OCR) are sequenced to prevent VRAM starvation.

This phase does NOT include: DOCX/PPTX/HTML ingestion (future enhancement), file classification/organization (Phase 5), email integration (Phase 5), spreadsheet generation (Phase 5), folder watching/auto-ingestion (v2), or admin UI for knowledge base management.

</domain>

<decisions>
## Implementation Decisions

### Ingestion Pipeline
- **D-01:** Document processing runs in a **background queue** using Redis + ARQ. Upload returns immediately with an acknowledgment and job ID. Background worker runs the Docling -> PaddleOCR (if needed) -> LlamaIndex chunking -> Qdrant embedding pipeline.
- **D-02:** Ingestion is **triggered via a skill** (e.g., `document_ingest`). User uploads a file in chat and says "index this document" or similar. The Skill Matcher routes to the ingestion skill, which queues the ARQ job. Also supports "index all files in folder X".
- **D-03:** Processing status is **poll-based**. User can ask "what's the status of my document?" and a status-check tool queries the ARQ job state. Initial acknowledgment includes the job ID.
- **D-04:** Phase 4 supports **PDF and images only**. Text PDFs processed by Docling; scanned/image-only PDFs processed by Docling with PaddleOCR as the OCR backend. Additional formats (DOCX, PPTX, HTML) deferred to future work.

### RAG Query Integration
- **D-05:** Users query indexed documents via a **dedicated RAG skill** (e.g., `ask_documents` / `search_knowledge_base`). The Skill Matcher routes document-related questions to this skill. Clear separation from freeform chat.
- **D-06:** RAG answers include **document + page reference citations** at the end of the response (e.g., "Source: document_name.pdf, page 3-4"). LlamaIndex chunk metadata provides source file and page number.
- **D-07:** Document chunking uses **LlamaIndex SemanticSplitterNodeParser** — splits on meaning boundaries rather than fixed character counts. Uses the embedding model (nomic-embed-text) to detect topic shifts. Better retrieval for mixed-content documents.
- **D-08:** Retrieval returns **top 5 chunks** by similarity score, injected as context into the RAG agent's prompt. Count is configurable via skill YAML and can be tuned later.

### Container Architecture
- **D-09:** Docling and PaddleOCR run in a **single `docproc` sidecar container** with a lightweight FastAPI service. Docling already integrates PaddleOCR as an OCR backend. One container, one health check, simpler topology.
- **D-10:** Core API communicates with docproc via **HTTP API** (e.g., POST /process). ARQ worker sends the file path (from maai-uploads shared volume) via HTTP to docproc. Clean interface, easy to test, follows existing service-to-service pattern on maai-net.
- **D-11:** **Qdrant and Redis** are both added to docker-compose.yml in this phase. Qdrant for vector storage (DOCP-04/05), Redis as ARQ broker. Both get named volumes for persistence and join maai-net.

### GPU Sequencing
- **D-12:** GPU workloads sequenced via an **application-level semaphore** (Redis-based distributed lock). Before LLM inference or OCR, the process acquires the lock. Only one GPU workload runs at a time. ARQ worker respects the same lock.
- **D-13:** **Chat (LLM inference) has priority** over document processing. If a user sends a message while OCR is running, the chat request gets priority. User-facing responsiveness matters more than background processing speed.

### Claude's Discretion
- ARQ worker configuration details (concurrency, retry policy, job timeout)
- Docproc FastAPI endpoint design (request/response schemas, error handling)
- LlamaIndex pipeline assembly details (node parsers, index type, query engine config)
- Qdrant collection schema and naming convention for per-client isolation
- Redis configuration (persistence, memory limits)
- Exact semaphore/lock implementation (asyncio vs Redis-based)
- Skill YAML content for document_ingest and ask_documents skills
- How "index all files in folder X" maps to multiple ARQ jobs
- Docproc container base image and dependency installation approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Documentation
- `.planning/PROJECT.md` -- Project vision, constraints, key decisions (Docling, PaddleOCR, LlamaIndex, Qdrant chosen)
- `.planning/REQUIREMENTS.md` -- DOCP-01 through DOCP-07 acceptance criteria
- `.planning/ROADMAP.md` -- Phase 4 success criteria and dependencies
- `CLAUDE.md` -- Technology stack, version compatibility, model recommendations

### Prior Phase Artifacts
- `.planning/phases/01-infrastructure-foundation/01-CONTEXT.md` -- Service topology, Docker network (maai-net), client config layout, model bootstrapping (nomic-embed-text)
- `.planning/phases/02-core-api-and-end-to-end-chat/02-CONTEXT.md` -- Core API architecture, maai-uploads volume (D-14/D-15), in-process CrewAI pattern, "add task queuing in Phase 4+" (D-11)
- `.planning/phases/03-tool-system-and-skills/03-CONTEXT.md` -- Tool plugin architecture (BaseTool in src/core_api/tools/), skill YAML format, Skill Matcher routing, tool allowlist

### Existing Code
- `src/core_api/routers/chat.py` -- Chat endpoint with skill routing (integration point for RAG skill)
- `src/core_api/skills/executor.py` -- Skill execution pattern (how skills run)
- `src/core_api/skills/matcher.py` -- Skill Matcher (routes user messages to skills)
- `src/core_api/skills/models.py` -- Skill data models and RoutingDecision enum
- `src/core_api/skills/registry.py` -- Skill registry (auto-discovery of YAML skill files)
- `src/core_api/skills/tool_registry.py` -- Tool registry (discovers BaseTool plugins)
- `src/core_api/tools/echo_tool.py` -- Example tool plugin (pattern to follow for new tools)
- `src/core_api/agents/freeform_crew.py` -- CrewAI crew pattern, LLM routing via LiteLLM, Ollama embedder config
- `src/core_api/main.py` -- FastAPI app entrypoint with lifespan initialization
- `docker-compose.yml` -- Current Docker stack (extend with docproc, qdrant, redis)
- `config/litellm/proxy_config.yaml` -- LiteLLM model aliases (embedding-model for nomic-embed-text)
- `clients/default/client.env` -- Current client config variables

### Technology References (from CLAUDE.md)
- Docling >= 2.84.0 with Python >= 3.10
- PaddleOCR >= 3.0 (PP-OCRv5) with paddlepaddle CPU or GPU variant
- LlamaIndex core >= 0.14.20, llama-index-vector-stores-qdrant for Qdrant integration
- Qdrant >= 1.13.x, single Docker container, REST + gRPC API
- Redis 7.x Docker image for ARQ broker
- ARQ >= 0.26.x async task queue
- nomic-embed-text embedding model (already pulled via Ollama bootstrap)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FreeformCrew` class (`src/core_api/agents/freeform_crew.py`) -- Pattern for assembling CrewAI crews with LLM routing through LiteLLM and Ollama embedder. RAG skill crew follows this pattern.
- `echo_tool.py` (`src/core_api/tools/echo_tool.py`) -- Template for creating new CrewAI BaseTool subclasses. New tools (qdrant_search, docling_extract, job_status) follow this pattern.
- Skill YAML auto-discovery (`src/core_api/skills/registry.py`) -- Drop-in skill files for document_ingest and ask_documents.
- Tool allowlist (`clients/default/tools.yaml`) -- New tools must be added to the allowlist.
- `maai-uploads` volume -- Already mounted in pipelines (write) and core-api (read). Docproc will also mount it.
- `logging_config.get_logger()` -- Established logging pattern for all new modules.

### Established Patterns
- CrewAI `@CrewBase` with YAML config for agent/task definition
- `LLM()` constructor with LiteLLM proxy URL and model alias
- `loop.run_in_executor()` for sync crew execution in async handlers
- Docker Compose profiles (gpu/cpu) for GPU-aware services
- Named volumes for persistence (ollama-models, webui-data, maai-uploads)
- Health checks on all services
- Service-to-service communication via container names on maai-net

### Integration Points
- `/chat` endpoint routes through Skill Matcher -- new skills auto-discoverable
- `clients/<client>/skills/` directory for new skill YAML files (document_ingest, ask_documents)
- `src/core_api/tools/` directory for new tool Python files
- `docker-compose.yml` needs: docproc, qdrant, redis services + volumes
- `clients/default/client.env` needs: Qdrant and Redis connection vars
- ARQ worker needs a new entrypoint/module in core-api

</code_context>

<specifics>
## Specific Ideas

- Background queue with Redis/ARQ was explicitly chosen over synchronous processing to avoid blocking chat during large PDF processing
- Chat priority over document processing -- user-facing responsiveness is more important than background processing speed
- Per-client Qdrant collections for data isolation (DOCP-05) -- critical for multi-client deployments
- Semantic chunking chosen over fixed-size for better retrieval quality on mixed-content documents (text + tables)

</specifics>

<deferred>
## Deferred Ideas

- **DOCX/PPTX/HTML ingestion** -- Docling supports these formats but Phase 4 focuses on PDF + images to keep scope tight. Can be enabled by extending the docproc service later.
- **Auto-ingest on upload** -- Automatically queue any uploaded file for ingestion without explicit command. Simpler UX but less user control. Consider for v2 with folder watching (AUTO-01).
- **Proactive completion notifications** -- System sends a chat message when document processing completes. Requires Open WebUI webhook or push mechanism. Poll-based status chosen for simplicity.
- **Hybrid RAG (auto-inject context)** -- Lightweight Qdrant check on every freeform message, inject context if highly relevant. More seamless but adds latency. Consider after dedicated RAG skill proves the pattern.
- **Inline citations** -- Academic-style [1][2] citations woven into answer text. More complex than document + page reference. Consider if users request it.

</deferred>

---

*Phase: 04-document-ingestion-and-rag*
*Context gathered: 2026-04-08*
