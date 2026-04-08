# Roadmap: MAAI Agent Platform

## Overview

The MAAI Agent Platform is built in strict dependency order: infrastructure and LLM serving first, then a minimal end-to-end chat path, then the YAML-driven tool/skills system (the platform's core differentiator), then document ingestion and RAG, then business-specific plugins (email, file organization, spreadsheets), and finally production hardening and deployment packaging. Each phase validates the layer below before the next is added. Nothing above the current layer is assumed to work until its smoke tests pass.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure Foundation** - Docker stack with Ollama, LiteLLM, and Open WebUI confirmed working end-to-end
- [ ] **Phase 2: Core API and End-to-End Chat** - Minimal chat path from Open WebUI through Pipelines to CrewAI freeform agent
- [ ] **Phase 3: Tool System and Skills** - Plugin registry, YAML-driven skills, and Skill Matcher routing
- [ ] **Phase 4: Document Ingestion and RAG** - Full ingestion pipeline (Docling + PaddleOCR) and per-client RAG knowledge base
- [ ] **Phase 5: Business Plugins** - File organization, email integration, spreadsheet generation, and NotebookLM MCP
- [ ] **Phase 6: Production Readiness** - Deployment packaging, health checks, onboarding flow, and resource safeguards

## Phase Details

### Phase 1: Infrastructure Foundation
**Goal**: The full Docker stack starts with a single command, LLMs serve locally, and the chat interface is accessible in a browser
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` brings the entire stack online without manual intervention
  2. Open WebUI is accessible in a browser and can send a chat message to Ollama
  3. LiteLLM proxy routes a test request to Qwen3 14B and a separate request to Gemma 3 4B correctly
  4. GPU acceleration is confirmed active (Ollama logs show GPU device, not CPU fallback)
  5. Per-client config folder is mounted and loaded — changing a value in client.env is reflected at startup
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Docker Compose stack, client config, LiteLLM proxy config, test scaffold
- [ ] 01-02-PLAN.md — Bootstrap script (GPU detection, model pull, config generation) + end-to-end verification

### Phase 2: Core API and End-to-End Chat
**Goal**: A user message travels from Open WebUI through the Pipelines connector and Core API to a CrewAI freeform agent and returns a coherent response
**Depends on**: Phase 1
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, AGNT-07, AGNT-08, AGNT-09
**Success Criteria** (what must be TRUE):
  1. User can send a freeform message in Open WebUI and receive a response from the local LLM via the Core API
  2. Chat history persists — closing and reopening the browser still shows previous conversations
  3. User can upload a file in chat and the system acknowledges it for processing
  4. Multi-turn context is maintained — a follow-up question in the same session can reference prior messages
  5. Agent inference does not silently drop tool calls (smoke test confirms stream=False path works end-to-end)
**Plans:** 1/3 plans executed

Plans:
- [ ] 02-01-PLAN.md — Core API service (FastAPI + CrewAI freeform agent + Dockerfile)
- [x] 02-02-PLAN.md — Pipelines pipe plugin (Open WebUI -> Core API bridge)
- [ ] 02-03-PLAN.md — Docker Compose wiring, test scaffold, and end-to-end verification

### Phase 3: Tool System and Skills
**Goal**: YAML-defined skills are triggerable by name or natural language, tools load from a plugin registry, and per-client tool enable/disable works without code changes
**Depends on**: Phase 2
**Requirements**: AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05, AGNT-06
**Success Criteria** (what must be TRUE):
  1. A skill defined only in YAML (no code change) can be triggered by typing its name in chat
  2. User can describe a task in natural language and the Skill Matcher routes it to the correct pre-configured skill
  3. A request with no matching skill falls through to the freeform agent without error
  4. Disabling a tool in YAML config causes it to disappear from the available tool set at next startup — no code change required
  5. A workflow configured as confirm-first pauses and shows a confirmation prompt before executing; auto-execute workflows run immediately
**Plans**: TBD

### Phase 4: Document Ingestion and RAG
**Goal**: Users can upload or point the system at documents and ask questions about their content; documents are classified and queryable via the per-client knowledge base
**Depends on**: Phase 3
**Requirements**: DOCP-01, DOCP-02, DOCP-03, DOCP-04, DOCP-05, DOCP-06, DOCP-07
**Success Criteria** (what must be TRUE):
  1. User can upload a PDF in chat and receive an accurate summary drawn from the document's text
  2. A scanned document (image-only PDF) is correctly OCR-processed and its text is searchable
  3. User can ask a question about an indexed document and receive an answer with relevant context retrieved from Qdrant
  4. Two test clients have isolated Qdrant collections — a document indexed for client A is not returned in client B's queries
  5. LLM inference and OCR do not run concurrently — GPU workloads are sequenced and no VRAM starvation occurs under load
**Plans**: TBD

### Phase 5: Business Plugins
**Goal**: The first client's core workflows are fully operational — files are organized, emails are searchable, structured data is exportable, and NotebookLM integration is live
**Depends on**: Phase 4
**Requirements**: BIZZ-01, BIZZ-02, BIZZ-03, BIZZ-04, BIZZ-05, BIZZ-06, BIZZ-07
**Success Criteria** (what must be TRUE):
  1. User can ask the system to scan a folder and receive a classification report of files by type, year, and category
  2. Classified files can be moved or copied into an organized directory structure via a single chat instruction
  3. User can connect an email account via IMAP credentials and search their inbox using natural language (e.g., "find invoices from March")
  4. User can ask for a summary of an email thread and receive a coherent summary without leaving the chat interface
  5. User can request a spreadsheet from document data and receive a downloadable .xlsx file with structured rows
**Plans**: TBD

### Phase 6: Production Readiness
**Goal**: The platform deploys cleanly to a new client machine via a single script, all services report health, and the system runs without impacting the client's daily desktop use
**Depends on**: Phase 5
**Requirements**: DEPL-01, DEPL-02, DEPL-03, DEPL-04, DEPL-05
**Success Criteria** (what must be TRUE):
  1. Running `deploy.sh <client-config-folder>` on a fresh machine starts the full platform without manual steps
  2. A health-check endpoint returns green status for every service; any failed service is identifiable immediately
  3. New client can complete email credential setup (IMAP or Gmail OAuth) through the onboarding flow without editing raw config files
  4. Platform runs successfully on a 16GB RAM desktop with 8GB GPU VRAM — models load and respond within acceptable time
  5. When idle, the platform's background resource usage does not noticeably impact the client's concurrent desktop applications
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure Foundation | 1/2 | In Progress|  |
| 2. Core API and End-to-End Chat | 1/3 | In Progress|  |
| 3. Tool System and Skills | 0/TBD | Not started | - |
| 4. Document Ingestion and RAG | 0/TBD | Not started | - |
| 5. Business Plugins | 0/TBD | Not started | - |
| 6. Production Readiness | 0/TBD | Not started | - |
