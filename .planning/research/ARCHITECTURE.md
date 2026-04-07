# Architecture Research

**Domain:** Config-driven local AI agent platform (Docker-deployed, per-client YAML configuration)
**Researched:** 2026-04-06
**Confidence:** HIGH — stack is fully decided, patterns are drawn from existing research and verified sources

---

## Standard Architecture

### System Overview

```
CLIENT MACHINE (Docker Compose)
+---------------------------------------------------------------------+
|                                                                     |
|  PRESENTATION LAYER                                                 |
|  +---------------------------------------------------------------+  |
|  |  Open WebUI  :3000                                            |  |
|  |    - Chat interface (Ollama-native, tool calling, file upload) |  |
|  |    - Connects to Core API via Pipelines (OpenAI-compatible)   |  |
|  +---------------------------------------------------------------+  |
|                          |  (HTTP /chat/completions)                |
|                          v                                          |
|  ORCHESTRATION LAYER                                                |
|  +---------------------------------------------------------------+  |
|  |  Core API  (FastAPI, stateless)  :8000                        |  |
|  |    - Receives chat messages from Open WebUI Pipelines         |  |
|  |    - Resolves client context from config volume               |  |
|  |    - Skill matcher: named skill OR freeform agent dispatch    |  |
|  |    - CrewAI Crew/Flow executor (reads YAML, runs agents)      |  |
|  |    - Tool registry (discovers + loads plugins at startup)     |  |
|  |    - Workflow engine (Celery DAG executor for async jobs)     |  |
|  |    - Streams results back via SSE                             |  |
|  +---------------------------------------------------------------+  |
|        |                   |                    |                   |
|        v                   v                    v                   |
|  +----------+   +--------------------+   +--------------+          |
|  | Plugin   |   | Config Volume      |   | LLM Layer    |          |
|  | Runtime  |   | /config/           |   |              |          |
|  |          |   |   agents.yaml      |   | LiteLLM :4000|          |
|  | pdf-reader|   |   workflows.yaml  |   |   ↓          |          |
|  | email    |   |   tools.yaml       |   | Ollama :11434|          |
|  | xlsx-io  |   |   prompts/         |   |   qwen2.5:14b|          |
|  | web-scrp |   |   client.env       |   |   gemma3:4b  |          |
|  +----------+   +--------------------+   +--------------+          |
|        |                                        |                   |
|        v                                        v                   |
|  DATA LAYER                                                         |
|  +----------+    +----------+    +----------+   +----------+       |
|  |PostgreSQL|    |  Redis   |    |  Qdrant  |   |File Store|       |
|  |(app state|    |(queue/   |    |(vector   |   |(client   |       |
|  | job logs)|    | cache)   |    | RAG DB)  |   | files)   |       |
|  +----------+    +----------+    +----------+   +----------+       |
|                                                                     |
+---------------------------------------------------------------------+
```

---

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| Open WebUI | Chat interface; routes user messages to Core API via Pipelines | Open WebUI (Docker image) |
| Open WebUI Pipelines | Bridges Open WebUI to Core API; translates OpenAI Chat Completions to internal requests | open-webui/pipelines (custom pipe) |
| Core API | Stateless request handler; skill dispatch; CrewAI orchestration; tool registry; config loading | FastAPI + CrewAI |
| Skill Matcher | Determines whether input maps to a named skill (YAML-defined) or requires freeform agent reasoning | Python module in Core API |
| CrewAI Executor | Loads agents.yaml + tasks, builds Crew/Flow, executes, returns result | CrewAI |
| Workflow Engine | Async DAG executor for multi-step workflows triggered by events or schedules | Celery + Redis |
| Tool Registry | Discovers plugins at startup via manifests; provides tools to CrewAI agents by name | Python module in Core API |
| Plugin Runtime | Subprocess per plugin; communicates with Core API via JSON-RPC; isolates tool logic | Subprocess + JSON-RPC |
| LiteLLM Proxy | Routes model requests to correct Ollama model; enforces per-agent model selection | LiteLLM (Docker image) |
| Ollama | Serves local LLMs; exposes OpenAI-compatible /api endpoints | Ollama (Docker image) |
| Config Volume | Per-client YAML + prompts mounted as Docker volume; no code changes per client | Docker bind mount |
| PostgreSQL | Persistent state: job results, conversation metadata, audit logs | PostgreSQL (Docker image) |
| Redis | Celery broker + result backend; short-term caching | Redis (Docker image) |
| Qdrant | Per-client vector store for RAG knowledge base | Qdrant (Docker image) |
| File Store | Client documents, processed outputs (PDFs, spreadsheets, exports) | Host bind mount |

---

## Recommended Project Structure

```
maai-agent-platform/
├── core/                        # Core API service
│   ├── api/                     # FastAPI route handlers
│   │   ├── chat.py              # /chat/completions endpoint (Open WebUI entry)
│   │   ├── jobs.py              # /jobs status endpoints
│   │   └── health.py            # /health check
│   ├── engine/                  # Orchestration logic
│   │   ├── skill_matcher.py     # Named skill vs freeform dispatch
│   │   ├── crew_executor.py     # Loads YAML, builds + runs CrewAI Crew/Flow
│   │   ├── workflow_engine.py   # Celery DAG definition + execution
│   │   └── config_loader.py     # Reads agents.yaml, workflows.yaml, prompts/
│   ├── tools/                   # Tool registry
│   │   ├── registry.py          # Discovers plugins, registers tools
│   │   └── base.py              # Base tool interface
│   ├── plugins/                 # Built-in plugin implementations
│   │   ├── pdf_reader/
│   │   │   ├── plugin.yaml      # Manifest (name, description, input schema)
│   │   │   └── main.py          # Tool logic (Docling + PaddleOCR)
│   │   ├── email_client/
│   │   │   ├── plugin.yaml
│   │   │   └── main.py          # IMAP / Gmail API / exchangelib adapter
│   │   ├── spreadsheet_writer/
│   │   │   ├── plugin.yaml
│   │   │   └── main.py          # XlsxWriter + pandas
│   │   └── rag_query/
│   │       ├── plugin.yaml
│   │       └── main.py          # LlamaIndex + Qdrant query
│   ├── ingestion/               # Document ingestion pipeline
│   │   ├── router.py            # MIME detection + type routing
│   │   ├── parsers.py           # Docling, PaddleOCR
│   │   ├── chunker.py           # LlamaIndex chunking
│   │   └── embedder.py          # sentence-transformers embedding
│   ├── models/                  # Pydantic models
│   │   ├── chat.py              # ChatRequest, ChatResponse
│   │   └── config.py            # AgentConfig, WorkflowConfig
│   └── main.py                  # FastAPI app entry point
│
├── pipelines/                   # Open WebUI Pipelines connector
│   └── maai_pipeline.py         # Pipe class: routes WebUI messages to Core API
│
├── clients/                     # Per-client config folders
│   └── acme-corp/
│       ├── agents.yaml          # Agent definitions (model, prompt, tools)
│       ├── workflows.yaml       # Workflow DAGs
│       ├── tools.yaml           # Which plugins are enabled
│       ├── prompts/
│       │   ├── invoice-extractor.txt
│       │   └── email-summarizer.txt
│       └── client.env           # Email creds, API keys (never committed)
│
├── docker/                      # Docker configuration
│   ├── docker-compose.yml       # Base stack (all services)
│   ├── docker-compose.override-example.yml  # Client-specific overrides
│   └── Dockerfile.core          # Core API image
│
└── deploy.sh                    # Deployment script: takes client dir, runs compose
```

### Structure Rationale

- **core/engine/:** Separates orchestration logic from HTTP handlers — core API stays thin; all agent reasoning is here
- **core/plugins/:** Each plugin is self-contained with a manifest; core never imports plugin code directly, only discovers via manifest
- **pipelines/:** Isolated connector between Open WebUI and Core API; if Open WebUI is replaced, only this file changes
- **clients/:** Config-only folders; adding a new client = copying a template folder and filling in YAML, no code changes
- **docker/:** Base compose file stays identical across clients; overrides layer client-specific env and volume mounts

---

## Architectural Patterns

### Pattern 1: Config-Driven Agent Definition

**What:** Agents are fully described in YAML — model selection, system prompt file reference, tool list, temperature. The Core API reads this at request time (or startup) and materializes CrewAI Agent objects dynamically.

**When to use:** Always — this is the primary extensibility mechanism. New business vertical = new YAML + prompts, no code.

**Trade-offs:** Requires discipline in YAML schema design upfront. Validation errors surface at runtime, not compile time — use Pydantic to parse YAML configs on load.

**Example:**
```yaml
# clients/acme-corp/agents.yaml
agents:
  invoice_processor:
    model: qwen2.5:14b
    prompt: prompts/invoice-extractor.txt
    tools: [pdf-reader, spreadsheet-writer, rag-query]
    temperature: 0.1
    max_iterations: 5
  email_summarizer:
    model: qwen2.5:14b
    prompt: prompts/email-summarizer.txt
    tools: [email-client]
    temperature: 0.3
```

### Pattern 2: Plugin Manifest + JSON-RPC Isolation

**What:** Each tool (plugin) declares a `plugin.yaml` manifest with its name, description, and JSON Schema for inputs. Core API scans the plugins directory at startup, registers tools by name. When CrewAI invokes a tool, Core API calls the plugin subprocess via JSON-RPC — no direct import.

**When to use:** All external business tools (PDF reader, email, spreadsheet, RAG). Keeps Core API lightweight and plugin failures isolated.

**Trade-offs:** Subprocess overhead per tool call (~10-50ms). Acceptable for document processing tasks; would be noticeable for tight inference loops. Pure Python tools that don't need isolation (e.g., simple string formatting) can be registered directly without subprocess.

**Example manifest:**
```yaml
# core/plugins/pdf_reader/plugin.yaml
name: pdf-reader
description: Extract text and tables from PDF files using Docling and PaddleOCR
input_schema:
  type: object
  properties:
    file_path:
      type: string
      description: Absolute path to the PDF file
  required: [file_path]
```

### Pattern 3: Skill Matcher — Named Skills vs Freeform

**What:** When Open WebUI sends a chat message to Core API, the Skill Matcher first checks whether the input matches a named skill (exact name or semantic similarity to a skill description). If matched, it dispatches the pre-configured workflow directly. If no match, it falls through to freeform agent reasoning over all available tools.

**When to use:** Always — this is what makes the system feel responsive (named skills are fast, deterministic) while remaining flexible (freeform for novel requests).

**Trade-offs:** Semantic matching requires either a small embedding model call (accurate but adds ~100ms) or keyword heuristics (fast but brittle). Start with keyword/fuzzy matching; upgrade to embedding-based matching if misclassification becomes a problem.

### Pattern 4: Celery DAG for Async Workflows

**What:** Long-running workflows (e.g., scan 1000 emails, process 50 PDFs) are submitted as Celery tasks to a Redis-backed queue. Each workflow step is a Celery task; dependencies enforced via Celery chords/chains matching the `depends_on` declarations in workflows.yaml.

**When to use:** Any workflow that takes more than ~5 seconds. Chat-initiated skills that complete quickly can be synchronous; file-watching triggers and scheduled runs must always be async.

**Trade-offs:** Adds operational complexity (Celery workers + Redis). Required for file watcher workflows and email polling — can't block a request thread.

---

## Data Flow

### Chat Message Flow (Named Skill)

```
User types "process invoices" in Open WebUI
    |
    v
Open WebUI Pipelines (maai_pipeline.py)
    |  POST /chat/completions to Core API
    v
Core API — chat.py route handler
    |  Passes message to skill_matcher.py
    v
Skill Matcher
    |  Fuzzy match → "invoice_pipeline" workflow found in workflows.yaml
    v
Workflow Engine (synchronous if fast, Celery if async)
    |  Step 1: crew_executor.py builds CrewAI Crew from agents.yaml
    |    - Loads invoice_processor agent config
    |    - Resolves tools: [pdf-reader, spreadsheet-writer]
    |    - System prompt: prompts/invoice-extractor.txt
    v
CrewAI Crew.kickoff()
    |  Agent calls pdf-reader tool
    v
Tool Registry → Plugin Runtime (pdf_reader subprocess)
    |  JSON-RPC: {file_path: "/files/invoice.pdf"}
    |  Docling parses → text + tables
    |  Returns structured JSON
    v
CrewAI Agent (Qwen 2.5 14B via LiteLLM → Ollama)
    |  Extracts fields, formats output
    v
Tool Registry → Plugin Runtime (spreadsheet_writer subprocess)
    |  XlsxWriter writes /files/output/invoice-data.xlsx
    v
Core API
    |  Streams result tokens back via SSE
    v
Open WebUI Pipelines
    |  Streams tokens to chat interface
    v
User sees: "Processed 3 invoices → invoice-data.xlsx saved"
```

### Chat Message Flow (Freeform)

```
User types "find all emails from ACME about pricing"
    |
    v
Open WebUI Pipelines → Core API → Skill Matcher
    |  No named skill match
    v
crew_executor.py — freeform mode
    |  Builds single-agent Crew with all enabled tools
    |  Uses qwen2.5:14b via LiteLLM → Ollama
    v
CrewAI agent reasons: uses email-client tool
    |  Searches IMAP for "ACME pricing"
    |  Returns email summaries
    v
Agent formats response → streams back to Open WebUI
```

### Document Ingestion Flow (File Watcher Trigger)

```
New file lands in /files/inbox/
    |
    v
File Watcher service (watchdog polling)
    |  Detects new file: invoice.pdf
    v
Publishes event to Redis
    |
    v
Celery Worker picks up task
    |
    v
ingestion/router.py — MIME detection
    |  PDF → Docling parser
    v
ingestion/parsers.py — Docling + PaddleOCR
    |  Extracts text, tables, metadata
    v
ingestion/chunker.py — LlamaIndex chunking
    |
    v
ingestion/embedder.py — sentence-transformers
    |
    v
Qdrant — stores chunks + embeddings in client collection
    |
    v
Classification agent (gemma3:4b via LiteLLM)
    |  Assigns category, year, document type
    v
PostgreSQL — records: file path, classification, processing status
    |
    v
(Optional) Trigger downstream workflow if rule matches
```

### Config Loading Flow

```
Core API startup
    |
    v
config_loader.py reads /config/agents.yaml, /config/workflows.yaml, /config/tools.yaml
    |  Validates against Pydantic models (fail fast on bad config)
    v
Tool Registry scans /plugins/ for plugin.yaml manifests
    |  Registers only tools listed in client tools.yaml (enable/disable per client)
    v
CrewAI agent instances pre-warmed (or loaded per-request — see anti-patterns)
    |
    v
First request ready to serve
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Open WebUI | Pipelines (custom pipe class); POST /chat/completions from WebUI → Core API | One pipe file handles routing; WebUI sees Core API as an OpenAI-compatible model |
| Ollama | OpenAI-compatible HTTP API at :11434; accessed via LiteLLM proxy | Never call Ollama directly from Core API — always via LiteLLM for model routing |
| LiteLLM | HTTP proxy at :4000; configured with litellm_config.yaml listing Ollama model aliases | Single routing point for all LLM calls — swap models without touching agent code |
| IMAP / Gmail / O365 | email_client plugin abstracts all three; credentials in client.env | Per-client config selects protocol; Core API never touches email directly |
| NotebookLM MCP | MCP client in Core API; pushes sources, retrieves generated content | Future integration; MCP protocol means swap to other MCP servers if needed |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Open WebUI Pipelines ↔ Core API | HTTP (OpenAI Chat Completions format + SSE for streaming) | Pipelines translate WebUI format to Core API format |
| Core API ↔ Plugin Runtime | JSON-RPC over subprocess stdin/stdout | Plugins never import from Core API; fully isolated |
| Core API ↔ Celery Workers | Redis broker (task messages) + PostgreSQL (results) | Workers are stateless; pull config from shared config volume |
| Core API ↔ LiteLLM | HTTP :4000 (OpenAI-compatible) | LiteLLM config maps model aliases to Ollama endpoints |
| LiteLLM ↔ Ollama | HTTP :11434 (native Ollama API) | LiteLLM handles retries, fallbacks, load balancing |
| CrewAI ↔ Tools | Python function calls via `@tool` decorator registered by Tool Registry | CrewAI passes tool name + JSON args; registry routes to subprocess |

---

## Build Order (Phase Dependencies)

The components have hard dependencies that dictate build order:

```
Phase 1 — Foundation (no dependencies)
  Docker Compose skeleton
  Ollama + LiteLLM serving (models loaded, API verified)
  Config loader + Pydantic validation (agents.yaml, workflows.yaml parsing)

Phase 2 — Core API (depends on Phase 1)
  FastAPI app skeleton
  LiteLLM integration (can call models)
  Minimal CrewAI executor (freeform agent, no tools yet)
  Open WebUI Pipelines connector (chat works end-to-end, even if basic)

Phase 3 — Tool System (depends on Phase 2)
  Plugin manifest format + Tool Registry
  First plugin: pdf-reader (Docling + PaddleOCR)
  CrewAI tool integration (agent can call pdf-reader)
  Skill Matcher (named skills dispatch)

Phase 4 — Document Ingestion + RAG (depends on Phase 3)
  Ingestion pipeline (router → parser → chunker → embedder → Qdrant)
  LlamaIndex RAG query plugin
  File watcher service + Celery async execution

Phase 5 — Business Plugins (depends on Phase 3)
  email-client plugin (IMAP first, then Gmail/O365)
  spreadsheet-writer plugin (XlsxWriter + pandas)
  Workflow engine (YAML DAG execution, depends_on chains)

Phase 6 — Polish (depends on all above)
  NotebookLM MCP integration
  Autonomy controls (confirm-first vs auto-execute per workflow)
  Health checks, structured logging, deployment packaging (deploy.sh)
```

**Rationale for this order:**
- LLM serving must work before any agent can reason
- Config loader must work before any YAML is consumed
- Open WebUI pipeline connection is Phase 2 (not Phase 1) because you need the FastAPI endpoint to exist first
- RAG depends on the ingestion pipeline, which depends on plugins — cannot skip Phase 3
- Business plugins (email, spreadsheet) can be built in parallel after Phase 3 but blocked by the tool registry existing

---

## Anti-Patterns

### Anti-Pattern 1: Direct Plugin Import in Core API

**What people do:** Import PDF reader, email client, etc. directly into the FastAPI app rather than using subprocess isolation.

**Why it's wrong:** A crashing plugin brings down the entire Core API. Heavy libraries (PaddleOCR, pandas) balloon the Core API image. Can't enable/disable plugins per client without rebuilding.

**Do this instead:** Subprocess JSON-RPC. Core API never imports plugin code. Plugin crashes return an error JSON; Core API handles gracefully.

### Anti-Pattern 2: Calling Ollama Directly from CrewAI

**What people do:** Set `llm="ollama/qwen2.5:14b"` directly in CrewAI agent config, bypassing LiteLLM.

**Why it's wrong:** Locks each agent to a hardcoded model path. Switching models for a client requires editing code or many YAML entries. No centralized routing, retry, or fallback logic.

**Do this instead:** All LLM calls go through LiteLLM at :4000. Agents reference model aliases (`model: agent-reasoning`). LiteLLM config maps aliases to actual Ollama models. Swapping models = update litellm_config.yaml, no agent YAML changes.

### Anti-Pattern 3: Loading All Agents at Startup

**What people do:** Pre-instantiate every CrewAI Agent on startup to reduce per-request latency.

**Why it's wrong:** CrewAI agents hold references to LLM connections. Large client configs with many agents will consume memory at idle — violates the "stay out of the way" constraint for everyday client machines.

**Do this instead:** Load and validate config at startup (parse YAML, catch errors early), but instantiate CrewAI Crew/Agent objects per-request. Latency impact is negligible (~10ms) for YAML parsing at request time.

### Anti-Pattern 4: Synchronous Long-Running Workflows in Request Thread

**What people do:** Run file-processing workflows (scan 500 emails, OCR 100 PDFs) synchronously in the FastAPI route handler.

**Why it's wrong:** Request times out. Open WebUI shows error. Client thinks it failed.

**Do this instead:** Submit to Celery immediately; return a job ID. Open WebUI pipeline polls `/jobs/{id}/status`. When done, streams the result. Chat shows "Processing 500 emails… done. Found 12 relevant threads."

### Anti-Pattern 5: Storing Client Credentials in agents.yaml

**What people do:** Put IMAP passwords, email addresses, or API keys directly in the YAML config files for convenience.

**Why it's wrong:** Config files get committed to version control. Credentials leak.

**Do this instead:** Credentials always in `client.env` (git-ignored). Config YAML references env var names: `email_password: "${ACME_EMAIL_PASSWORD}"`. Core API resolves via `os.environ` at runtime.

---

## Scaling Considerations

This platform runs on a single client machine — the relevant "scaling" axis is resource consumption, not horizontal scaling.

| Concern | Idle | Light Use (1-2 concurrent tasks) | Heavy Use (batch jobs) |
|---------|------|----------------------------------|------------------------|
| RAM | ~4GB (all containers up, models loaded) | ~8-12GB (model active) | ~12-20GB (model + ingestion pipeline) |
| GPU VRAM | ~10GB (qwen2.5:14b loaded) | ~10-13GB (inference active) | ~10-13GB (same — Ollama serializes requests) |
| CPU | <5% (idle polling) | 20-40% (OCR, embedding) | 60-80% (batch OCR + embedding) |

**First bottleneck:** Concurrent LLM requests. Ollama queues requests; only one runs at a time per model. Mitigation: classification tasks use gemma3:4b (fast, small) so the 14B model is free for agent reasoning.

**Second bottleneck:** Disk I/O during batch ingestion. Large client with 10K+ documents will saturate disk during initial RAG indexing. Mitigation: throttle the file watcher batch size; run initial indexing as a scheduled off-hours job.

**Out of scope for v1:** Horizontal scaling, multi-GPU, multiple clients on one machine. Each client gets their own Docker stack on their own machine.

---

## Sources

- [CrewAI Documentation](https://docs.crewai.com/)
- [CrewAI YAML Configuration Guide](https://codesignal.com/learn/courses/getting-started-with-crewai-agents-and-tasks/lessons/configuring-crewai-agents-and-tasks-with-yaml-files)
- [Open WebUI Pipelines](https://docs.openwebui.com/features/extensibility/pipelines/)
- [Open WebUI Pipelines GitHub](https://github.com/open-webui/pipelines)
- [LiteLLM Documentation](https://github.com/BerriAI/litellm)
- [Dify Plugin System Design](https://dify.ai/blog/dify-plugin-system-design-and-implementation)
- [AWS Agentic AI Architecture Patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/introduction.html)
- [Microsoft AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [CrewAI + FastAPI Integration Guide](https://halilural5.medium.com/building-smarter-apis-a-guide-to-integrating-crewai-with-fastapi-e0f4b69cbb34)
- [Open WebUI + FastAPI Agent Guide](https://medium.com/@emiljohansson0211/easy-guide-on-how-to-make-an-ai-agent-with-fastapi-and-open-webui-3acef4c54354)
- Source research: `cerebro 2.0/maai-software-inc/10 - Generic AI Agent Platform Research.md`

---
*Architecture research for: MAAI Agent Platform (config-driven local AI agent system)*
*Researched: 2026-04-06*
