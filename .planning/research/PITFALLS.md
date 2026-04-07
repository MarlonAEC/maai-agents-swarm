# Pitfalls Research

**Domain:** Local AI agent platform — config-driven agents, Open WebUI, CrewAI, Ollama, Docker on consumer Windows desktop
**Researched:** 2026-04-06
**Confidence:** HIGH (tool calling / embedding defaults); MEDIUM (Docker GPU, file watching, RAG chunking); LOW (Open WebUI–CrewAI direct integration patterns)

---

## Critical Pitfalls

### Pitfall 1: CrewAI Silently Falls Back to OpenAI for Embeddings

**What goes wrong:**
CrewAI uses OpenAI's embedding endpoint as its default embedder for all knowledge sources, memory, and RAG-enabled tools. Even when you correctly configure a local Ollama LLM as the crew's LLM provider, the embedder is initialized separately. If `OPENAI_API_KEY` is absent or empty, the crew either throws a cryptic auth error at startup or silently fails to index any documents. This affects `TextFileKnowledgeSource`, `MDXSearchTool`, the built-in memory subsystem, and any tool that performs vector search.

**Why it happens:**
CrewAI was designed with OpenAI as the default provider. The embedder config path is separate from the LLM config path. YAML-only configs often omit the embedder block entirely because it is not prominently documented. GitHub Issues #1797, #2033, #3622, and #5387 all document this behavior persisting into late 2025.

**How to avoid:**
Explicitly set the embedder to Ollama in every crew that uses knowledge or memory. Add to `crew.py` or the relevant YAML:
```python
embedder={
    "provider": "ollama",
    "config": {"model": "nomic-embed-text", "base_url": "http://ollama:11434"}
}
```
Never set a dummy `OPENAI_API_KEY` as a workaround — it will pass validation but incur silent network calls if a code path misroutes.

**Warning signs:**
- Startup error: "Failed to init knowledge: Please provide an OpenAI API key"
- RAG queries return empty results despite documents being present
- `OPENAI_API_KEY` mentioned in logs when no OpenAI services are configured

**Phase to address:**
Foundation / core agent setup phase — must be validated before any RAG or memory feature is built on top.

---

### Pitfall 2: Ollama Tool Calling Drops via Streaming Protocol Bug

**What goes wrong:**
When a local model decides to invoke a tool, it emits the tool call as a structured JSON chunk in the streaming response. Ollama's streaming implementation (documented in GitHub Issue #5769) does not correctly return `tool_calls` delta chunks. The tool invocation is silently dropped — the agent appears to respond normally but the tool never executes. This is the primary reliability failure for agent workflows that depend on tool use.

**Why it happens:**
Ollama's streaming SSE protocol omits the `tool_calls` field in intermediate delta chunks. Frameworks that consume the streaming API (CrewAI via LiteLLM) receive incomplete data and treat the response as a plain text answer.

**How to avoid:**
- Disable streaming for all agent/tool-calling paths. Use `stream=False` on LiteLLM / Ollama calls made through CrewAI agents.
- Validate tool calling explicitly on target model and Ollama version before committing to a model selection.
- Prefer Qwen2.5 14B over Llama 3 or Mistral for tool calling reliability at the 14B tier. Qwen models handle OpenAI-compatible tool call format more reliably.
- Pin Ollama to a version where tool calling is confirmed working; test after every Ollama upgrade.

**Warning signs:**
- Agent says "I searched for X" but no tool execution appears in logs
- Agent provides answers that should have required tool output but gives plausible-sounding hallucinations instead
- Tool call errors only occur in streaming mode, not non-streaming

**Phase to address:**
Foundation phase — tool calling must be verified working before any workflow is built on it. Build a tool-call smoke test into the core integration tests.

---

### Pitfall 3: CrewAI Agent Infinite Retry Loop with Local LLMs

**What goes wrong:**
When a local model generates a response that fails CrewAI's output parser (e.g., attempts to emit both an Action and a Final Answer simultaneously, or produces malformed JSON for tool arguments), CrewAI retries the same prompt repeatedly until `max_iter` is reached. With weaker quantized local models, this loop can run to exhaustion on every request — consuming full VRAM time for minutes, producing no useful output, and blocking subsequent requests.

**Why it happens:**
CrewAI's ReAct-style agent loop expects strict output format from the LLM. Local models at 7B–14B scale with Q4 quantization frequently break format, especially under complex multi-step instructions or long context windows. The retry strategy escalates the same failing prompt without modifying it, making recovery unlikely.

**How to avoid:**
- Set `max_iter` to a low value (e.g., 5) per agent to prevent runaway loops.
- Use `max_execution_time` to cap total wall time per task.
- Tune system prompts to reinforce output format constraints. Add explicit negative examples ("Do not emit both Action and Final Answer").
- Route classification tasks to the smaller Gemma 3 4B model; only use the 14B model for reasoning tasks that actually need it.
- Log every retry at WARN level so loops are visible immediately.

**Warning signs:**
- Log lines: "Error parsing LLM output, agent will retry" appearing more than twice in succession
- VRAM saturated for extended periods with no task completion
- Request queue depth growing while completed task count stays flat

**Phase to address:**
Core agent framework phase — before exposing agents to any real workflow, stress test with adversarial inputs that trigger format failures.

---

### Pitfall 4: Docker GPU Passthrough Breaks or Starves Sibling Containers

**What goes wrong:**
On consumer Windows with Docker Desktop + WSL2, GPU passthrough via `--gpus all` works for individual containers but does not enforce VRAM limits. When Ollama loads a 14B model (~10GB VRAM), it can consume nearly all available GPU memory on a 12–16GB card. Docling + PaddleOCR in a sibling container then fails to allocate GPU memory and silently falls back to CPU — or crashes entirely. The VRAM starvation is asymmetric: Ollama does not release memory until the `keep_alive` timer expires.

**Why it happens:**
Docker's `--gpus` flag selects which GPU a container can use but does not partition VRAM. Ollama's default `OLLAMA_KEEP_ALIVE=5m` holds models in VRAM after each inference. If a document processing job runs immediately after an LLM call, Ollama still holds the model and OCR has no GPU headroom.

**How to avoid:**
- Set `OLLAMA_KEEP_ALIVE=0` during document processing jobs, or use `ollama stop <model>` via the API before kicking off GPU-intensive OCR/Docling pipelines.
- Schedule LLM inference and OCR/document processing as non-concurrent steps in CrewAI task sequences.
- Set `OLLAMA_MAX_LOADED_MODELS=1` to prevent two models occupying VRAM simultaneously.
- Use `OLLAMA_GPU_OVERHEAD` to reserve headroom for the OS and other processes.
- During development, monitor with `nvidia-smi` or `rocm-smi` to catch silent CPU fallback early.

**Warning signs:**
- PaddleOCR processing time suddenly jumps from ~6s to ~30s per page (CPU fallback)
- Container logs show "CUDA out of memory" or "GPU memory allocation failed"
- `nvidia-smi` shows 100% VRAM used by a single process while another container is active

**Phase to address:**
Infrastructure / Docker Compose phase — resource management strategy must be designed before integrating Ollama and Docling/OCR into the same stack.

---

### Pitfall 5: Open WebUI to Ollama DNS Resolution Fails in Docker Compose

**What goes wrong:**
Open WebUI's default `OLLAMA_BASE_URL` is `http://localhost:11434`. Inside a Docker container, `localhost` refers to the container's own network namespace, not the host. If Ollama runs in a separate container or on the host, Open WebUI cannot connect, producing "Connection refused" or "No models available" errors. The failure is silent at startup — the UI loads but the model dropdown is empty or shows an error only on first use.

**Why it happens:**
Docker networking isolates containers by default. `localhost` inside a container is not the host. Open WebUI's default configuration assumes Ollama is co-located in the same container or on the host network, but Docker Compose puts each service in its own namespace unless `network_mode: host` or a shared network is explicitly configured.

**How to avoid:**
- In Docker Compose, put Open WebUI and Ollama on the same named network. Set `OLLAMA_BASE_URL=http://ollama:11434` using the service name.
- Set `OLLAMA_HOST=0.0.0.0:11434` and `OLLAMA_ORIGINS=*` on the Ollama container to allow cross-container connections.
- Never use `http://localhost:11434` in any container's environment variable unless `network_mode: host` is set.
- Smoke test connectivity at `docker compose up` time with a health check: `curl -f http://ollama:11434/api/tags`.

**Warning signs:**
- Open WebUI loads but shows "No models" or "Could not connect to Ollama"
- `docker compose logs open-webui` shows connection refused to 127.0.0.1:11434
- Models work when tested directly against the Ollama container but not through the UI

**Phase to address:**
Infrastructure / Docker Compose phase — verify this in the very first `docker compose up` before any application code is written.

---

### Pitfall 6: File Watcher Events Do Not Fire Inside Docker on Windows

**What goes wrong:**
The folder watching feature (monitor client directories for new files to process) relies on filesystem change events (inotify on Linux). On Windows, Docker Desktop runs Linux containers inside a WSL2 VM. Bind-mounted Windows host directories do not propagate inotify events into the container — the watcher never triggers despite files being added on the Windows host.

**Why it happens:**
The Linux kernel's inotify subsystem monitors the container-side filesystem. Windows NTFS change notifications are not translated to inotify events for bind mounts in Docker Desktop's WSL2 backend. This is a documented limitation going back to Docker Issue #18246 and remains unresolved as of 2025.

**How to avoid:**
- Use polling-based watching (`watchdog` with `polling=True` or `PollingObserver`) inside the container instead of inotify. Accept ~1–5 second detection latency.
- Alternatively, run the watcher process on the Windows host (as a native Python process or scheduled task) and POST to the platform's API when new files are detected — keeping the container fully event-driven via HTTP callbacks.
- Document this clearly in the deployment guide: inotify-based watchers will silently fail on Docker Desktop for Windows.

**Warning signs:**
- Files added to watched folder do not trigger processing
- Watcher logs show no events despite new files being present
- Watcher works in development (on Linux) but silently fails in client Docker Desktop deployment

**Phase to address:**
File processing / folder watch phase — verify on Windows Docker Desktop specifically, not just in Linux CI.

---

### Pitfall 7: CrewAI YAML Config Requires Code-Side Sync That Breaks at Runtime

**What goes wrong:**
CrewAI's YAML-driven config (`agents.yaml`, `tasks.yaml`) references Python objects (tool instances, LLM instances) by name. If a tool is renamed in Python code but not in the YAML, or if the YAML references a tool that is conditionally not instantiated for a given client, CrewAI throws a `KeyError` at crew startup — not at config load time, meaning the error surfaces only when the crew is first triggered. For a per-client deployment model where YAML varies per client, this is a recurring integration failure surface.

**Why it happens:**
The `@CrewBase` decorator maps YAML string references to live Python objects at instantiation time. There is no static validation step. Client-specific YAML configs that enable/disable tools via config flags can easily get out of sync with the tool registry.

**How to avoid:**
- Build a config validation step that runs on `docker compose up` and fails fast if any YAML tool reference cannot be resolved. Do not wait for first user request to discover this.
- Enforce a naming convention: tool class names and YAML `tool_name` values must match exactly and be checked by a unit test.
- For optional tools (enabled per client), implement a tool registry that provides no-op stubs for disabled tools rather than omitting them from the namespace entirely.

**Warning signs:**
- `KeyError` in CrewAI logs on first crew execution after YAML change
- "Config files: Agents and Tasks" errors in startup logs
- Silent failures where agents complete tasks but skip tool steps without error

**Phase to address:**
Config system / YAML agent definition phase — config validation must be part of the startup sequence from day one.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Set `OPENAI_API_KEY=dummy` to silence CrewAI embedding errors | Stops startup error immediately | Masks the real misconfiguration; embedding silently uses wrong provider | Never — fix the embedder config properly |
| Use `network_mode: host` for Docker Compose instead of named networks | Eliminates DNS headaches quickly | Breaks on multi-host setups, security regression, hides real network config | Only in single-machine local dev, never in client deployment |
| Leave `OLLAMA_KEEP_ALIVE=-1` (always loaded) | Fast inference, no cold start | Locks VRAM permanently, starves OCR/Docling containers | Acceptable only if client has 24GB+ VRAM and no other GPU workloads |
| Fixed chunk size (1024 tokens) for all RAG documents | Simple to implement | 30–40% retrieval accuracy loss on short or highly structured documents | MVP only, must be tuned per document type before production |
| Polling file watcher with 5-second interval | Works on Windows Docker immediately | Misses rapid file bursts; high CPU overhead if watching many folders | Acceptable for MVP; replace with host-side event bridge for production |
| Skip tool call smoke tests in CI | Faster pipeline | Tool calling regressions go undetected across Ollama/model upgrades | Never — tool calling is the core reliability surface |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CrewAI + Ollama via LiteLLM | Using `model="ollama/llama3"` without explicit `base_url` — LiteLLM defaults to `localhost:11434` which fails inside Docker | Always pass `base_url="http://ollama:11434"` explicitly |
| CrewAI + Qdrant knowledge | Not setting embedder — defaults to OpenAI, causes auth error with no OpenAI key | Set `embedder={"provider": "ollama", "config": {...}}` at crew level and per tool |
| Open WebUI + CrewAI backend | Trying to wire CrewAI directly as a "model" in Open WebUI | Expose CrewAI via an OpenAI-compatible API endpoint (FastAPI wrapper); Open WebUI connects to it as a custom model |
| Docling + PaddleOCR in same container | Installing both in the same Python environment causes dependency conflicts (PaddlePaddle vs PyTorch versions) | Run Docling and PaddleOCR in separate containers; use HTTP APIs between them |
| Ollama + Docker GPU | Using `docker-compose.yml` without NVIDIA runtime config — GPU silently unused | Add `runtime: nvidia` and `NVIDIA_VISIBLE_DEVICES: all` to Ollama service |
| LiteLLM proxy + multiple Ollama models | Not configuring per-model `api_base` in `litellm_config.yaml` — all models route to wrong endpoint | Define separate model entries with explicit `api_base` per model in LiteLLM config |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading two Ollama models simultaneously | Second model load causes first to unload mid-task; queue backup | Set `OLLAMA_MAX_LOADED_MODELS=1`; sequence tasks that use different models | Any time a 14B classification task and 4B summarization task overlap |
| Long context windows in RAG | VRAM spikes from KV cache; 14B model at 32K context needs ~18GB VRAM | Cap context per agent; use retrieval to pass only relevant chunks | >8K tokens context on a 12GB VRAM card |
| PaddleOCR without GPU | ~30s per page (CPU) vs ~6s per page (GPU) | Ensure GPU is properly passed through; log inference time at WARN if >10s | First page after GPU starvation by Ollama |
| RAG with fixed 1024-token chunks on short documents | Chunks larger than document sections; retrieval returns irrelevant context | Use sentence-aware or section-aware chunking for client documents | Any document with sections shorter than 1024 tokens |
| Qdrant in-memory mode for large document sets | Collection exceeds RAM; Qdrant crashes silently | Use persistent storage mode with Docker volume from day one | >1000 documents at 1536-dimensional embeddings |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing `WEBUI_ADMIN_PASSWORD` in plain-text `docker-compose.yml` | Credential exposed in version control or shared config files | Use Docker secrets or `.env` file excluded from git; inject at deployment time |
| Exposing Open WebUI on `0.0.0.0:3000` on client machine with no auth | Anyone on the local network can access the AI interface and all client documents | Bind to `127.0.0.1:3000` only; require WEBUI auth even for local deployment |
| Mounting entire client home directory as a Docker volume | Agent can read/write all user files, not just designated work folders | Mount only specific subdirectories (e.g., `/data/watch`, `/data/output`); use read-only mounts where write is not needed |
| API credentials in `agents.yaml` or `prompts/` YAML files | YAML committed to version control leaks credentials | All secrets go in `client.env` only; YAML config must not contain any credential values |
| No rate limiting on CrewAI task triggers from Open WebUI | Malicious or accidental rapid task submission exhausts resources | Implement per-session task queue; reject new task if one is already running per user |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress feedback during long agent tasks | User sees nothing for 30–120 seconds, assumes the system is broken, submits duplicate requests | Stream intermediate agent thoughts/steps to Open WebUI via SSE; show "Agent is working: [step]" |
| Cold start latency on first message | First message after idle takes 15–30 seconds to load model — no indication of why | Show a "Loading model..." status message; pre-warm the primary model on container startup |
| Freeform chat fails on requests that match a skill by keyword | User says "summarize my emails" and gets a generic chat response instead of the email summary skill | Implement intent detection that routes to skill before falling through to freeform |
| Silent file processing failures | Client drops PDF into watched folder, nothing happens, no feedback | Emit a processing event to Open WebUI on file detection and on completion/failure; never silently discard |
| Skill names not discoverable | Client doesn't know what skills exist; types freeform and gets worse results | Show available skills on chat load; support "list skills" as a built-in command |

---

## "Looks Done But Isn't" Checklist

- [ ] **Tool calling:** Model generates the right text but tool never executed — verify tool execution appears in CrewAI task output logs, not just the final answer
- [ ] **RAG knowledge base:** Query returns results but they are from wrong document — verify collection name isolation per client, not a shared Qdrant collection
- [ ] **File watcher:** Watcher process starts without error — verify by dropping a test file and confirming a processing event fires within expected polling interval
- [ ] **GPU acceleration:** Ollama reports GPU in `ollama show` — verify with `nvidia-smi` that VRAM is actually allocated (not CPU fallback)
- [ ] **CrewAI YAML config:** Crew instantiates without error — verify by triggering a task that uses every configured tool, not just the crew constructor
- [ ] **Email integration:** IMAP connection succeeds — verify folder enumeration, search, and attachment download all work; auth success does not mean full access
- [ ] **Docker Compose restart:** `docker compose restart` brings all services back healthy — verify Qdrant collection data persists across restarts (volume not ephemeral)
- [ ] **Per-client config isolation:** Deploying second client config — verify first client's agents.yaml, prompts, and Qdrant collection are untouched

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| OpenAI embedder default blocked RAG from working | MEDIUM | Add embedder config to crew and all tools; re-index all documents (Qdrant collection must be recreated with correct embeddings) |
| Infinite agent loop filled disk with logs | LOW | Cap log file size with Docker `--log-opt max-size`; set `max_iter` per agent; restart container |
| GPU starvation broke OCR jobs silently | LOW | Sequence tasks so Ollama unloads before OCR runs; verify with `nvidia-smi` spot check |
| Client YAML broke tool name sync | LOW | Add startup validation script; fix YAML reference; no data migration needed |
| File watcher never fired on Windows | MEDIUM | Replace inotify watcher with polling observer or host-side event bridge; no historical files are lost but reprocessing may be needed |
| Qdrant data lost after container restart | HIGH | Restore from document re-ingestion (no backup); add persistent volume immediately; implement nightly collection snapshot going forward |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CrewAI defaults to OpenAI embedder | Foundation: core agent setup | Unit test: instantiate crew with no `OPENAI_API_KEY`; verify no auth errors |
| Ollama tool calling drops via streaming | Foundation: tool calling integration | Smoke test: trigger a tool call and assert tool execution log appears |
| CrewAI infinite retry loop | Core agent framework | Integration test: submit malformed prompt; assert loop terminates within `max_iter` |
| Docker GPU starvation | Infrastructure: Docker Compose | Load test: run Ollama inference then OCR job back-to-back; assert OCR uses GPU |
| Open WebUI DNS resolution failure | Infrastructure: Docker Compose | Health check at `docker compose up`: curl from Open WebUI container to Ollama |
| File watcher silent on Windows | File processing feature phase | Manual test on Windows Docker Desktop: drop file, assert event fires within 10s |
| CrewAI YAML KeyError on tool rename | Config system phase | Startup validator: resolve all YAML tool refs before accepting first request |

---

## Sources

- [CrewAI Issue #1797 — Default embedder uses OpenAI even with Azure config](https://github.com/crewAIInc/crewAI/issues/1797)
- [CrewAI Issue #3622 — MDXSearchTool requires OpenAI key with Ollama LLM](https://github.com/crewAIInc/crewAI/issues/3622)
- [CrewAI Issue #2033 — Knowledge source ignores custom embedder](https://github.com/crewAIInc/crewAI/issues/2033)
- [CrewAI Community — Agents loop infinitely](https://community.crewai.com/t/agents-keeps-going-in-a-loop/1053)
- [CrewAI Issue #983 — Multiple LLMs cause infinite loop](https://github.com/crewAIInc/crewAI/issues/983)
- [CrewAI Issue #3031 — Ollama LLM not working with crewai agents](https://github.com/crewAIInc/crewAI/issues/3031)
- [CrewAI Community — KeyError parsing agents.yaml](https://community.crewai.com/t/keyerror-when-parsing-config-agents-yaml-file-in-a-trivial-crew-configuration/5073)
- [CrewAI Issue #2216 — Agent fails to pass endpoint to LiteLLM for Ollama](https://github.com/crewAIInc/crewAI/issues/2216)
- [Ollama Issue #5769 — Streaming doesn't return tool_calls delta chunks (referenced in OpenClaw research)](https://www.betterclaw.io/blog/openclaw-ollama-guide)
- [Ollama Issue #10597 — Unloading model doesn't free all GPU memory](https://github.com/ollama/ollama/issues/10597)
- [Ollama Issue #11812 — After VRAM spill, new model uses only CPU](https://github.com/ollama/ollama/issues/11812)
- [Open WebUI Issue #19376 — Docker Compose service does not resolve Ollama service name](https://github.com/open-webui/open-webui/issues/19376)
- [Open WebUI Discussion #5903 — Containerized WebUI cannot access non-containerized Ollama](https://github.com/open-webui/open-webui/discussions/5903)
- [Open WebUI Discussion #12161 — Native tool calling with streaming mode off does nothing](https://github.com/open-webui/open-webui/discussions/12161)
- [Docker Issue #18246 — inotify does not work with Docker volume mounts in VMs](https://github.com/moby/moby/issues/18246)
- [Docker Windows Volume Watcher — workaround tool for Windows inotify gap](https://github.com/merofeev/docker-windows-volume-watcher)
- [PaddleOCR Issue #10147 — Very slow inference in Docker vs conda](https://github.com/PaddlePaddle/PaddleOCR/issues/10147)
- [Docling Issue #440 — Configurable GPU VRAM limit for shared GPU environments](https://github.com/docling-project/docling-serve/issues/440)
- [Procycons PDF Extraction Benchmark 2025](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/)
- [Firecrawl — Best Chunking Strategies for RAG 2026](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [Ollama FAQ — keep_alive and model unloading](https://docs.ollama.com/faq)

---
*Pitfalls research for: Local AI agent platform — config-driven agents on consumer Windows hardware*
*Researched: 2026-04-06*
