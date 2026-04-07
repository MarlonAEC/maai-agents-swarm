# Feature Research

**Domain:** Local AI Agent Platform (Docker-deployed, config-driven, privacy-first)
**Researched:** 2026-04-06
**Confidence:** HIGH for table stakes (cross-verified across Dify, FlowiseAI, Open WebUI, AnythingLLM); MEDIUM for differentiators (platform-specific, less standardized)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Persistent chat history | Every chat interface (ChatGPT, Open WebUI, LibreChat) stores conversations; users will assume sessions are saved | LOW | Open WebUI handles this natively; don't re-implement |
| Multi-turn conversation context | Agents must remember what was said earlier in the same session | LOW | Handled by LLM context window + CrewAI memory primitives |
| File upload to chat | Open WebUI, Dify, AnythingLLM all support drag-drop files into chat | MEDIUM | Open WebUI supports this natively; backend parsing is the work |
| Document Q&A (RAG) | Users uploading PDFs expect to ask questions about them; this is now baseline for any AI assistant | MEDIUM | LlamaIndex + Qdrant; Docling for parsing |
| PDF text extraction | PDF summarization is the most common first use case for enterprise AI assistants | MEDIUM | Docling (IBM, MIT) handles multi-format including scanned via OCR |
| Natural language task invocation | Users must be able to describe what they want without knowing command syntax | MEDIUM | Skills pattern + freeform agent fallback covers this |
| Freeform chat (off-script requests) | Users will always go off-script; a system that only handles pre-configured tasks feels like a menu, not an assistant | MEDIUM | CrewAI agent with tools available as fallback when no skill matches |
| Docker single-command deploy | Any ops-heavy install process will block client adoption; `docker compose up` is the standard expectation for self-hosted tools | MEDIUM | Already in requirements; per-client compose file |
| Local/private processing | Client expectation for any "bring to my machine" product; data never leaving the machine is the core value prop | HIGH | Entire stack (Ollama, Qdrant, Docling) runs locally |
| Conversation-scoped document access | Documents uploaded in a session should be queryable within that session | LOW | Open WebUI handles per-conversation document attachment |
| Tool calling / function execution | Agents that can only generate text are limited; users expect agents to actually do things (search, run code, call APIs) | HIGH | CrewAI tool system; Ollama function calling support required |

### Differentiators (Competitive Advantage)

Features that set this platform apart from Dify, FlowiseAI, or Open WebUI used standalone. These align with the core value: "describe what you need, system executes it locally."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Config-driven skills (YAML) | Pre-configured named tasks that clients trigger by name or natural language match — like Claude Code `/project:do-thing`. No GUI builder needed, no code change per client | HIGH | CrewAI is the only major framework with full YAML-driven agent/task/tool config. This is the core architectural differentiator vs Dify (visual) and FlowiseAI (visual) |
| Per-client config isolation | Each client gets their own `agents.yaml`, `workflows.yaml`, `prompts/`, `client.env` — same container image, different behavior | MEDIUM | Enables consulting model: one platform, N client configs. Competitors ship one config per deployment |
| Plugin-based tool enable/disable | Turn specific tools on or off per client deployment without code changes | MEDIUM | YAML flag per tool; some clients need email, others don't. Dify/Flowise require rebuilding flows |
| Configurable autonomy per workflow | Some tasks auto-execute (file classification), others require human confirmation (send email, delete files). Per-workflow, not global | HIGH | Not standard in any platform reviewed. Dify has approval gates but they're per-node in a visual flow, not YAML-configurable |
| File system watching (local folder monitor) | Agents react to new files dropped in watched directories without user interaction. Passive automation. | HIGH | watchdog library; triggers classification/processing pipelines automatically. No competitor does this in a self-hosted chat-first product |
| Email integration (IMAP/Gmail/O365) | Search, summarize, draft responses from inbox directly in chat. First-class, not a bolt-on | HIGH | CrewAI + Gmail/IMAP tools; most platforms support this via workflow builder but not as a first-class configured skill |
| Spreadsheet generation from documents | Extract structured data from PDFs/emails, output to .xlsx | MEDIUM | openpyxl or pandas; bridges document processing to business output format |
| NotebookLM MCP integration | Push processed documents to NotebookLM for synthesis/presentation generation without rebuilding that capability | MEDIUM | Leverages existing MCP ecosystem; no competitor has this integration |
| LiteLLM routing proxy | Route different tasks to different local models (Qwen 14B for reasoning, Gemma 4B for classification) — cost/performance optimization per task | MEDIUM | Transparent to the agent layer; optimizes resource use on constrained hardware |
| RAG knowledge base per client | Each client's indexed documents are isolated and persistent across sessions — not per-conversation only | HIGH | Qdrant collections per client; enables "ask about all your company docs" not just "ask about this file" |
| OCR for scanned documents | Older business documents are scanned PDFs; platforms without OCR turn away this use case | MEDIUM | PaddleOCR via Docling pipeline; critical for first client (document organizer) |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but create disproportionate cost or risk for this platform.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Visual workflow builder (drag-drop) | Clients want to see and edit their automations visually, like Dify or n8n | Adds a full GUI application layer; defeats the YAML-config simplicity; client should never need to edit flows — MAAI configures them | YAML skills files are the config layer; MAAI consultant edits them, not the client |
| Multi-tenant SaaS with shared infrastructure | Operational simplicity of one deployment serving many clients | Client data isolation becomes a hard security problem; local-only guarantee evaporates; licensing model changes | One Docker instance per client — already decided |
| Cloud storage sync (Google Drive, OneDrive) | Clients have files in cloud storage | Requires OAuth flows, external API keys, breaks local-only guarantee, adds per-provider maintenance burden | v2 explicitly; focus on local filesystem first |
| Real-time streaming for every agent response | Feels faster and more alive | CrewAI multi-agent tasks are non-streaming by nature; forcing streaming requires custom buffering that adds fragility | Show task status/progress indicator instead; stream final output where possible |
| Custom branding / white-label per client | Clients want it to feel like their product | Frontend theming work that doesn't create agent capability value; distraction for v1 | Open WebUI supports basic customization; full white-label deferred to v2 |
| Mobile app | Accessibility on phones | Target use case is desktop automation (file organization, email on a work PC); mobile adds a full separate delivery surface | Desktop-only for v1 |
| Network drive / NAS support | Enterprise clients often have shared drives | Latency, permission complexity, mount point variability across OS; significantly harder than local path watching | v2; local filesystem first |
| Multi-model chat (simultaneous A/B) | Power users want to compare model outputs side by side | Doubles inference load on constrained hardware; not the target user workflow | Single-model routing through LiteLLM already handles model selection per task |
| Agent "memory" across all conversations globally | Persistent long-term memory that accumulates over time | Without careful scoping, global memory causes context bleed between unrelated tasks; hard to test, debug, and reset | Per-session context + explicit RAG knowledge base for intentional persistent knowledge |

---

## Feature Dependencies

```
[RAG Knowledge Base]
    └──requires──> [Document Ingestion Pipeline]
                       └──requires──> [Docling + OCR]
                       └──requires──> [Qdrant vector store]
                       └──requires──> [LlamaIndex embedding]

[Skills / YAML Config System]
    └──requires──> [CrewAI YAML agent/task loader]
    └──requires──> [Plugin-based tool registry]
                       └──required by──> [Email Integration]
                       └──required by──> [File Organization Tool]
                       └──required by──> [Spreadsheet Generation]

[Configurable Autonomy]
    └──requires──> [Skills System]
    └──requires──> [Human-in-the-loop confirmation UI in Open WebUI or pipeline]

[File System Watching]
    └──requires──> [File Classification Tool]
    └──requires──> [Document Ingestion Pipeline]
    └──enhances──> [RAG Knowledge Base] (auto-index new files)

[Email Integration]
    └──requires──> [Plugin-based tool system]
    └──enhances──> [Spreadsheet Generation] (extract email data to spreadsheet)

[Freeform Chat]
    └──requires──> [Tool calling via Ollama function calling]
    └──requires──> [Skills System] (skills are tried first; freeform is fallback)

[Per-client Config Isolation]
    └──requires──> [Docker Compose per-client structure]
    └──enables──> [Plugin enable/disable per client]
    └──enables──> [RAG Knowledge Base per client]

[NotebookLM MCP Integration]
    └──requires──> [Document Ingestion Pipeline] (processed docs are the source)
    └──requires──> [MCP server running locally]
```

### Dependency Notes

- **RAG requires Document Ingestion Pipeline:** You cannot query what isn't indexed. Docling + Qdrant must be operational before any RAG feature is usable.
- **Skills System requires CrewAI YAML loader:** The entire config-driven value prop depends on CrewAI's native YAML support. If CrewAI drops or degrades YAML config, this needs rearchitecting.
- **Configurable Autonomy requires Skills System:** Autonomy is a per-skill setting (`auto_execute: true/false`). Without skills, there's nothing to attach autonomy to.
- **File System Watching enhances RAG:** A watched folder that auto-ingests new files keeps the knowledge base current without user action — but file watching is functional without RAG.
- **Freeform Chat requires Skills first:** The architecture is skills-first, freeform fallback. Deploying freeform-only without skills defeats the platform value proposition.
- **Per-client Config Isolation enables Plugin enable/disable:** Per-client YAML is the mechanism by which tools are toggled. They are the same feature from different angles.

---

## MVP Definition

### Launch With (v1)

Minimum viable to validate with first client (document organizer use case).

- [ ] Docker Compose single-command deployment — without this nothing else matters
- [ ] Open WebUI chat interface backed by Ollama — primary user interaction surface
- [ ] YAML-driven skills system (CrewAI) — core architectural differentiator; proves the config-layer concept
- [ ] Per-client config folder structure — needed even for one client to prove the model
- [ ] Document ingestion pipeline (Docling + OCR + Qdrant) — first client's primary need
- [ ] RAG knowledge base (query indexed documents) — transforms ingestion into value
- [ ] File classification and organization tool — first client's explicit requirement
- [ ] PDF summarization skill — first client's explicit requirement; proves document processing
- [ ] Email search and summarization (IMAP) — first client's explicit requirement
- [ ] Spreadsheet generation from extracted data — first client's explicit requirement
- [ ] Configurable autonomy (auto-execute vs confirm-first per skill) — required for email/file operations; safety gate

### Add After Validation (v1.x)

Add once v1 is deployed and validated with first client.

- [ ] File system watching (local folder monitor) — adds passive automation; trigger: client asks "can it just watch my Downloads folder?"
- [ ] NotebookLM MCP integration — trigger: client has processed documents and wants presentation output
- [ ] Freeform chat fully tuned — v1 ships with basic freeform; tune based on what clients actually ask off-script
- [ ] LiteLLM routing optimization — trigger: performance complaints on constrained hardware

### Future Consideration (v2+)

Defer until product-market fit established.

- [ ] Cloud storage integrations (Drive, OneDrive) — why defer: breaks local-only simplicity; adds OAuth complexity
- [ ] White-label branding — why defer: no client has asked; consulting relationship makes MAAI branding acceptable
- [ ] Network drive / NAS support — why defer: adds mount/permission complexity; local filesystem handles first client
- [ ] Multi-tenant SaaS — why defer: requires fundamental architecture change; licensing model question unanswered
- [ ] Mobile app — why defer: desktop automation use case; mobile adds full separate delivery surface

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Docker single-command deploy | HIGH | MEDIUM | P1 |
| Open WebUI + Ollama chat | HIGH | LOW (existing tool) | P1 |
| YAML skills system (CrewAI) | HIGH | HIGH | P1 |
| Document ingestion (Docling + Qdrant) | HIGH | HIGH | P1 |
| RAG Q&A over indexed documents | HIGH | MEDIUM | P1 |
| PDF summarization skill | HIGH | MEDIUM | P1 |
| File classification + organization | HIGH | MEDIUM | P1 |
| Email integration (IMAP) | HIGH | HIGH | P1 |
| Spreadsheet generation | MEDIUM | MEDIUM | P1 |
| Configurable autonomy per skill | HIGH | MEDIUM | P1 |
| Per-client config isolation | HIGH | MEDIUM | P1 |
| Plugin enable/disable per client | MEDIUM | LOW | P1 |
| File system watching (watchdog) | MEDIUM | MEDIUM | P2 |
| Freeform chat tuning | MEDIUM | MEDIUM | P2 |
| NotebookLM MCP integration | MEDIUM | MEDIUM | P2 |
| LiteLLM model routing optimization | MEDIUM | MEDIUM | P2 |
| OCR for scanned PDFs | HIGH | LOW (via Docling/PaddleOCR) | P1 |
| Conversation history (persistent) | HIGH | LOW (Open WebUI native) | P1 |
| White-label branding | LOW | HIGH | P3 |
| Cloud storage integrations | LOW | HIGH | P3 |
| Network drive / NAS | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1 launch
- P2: Add post-validation, before second client
- P3: Future consideration, v2+

---

## Competitor Feature Analysis

| Feature | Dify | FlowiseAI | Open WebUI (standalone) | AnythingLLM | MAAI Platform |
|---------|------|-----------|------------------------|-------------|---------------|
| Chat interface | Yes (built-in) | Embedded chat widget | Yes (primary surface) | Yes (workspace-based) | Open WebUI (reused) |
| Agent configuration | Visual workflow builder | Visual node graph | Pipeline plugins | Agent builder (GUI) | YAML files (config-driven) |
| RAG / document Q&A | Yes, native | Yes, native | Yes, native | Yes (workspace-scoped) | LlamaIndex + Qdrant (per-client) |
| Multi-LLM routing | Yes (100+ providers) | Yes (most providers) | Yes (Ollama + OpenAI API) | Yes | LiteLLM proxy (local models only) |
| Local/offline capable | Partial (self-hosted but cloud features) | Partial (self-hosted) | Yes (Ollama) | Yes (Ollama) | Full — no external deps |
| File system watching | No | No | No | No | Yes (differentiator) |
| Per-client config isolation | No (multi-workspace, not per-deploy) | No | No | Workspace isolation | Yes (per Docker instance) |
| Configurable autonomy per task | Approval nodes in visual flow | Human-in-loop node | No | No | YAML flag per skill |
| Email integration | Via HTTP/webhook node | Via tool node | No | No | First-class IMAP/Gmail tool |
| Spreadsheet generation | Via code node | Via custom tool | No | No | First-class skill output |
| Skills / named task triggers | No | No | No | No | Core feature (differentiator) |
| Single `docker compose up` deploy | Partial (multi-service) | Yes | Yes | Yes | Yes |
| YAML-only config (no GUI needed) | No | No | Partially (config files) | No | Yes (differentiator) |

---

## Sources

- [Dify — Leading Agentic Workflow Builder](https://dify.ai/)
- [Dify AI Review (2026): Features, Alternatives, and Use Cases](https://www.gptbots.ai/blog/dify-ai)
- [Flowise — Build AI Agents, Visually](https://flowiseai.com/)
- [Flowise Review 2026](https://aiagentslist.com/agents/flowise)
- [n8n vs. Flowise: AI Agent Frameworks Comparison](https://oxylabs.io/blog/n8n-vs-flowise)
- [Open WebUI — RAG Documentation](https://docs.openwebui.com/features/chat-conversations/rag/)
- [Open WebUI — Pipelines Plugin Framework](https://github.com/open-webui/pipelines)
- [Open WebUI vs AnythingLLM vs LibreChat: Best Self-Hosted AI Chat in 2026](https://toolhalla.ai/blog/open-webui-vs-anythingllm-vs-librechat-2026)
- [Dify vs Open-WebUI 2025: Complete Comparison](https://markaicode.com/dify-vs-open-webui-comparison-2025/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [How to Build Multi-Agent RAG Systems with CrewAI](https://ragaboutit.com/how-to-build-multi-agent-rag-systems-with-crewai-the-complete-enterprise-implementation-guide/)
- [CrewAI Framework 2025: Complete Review](https://latenode.com/blog/ai-frameworks-technical-infrastructure/crewai-framework/crewai-framework-2025-complete-review-of-the-open-source-multi-agent-ai-platform)
- [The State of AI Agent Platforms in 2025: Comparative Analysis](https://www.ionio.ai/blog/the-state-of-ai-agent-platforms-in-2025-comparative-analysis)
- [AI Agent Anti-Patterns Part 1: Architectural Pitfalls](https://achan2013.medium.com/ai-agent-anti-patterns-part-1-architectural-pitfalls-that-break-enterprise-agents-before-they-32d211dded43)
- [Patterns That Work and Pitfalls to Avoid in AI Agent Deployment](https://hackernoon.com/patterns-that-work-and-pitfalls-to-avoid-in-ai-agent-deployment)
- [Docker Sandboxes: Run Agents in YOLO Mode, Safely](https://www.docker.com/blog/docker-sandboxes-run-agents-in-yolo-mode-safely/)
- [The Best Pre-Built Enterprise RAG Platforms in 2025](https://www.firecrawl.dev/blog/best-enterprise-rag-platforms-2025)

---
*Feature research for: Local AI Agent Platform (MAAI)*
*Researched: 2026-04-06*
