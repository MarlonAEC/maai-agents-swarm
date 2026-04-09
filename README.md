# MAAI Agent Platform

A generic, reusable AI agent platform that deploys to client machines via Docker. Clients interact through an [Open WebUI](https://github.com/open-webui/open-webui) chat interface backed by local LLMs ([Ollama](https://ollama.com)), with pre-configured "skills" (YAML-defined tasks) for common workflows and freeform chat for ad-hoc requests.

**Core value:** Describe what you need in natural language and the system executes it using local AI — no cloud dependencies, no data leaving your machine.

## Architecture

```
Open WebUI  -->  Pipelines (maai_pipe)  -->  Core API (FastAPI + CrewAI)
                                                 |
                                   +-------------+-------------+
                                   |             |             |
                              Skill System   Freeform      RAG Pipeline
                              (YAML-based)    Agent      (Docling + Qdrant)
                                   |             |             |
                                   +------+------+       Ingest Worker
                                          |              (ARQ + Redis)
                                     LiteLLM Proxy
                                          |
                                       Ollama
                                    (local LLMs)
```

### Services

| Service | Purpose | Port |
|---------|---------|------|
| Open WebUI | Chat interface | 3000 |
| Pipelines | Pipe plugin host (routes to Core API) | 9099 |
| Core API | FastAPI + CrewAI skill execution | 8000 |
| LiteLLM | OpenAI-compatible LLM proxy | 4000 |
| Ollama | Local LLM inference (GPU/CPU) | 11434 |
| Qdrant | Vector database for RAG | 6333 |
| Redis | Task queue broker + GPU lock | 6379 |
| Docproc | Document processing (Docling + EasyOCR) | 8001 |
| Ingest Worker | Background document indexing (ARQ) | — |

## Prerequisites

- **Docker Desktop** (with Docker Compose V2)
- **16-32 GB RAM** (8 GB minimum for CPU-only with smaller models)
- **GPU (optional):** NVIDIA GPU with 8-24 GB VRAM for faster inference

## Quick Start

```bash
git clone https://github.com/MarlonAEC/maai-agents-swarm.git
cd maai-agents-swarm
./bootstrap.sh
```

The bootstrap script:
1. Validates Docker Compose V2 is installed
2. Generates a `WEBUI_SECRET_KEY` if not set
3. Detects GPU availability (falls back to CPU with smaller models)
4. Generates LiteLLM proxy config with correct model tags
5. Runs a security check against backdoored LiteLLM versions
6. Starts Ollama and pulls required models
7. Starts the full Docker Compose stack

After bootstrap completes, open **http://localhost:3000** and create an account. Select **"MAAI Agent: Chat"** from the model dropdown.

## Models

| Model | Use Case | VRAM |
|-------|----------|------|
| Qwen3 14B (GPU) / 7B (CPU) | Agent reasoning, task planning | 10-12 GB / 5-6 GB |
| Gemma3 4B (GPU) / 1B (CPU) | Classification, skill matching | 3-4 GB / ~1 GB |
| nomic-embed-text | Embeddings for RAG | ~300 MB |

## Skills

Skills are YAML-defined agent tasks in `clients/default/skills/`. Each skill has triggers, tools, and an agent definition.

**Built-in skills:**
- `document_ingest` — Index a document into the knowledge base
- `ask_documents` — Search and answer questions about indexed documents
- `example_skill` — Echo/test skill

Create new skills by adding YAML files to `clients/<client>/skills/` and listing tools in `clients/<client>/tools.yaml`.

## Document Ingestion & RAG

Upload a PDF in Open WebUI, then say **"index this document"**. The pipeline:

1. Detects the uploaded file in Open WebUI's storage
2. Copies it to the shared volume
3. Calls the Core API `/ingest` endpoint
4. ARQ worker processes it: Docling extracts text, EasyOCR handles scanned pages
5. LlamaIndex chunks and embeds the text into Qdrant (per-client collections)

Then ask **"what does my document say about X?"** to query the knowledge base with source citations.

## Project Structure

```
maai-agents-swarm/
  bootstrap.sh              # One-command setup
  docker-compose.yml        # Full service stack
  clients/
    default/
      client.env            # Client configuration
      skills/               # YAML skill definitions
      tools.yaml            # Tool allowlist
  src/
    core_api/               # FastAPI + CrewAI backend
      agents/               # Crew definitions (freeform, RAG)
      routers/              # HTTP endpoints (chat, ingest)
      skills/               # Skill matcher, executor, registry
      tools/                # CrewAI BaseTool implementations
      rag/                  # LlamaIndex pipeline, GPU lock
      workers/              # ARQ background workers
    docproc/                # Document processing sidecar
    pipelines/              # Open WebUI pipe plugin
  config/
    litellm/                # LiteLLM proxy config (generated)
  tests/                    # pytest test suites
```

## Configuration

Client-specific config lives in `clients/<client>/client.env`. Key variables:

```env
REASONING_MODEL=qwen3:14b      # Main agent LLM
CLASSIFIER_MODEL=gemma3:4b     # Skill classification LLM
EMBEDDING_MODEL=nomic-embed-text # RAG embeddings
LITELLM_MASTER_KEY=sk-maai-local # LiteLLM auth key
WEBUI_PORT=3000                  # Open WebUI port
```

## Constraints

- **Local-only** — No paid third-party APIs. All processing on client's machine.
- **Privacy** — Client data never leaves their machine.
- **Lightweight** — Runs on consumer desktops, must not hog resources when idle.
- **Permissive licensing** — All dependencies MIT, Apache 2.0, or BSD.

## License

MIT
