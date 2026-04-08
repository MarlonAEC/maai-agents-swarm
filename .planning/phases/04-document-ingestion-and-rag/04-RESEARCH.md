# Phase 4: Document Ingestion and RAG - Research

**Researched:** 2026-04-08
**Domain:** Document processing pipeline, RAG, vector storage, background task queuing, GPU sequencing
**Confidence:** HIGH (most findings verified against official documentation or PyPI registry)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Document processing runs in a background queue using Redis + ARQ. Upload returns immediately with an acknowledgment and job ID. Background worker runs the Docling -> PaddleOCR (if needed) -> LlamaIndex chunking -> Qdrant embedding pipeline.
- **D-02:** Ingestion is triggered via a skill (`document_ingest`). User uploads a file in chat and says "index this document" or similar. The Skill Matcher routes to the ingestion skill, which queues the ARQ job. Also supports "index all files in folder X".
- **D-03:** Processing status is poll-based. User can ask "what's the status of my document?" and a status-check tool queries the ARQ job state. Initial acknowledgment includes the job ID.
- **D-04:** Phase 4 supports PDF and images only. Text PDFs processed by Docling; scanned/image-only PDFs processed by Docling with an OCR backend. Additional formats (DOCX, PPTX, HTML) deferred to future work.
- **D-05:** Users query indexed documents via a dedicated RAG skill (`ask_documents` / `search_knowledge_base`). The Skill Matcher routes document-related questions to this skill. Clear separation from freeform chat.
- **D-06:** RAG answers include document + page reference citations at the end of the response. LlamaIndex chunk metadata provides source file and page number.
- **D-07:** Document chunking uses LlamaIndex `SemanticSplitterNodeParser` — splits on meaning boundaries rather than fixed character counts. Uses the embedding model (nomic-embed-text) to detect topic shifts.
- **D-08:** Retrieval returns top 5 chunks by similarity score, injected as context into the RAG agent's prompt. Count is configurable via skill YAML.
- **D-09:** Docling and OCR processing run in a single `docproc` sidecar container with a lightweight FastAPI service. One container, one health check.
- **D-10:** Core API communicates with docproc via HTTP API (POST /process). ARQ worker sends the file path (from maai-uploads shared volume) via HTTP to docproc.
- **D-11:** Qdrant and Redis are both added to docker-compose.yml in this phase.
- **D-12:** GPU workloads sequenced via an application-level semaphore (Redis-based distributed lock). Only one GPU workload runs at a time.
- **D-13:** Chat (LLM inference) has priority over document processing.

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

### Deferred Ideas (OUT OF SCOPE)

- DOCX/PPTX/HTML ingestion
- Auto-ingest on upload (folder watching, AUTO-01)
- Proactive completion notifications (push/webhook mechanism)
- Hybrid RAG (auto-inject context on every freeform message)
- Inline citations (academic-style [1][2] woven into text)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCP-01 | PDF text extraction and summarization via Docling | Docling 2.85.0 DocumentConverter with PdfPipelineOptions; verified API |
| DOCP-02 | OCR for scanned documents via PaddleOCR | EasyOcrOptions (GPU) or RapidOcrOptions(backend="paddle") — see critical finding below |
| DOCP-03 | Document chunking and embedding via LlamaIndex with local embedding model | SemanticSplitterNodeParser + OllamaEmbedding(nomic-embed-text) — verified |
| DOCP-04 | Vector storage in Qdrant with persistent data volumes | QdrantVectorStore + named Docker volume — verified |
| DOCP-05 | Per-client RAG knowledge base (isolated Qdrant collections) | Separate collection per client_id — appropriate for 2-client scale |
| DOCP-06 | User can ask questions about indexed documents via chat | ask_documents skill + RAG crew with MetadataFilters — verified pattern |
| DOCP-07 | GPU workloads sequenced (LLM and OCR not concurrent) to prevent VRAM starvation | Redis-based distributed lock via arq Redis connection — viable pattern |
</phase_requirements>

---

## Summary

Phase 4 builds a full document ingestion and RAG pipeline: users upload PDFs via chat, a background ARQ worker processes them through Docling (text extraction) and an OCR backend (for scanned pages), LlamaIndex chunks and embeds the text into per-client Qdrant collections, and a dedicated RAG skill answers questions by retrieving relevant chunks.

**Critical finding on OCR:** PaddleOCR is NOT a native Docling OCR backend. Docling's supported OCR backends are: EasyOCR, Tesseract CLI, Tesseract (Python), RapidOCR, and macOS Vision. The decision in CONTEXT.md (D-09: "Docling already integrates PaddleOCR as an OCR backend") is incorrect. The correct approach is to use either `EasyOcrOptions` (uses PyTorch; GPU-aware, 80+ languages) or `RapidOcrOptions(backend="paddle")` (uses PaddlePaddle ONNX models via RapidOCR — this is the PaddlePaddle-backed path that matches the spirit of the original requirement). Recommend `EasyOcrOptions` as the primary backend since it uses PyTorch which is already present for Docling's layout models, avoids an extra dependency (paddlepaddle ONNX), and supports GPU acceleration. CLAUDE.md's recommendation for PaddleOCR accuracy advantages remains valid if using standalone PaddleOCR, but in Docling's context EasyOCR is the practical equivalent.

**Critical finding on vector dimensions:** nomic-embed-text produces **768-dimensional** vectors. LlamaIndex/Qdrant default to 1536 dimensions (OpenAI). You MUST call `Settings.embed_model` globally with the OllamaEmbedding instance before any collection creation, or the collection will be created with wrong dimensions causing all vector operations to fail.

The overall architecture is straightforward: 3 new services (redis, qdrant, docproc) + 1 ARQ worker process (runs inside core-api container or as a separate service) + 2 new skills (document_ingest, ask_documents) + 3 new tools (docling_extract, qdrant_search, job_status).

**Primary recommendation:** Use EasyOcrOptions for Docling OCR backend; set `Settings.embed_model` globally before any Qdrant collection creation; use separate Qdrant collections per client_id; run ARQ worker as a separate process or service alongside core-api.

---

## Standard Stack

### Core (verified against PyPI registry 2026-04-08)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `docling` | 2.85.0 | PDF/image document parsing, text extraction, table detection | IBM-backed, structured JSON output, layout analysis; latest is 2.85.0 (CLAUDE.md references 2.84.x — safe to use 2.85.0) |
| `easyocr` | latest | OCR backend for Docling scanned pages | GPU-aware PyTorch-based OCR; native Docling backend via `EasyOcrOptions`; shares PyTorch already present in Docling |
| `arq` | 0.27.0 | Async Redis task queue | Async-native, perfect fit for FastAPI; latest is 0.27.0 (CLAUDE.md references 0.26.x) |
| `redis` | 7.x Docker | ARQ broker + GPU lock storage | Lightweight sidecar; ARQ uses it as both queue and result store |
| `qdrant-client` | 1.17.1 | Qdrant vector database client | Official client; latest is 1.17.1 (CLAUDE.md references 1.13.x) |
| `qdrant/qdrant` | 1.17.x Docker | Vector database | Single-binary Docker container, persistent volumes |
| `llama-index-core` | 0.14.20 | RAG pipeline: chunking, embedding, indexing, querying | Verified current version |
| `llama-index-vector-stores-qdrant` | latest | LlamaIndex-Qdrant integration | Correct integration package (not the deprecated import path) |
| `llama-index-embeddings-ollama` | latest | OllamaEmbedding class for nomic-embed-text | Connects LlamaIndex to Ollama embedding endpoint |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `opencv-python-headless` | latest | Dependency for EasyOCR and Docling layout models in Docker | Must use headless variant in Docker to avoid libGL conflicts — do NOT install `opencv-python` |
| `rapidocr-onnxruntime` | latest | Alternative OCR backend via RapidOCR | Use if EasyOCR memory issues arise; install `rapidocr-paddle` for PaddlePaddle ONNX path |
| `httpx` | 0.27.x | HTTP client in ARQ worker for docproc calls | Already in core-api; async-native |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| EasyOcrOptions | RapidOcrOptions(backend="paddle") | RapidOCR uses ONNX runtime, lower memory than EasyOCR; EasyOCR is simpler to configure in Docker |
| Separate collections per client | Single collection + payload filter | Single collection more efficient at scale (1000s of tenants); overkill for 2 clients; separate collections are simpler to implement and enforce isolation guarantees |
| ARQ worker in separate service | ARQ worker in core-api container | Separate service adds Docker complexity; single container is simpler; ARQ CLI command runs as a separate process within the same image |

**Installation for docproc container:**

```bash
uv pip install --system --no-cache \
  "docling>=2.85.0" \
  "easyocr" \
  "opencv-python-headless" \
  "fastapi>=0.115.0" \
  "uvicorn[standard]>=0.29.0" \
  "python-dotenv>=1.0" \
  "httpx>=0.27.0"
```

**Installation additions to core-api:**

```bash
uv pip install --system --no-cache \
  "arq>=0.27.0" \
  "qdrant-client>=1.13.0" \
  "llama-index-core>=0.14.20" \
  "llama-index-vector-stores-qdrant" \
  "llama-index-embeddings-ollama"
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── core_api/
│   ├── agents/
│   │   ├── freeform_crew.py          # existing
│   │   └── rag_crew.py               # NEW: ask_documents skill crew
│   ├── tools/
│   │   ├── echo_tool.py              # existing
│   │   ├── qdrant_search_tool.py     # NEW: vector search
│   │   └── job_status_tool.py        # NEW: ARQ job status check
│   ├── workers/
│   │   └── ingest_worker.py          # NEW: ARQ worker + job functions
│   ├── skills/                       # existing
│   ├── routers/
│   │   ├── chat.py                   # existing
│   │   └── ingest.py                 # NEW: POST /ingest endpoint
│   └── rag/
│       └── pipeline.py               # NEW: LlamaIndex setup helpers
├── docproc/
│   ├── Dockerfile                    # NEW: Docling + EasyOCR container
│   ├── pyproject.toml                # NEW: docproc dependencies
│   └── main.py                       # NEW: FastAPI /process endpoint
clients/
└── default/
    ├── skills/
    │   ├── example_skill.yaml        # existing
    │   ├── document_ingest.yaml      # NEW
    │   └── ask_documents.yaml        # NEW
    └── tools.yaml                    # extend with new tools
```

### Pattern 1: ARQ Worker Definition

**What:** Define async job functions and WorkerSettings; run worker as a separate process via `arq workers.ingest_worker.WorkerSettings`.

**When to use:** All background document processing tasks.

```python
# Source: https://arq-docs.helpmanual.io/
from arq import Worker
from arq.connections import RedisSettings

async def process_document(ctx: dict, file_path: str, client_id: str, job_id: str) -> dict:
    """ARQ job function — first arg is always ctx."""
    logger = get_logger(__name__)
    logger.info("Processing document job_id=%s file_path=%s", job_id, file_path)
    # call docproc via HTTP, then LlamaIndex indexing
    ...
    return {"status": "complete", "chunks": n}

async def startup(ctx: dict) -> None:
    """Called once when worker starts — initialize shared resources."""
    ctx["http_client"] = httpx.AsyncClient()

async def shutdown(ctx: dict) -> None:
    """Called once when worker shuts down — clean up resources."""
    await ctx["http_client"].aclose()

class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings(host="redis", port=6379)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 1          # one document at a time (GPU sequencing)
    job_timeout = 300     # 5 minutes max per document
    keep_result = 3600    # keep results 1 hour for status polling
```

### Pattern 2: Enqueueing Jobs from FastAPI

**What:** Create a Redis pool in the FastAPI endpoint and call `enqueue_job`.

```python
# Source: https://arq-docs.helpmanual.io/
from arq import create_pool
from arq.connections import RedisSettings

@router.post("/ingest")
async def ingest_document(request: IngestRequest) -> IngestResponse:
    redis = await create_pool(RedisSettings(host="redis", port=6379))
    job = await redis.enqueue_job(
        "process_document",
        file_path=request.file_path,
        client_id=request.client_id,
        job_id=str(uuid.uuid4()),
    )
    await redis.close()
    return IngestResponse(job_id=job.job_id, status="queued")
```

### Pattern 3: LlamaIndex Pipeline with Qdrant

**What:** Set the global embed_model BEFORE any collection interaction, then use VectorStoreIndex.

**Critical:** `Settings.embed_model` must be set before calling `VectorStoreIndex.from_documents()` or the Qdrant collection will be created with 1536 dimensions (OpenAI default) instead of 768 (nomic-embed-text).

```python
# Source: https://developers.llamaindex.ai/python/examples/vector_stores/qdrantindexdemo/
from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

# MUST set globally before any vector store operations
embed_model = OllamaEmbedding(
    model_name="nomic-embed-text",
    base_url="http://ollama:11434",
)
Settings.embed_model = embed_model

# Semantic splitter uses the same embed_model
splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=embed_model,
)

# Per-client collection naming
collection_name = f"maai_{client_id}_documents"

client = qdrant_client.QdrantClient(host="qdrant", port=6333)
vector_store = QdrantVectorStore(
    client=client,
    collection_name=collection_name,
)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Ingest documents
nodes = splitter.get_nodes_from_documents(documents)
index = VectorStoreIndex(nodes, storage_context=storage_context)
```

### Pattern 4: RAG Query with Citation Metadata

**What:** Query the Qdrant index, retrieve source file and page number from chunk metadata.

```python
# Source: https://developers.llamaindex.ai/python/examples/vector_stores/qdrantindexdemo/
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores.types import MetadataFilters, ExactMatchFilter

# Restore index from existing collection (no re-indexing needed)
index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

retriever = index.as_retriever(
    similarity_top_k=5,  # D-08: top 5 chunks
    filters=MetadataFilters(
        filters=[ExactMatchFilter(key="client_id", value=client_id)]
    ),
)
nodes = retriever.retrieve(user_question)

# Build citation suffix
citations = []
for node in nodes:
    source = node.metadata.get("file_name", "unknown")
    page = node.metadata.get("page_label", "?")
    citations.append(f"Source: {source}, page {page}")
```

### Pattern 5: Docling Document Processing

**What:** Use DocumentConverter with EasyOcrOptions for scanned PDFs; plain conversion for text PDFs.

```python
# Source: https://www.mintlify.com/docling-project/docling/guides/ocr-configuration
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# For scanned/image PDFs (OCR required)
pipeline_options = PdfPipelineOptions(
    do_ocr=True,
    do_table_structure=True,
    ocr_options=EasyOcrOptions(
        lang=["en"],
        use_gpu=False,   # GPU check done at startup; set True if GPU available
        force_full_page_ocr=True,
    ),
)
converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)
result = converter.convert(file_path)
doc = result.document

# Extract text blocks with page numbers (for LlamaIndex metadata)
for element, level in doc.iterate_items():
    text = element.text if hasattr(element, "text") else ""
    # element.prov[0].page_no gives the page number
```

### Pattern 6: Redis-Based GPU Lock

**What:** Use a Redis SET NX PX (set-if-not-exists with TTL) as a distributed semaphore. ARQ worker's `max_jobs=1` already serializes document jobs; the lock only needs to coordinate with LLM inference in core-api.

```python
# Source: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
import redis.asyncio as aioredis

GPU_LOCK_KEY = "maai:gpu_lock"
GPU_LOCK_TTL_MS = 120_000  # 2 minutes max hold

async def acquire_gpu_lock(redis_client, ttl_ms: int = GPU_LOCK_TTL_MS) -> bool:
    """Try to acquire GPU lock. Returns True if acquired."""
    result = await redis_client.set(GPU_LOCK_KEY, "1", nx=True, px=ttl_ms)
    return result is True

async def release_gpu_lock(redis_client) -> None:
    await redis_client.delete(GPU_LOCK_KEY)
```

**Priority rule (D-13):** The chat handler acquires the lock before calling the LLM. If a document worker holds it, chat waits up to a timeout (e.g., 10s) then proceeds anyway (chat responsiveness over background job speed). Workers acquire the lock before OCR and yield if chat is waiting.

### Anti-Patterns to Avoid

- **Installing opencv-python in Docker:** Always use `opencv-python-headless` in Docker containers. The non-headless version requires libGL (OpenGL) which is not present in slim images and causes ImportError at runtime.
- **Creating Qdrant collections before setting Settings.embed_model:** If LlamaIndex creates the collection before the embedding model is set, it defaults to 1536 dimensions (OpenAI). This causes all subsequent operations to fail with "Bad Request" errors. Always set `Settings.embed_model` at module/application startup.
- **Running ARQ worker with max_jobs > 1 on GPU-constrained hardware:** This allows multiple document processing jobs to run concurrently, causing VRAM starvation. Always set `max_jobs=1` for the ingest worker.
- **Using `asyncio.run()` inside ARQ job functions:** ARQ job functions are already async coroutines running inside an event loop. Calling `asyncio.run()` inside them will raise a RuntimeError. Use `await` directly.
- **Storing maai-uploads paths as absolute host paths in ARQ jobs:** The file path passed to the ARQ job must be the path inside the container (`/app/uploads/...`), not the host path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PyMuPDF pipeline | Docling DocumentConverter | Docling handles layout analysis, table extraction, page structure, and figure detection that raw PyMuPDF misses |
| Semantic chunking | Fixed-size character splitter | SemanticSplitterNodeParser | Fixed chunking splits sentences mid-thought; semantic splitter detects topic boundaries using embeddings |
| Vector similarity search | Manual cosine similarity in Python | Qdrant via LlamaIndex | HNSW indexing, ANN search, payload filtering — re-implementing this is months of work |
| Job queue with Redis | Custom Redis list polling | ARQ | ARQ handles job deduplication, retries, result storage, job status tracking, and worker lifecycle |
| OCR pipeline | Custom Tesseract subprocess management | EasyOcrOptions in Docling | Docling manages OCR lifecycle, page batching, and result integration into the document model |
| Citation extraction | Parsing LLM output for source references | LlamaIndex NodeWithScore metadata | Each retrieved chunk carries file_name and page_label metadata — just read it, don't re-infer it |

**Key insight:** Every component in this phase (document parsing, chunking, vector search, task queuing) has well-tested library implementations. The value is in wiring them together correctly, not reimplementing them.

---

## Common Pitfalls

### Pitfall 1: opencv-python vs opencv-python-headless in Docker

**What goes wrong:** `ImportError: libGL.so.1: cannot open shared object file: No such file or directory` at EasyOCR or Docling import time in Docker.

**Why it happens:** `opencv-python` links against OpenGL (libGL). Docker slim images don't include OpenGL libraries. `opencv-python-headless` is a drop-in replacement that doesn't require libGL.

**How to avoid:** In docproc's pyproject.toml, explicitly list `opencv-python-headless` and ensure `opencv-python` is never a transitive dependency. Run `pip list | grep opencv` during the Docker build to verify only headless is installed.

**Warning signs:** `libGL` errors during container startup; EasyOCR or Docling fails to import.

### Pitfall 2: nomic-embed-text dimension mismatch (768 vs 1536)

**What goes wrong:** Qdrant collection is created with 1536-dimensional vectors (OpenAI default), but nomic-embed-text outputs 768-dimensional vectors. All insert and search operations fail with `400 Bad Request: wrong input vector size`.

**Why it happens:** LlamaIndex's Settings default embed_model dimension is assumed to be 1536 (matching text-embedding-ada-002). If `Settings.embed_model` is not set before collection creation, the wrong dimension is used.

**How to avoid:** Set `Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text", base_url=...)` at application startup in `main.py` lifespan, before any Qdrant operations. Do this before initializing the RAG pipeline module.

**Warning signs:** `ValueError` or HTTP 400 responses from Qdrant on first document insert.

### Pitfall 3: ARQ job function receives wrong file path

**What goes wrong:** Worker can't open the file because the path from the ingest request was the host filesystem path, not the container path.

**Why it happens:** `maai-uploads` is a named Docker volume mounted at `/app/uploads` inside containers. The path inside the container is always `/app/uploads/{filename}`, not a host path.

**How to avoid:** The ingest endpoint must receive a relative filename (e.g., from the upload handling in Pipelines), prepend `/app/uploads/`, and pass the full container path to ARQ. Never accept absolute host paths.

**Warning signs:** `FileNotFoundError` in worker logs despite the file existing.

### Pitfall 4: EasyOCR model download on first run

**What goes wrong:** First time EasyOCR processes a document, it downloads model weights from the internet. In a restricted or offline environment, this hangs or fails. Also adds 10-30s latency to the first OCR job.

**Why it happens:** EasyOCR fetches models from a CDN at runtime unless they are pre-cached.

**How to avoid:** Pre-download EasyOCR models during Docker build or on container startup:
```python
import easyocr
reader = easyocr.Reader(["en"], gpu=False)  # download on startup
```
Mount a volume for the model cache directory (`/root/.EasyOCR/`) to persist downloads across restarts.

**Warning signs:** First document takes unexpectedly long; network timeout errors in docproc logs.

### Pitfall 5: Qdrant collection already exists on re-start

**What goes wrong:** Application crashes on startup because `QdrantVectorStore` tries to create a collection that already exists.

**Why it happens:** Qdrant uses a persistent volume. On restart, the collection exists but the code tries to create it again.

**How to avoid:** Use `QdrantClient.collection_exists(collection_name)` before creation, or use `QdrantVectorStore` with `collection_to_create=None` (let LlamaIndex handle idempotent creation). Alternatively, catch the already-exists exception and proceed.

**Warning signs:** Startup errors like `Collection already exists` or `400 Bad Request` on collection creation.

### Pitfall 6: Docling PaddleOCR backend does not exist natively

**What goes wrong:** Code attempts to use `PaddleOcrOptions` in Docling and gets `ImportError` or `AttributeError` because this class doesn't exist.

**Why it happens:** CONTEXT.md D-09 states "Docling already integrates PaddleOCR as an OCR backend" — this is incorrect. Docling's supported backends are: EasyOCR, Tesseract (CLI and Python), RapidOCR, and macOS Vision only. PaddleOCR is not a direct Docling OCR backend as of Docling 2.85.0.

**How to avoid:** Use `EasyOcrOptions` (recommended) or `RapidOcrOptions(backend="paddle")` for PaddlePaddle-based processing via RapidOCR's ONNX models. Do not reference `PaddleOcrOptions`.

**Warning signs:** `ImportError: cannot import name 'PaddleOcrOptions'` from `docling.datamodel.pipeline_options`.

### Pitfall 7: ARQ worker blocks the FastAPI event loop

**What goes wrong:** Worker is started inside the FastAPI process with `asyncio.run(Worker(...).run())`, blocking the API server.

**Why it happens:** ARQ Worker.run() runs indefinitely. Running it inside the same process as FastAPI blocks request handling.

**How to avoid:** Run the ARQ worker as a separate Docker Compose service or as a separate process started via Docker Compose command override: `arq workers.ingest_worker.WorkerSettings`. The core-api image already has all dependencies; a separate service with a different CMD is the cleanest approach.

**Warning signs:** FastAPI stops responding to requests after the worker starts.

---

## Code Examples

Verified patterns from official sources:

### Docling Text PDF Conversion (no OCR)

```python
# Source: Docling official docs https://docling-project.github.io/docling/
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("/app/uploads/document.pdf")
doc = result.document

# Export to plain text
full_text = doc.export_to_text()

# OR iterate structured items with page metadata
from docling.datamodel.base_models import InputFormat
for element, level in doc.iterate_items():
    if hasattr(element, "text") and element.text:
        page_no = element.prov[0].page_no if element.prov else 0
        # page_no is available for citation metadata
```

### Docling Scanned PDF with EasyOCR

```python
# Source: https://www.mintlify.com/docling-project/docling/guides/ocr-configuration
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

ocr_options = EasyOcrOptions(lang=["en"], use_gpu=False, force_full_page_ocr=True)
pipeline_options = PdfPipelineOptions(do_ocr=True, do_table_structure=True, ocr_options=ocr_options)
converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)
result = converter.convert("/app/uploads/scanned.pdf")
```

### LlamaIndex Indexing from Docling Output

```python
# Source: https://developers.llamaindex.ai/python/examples/vector_stores/qdrantindexdemo/
from llama_index.core import Settings, VectorStoreIndex, StorageContext, Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

# Set globally BEFORE any vector store ops
Settings.embed_model = OllamaEmbedding(
    model_name="nomic-embed-text",
    base_url="http://ollama:11434",
)

splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=Settings.embed_model,
)

# Convert Docling output to LlamaIndex Documents
documents = [
    Document(
        text=chunk_text,
        metadata={
            "file_name": original_filename,
            "page_label": str(page_no),
            "client_id": client_id,
        },
    )
    for chunk_text, page_no in docling_chunks
]

qclient = qdrant_client.QdrantClient(host="qdrant", port=6333)
collection_name = f"maai_{client_id}_documents"
vector_store = QdrantVectorStore(client=qclient, collection_name=collection_name)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

nodes = splitter.get_nodes_from_documents(documents)
index = VectorStoreIndex(nodes, storage_context=storage_context)
```

### ARQ Job Status Check

```python
# Source: https://arq-docs.helpmanual.io/
from arq import ArqRedis
from arq.jobs import Job, JobStatus

async def check_job_status(redis: ArqRedis, job_id: str) -> dict:
    job = Job(job_id=job_id, redis=redis)
    status = await job.status()
    if status == JobStatus.complete:
        result = await job.result(timeout=1)
        return {"status": "complete", "result": result}
    return {"status": status.value}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-size chunking (RecursiveCharacterTextSplitter) | SemanticSplitterNodeParser | LlamaIndex 0.10.x | Better retrieval coherence on mixed-content documents |
| Single global Qdrant collection | Per-client isolated collections | Always supported | Required for multi-tenant data isolation |
| Service context pattern (ServiceContext.from_defaults) | Global Settings pattern (Settings.embed_model) | LlamaIndex 0.10.x | ServiceContext is deprecated; use Settings |
| `docker-compose` binary | `docker compose` plugin | 2024 Docker CLI | Standalone binary EOL; use `docker compose` |

**Deprecated/outdated:**
- `ServiceContext.from_defaults(embed_model=...)`: Deprecated in LlamaIndex 0.10.x. Use `Settings.embed_model = ...` instead.
- `llama_index.vector_stores.qdrant` (old import path from 0.10.x): Use `llama_index.vector_stores.qdrant` from the `llama-index-vector-stores-qdrant` package (the new split-package import path).

---

## Open Questions

1. **EasyOCR GPU detection in docproc container**
   - What we know: EasyOcrOptions supports `use_gpu=True`; Docling passes it to EasyOCR
   - What's unclear: Whether the docproc container needs NVIDIA GPU access (Compose `deploy.resources.reservations`) or whether GPU use should be disabled to reduce VRAM pressure during OCR (given D-12/D-13)
   - Recommendation: Start with `use_gpu=False` in EasyOcrOptions. OCR with CPU EasyOCR is slower but avoids competing with Ollama for VRAM. GPU OCR can be enabled via env var later.

2. **ARQ worker as separate Compose service vs process in core-api**
   - What we know: ARQ worker needs to import core-api modules (LlamaIndex pipeline, etc.)
   - What's unclear: Whether to share the core-api Docker image with a different CMD or build a new service
   - Recommendation: Add `arq-worker` service to docker-compose.yml using the same `build: context: ./src/core_api` as core-api but with `command: arq workers.ingest_worker.WorkerSettings`. Avoids code duplication while keeping services separate.

3. **LlamaIndex async support for Qdrant operations**
   - What we know: QdrantVectorStore supports `AsyncQdrantClient` with `use_async=True`; ARQ job functions are async
   - What's unclear: Whether the full LlamaIndex pipeline (indexing + querying) works reliably in async mode
   - Recommendation: Use synchronous QdrantClient in the ARQ worker (the job function is async but can await sync operations). Use `AsyncQdrantClient` only if explicit benchmarking shows the sync client is a bottleneck.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Container orchestration | Yes | 28.5.1 | — |
| Docker Compose | Stack deployment | Yes | v2.40.3 | — |
| Ollama (running) | nomic-embed-text embeddings | Yes (via container) | — | Cannot proceed without |
| Redis (new) | ARQ broker + GPU lock | Not yet | — | Must be added in this phase |
| Qdrant (new) | Vector storage | Not yet | — | Must be added in this phase |
| Python 3.11 in container | docproc/core-api | Yes (FROM python:3.11-slim) | 3.11.x | — |
| nvidia-container-toolkit | GPU OCR | Unknown | — | Use CPU OCR (use_gpu=False) |

**Missing dependencies with no fallback:**
- Redis: ARQ requires it; must be added as Docker Compose service
- Qdrant: Vector storage for RAG; must be added as Docker Compose service

**Missing dependencies with fallback:**
- NVIDIA container toolkit: If absent, set `use_gpu=False` in EasyOcrOptions and accept slower OCR

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` (existing, `testpaths = tests`, `asyncio_mode = auto`) |
| Quick run command | `pytest tests/phase4/ -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCP-01 | Docling converts a text PDF and returns extractable text | unit (mock) | `pytest tests/phase4/test_docproc_client.py::test_text_pdf_extraction -x` | Wave 0 |
| DOCP-02 | EasyOCR pipeline runs for scanned PDF (force_full_page_ocr=True) | unit (mock docproc) | `pytest tests/phase4/test_docproc_client.py::test_scanned_pdf_ocr -x` | Wave 0 |
| DOCP-03 | SemanticSplitterNodeParser produces nodes with page metadata | unit | `pytest tests/phase4/test_rag_pipeline.py::test_semantic_chunking -x` | Wave 0 |
| DOCP-04 | Qdrant collection is created and a vector can be upserted | integration (real Qdrant) | `pytest tests/phase4/test_rag_pipeline.py::test_qdrant_upsert -x` | Wave 0 |
| DOCP-05 | Two client_ids produce isolated collections; query returns only own docs | integration | `pytest tests/phase4/test_rag_pipeline.py::test_collection_isolation -x` | Wave 0 |
| DOCP-06 | ask_documents skill routes through Skill Matcher and returns answer with citation | integration (mock LLM) | `pytest tests/phase4/test_ask_documents_skill.py::test_rag_response_with_citation -x` | Wave 0 |
| DOCP-07 | GPU lock prevents concurrent LLM and OCR operations | unit | `pytest tests/phase4/test_gpu_lock.py::test_lock_serializes_workloads -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/phase4/ -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- `tests/phase4/__init__.py` — empty init
- `tests/phase4/conftest.py` — path setup, stubs for docling/arq/qdrant_client/llama_index when not installed
- `tests/phase4/test_docproc_client.py` — docproc HTTP client tests (DOCP-01, DOCP-02)
- `tests/phase4/test_rag_pipeline.py` — LlamaIndex + Qdrant pipeline tests (DOCP-03, DOCP-04, DOCP-05)
- `tests/phase4/test_ask_documents_skill.py` — end-to-end skill routing test (DOCP-06)
- `tests/phase4/test_gpu_lock.py` — Redis lock serialization test (DOCP-07)

---

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md apply to this phase and MUST be honored by the planner:

- Use `logging_config.get_logger(__name__)` for ALL logging — never `print()` or `console.log()`
- `litellm>=1.83.0` only — versions 1.82.7/1.82.8 were backdoored
- Python 3.11 only — `FROM python:3.11-slim` in all Dockerfiles
- Use `uv pip install` not `pip install` in Dockerfiles
- Use `opencv-python-headless` not `opencv-python` in Docker
- Use `docker compose` (plugin, no hyphen) — not `docker-compose`
- All dependencies must be permissively licensed (MIT, Apache 2.0, BSD): EasyOCR (Apache 2.0), ARQ (MIT), Qdrant client (Apache 2.0), LlamaIndex (MIT), Docling (MIT) — all compliant
- No paid third-party APIs — all processing local
- Do NOT use `requests` in async FastAPI/ARQ code — use `httpx`
- Ruff for linting/formatting (configured in pyproject.toml)
- `pyproject.toml` for all new service dependencies (not requirements.txt)

---

## Sources

### Primary (HIGH confidence)

- [ARQ official documentation](https://arq-docs.helpmanual.io/) — WorkerSettings, job function signature, enqueueing, status checking
- [Docling OCR configuration guide](https://www.mintlify.com/docling-project/docling/guides/ocr-configuration) — all OCR backend options, their configuration classes with code examples
- [LlamaIndex Qdrant Vector Store demo](https://developers.llamaindex.ai/python/examples/vector_stores/qdrantindexdemo/) — complete indexing and query pipeline
- [LlamaIndex Ollama Embeddings](https://developers.llamaindex.ai/python/examples/embeddings/ollama_embedding/) — OllamaEmbedding class + SemanticSplitterNodeParser integration
- [Qdrant Multitenancy docs](https://qdrant.tech/documentation/manage-data/multitenancy/) — separate collections vs payload partitioning tradeoffs
- [Qdrant + LlamaIndex multitenancy guide](https://qdrant.tech/documentation/examples/llama-index-multitenancy/) — per-tenant filtering with MetadataFilters
- PyPI registry (verified 2026-04-08): arq 0.27.0, qdrant-client 1.17.1, llama-index-core 0.14.20, docling 2.85.0

### Secondary (MEDIUM confidence)

- [Docling OCR Models (deepwiki)](https://deepwiki.com/docling-project/docling/4.1-ocr-models) — confirms PaddleOCR not a native backend; supported backends list
- [nomic-embed-text dimension issue (mem0 GitHub)](https://github.com/mem0ai/mem0/issues/4212) — confirms 768 vs 1536 dimension mismatch root cause and fix pattern
- [RapidAI/RapidOCR GitHub](https://github.com/RapidAI/RapidOCR) — RapidOCR uses PaddleOCR ONNX models; paddle backend availability confirmed

### Tertiary (LOW confidence)

- [Docling PaddleOCR-VL integration request](https://github.com/docling-project/docling/issues/2495) — confirms PaddleOCR-VL not yet integrated as of late 2025
- EasyOCR GPU memory leak reports (Docling GitHub discussions) — memory leak from repeated `reader.readertxt` calls; mitigate by initializing reader once at startup

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — versions verified against PyPI registry 2026-04-08
- Architecture: HIGH — patterns verified against official ARQ, LlamaIndex, Qdrant, Docling docs
- OCR backend finding: HIGH — verified across multiple official Docling sources; PaddleOCR absence confirmed
- Vector dimension pitfall: HIGH — confirmed via official bug reports with root cause documented
- GPU lock pattern: MEDIUM — Redis SET NX PX is a well-known pattern; interaction with ARQ's max_jobs=1 is by design but untested in this specific stack

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days — stable libraries, but LlamaIndex releases frequently)
