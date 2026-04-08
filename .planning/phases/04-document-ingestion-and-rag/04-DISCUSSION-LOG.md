# Phase 4: Document Ingestion and RAG - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 04-document-ingestion-and-rag
**Areas discussed:** Ingestion pipeline, RAG query integration, Container architecture, GPU sequencing

---

## Ingestion Pipeline

### Processing Model

| Option | Description | Selected |
|--------|-------------|----------|
| Background queue | Redis + ARQ async queue. Upload returns immediately. Background worker runs pipeline. | ✓ |
| Synchronous in-request | Process during chat request. Simpler but blocks user. | |
| You decide | Claude picks. | |

**User's choice:** Background queue (Recommended)
**Notes:** Matches Phase 2 D-11 plan for adding task queuing in Phase 4+.

### Trigger Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Chat upload + skill | User uploads file and says "index this document". Skill matches and queues. | ✓ |
| Auto-ingest on upload | Any uploaded file automatically queued. Less control. | |
| You decide | Claude picks. | |

**User's choice:** Chat upload + skill (Recommended)

### Status Communication

| Option | Description | Selected |
|--------|-------------|----------|
| Poll-based status | User asks "what's the status?" Tool queries ARQ job state. | ✓ |
| Proactive notification | System sends message when done. Requires webhook/push. | |
| You decide | Claude picks. | |

**User's choice:** Poll-based status (Recommended)

### Document Formats

| Option | Description | Selected |
|--------|-------------|----------|
| PDF + images only | Focus on PDF (text and scanned). Tight scope. | ✓ |
| All Docling formats | PDF, DOCX, PPTX, HTML, images. Broader but more testing. | |
| You decide | Claude picks. | |

**User's choice:** PDF + images only (Recommended)

---

## RAG Query Integration

### Query Routing

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated RAG skill | Specific skill for document queries. Clear separation from chat. | ✓ |
| Auto-inject on every message | Qdrant search on all messages. Seamless but adds latency. | |
| Hybrid approach | Dedicated skill + lightweight context hint on freeform. | |
| You decide | Claude picks. | |

**User's choice:** Dedicated RAG skill (Recommended)

### Source Citations

| Option | Description | Selected |
|--------|-------------|----------|
| Document + page reference | "Source: doc.pdf, page 3-4" at end of answer. | ✓ |
| Inline citations | [1][2] style with references section. | |
| No citations | Just the answer. | |

**User's choice:** Document + page reference (Recommended)

### Chunking Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Semantic chunking | LlamaIndex SemanticSplitterNodeParser. Meaning boundaries. | ✓ |
| Fixed-size with overlap | 512-token chunks, 50-token overlap. Simple, predictable. | |
| You decide | Claude picks. | |

**User's choice:** Semantic chunking (Recommended)

### Retrieval Count

| Option | Description | Selected |
|--------|-------------|----------|
| Top 5 chunks | Good balance of coverage and context size. | ✓ |
| Top 3 chunks | Minimal context, faster, may miss info. | |
| You decide | Claude picks. | |

**User's choice:** Top 5 chunks (Recommended)

---

## Container Architecture

### Containerization

| Option | Description | Selected |
|--------|-------------|----------|
| Single docproc sidecar | One container with Docling + PaddleOCR + FastAPI. | ✓ |
| Two separate containers | Separate docling and paddleocr containers. More isolation. | |
| You decide | Claude picks. | |

**User's choice:** Single docproc sidecar (Recommended)

### Communication Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP API | Docproc exposes FastAPI endpoint. Core API calls via HTTP. | ✓ |
| Shared volume only | File-based communication via watched directory. | |
| You decide | Claude picks. | |

**User's choice:** HTTP API (Recommended)

### New Services

| Option | Description | Selected |
|--------|-------------|----------|
| Add both in Phase 4 | Qdrant + Redis added to docker-compose.yml now. | ✓ |
| Redis now, Qdrant later | Stage the service additions. | |
| You decide | Claude picks. | |

**User's choice:** Add both in Phase 4 (Recommended)

---

## GPU Sequencing

### Sequencing Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Application-level semaphore | Redis-based distributed lock. One GPU workload at a time. | ✓ |
| Queue-based sequencing | Single ARQ queue with concurrency=1 for all GPU work. | |
| Container resource limits | Docker deploy.resources VRAM caps per container. | |
| You decide | Claude picks. | |

**User's choice:** Application-level semaphore (Recommended)

### Priority Model

| Option | Description | Selected |
|--------|-------------|----------|
| Chat priority | Chat requests preempt document processing. | ✓ |
| FIFO | Strict ordering. Large jobs could block chat. | |
| You decide | Claude picks. | |

**User's choice:** Chat priority (Recommended)

---

## Claude's Discretion

- ARQ worker configuration details (concurrency, retry policy, job timeout)
- Docproc FastAPI endpoint design (request/response schemas)
- LlamaIndex pipeline assembly details (node parsers, index type, query engine)
- Qdrant collection schema and naming convention
- Redis configuration (persistence, memory limits)
- Exact semaphore/lock implementation details
- Skill YAML content for document_ingest and ask_documents
- Docproc container base image and dependency installation

## Deferred Ideas

- DOCX/PPTX/HTML ingestion (format expansion)
- Auto-ingest on upload (v2 with folder watching)
- Proactive completion notifications (webhook/push)
- Hybrid RAG auto-inject on freeform messages
- Inline academic-style citations
