# MAAI Agent Platform

## What This Is

A generic, reusable AI agent platform that deploys to client machines via Docker. Clients interact through an Open WebUI chat interface backed by local LLMs (Ollama), with pre-configured "skills" (YAML-defined tasks) for common workflows and freeform chat for ad-hoc requests. The core infrastructure is identical across deployments — agents, prompts, tools, and workflows are the configurable layer per client.

## Core Value

Clients can describe what they need in natural language and the system executes it using local AI — no cloud dependencies, no data leaving their machine.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Config-driven agent system (YAML-defined agents, tools, prompts — like Claude skills)
- [ ] Open WebUI chat interface backed by local Ollama models
- [ ] Plugin-based tool system (enable/disable tools per client via config)
- [ ] File classification and organization (scan local folders, classify by type/year/category)
- [ ] PDF summarization and data extraction
- [ ] Email integration (IMAP/Gmail/O365 — connect, search, summarize)
- [ ] Spreadsheet generation from extracted document data
- [ ] NotebookLM MCP integration for presentation material generation
- [ ] RAG knowledge base per client (documents indexed for Q&A)
- [ ] Configurable autonomy (per-workflow: auto-execute vs confirm-first)
- [ ] Docker Compose deployment (single `docker compose up` per client)
- [ ] Per-client config folder (agents.yaml, workflows.yaml, prompts/, client.env)
- [ ] Freeform chat capability (handle requests not covered by pre-configured skills)
- [ ] Local folder watching (monitor directories for new files to process)

### Out of Scope

- Cloud storage integrations (Google Drive, OneDrive, Dropbox) — v2
- White-label branding — v2, start MAAI-branded
- Presentation generation via python-pptx — using NotebookLM MCP instead
- Mobile app — desktop deployment only for now
- Multi-tenant SaaS — each client gets their own Docker instance
- Network drive / NAS support — v2

## Context

- **Business model**: Start as consulting deliverable (deploy for clients), evolve into licensed product
- **First client**: Document organizer — needs file classification, PDF summaries, email search, spreadsheet output
- **Target hardware**: Client's everyday Windows desktop (must be lightweight, stay out of the way)
- **Chat interface**: Open WebUI (supports Ollama, tool calling, file uploads, conversation history)
- **LLM strategy**: Ollama with LiteLLM routing proxy. Qwen 2.5 14B for agent reasoning, Gemma 3 4B for classification
- **Agent framework**: CrewAI with YAML-driven agent/task/tool configuration
- **Document processing**: Docling (IBM, MIT) for parsing, PaddleOCR for OCR, LlamaIndex + Qdrant for RAG
- **Skills pattern**: Pre-configured tasks defined in YAML (like Claude Code skills) — client triggers by name or natural language match. Freeform requests handled by agent reasoning over available tools
- **NotebookLM**: MCP integration for pushing sources and generating presentation/synthesis material
- **Research completed**: Full research in `cerebro 2.0/maai-software-inc/10 - Generic AI Agent Platform Research.md`

## Constraints

- **Local-only**: No paid third-party APIs. All processing on client's machine
- **Hardware**: Must run on consumer desktop (16-32GB RAM, 8-24GB GPU VRAM)
- **Lightweight**: Runs on client's everyday machine — must not hog resources when idle
- **Docker**: Entire stack containerized via Docker Compose
- **License**: All dependencies must be permissively licensed (MIT, Apache 2.0, BSD)
- **Privacy**: Client data never leaves their machine

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CrewAI over LangGraph | Only framework with full YAML-driven agent/task/tool config — matches "configurable layer" requirement | — Pending |
| Open WebUI for chat | Already supports Ollama, tool calling, file uploads. Don't reinvent | — Pending |
| Ollama + LiteLLM | Simplest local LLM serving + multi-model routing | — Pending |
| Qdrant over ChromaDB | Better production scaling, excellent filtering, single binary | — Pending |
| Docling for parsing | MIT license, broadest format support, IBM-backed | — Pending |
| NotebookLM MCP for presentations | Leverage existing MCP integration instead of building pptx generation | — Pending |
| MAAI branded (not white-label) | Simpler for v1, white-label deferred to product evolution | — Pending |
| Skills pattern for task config | Familiar pattern (Claude Code), flexible (pre-configured + freeform) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after initialization*
