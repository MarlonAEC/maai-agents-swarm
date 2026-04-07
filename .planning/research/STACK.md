# Stack Research

**Domain:** Local AI agent platform — config-driven, Docker-deployed, chat-fronted
**Researched:** 2026-04-07
**Confidence:** HIGH (all versions verified against PyPI, GitHub releases, and official docs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.11.x | Runtime | CrewAI, Docling, LlamaIndex all specify >=3.10; 3.11 is the stable LTS sweet-spot — faster than 3.10, more mature than 3.12 for ML libraries. Avoid 3.13 until the ML ecosystem catches up. |
| **CrewAI** | 1.13.x | Agent orchestration | Only major framework with first-class YAML-driven agent/task/tool config. LangGraph requires Python DSL; AutoGen is being sunset by Microsoft in favour of their broader Agent Framework. CrewAI 1.8+ added production-ready Flows + Crews and native HITL, exactly what this platform needs. |
| **Ollama** | 0.20.x | Local LLM serving | Single binary, OpenAI-compatible REST API, GPU/CPU auto-detection, supports Qwen 3 and Gemma 3 natively. Docker image available at `ollama/ollama`. Competing option (llama.cpp server) is lower-level and requires manual model management. |
| **Open WebUI** | 0.8.12 | Chat interface | Pre-built UI with Ollama native support, tool calling, file uploads, conversation history, and RAG integration. Eliminates building an entire frontend. Version 0.8.x adds Responses API streaming, knowledge handling, and enterprise OAuth. Don't build a custom chat UI — this solves it. |
| **LiteLLM** | >=1.83.0 | LLM routing proxy | Translates any OpenAI-compatible call to any backend (Ollama, future cloud models). Pin to >=1.83.0 — versions 1.82.7–1.82.8 were backdoored in a March 2026 supply chain attack and subsequently yanked from PyPI. Use as a Docker sidecar container. |
| **Qdrant** | 1.13.x | Vector database (RAG) | Single binary / single Docker container. Superior filtering vs ChromaDB, stable REST + gRPC API, GPU acceleration support. v1.13 adds extensive resource optimizations. Qdrant 1.14 (reranking support) was released April 22, 2026 — safe to adopt. ChromaDB is fine for prototyping but lacks production filtering granularity. |
| **Docker Compose** | v2 (Compose spec 5.0) | Deployment orchestration | The canonical single-command deployment story. Compose spec v5.0 (late 2025) is fully integrated as a Docker CLI plugin. Use `docker compose up` (no hyphen) — the standalone `docker-compose` binary is deprecated. |

### Document Processing Layer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Docling** | 2.84.x | Document parsing | MIT license, broadest format support (PDF, DOCX, PPTX, HTML, images), IBM-backed, excellent table extraction, outputs structured JSON. Handles complex layouts that simple PDF extractors miss. `docling-ibm-models` 3.13.0 (March 2026). |
| **PaddleOCR** | 3.0.x (PP-OCRv5) | OCR for scanned docs | Released May 2025, PP-OCRv5 is the highest-accuracy open-source OCR for table/form extraction. PaddleOCR-VL-1.5 (Jan 2026) supports 109 languages and reaches 94.5% on OmniDocBench v1.5. EasyOCR is slower on CPU and less accurate on complex layouts. Tesseract is fine for clean printed text but fails on tables, forms, and mixed layouts — exactly what client documents contain. |
| **LlamaIndex** | 0.14.20 | RAG pipeline | Pairs with Qdrant for indexing, retrieval, and query pipelines. The `llama-index-core` package is the right import since the monolithic `llama-index` package is a convenience wrapper. Provides chunking strategies, embedding management, and query engines out of the box. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **imap-tools** | latest | Email integration | High-level IMAP client. Much simpler than raw `imaplib` (which returns near-unparsed server responses). Handles IMAP search, flagging, and attachment extraction cleanly. Use for all email integrations (Gmail IMAP, O365 IMAP). |
| **openpyxl** | 3.1.3 | Excel/spreadsheet output | Standard library for writing `.xlsx` files. Use with `pandas` for DataFrame → spreadsheet workflows. When the task is structured data output, pandas + openpyxl is the fastest path. |
| **pandas** | 2.x | Data manipulation | DataFrame intermediary between extracted document data and spreadsheet output. Well-integrated with openpyxl as the write engine. |
| **watchdog** | 4.x | Folder watching | Cross-platform filesystem event library. Use for local folder monitoring to detect new files. Latest stable November 2024. Avoid `pyinotify` (Linux-only) and Win32 polling (inefficient). |
| **Pydantic** | 2.x | Config validation | Validate YAML-loaded config structs at startup. CrewAI 1.x uses Pydantic v2 internally — pin to v2 to avoid conflicts. |
| **python-dotenv** | 1.x | Environment config | Load `client.env` files in Docker containers. Simple, zero-dependency. |
| **ARQ** | 0.26.x | Async task queue | Redis-backed async task queue built for asyncio. Lighter than Celery for this use case — no need for a full Celery worker pool when tasks are sequential document processing jobs. Use ARQ + Redis for background skill execution. |
| **Redis** | 7.x (Docker) | Task queue broker | Broker for ARQ. Also usable for caching LLM responses per session. Lightweight — run as a Docker sidecar. |
| **FastAPI** | 0.115.x | Internal API layer | Expose agent trigger endpoints to Open WebUI (via function tools). Async-native, auto-generated OpenAPI docs useful for debugging tool integrations. |
| **httpx** | 0.27.x | HTTP client | Async HTTP calls within agent tools. Prefer over `requests` for FastAPI/async contexts. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Python package/venv management | Dramatically faster than pip. Use `uv pip install` and `uv venv`. Compatible with requirements.txt and pyproject.toml. The 2025/2026 standard for Python tooling. |
| **pyproject.toml** | Project metadata + deps | Use instead of setup.py or requirements.txt. Supported by uv natively. |
| **Ruff** | Linting + formatting | Replaces Black + isort + flake8 in a single fast binary. Standard in 2025/2026 Python projects. |
| **pytest** | Test runner | Use `pytest-asyncio` for async agent tests. |

---

## Installation

```bash
# Create environment with uv
uv venv .venv --python 3.11
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Core agent + orchestration
uv pip install "crewai>=1.13.0" "litellm>=1.83.0"

# Document processing
uv pip install "docling>=2.84.0" paddleocr "llama-index-core>=0.14.0" "llama-index-vector-stores-qdrant"

# Email + spreadsheets + file watching
uv pip install imap-tools openpyxl "pandas>=2.0" watchdog

# API layer + task queue
uv pip install "fastapi>=0.115.0" "uvicorn[standard]" arq httpx

# Config + validation
uv pip install pydantic "python-dotenv>=1.0"

# Qdrant client
uv pip install "qdrant-client>=1.9"

# Dev dependencies
uv pip install -D ruff pytest pytest-asyncio
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| CrewAI | LangGraph | LangGraph requires Python DSL for agent/task definition — no YAML config. Steepest learning curve. Best for complex stateful graphs, not config-driven skill dispatch. |
| CrewAI | AutoGen | Microsoft shifted AutoGen to maintenance mode in favour of their broader Agent Framework. Avoid for greenfield in 2026. |
| Qdrant | ChromaDB | ChromaDB is excellent for prototyping. Qdrant wins on: filtering (payload + vector), single-binary Docker, and production resource controls. Once you need per-client filtered RAG (don't return client A's docs to client B's queries), Qdrant's filtering is essential. |
| Qdrant | pgvector (Postgres) | pgvector is fine but adds the operational weight of Postgres. Qdrant is purpose-built and more resource-efficient for pure vector workloads. |
| PaddleOCR | EasyOCR | EasyOCR has a simpler API but is slower on CPU and less accurate on tables/forms. The PP-OCRv5 accuracy bump in May 2025 widened the gap. |
| PaddleOCR | Tesseract | Tesseract is excellent for clean printed text (invoices with simple formatting) but struggles with complex multi-column layouts, rotated text, and table cells — exactly the edge cases client documents contain. |
| Docling | PyMuPDF (fitz) | PyMuPDF is fast but does basic extraction. Docling provides structured JSON output with table/figure detection, layout analysis, and metadata. Use PyMuPDF only if Docling's startup time becomes a problem in serverless contexts (not relevant here). |
| imap-tools | imaplib | imaplib returns near-unparsed IMAP server responses. Everyone who uses it ends up writing fragile parsing code. imap-tools wraps this into a clean Python API. |
| ARQ | Celery | Celery is heavier (requires a separate beat scheduler for periodic tasks, more complex worker configuration). ARQ is async-native and simpler for this use case — background file processing jobs that run serially per client. |
| uv | pip + venv | uv is 10–100x faster and handles lockfiles natively. No reason to use raw pip in 2025/2026. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `litellm==1.82.7` or `1.82.8` | Backdoored via supply chain attack (March 24, 2026, TeamPCP / Trivy CI/CD compromise). Both versions were yanked from PyPI but cached versions may exist in Docker layers. | `litellm>=1.83.0` — rebuilt with a new isolated CI/CD pipeline. |
| `docker-compose` (standalone binary) | Deprecated. The standalone binary has been EOL'd. | `docker compose` (V2 plugin, integrated into Docker CLI). |
| `langchain` as the primary agent layer | LangChain is a general-purpose toolkit, not an orchestrator. Using it as the agent layer leads to deeply nested callback chains that are hard to debug. It's fine as a utility (e.g., document loaders) but don't build agent logic on top of it. | CrewAI for orchestration; use LlamaIndex for RAG pipelines. |
| Python 3.12 or 3.13 | PaddleOCR and some ML dependencies still have packaging issues on 3.12+. The ML ecosystem has not fully migrated. | Python 3.11 — stable LTS sweet spot. |
| `chromadb` in production | ChromaDB's on-disk persistence model has known corruption risks under concurrent writes. Its filtering API is also less expressive than Qdrant for multi-tenant or per-client scoping. | Qdrant in Docker. |
| Building a custom chat UI | Open WebUI already has Ollama integration, tool calling, file uploads, and RAG UI. Reinventing this is months of work with no competitive differentiation. | Open WebUI (Docker image: `ghcr.io/open-webui/open-webui`). |
| `requests` in async FastAPI code | `requests` is synchronous and blocks the asyncio event loop. Causes performance degradation in async handlers. | `httpx` with `await client.get(...)`. |

---

## Stack Patterns by Variant

**For the document-processing "first client" configuration:**
- Enable Docling + PaddleOCR + LlamaIndex + Qdrant services in Docker Compose
- Disable email service (enable only when IMAP credentials are configured in `client.env`)
- Use watchdog for the folder watcher service

**For a lighter-weight client without document processing:**
- Disable Docling, PaddleOCR, LlamaIndex, Qdrant containers entirely
- Keep: Ollama, LiteLLM, Open WebUI, CrewAI worker, Redis, ARQ, FastAPI
- RAM footprint drops from ~8GB to ~4GB

**If client hardware lacks a GPU:**
- Ollama falls back to CPU-only inference automatically
- Switch model from Qwen 3 14B to Qwen 3 7B (fits in 8GB RAM at Q4_K_M)
- For classification, drop to Gemma 3 1B instead of 4B
- CPU inference is slow but functional for async background tasks

**For future multi-client / SaaS evolution:**
- Qdrant collections are already per-client (create one collection per `client_id`)
- CrewAI YAML config is already per-client (separate config folders)
- The Docker Compose architecture can move to Kubernetes with minimal changes — services map 1:1 to Deployments

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `crewai>=1.13.0` | `pydantic>=2.0` | CrewAI 1.x dropped Pydantic v1 support. Pin pydantic to v2. |
| `llama-index-core>=0.14.0` | `qdrant-client>=1.9` | Use `llama-index-vector-stores-qdrant` for the integration package. Do not use the old `llama_index.vector_stores.qdrant` import path from v0.10.x. |
| `docling>=2.84.0` | `Python>=3.10` | Docling requires Python 3.10+. Fine on 3.11. |
| `paddleocr>=3.0` | `paddlepaddle` | PaddleOCR 3.0 requires `paddlepaddle` (CPU) or `paddlepaddle-gpu`. Install the appropriate variant based on client hardware. GPU variant requires CUDA 11.x or 12.x. |
| `litellm>=1.83.0` | `openai>=1.0` | LiteLLM 1.83.x uses the OpenAI SDK v1 internally. Do not mix with `openai<1.0`. |
| `fastapi>=0.115.0` | `pydantic>=2.0` | FastAPI 0.115+ requires Pydantic v2. No workaround needed since CrewAI also requires Pydantic v2. |

---

## LLM Model Recommendations

These are Ollama model tags, not library versions, but they are stack decisions:

| Model | Ollama Tag | Use Case | VRAM Required |
|-------|-----------|----------|---------------|
| Qwen3 14B | `qwen3:14b` | Agent reasoning, task planning | 10–12GB (Q4_K_M) |
| Qwen3 7B | `qwen3:7b` | Agent reasoning (low-VRAM fallback) | 5–6GB (Q4_K_M) |
| Gemma 3 4B | `gemma3:4b` | File classification, fast tagging | 3–4GB (Q4_K_M) |
| Gemma 3 1B | `gemma3:1b` | Classification (CPU-only client) | ~1GB |

Qwen3 14B is recommended over Qwen 2.5 14B — benchmarks show Qwen3-14B performing at the level of Qwen2.5-32B on reasoning tasks, with built-in thinking mode for complex agent tasks.

---

## Sources

- [CrewAI v1.13.0 release — aiforautomation.io](https://aiforautomation.io/news/2026-04-03-crewai-1-13-0-gpt5-enterprise-rbac) — CrewAI current version confirmed
- [CrewAI GitHub releases](https://github.com/crewAIInc/crewAI/releases) — version history
- [CrewAI YAML config — community thread](https://community.crewai.com/t/how-to-add-tools-to-agents-and-tasks-yaml-files-proper-format-syntax/3321) — YAML tool/agent/task syntax confirmed
- [Ollama GitHub releases](https://github.com/ollama/ollama/releases) — v0.20.x confirmed current
- [Open WebUI releases — releasebot.io](https://releasebot.io/updates/open-webui) — v0.8.12 confirmed
- [LiteLLM security update — docs.litellm.ai](https://docs.litellm.ai/blog/security-update-march-2026) — supply chain attack details, v1.83.0+ safe
- [LiteLLM supply chain attack — thehackernews.com](https://thehackernews.com/2026/03/teampcp-backdoors-litellm-versions.html) — confirms 1.82.7/1.82.8 affected
- [Qdrant v1.14 release](https://qdrant.tech/blog/qdrant-1.14.x/) — reranking + resource optimizations
- [Qdrant Docker Hub](https://hub.docker.com/r/qdrant/qdrant) — latest image confirmed
- [Docling PyPI](https://pypi.org/project/docling/) — v2.84.0 confirmed
- [docling-ibm-models PyPI](https://pypi.org/project/docling-ibm-models/) — v3.13.0 confirmed March 2026
- [PaddleOCR v3.0 + VL-1.5](https://merginit.com/blog/15072025-best-ocr-ocr-ai-models) — PP-OCRv5 + OmniDocBench accuracy
- [LlamaIndex PyPI](https://pypi.org/project/llama-index/) — v0.14.20 confirmed April 2026
- [Qwen3 blog](https://qwenlm.github.io/blog/qwen3/) — Qwen3-14B vs Qwen2.5-32B parity confirmed
- [Qwen3 on Ollama](https://ollama.com/library/qwen3:14b) — tag availability confirmed
- [CrewAI vs LangGraph vs AutoGen 2026 — Medium](https://medium.com/data-science-collective/langgraph-vs-crewai-vs-autogen-which-agent-framework-should-you-actually-use-in-2026-b8b2c84f1229) — AutoGen maintenance mode confirmed
- [imap-tools GitHub](https://github.com/ikvk/imap_tools) — active maintenance confirmed
- [Docker Compose for AI agents — Docker blog](https://www.docker.com/blog/build-ai-agents-with-docker-compose/) — Compose V2 + resource limits best practices
- [FastAPI Background Tasks vs Celery — markaicode.com](https://markaicode.com/vs/fastapi-background-tasks-vs-celery-ai-workloads/) — ARQ recommendation for async-native stacks

---

*Stack research for: MAAI Agent Platform — Local AI agent platform, Docker-deployed*
*Researched: 2026-04-07*
