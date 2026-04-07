# Project Research Summary

**Project:** MAAI Agent Platform
**Domain:** Config-driven local AI agent platform (Docker-deployed, privacy-first, per-client YAML)
**Researched:** 2026-04-07
**Confidence:** HIGH

## Executive Summary

The MAAI Agent Platform is a locally-deployed, config-driven AI agent system that runs entirely on a client machine inside Docker. The dominant architecture pattern for this class of product is a layered stack: Open WebUI as the chat surface, a FastAPI Core API as the orchestration hub, CrewAI as the YAML-driven agent executor, LiteLLM as the LLM routing proxy, and Ollama as the local model server. This stack is well-validated by 2026 community practice. The core competitive differentiator is YAML-driven skills with per-client config isolation, uniquely achievable with CrewAI as the only major agent framework offering first-class YAML config support. Every major alternative (Dify, FlowiseAI, AnythingLLM) uses a visual workflow builder, not declarative config files.

The recommended approach is to build the platform in clear dependency order: infrastructure and LLM serving first, then a minimal end-to-end chat path, then the tool/plugin system, then document ingestion and RAG, then business-specific plugins (email, spreadsheets). Each phase validates the layer below before the next is added. The critical insight from combined research is that the Skills System (YAML-driven named tasks) is the architectural foundation for every differentiating feature. Configurable autonomy, per-client tool enable/disable, and the freeform fallback all depend on it. Build this early.

The top risk is integration reliability between components with well-known failure modes in this exact combination. CrewAI silently defaults to OpenAI embeddings (breaking RAG without an OpenAI key), Ollama streaming drops tool calls (silently breaking all agent tool use), and Docker Desktop on Windows does not propagate inotify events (silently breaking file watching). All three failures are invisible at startup, surface only at runtime, and each takes significant debugging time. The mitigation strategy is explicit smoke tests for each integration point at the end of every build phase.

---

## Key Findings

### Recommended Stack

The stack is fully decided and version-pinned with high confidence. Python 3.11 is the stable sweet spot for the ML ecosystem as 3.12+ has known packaging issues with PaddleOCR and other ML dependencies. CrewAI 1.13.x is the only major agent framework with native YAML config support. LiteLLM must be pinned to >=1.83.0 as versions 1.82.7 and 1.82.8 were backdoored in a confirmed March 2026 supply chain attack and yanked from PyPI.

**Core technologies:**
- **Python 3.11**: Runtime -- stable LTS sweet spot; avoid 3.12/3.13 for ML ecosystem compatibility
- **CrewAI 1.13.x**: Agent orchestration -- only framework with first-class YAML agent/task/tool config
- **Ollama 0.20.x**: Local LLM serving -- single binary, OpenAI-compatible REST, GPU/CPU auto-detection
- **Open WebUI 0.8.12**: Chat interface -- eliminates custom frontend; native Ollama plus tool calling
- **LiteLLM >=1.83.0**: LLM routing proxy -- centralized model routing; CRITICAL: avoid 1.82.7/1.82.8 (backdoored March 2026 supply chain attack)
- **Qdrant 1.13.x+**: Vector database -- superior filtering for per-client RAG isolation; single-binary Docker
- **Docling 2.84.x + PaddleOCR 3.0.x**: Document parsing -- broadest format support plus highest-accuracy OCR for tables/forms
- **LlamaIndex 0.14.x**: RAG pipeline -- chunking, embedding management, Qdrant integration
- **FastAPI 0.115.x + ARQ 0.26.x**: Internal API plus async task queue -- agent triggers and background job execution
- **Docker Compose V2**: Deployment -- docker compose up (V2 plugin); standalone docker-compose binary is EOL
- **LLM models**: Qwen3 14B for agent reasoning (performs at Qwen2.5-32B level); Gemma 3 4B for classification

### Expected Features

**Must have (table stakes):**
- Persistent chat history -- Open WebUI handles natively
- Multi-turn conversation context -- LLM context window plus CrewAI memory
- File upload to chat plus document Q/A (RAG) -- Open WebUI native plus Docling plus Qdrant
- PDF summarization -- first client primary use case
- Natural language task invocation -- Skills pattern with freeform fallback
- Docker single-command deploy -- without this client adoption is blocked
- Local/private processing -- entire stack on-premise, no external data transmission
- Tool calling / function execution -- CrewAI tool system via Ollama function calling

**Should have (competitive differentiators):**
- Config-driven skills (YAML) -- pre-configured named tasks; unique in market vs visual-builder competitors
- Per-client config isolation -- same container image, different YAML behavior; enables consulting model
- Plugin-based tool enable/disable -- toggle per client without code changes
- Configurable autonomy per skill -- auto-execute vs confirm-first per workflow; no competitor does this in YAML
- Email integration (IMAP/Gmail/O365) -- first-class configured skill, not a visual workflow node
- File system watching -- passive automation via local folder monitor; no self-hosted chat-first competitor has this
- Spreadsheet generation from documents -- extract structured data to xlsx
- RAG knowledge base per client -- persistent isolated Qdrant collections across sessions
- OCR for scanned documents -- PaddleOCR via Docling; critical for older business documents

**Defer (v2+):**
- Cloud storage sync (Google Drive, OneDrive) -- breaks local-only guarantee; adds OAuth complexity
- Visual workflow builder -- defeats YAML-config simplicity; clients should never edit flows
- White-label branding -- no client has asked; consulting relationship makes MAAI branding acceptable
- Network drive / NAS support -- mount and permission complexity; local filesystem covers first client
- Multi-tenant SaaS -- requires fundamental architecture change; premature

### Architecture Approach

The system uses a strict layered architecture. Open WebUI connects to a stateless FastAPI Core API via an Open WebUI Pipelines connector. The Core API owns skill dispatch (named match or freeform fallback), CrewAI orchestration, and the plugin/tool registry. All LLM calls route through a LiteLLM proxy to Ollama -- never direct. Tools run as isolated subprocesses communicating via JSON-RPC. Long-running workflows run asynchronously via ARQ plus Redis. Per-client behavior is entirely driven by YAML config files mounted as Docker volumes -- no code changes per client.

**Major components:**
1. **Open WebUI + Pipelines connector** -- chat interface; bridges WebUI to Core API via OpenAI-compatible format
2. **Core API (FastAPI)** -- stateless orchestration hub; skill matcher, CrewAI executor, tool registry, config loader
3. **Skill Matcher** -- named skill dispatch vs freeform agent; the intelligence routing layer
4. **Plugin Runtime (subprocess + JSON-RPC)** -- isolated tool execution; plugin crashes do not kill Core API
5. **LiteLLM proxy** -- centralized LLM routing; all model swaps happen here, not in agent code
6. **Ollama** -- local LLM server; Qwen3 14B for reasoning, Gemma 3 4B for classification
7. **Document Ingestion Pipeline** -- Docling plus PaddleOCR to LlamaIndex chunking to Qdrant embedding
8. **Qdrant** -- per-client vector collections; RAG with payload filtering for client isolation
9. **Config Volume** -- per-client YAML plus prompts as Docker bind mount; the extensibility mechanism

### Critical Pitfalls

1. **CrewAI defaults to OpenAI embedder** -- Explicitly set embedder to Ollama nomic-embed-text in every Crew using knowledge or memory. Never use a dummy OPENAI_API_KEY. Address in Foundation phase before any RAG is built.

2. **Ollama streaming drops tool calls** -- Disable streaming for all agent/tool-calling paths (stream=False on LiteLLM calls). Validate with a smoke test before building any workflow. Prefer Qwen3 for tool call format reliability.

3. **CrewAI infinite retry loop with local LLMs** -- Set max_iter=5 and max_execution_time per agent. Tune system prompts with explicit output format constraints. Log every retry at WARN level.

4. **Docker GPU starvation (Ollama + Docling/OCR concurrent)** -- Set OLLAMA_KEEP_ALIVE=0 during document processing; OLLAMA_MAX_LOADED_MODELS=1. Sequence LLM inference and OCR as non-concurrent steps.

5. **File watcher silent failure on Windows Docker Desktop** -- inotify events do not propagate from Windows host to WSL2 containers. Use watchdog with PollingObserver (1-5s latency) or run the watcher natively on Windows host and POST to the platform API.

6. **Open WebUI DNS resolution failure in Docker Compose** -- Always use OLLAMA_BASE_URL=http://ollama:11434 (service name); never localhost:11434 inside containers. Verify with health check at docker compose up time.

7. **CrewAI YAML KeyError on tool rename** -- Build a startup validation step that resolves all YAML tool references before accepting the first request. Fail fast on misconfiguration, not on first user request.

---

## Implications for Roadmap

Based on research, the architecture defines a strict dependency chain. Each phase is blocked until the previous is verified working.

### Phase 1: Infrastructure Foundation
**Rationale:** LLM serving and Docker networking must be verified before any application code. The two most painful pitfalls (Docker GPU starvation design, Open WebUI DNS failure) must be resolved here, not discovered later.
**Delivers:** Working docker compose up with Ollama plus Open WebUI connected; GPU confirmed active; LiteLLM proxy routing to correct Ollama models; config loader validating YAML with Pydantic models.
**Addresses:** Docker single-command deploy (table stakes); local/private processing (table stakes)
**Avoids:** Open WebUI DNS resolution failure (Pitfall 6); Docker GPU starvation design (Pitfall 4); LiteLLM supply chain risk (pin >=1.83.0); Docling plus PaddleOCR dependency conflict (separate containers from the start)

### Phase 2: Core API and End-to-End Chat
**Rationale:** Before agent logic, a minimal end-to-end chat path must work. This validates the Pipelines connector, FastAPI entry point, and basic CrewAI freeform agent. Also the phase to resolve the OpenAI embedder pitfall since it blocks all subsequent RAG work.
**Delivers:** User message to Open WebUI Pipelines to Core API to freeform CrewAI agent to Qwen3 14B via LiteLLM to response back to chat.
**Uses:** FastAPI, Open WebUI Pipelines, CrewAI, LiteLLM, Ollama
**Implements:** Core API chat route, crew_executor.py freeform mode, maai_pipeline.py
**Avoids:** CrewAI OpenAI embedder default (Pitfall 1 -- configure Ollama embedder now); loading all agents at startup (Anti-Pattern -- lazy instantiation from day one)

### Phase 3: Tool System and Skills
**Rationale:** The plugin/tool registry is the foundation for every differentiating feature. Skills dispatch, email, spreadsheet, and RAG all depend on it. This must exist before any named skill works. Also where Ollama tool-calling reliability must be smoke-tested.
**Delivers:** Plugin manifest format plus Tool Registry; pdf-reader plugin (Docling plus PaddleOCR); Skill Matcher (named skill dispatch from YAML); tool calling verified end-to-end with smoke test.
**Addresses:** YAML-driven skills system (differentiator); plugin-based tool enable/disable; PDF text extraction (table stakes)
**Avoids:** Ollama streaming drops tool calls (Pitfall 2 -- disable streaming, add smoke test); CrewAI YAML KeyError (Pitfall 7 -- startup validator at docker compose up); direct plugin import in Core API (subprocess JSON-RPC from day one)

### Phase 4: Document Ingestion and RAG
**Rationale:** RAG depends entirely on ingestion. Nothing can be queried until indexed. File watching feeds ingestion and belongs in the same phase. This phase completes the document organizer use case for the first client.
**Delivers:** Full ingestion pipeline (Docling plus PaddleOCR to LlamaIndex to Qdrant); per-client RAG knowledge base (isolated Qdrant collections); file classification skill; file system watching (PollingObserver for Windows compatibility).
**Addresses:** Document Q/A RAG (table stakes); OCR for scanned documents; per-client RAG knowledge base (differentiator); file system watching (differentiator); PDF summarization skill (v1 launch requirement)
**Avoids:** Qdrant in-memory mode (persistent volume from day one); fixed chunk size on short documents (section-aware chunking per document type); file watcher Windows silent failure (PollingObserver not inotify)

### Phase 5: Business Plugins and Workflow Engine
**Rationale:** Email and spreadsheet plugins share the tool registry from Phase 3. The workflow engine (ARQ DAGs) enables multi-step pipelines. Configurable autonomy is a safety gate required before any email or file operations touch real client data.
**Delivers:** email-client plugin (IMAP first, then Gmail/O365 adapters); spreadsheet-writer plugin (pandas plus openpyxl); workflow engine (YAML DAG execution with ARQ); configurable autonomy (auto-execute vs confirm-first per skill).
**Addresses:** Email integration (v1 launch requirement); spreadsheet generation (v1 launch requirement); configurable autonomy (v1 launch requirement)
**Avoids:** Synchronous long-running workflows in request thread (Anti-Pattern -- ARQ async submission with job status polling); credentials in agents.yaml (client.env only for all secrets)

### Phase 6: Polish and Production Readiness
**Rationale:** UX feedback, health checks, and deployment packaging wrap complete functionality. NotebookLM MCP integration is v1.x, not MVP. Per-client isolation verified with a second test client config.
**Delivers:** Intermediate agent progress streaming to Open WebUI (SSE); list skills built-in command; structured logging throughout; health checks on all services; deploy.sh packaging; per-client config isolation verified with second test client; NotebookLM MCP integration (v1.x).
**Addresses:** No progress feedback during long tasks (UX pitfall); skill discoverability (UX pitfall); cold start latency messaging (UX pitfall)
**Avoids:** Silent file processing failures (UX pitfall); rate limiting on task triggers (Security pitfall); per-client config bleed between deployments

### Phase Ordering Rationale

- LLM serving before app code: Ollama, LiteLLM, and Docker networking confirmed working before FastAPI is wired. The DNS pitfall is invisible at startup and wastes hours if not caught in Phase 1.
- Freeform chat before skills: A minimal end-to-end path validates the Pipelines connector before the more complex Skill Matcher is added. Forces the OpenAI embedder pitfall to be resolved at the right time.
- Tool registry before RAG: RAG is a plugin (rag-query). Ingestion writes to Qdrant via LlamaIndex. Neither works until the plugin system exists and tool calling is verified reliable (stream=False).
- Business plugins after ingestion: Email and spreadsheet plugins share tool infrastructure and are blocked by Phase 3. The workflow engine is required for multi-step pipelines.
- Polish last: Progress streaming, health checks, and deployment packaging require complete functionality to wrap.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Tool System):** Open WebUI Pipelines plus Core API integration is sparsely documented at implementation level. The exact Pipe class mechanics for routing to an external FastAPI endpoint need validation. LOW confidence from PITFALLS.md on this integration.
- **Phase 5 (Business Plugins):** Gmail OAuth vs IMAP token flows, O365 exchangelib vs Graph API choice, and whether ARQ supports YAML depends_on DAG chains need implementation-level research before execution.
- **Phase 4 (File Watching on Windows):** The host-side event bridge alternative needs a validated implementation pattern.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Docker Compose plus Ollama plus LiteLLM is well-documented with direct official sources. Straight implementation.
- **Phase 2 (Core API):** FastAPI plus CrewAI freeform agent is well-documented with multiple tutorials and official docs.
- **Phase 6 (Polish):** SSE streaming, health checks, structured logging -- standard patterns with no novel integrations.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI, GitHub releases, and official docs as of April 2026. LiteLLM supply chain issue confirmed by two independent sources. |
| Features | HIGH (table stakes) / MEDIUM (differentiators) | Table stakes cross-verified across Dify, FlowiseAI, Open WebUI, AnythingLLM. Differentiators are platform-specific with less standardized documentation. |
| Architecture | HIGH | Stack fully decided; patterns from CrewAI, Open WebUI, LiteLLM official docs. Component boundaries clearly defined with data flow diagrams. |
| Pitfalls | HIGH (tool calling, embedder defaults) / MEDIUM (GPU, RAG chunking) / LOW (Pipelines integration) | Pitfalls 1-3 backed by multiple GitHub issues. File watcher pitfall backed by documented Docker Issue #18246. Open WebUI-CrewAI direct integration patterns sparsely documented. |

**Overall confidence:** HIGH

### Gaps to Address

- **Open WebUI Pipelines implementation pattern:** The exact Pipe class implementation for routing to an external FastAPI endpoint is sparsely documented. Needs implementation validation in Phase 2. Reference: github.com/open-webui/pipelines.
- **ARQ DAG depends_on support:** Whether ARQ supports the YAML depends_on DAG pattern from ARCHITECTURE.md needs verification. If not, Celery may be required for Phase 5.
- **Docling + PaddleOCR container split:** Dependency conflict (PaddlePaddle vs PyTorch) requires separate containers. Must be reflected in Docker Compose design during Phase 1.
- **nomic-embed-text bootstrap:** The CrewAI embedder config requires nomic-embed-text available in Ollama. This model must be explicitly pulled in deployment bootstrap -- not pulled automatically with Qwen3 or Gemma 3.
- **Chunk size strategy per document type:** Fixed 1024-token chunking causes 30-40% retrieval accuracy loss on short structured documents. Section-aware chunking strategy must be designed per document type during Phase 4 planning.

---

## Sources

### Primary (HIGH confidence)
- CrewAI v1.13.0 release -- aiforautomation.io + CrewAI GitHub releases
- LiteLLM security update -- docs.litellm.ai/blog/security-update-march-2026
- LiteLLM supply chain attack -- thehackernews.com/2026/03/teampcp-backdoors-litellm-versions
- Ollama GitHub releases -- v0.20.x confirmed
- Open WebUI releases -- releasebot.io v0.8.12
- Qdrant v1.14 release -- qdrant.tech/blog/qdrant-1.14.x
- Docling PyPI -- v2.84.0; docling-ibm-models v3.13.0
- LlamaIndex PyPI -- v0.14.20 April 2026
- Qwen3 blog -- qwenlm.github.io/blog/qwen3 (14B vs 32B parity confirmed)
- CrewAI Issues #1797, #2033, #3622, #5387 -- OpenAI embedder default behavior
- Ollama Issue #5769 -- streaming drops tool_calls delta chunks
- Docker Issue #18246 -- inotify does not work with Docker volume mounts in VMs
- Open WebUI Issue #19376, Discussion #5903 -- Docker Compose DNS resolution

### Secondary (MEDIUM confidence)
- Open WebUI Pipelines GitHub -- github.com/open-webui/pipelines
- CrewAI vs LangGraph vs AutoGen 2026 -- Medium/data-science-collective
- Docker Compose for AI agents -- Docker blog (Compose V2 + resource limits)
- Dify, FlowiseAI, AnythingLLM feature surveys -- gptbots.ai, aiagentslist.com, toolhalla.ai
- FastAPI Background Tasks vs Celery -- markaicode.com

### Tertiary (LOW confidence)
- Open WebUI + CrewAI direct integration patterns -- community threads; implementation-level details sparse
- ARQ DAG depends_on support -- inferred from ARQ docs; needs implementation validation
- Docling + PaddleOCR container split pattern -- derived from pitfall analysis; not directly sourced

---
*Research completed: 2026-04-07*
*Ready for roadmap: yes*
