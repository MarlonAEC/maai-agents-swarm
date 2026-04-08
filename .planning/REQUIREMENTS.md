# Requirements: MAAI Agent Platform

**Defined:** 2026-04-07
**Core Value:** Clients can describe what they need in natural language and the system executes it using local AI — no cloud dependencies, no data leaving their machine.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure

- [x] **INFRA-01**: Platform deploys via single `docker compose up` command per client
- [x] **INFRA-02**: All processing runs locally — no data leaves the client's machine
- [x] **INFRA-03**: Each client has isolated config folder (agents.yaml, workflows.yaml, prompts/, client.env)
- [x] **INFRA-04**: Ollama serves local LLMs with GPU acceleration when available
- [x] **INFRA-05**: LiteLLM proxy routes requests to different models per task type
- [x] **INFRA-06**: Docker Compose networking resolves service names correctly (no localhost pitfalls)

### Chat Interface

- [x] **CHAT-01**: User interacts via Open WebUI chat interface in their browser
- [x] **CHAT-02**: Chat history persists across browser sessions
- [x] **CHAT-03**: User can upload files directly in chat for processing
- [ ] **CHAT-04**: User can describe tasks in natural language and the system executes them
- [ ] **CHAT-05**: User can ask freeform questions not covered by pre-configured skills
- [ ] **CHAT-06**: Multi-turn conversation context maintained within a session

### Agent System

- [ ] **AGNT-01**: Agents, tasks, and tool assignments defined in YAML config files
- [ ] **AGNT-02**: Pre-configured "skills" (named tasks) triggered by name or natural language match
- [ ] **AGNT-03**: Skill Matcher routes user requests to the best matching skill or freeform fallback
- [ ] **AGNT-04**: Plugin-based tool system — tools enabled/disabled per client via YAML config
- [ ] **AGNT-05**: Tool registry discovers and loads available plugins at startup
- [ ] **AGNT-06**: Per-workflow autonomy control (auto-execute vs confirm-first) configurable in YAML
- [ ] **AGNT-07**: CrewAI embedder explicitly configured for Ollama (not defaulting to OpenAI)
- [ ] **AGNT-08**: Agent inference uses non-streaming mode to prevent tool call drops
- [ ] **AGNT-09**: max_iter and max_execution_time caps on all agent loops to prevent runaway inference

### Document Processing

- [ ] **DOCP-01**: PDF text extraction and summarization via Docling
- [ ] **DOCP-02**: OCR for scanned documents via PaddleOCR
- [ ] **DOCP-03**: Document chunking and embedding via LlamaIndex with local embedding model
- [ ] **DOCP-04**: Vector storage in Qdrant with persistent data volumes
- [ ] **DOCP-05**: Per-client RAG knowledge base (isolated Qdrant collections)
- [ ] **DOCP-06**: User can ask questions about their indexed documents via chat
- [ ] **DOCP-07**: GPU workloads sequenced (LLM inference and OCR not concurrent) to prevent VRAM starvation

### Business Tools

- [ ] **BIZZ-01**: File classification — scan local folders, classify files by type/year/category
- [ ] **BIZZ-02**: File organization — move/copy classified files into organized directory structure
- [ ] **BIZZ-03**: Email integration — connect via IMAP credentials or Gmail OAuth
- [ ] **BIZZ-04**: Email search — find emails by topic, sender, date range via natural language
- [ ] **BIZZ-05**: Email summarization — summarize email threads or inbox activity
- [ ] **BIZZ-06**: Spreadsheet generation — extract structured data from documents into .xlsx files
- [ ] **BIZZ-07**: NotebookLM MCP integration — push processed documents as sources for synthesis

### Deployment

- [ ] **DEPL-01**: deploy.sh script that takes a client config folder and starts the stack
- [ ] **DEPL-02**: Health-check endpoint confirms all services are running
- [ ] **DEPL-03**: Client onboarding flow for email credential setup (IMAP/Gmail OAuth)
- [ ] **DEPL-04**: Platform runs on consumer desktop hardware (16-32GB RAM, 8-24GB GPU VRAM)
- [ ] **DEPL-05**: Idle resource usage is minimal — does not impact client's daily desktop use

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Automation

- **AUTO-01**: File system watching — auto-process files dropped in watched folders
- **AUTO-02**: Scheduled tasks — run skills on a cron schedule
- **AUTO-03**: Agent persistent memory across conversations (scoped, not global)

### Integrations

- **INTG-01**: Cloud storage sync (Google Drive, OneDrive, Dropbox)
- **INTG-02**: Network drive / NAS support
- **INTG-03**: Calendar integration

### Platform

- **PLAT-01**: White-label branding per client
- **PLAT-02**: Client self-service onboarding (web-based setup wizard)
- **PLAT-03**: Usage analytics dashboard

## Out of Scope

| Feature | Reason |
|---------|--------|
| Visual workflow builder (drag-drop) | Defeats YAML-config simplicity; MAAI configures skills, not the client |
| Multi-tenant SaaS | Breaks local-only guarantee; each client gets their own Docker instance |
| Mobile app | Target use case is desktop automation on a work PC |
| Real-time streaming for all agent responses | CrewAI multi-agent tasks are non-streaming; show progress indicators instead |
| Multi-model chat (A/B comparison) | Doubles inference load on constrained hardware |
| Global agent memory across all conversations | Causes context bleed; use explicit RAG knowledge base instead |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 1 | Complete |
| CHAT-01 | Phase 2 | Complete |
| CHAT-02 | Phase 2 | Complete |
| CHAT-03 | Phase 2 | Complete |
| CHAT-04 | Phase 2 | Pending |
| CHAT-05 | Phase 2 | Pending |
| CHAT-06 | Phase 2 | Pending |
| AGNT-01 | Phase 3 | Pending |
| AGNT-02 | Phase 3 | Pending |
| AGNT-03 | Phase 3 | Pending |
| AGNT-04 | Phase 3 | Pending |
| AGNT-05 | Phase 3 | Pending |
| AGNT-06 | Phase 3 | Pending |
| AGNT-07 | Phase 2 | Pending |
| AGNT-08 | Phase 2 | Pending |
| AGNT-09 | Phase 2 | Pending |
| DOCP-01 | Phase 4 | Pending |
| DOCP-02 | Phase 4 | Pending |
| DOCP-03 | Phase 4 | Pending |
| DOCP-04 | Phase 4 | Pending |
| DOCP-05 | Phase 4 | Pending |
| DOCP-06 | Phase 4 | Pending |
| DOCP-07 | Phase 4 | Pending |
| BIZZ-01 | Phase 5 | Pending |
| BIZZ-02 | Phase 5 | Pending |
| BIZZ-03 | Phase 5 | Pending |
| BIZZ-04 | Phase 5 | Pending |
| BIZZ-05 | Phase 5 | Pending |
| BIZZ-06 | Phase 5 | Pending |
| BIZZ-07 | Phase 5 | Pending |
| DEPL-01 | Phase 6 | Pending |
| DEPL-02 | Phase 6 | Pending |
| DEPL-03 | Phase 6 | Pending |
| DEPL-04 | Phase 6 | Pending |
| DEPL-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after roadmap creation — all requirements mapped*
