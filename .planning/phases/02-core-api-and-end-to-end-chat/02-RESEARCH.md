# Phase 02: Core API and End-to-End Chat - Research

**Researched:** 2026-04-07
**Domain:** FastAPI + CrewAI + Open WebUI Pipelines integration
**Confidence:** HIGH (most findings verified against official docs or multiple sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Open WebUI connects to Core API via a **Pipelines plugin** (filter/pipe). The Pipelines server runs as a separate Docker container with the plugin mounted as a volume.
- **D-02:** **ALL chat messages** route through the Pipeline -> Core API -> CrewAI agent. No split routing. The agent handles everything.
- **D-03:** During agent processing, the Pipeline sends **intermediate status messages** ('Thinking...', 'Processing your request...') as partial streaming responses so the user sees progress.
- **D-04:** Open WebUI's existing config stays: `ENABLE_OLLAMA_API=false`, `OPENAI_API_BASE_URLS=http://litellm:4000/v1`. The Pipelines container is registered as a pipeline endpoint in Open WebUI.
- **D-05:** Phase 2 agent is **pure conversational** — no tools. Gracefully declines tasks it can't do yet.
- **D-06:** **Pipeline passes full message history** to Core API. Open WebUI tracks chat history. Core API injects history into CrewAI agent context.
- **D-07:** Agent uses the **`reasoning-model`** alias from LiteLLM (Qwen3 14B / Qwen3 7B on CPU).
- **D-08:** Agent runs with **non-streaming mode** (`stream=False`) per AGNT-08.
- **D-09:** **Conservative guardrails**: `max_iter=5`, `max_execution_time=60s` per AGNT-09.
- **D-10:** CrewAI embedder explicitly configured for Ollama using `embedding-model` alias (AGNT-07).
- **D-11:** CrewAI runs **in-process** inside the FastAPI service. No Redis or ARQ in Phase 2.
- **D-12:** Two new Docker services: (1) `core-api` (FastAPI + CrewAI, Python 3.11), (2) `pipelines` (Open WebUI Pipelines server with plugin). Both join `maai-net`.
- **D-13:** Python code at `src/core_api/` with Dockerfile at `src/core_api/Dockerfile`. Pipelines plugin at `src/pipelines/`.
- **D-14:** Pipeline **accepts files from Open WebUI** and stores in `maai-uploads` volume. Response: "File received: {filename}. Document processing will be available in a future update."
- **D-15:** Shared volume `maai-uploads` mounted in both Pipelines and Core API containers.
- **D-16:** No file parsing or processing in Phase 2. Receipt acknowledgment only.

### Claude's Discretion

- Pipelines plugin implementation details (filter vs pipe type, exact protocol)
- FastAPI endpoint design (routes, request/response schemas)
- CrewAI agent system prompt content
- Docker health check configuration for new services
- Exact Pipelines server image and configuration

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | User interacts via Open WebUI chat interface in their browser | Open WebUI already deployed in Phase 1; Pipelines plugin exposes it as a selectable model |
| CHAT-02 | Chat history persists across browser sessions | Open WebUI persists history in webui-data volume; passed in full on each request via `messages` array |
| CHAT-03 | User can upload files directly in chat for processing | Pipelines pipe() receives multipart body; files saved to maai-uploads volume |
| CHAT-04 | User can describe tasks in natural language and the system executes them | CrewAI agent + task accepts free-form user_message; returns LLM response |
| CHAT-05 | User can ask freeform questions not covered by pre-configured skills | Phase 2 agent is purely conversational — handles all free-form queries |
| CHAT-06 | Multi-turn conversation context maintained within a session | Full messages array passed to Core API; injected into task description as conversation history |
| AGNT-07 | CrewAI embedder explicitly configured for Ollama (not defaulting to OpenAI) | `embedder={"provider": "ollama", "config": {"model_name": "nomic-embed-text", "url": "http://ollama:11434/api/embeddings"}}` passed to Crew() |
| AGNT-08 | Agent inference uses non-streaming mode to prevent tool call drops | `LLM(stream=False, ...)` — confirmed working pattern |
| AGNT-09 | max_iter and max_execution_time caps on all agent loops | `Agent(max_iter=5, max_execution_time=60)` — bug fixed in CrewAI post-v0.55.2; 1.13.x is safe |
</phase_requirements>

---

## Summary

Phase 2 wires together four components into a complete chat pipeline: Open WebUI (already running) → a Pipelines **pipe** plugin (new service) → FastAPI Core API (new service) → CrewAI conversational agent → LiteLLM (already running). The architecture is well-supported by official tooling and documented patterns.

The **Pipelines pipe pattern** is the right choice over a filter. A `pipe` type shows up as a selectable model in Open WebUI's dropdown, intercepts the full request, makes an HTTP call to Core API, emits intermediate status events via `__event_emitter__`, and returns the final response string. The Pipelines server (`ghcr.io/open-webui/pipelines:main`) mounts plugin `.py` files from a local volume.

Open WebUI connects to the Pipelines server by adding it as an additional entry in `OPENAI_API_BASE_URLS` (semicolon-separated). This means **no manual admin UI steps** are needed — the connection is fully configured via environment variables in docker-compose.yml, which fits the "single `docker compose up`" deployment story.

The **CrewAI side** is a minimal single-agent, single-task crew. YAML config defines role/goal/backstory. Python code sets `max_iter=5`, `max_execution_time=60`, `memory=False` (no embedder needed for conversation-only), and `LLM(model="openai/reasoning-model", base_url="http://litellm:4000/v1", api_key="...", stream=False)`. Conversation history is passed via `crew.kickoff(inputs={"messages": ..., "user_message": ...})` with the task description referencing `{messages}` and `{user_message}` as template variables.

**Primary recommendation:** Use a **pipe-type** Pipelines plugin (not a filter), connect it via `OPENAI_API_BASE_URLS` semicolon extension, and run CrewAI synchronously inside the FastAPI endpoint wrapped in `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking the async event loop.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | >=0.115.0 | Core API HTTP layer | Async-native, Pydantic v2 compatible, already in CLAUDE.md |
| `uvicorn` | latest stable | ASGI server for FastAPI | Standard companion to FastAPI in Docker deployments |
| `crewai` | >=1.13.0 | Agent orchestration | YAML-driven config; fixes max_execution_time bug post-v0.55.2 |
| `httpx` | >=0.27.x | Async HTTP from Pipelines -> Core API | Preferred over `requests` in async contexts (CLAUDE.md) |
| `pydantic` | v2 | Request/response schemas | Required by both FastAPI and CrewAI 1.x |
| `python-dotenv` | 1.x | Load client.env in containers | Already in use in Phase 1 pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyyaml` | 6.x | Load CrewAI YAML configs | Already in dev dependencies (pyproject.toml) |
| `python-multipart` | latest | File upload handling in FastAPI | Required for `UploadFile` endpoint support |

### Docker Images

| Image | Purpose | Notes |
|-------|---------|-------|
| `ghcr.io/open-webui/pipelines:main` | Pipelines server | Runs on port 9099; mounts `/app/pipelines` |
| Custom Python 3.11 image | Core API (FastAPI + CrewAI) | Built from `src/core_api/Dockerfile` |

### Installation (Core API container)

```bash
uv pip install "fastapi>=0.115.0" "uvicorn[standard]" "crewai>=1.13.0" \
  "httpx>=0.27.0" "pydantic>=2.0" "python-dotenv>=1.0" "pyyaml>=6.0" \
  "python-multipart"
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── core_api/
│   ├── Dockerfile
│   ├── pyproject.toml          # or requirements.txt
│   ├── main.py                 # FastAPI app entrypoint
│   ├── routers/
│   │   └── chat.py             # POST /chat endpoint
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── freeform_crew.py    # @CrewBase class
│   │   └── config/
│   │       ├── agents.yaml
│   │       └── tasks.yaml
│   └── logging_config.py       # Logger setup (CLAUDE.md requirement)
└── pipelines/
    └── maai_pipe.py            # Pipe plugin loaded by Pipelines server
```

### Pattern 1: Pipelines Pipe Plugin (pipe type — not filter)

**What:** A `pipe`-type plugin appears as a selectable "model" in Open WebUI's dropdown. It intercepts the full message body, makes an HTTP call to Core API, emits intermediate status events, and returns the response.

**When to use:** Any time the pipeline needs to invoke an external service and return a full response. Pipe is the correct type when Open WebUI does NOT need to forward to an LLM afterward — the pipe IS the model endpoint.

**Key structural requirement:** `self.type = "pipe"` (not `"filter"`) in `__init__`.

```python
# Source: https://deepwiki.com/open-webui/pipelines/7.1-creating-custom-pipelines
# Source: https://github.com/sboily/open-webui-n8n-pipe
from typing import Optional
from pydantic import BaseModel
import httpx


class Pipeline:
    class Valves(BaseModel):
        core_api_url: str = "http://core-api:8000"
        core_api_key: str = ""
        timeout: float = 90.0

    def __init__(self):
        self.name = "MAAI Agent"
        self.type = "pipe"   # shows up as a model in Open WebUI dropdown
        self.valves = self.Valves()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    async def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: list,
        body: dict,
        __event_emitter__=None,
    ) -> str:
        # Emit intermediate status
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "status": "in_progress",
                    "description": "Thinking...",
                    "done": False,
                },
            })

        # Forward to Core API
        async with httpx.AsyncClient(timeout=self.valves.timeout) as client:
            response = await client.post(
                f"{self.valves.core_api_url}/chat",
                json={"messages": messages, "user_message": user_message},
                headers={"X-API-Key": self.valves.core_api_key},
            )
            response.raise_for_status()
            result = response.json()

        # Emit completion status
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "status": "complete",
                    "description": "Done",
                    "done": True,
                },
            })

        return result["response"]
```

### Pattern 2: FastAPI Chat Endpoint

**What:** A POST `/chat` endpoint that receives message history and user message, invokes CrewAI, and returns a response string. CrewAI's synchronous `kickoff()` is wrapped in `run_in_executor` to avoid blocking the asyncio event loop.

```python
# Source: FastAPI async docs + CrewAI kickoff_async docs
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    user_message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_freeform_crew(request.messages, request.user_message),
        )
        return ChatResponse(response=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Pattern 3: CrewAI Freeform Agent (YAML + Python)

**agents.yaml:**
```yaml
freeform_agent:
  role: >
    MAAI Assistant
  goal: >
    Help the user with their questions and tasks using clear, helpful responses.
    If asked about capabilities not yet available, explain what is coming and
    offer to assist with what is currently possible.
  backstory: >
    You are a knowledgeable AI assistant running locally on the user's machine.
    All processing stays on their device. You have access to the conversation
    history and help users with general questions and analysis tasks.
```

**tasks.yaml:**
```yaml
freeform_task:
  description: >
    Respond to the user's message in the context of the conversation history.

    Conversation history:
    {messages}

    Current user message: {user_message}

    Provide a clear, helpful response. If the user asks you to do something
    that requires capabilities not yet implemented (file processing, email,
    spreadsheets), acknowledge the request and explain it will be available
    in a future update.
  expected_output: >
    A clear, conversational response to the user's message.
  agent: freeform_agent
```

**Python crew class:**
```python
# Source: https://docs.crewai.com/en/quickstart
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
import os

@CrewBase
class FreeformCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def _llm(self) -> LLM:
        return LLM(
            model="openai/reasoning-model",         # LiteLLM alias; openai/ prefix required
            base_url=os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1"),
            api_key=os.getenv("LITELLM_MASTER_KEY", "sk-maai-local"),
            stream=False,                            # AGNT-08: prevent tool call drops
            timeout=60.0,
        )

    @agent
    def freeform_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["freeform_agent"],
            llm=self._llm(),
            max_iter=5,                             # AGNT-09
            max_execution_time=60,                  # AGNT-09
            memory=False,                           # history injected via task inputs
            verbose=False,
        )

    @task
    def freeform_task(self) -> Task:
        return Task(config=self.tasks_config["freeform_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            embedder={                              # AGNT-07: explicit Ollama embedder
                "provider": "ollama",
                "config": {
                    "model_name": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                    "url": "http://ollama:11434/api/embeddings",
                },
            },
        )


def run_freeform_crew(messages: list, user_message: str) -> str:
    crew = FreeformCrew().crew()
    # Format message history for task template variable
    history = "\n".join(
        f"{m.role}: {m.content}" for m in messages[:-1]  # exclude the latest user msg
    )
    result = crew.kickoff(inputs={
        "messages": history or "(no prior messages)",
        "user_message": user_message,
    })
    return str(result)
```

### Pattern 4: Open WebUI + Pipelines Connection via OPENAI_API_BASE_URLS

**What:** Pipelines server is added as a second entry in `OPENAI_API_BASE_URLS`. Open WebUI discovers the pipe's model and shows it in the dropdown. No manual admin UI steps required after `docker compose up`.

```yaml
# In docker-compose.yml, open-webui service environment:
- OPENAI_API_BASE_URLS=http://litellm:4000/v1;http://pipelines:9099
- OPENAI_API_KEYS=${LITELLM_MASTER_KEY};${PIPELINES_API_KEY}
```

Source: OpenWebUI env config docs confirm semicolon-separated format for `OPENAI_API_BASE_URLS` and `OPENAI_API_KEYS`.

### Pattern 5: Docker Compose Services

```yaml
# New core-api service
core-api:
  container_name: core-api
  build:
    context: ./src/core_api
    dockerfile: Dockerfile
  env_file:
    - ${CLIENT_ENV_PATH:-clients/default/client.env}
  environment:
    - LITELLM_BASE_URL=http://litellm:4000/v1
  volumes:
    - maai-uploads:/app/uploads
  ports:
    - "${CORE_API_PORT:-8000}:8000"
  healthcheck:
    test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 30s
  depends_on:
    litellm:
      condition: service_healthy
  networks:
    - maai-net
  restart: unless-stopped

# New pipelines service
pipelines:
  container_name: pipelines
  image: ghcr.io/open-webui/pipelines:main
  environment:
    - PIPELINES_API_KEY=${PIPELINES_API_KEY:-0p3n-w3bu!}
  volumes:
    - ./src/pipelines:/app/pipelines    # mount plugin files directly
  healthcheck:
    test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:9099/health')\""]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 20s
  networks:
    - maai-net
  restart: unless-stopped

# New shared volume
volumes:
  ollama-models:
  webui-data:
  maai-uploads:      # new — shared between pipelines and core-api
```

### Anti-Patterns to Avoid

- **Using a filter-type plugin instead of pipe:** Filters require Open WebUI with Pipelines support AND still forward to an LLM after filtering. Pipe is the correct type when Core API IS the LLM endpoint.
- **Calling Ollama directly from Core API:** Always call LiteLLM at `http://litellm:4000/v1`. LiteLLM is the single LLM gateway per the project's established pattern.
- **Synchronous `kickoff()` directly in an async FastAPI handler:** Blocks the uvicorn event loop. Wrap in `run_in_executor(None, ...)` or use `crew.kickoff_async()` / `crew.akickoff()`.
- **Setting `OPENAI_API_KEYS` without a second key for Pipelines:** Both `OPENAI_API_BASE_URLS` and `OPENAI_API_KEYS` use semicolon separators — they must have the same count of entries.
- **Omitting `model="openai/reasoning-model"` prefix:** CrewAI + LiteLLM requires the `openai/` prefix when calling a custom `base_url`. Without it, CrewAI may try to validate the key against the real OpenAI API.
- **Enabling CrewAI memory without an embedder:** Memory defaults to OpenAI embeddings. Since this phase disables memory (`memory=False`), this is avoided — but the embedder config must still be set on the Crew if memory is ever enabled.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plugin server for Open WebUI | Custom FastAPI endpoint pretending to be a model | `ghcr.io/open-webui/pipelines:main` | Already implements OpenAI-compatible discovery, authentication, valve config UI |
| Status/progress events in chat | Custom SSE or WebSocket streaming | `__event_emitter__` in pipe() | Built into Open WebUI Pipelines — works out of the box |
| LLM request routing | Direct Ollama calls from Core API | LiteLLM proxy at `http://litellm:4000/v1` | Alias-based routing already configured; Phase 1 pattern |
| Chat history storage | Redis session store, DB | Pass `messages` array from Open WebUI | Open WebUI already persists history and sends it on each request |
| Agent orchestration | Raw LLM API calls with custom retry/timeout logic | CrewAI Crew + Task | Handles retry, iteration limits, tool execution, multi-agent context |

**Key insight:** The Pipelines server is a complete plugin runtime. The developer only needs to drop a `.py` file in the mounted volume — no custom server code needed.

---

## Common Pitfalls

### Pitfall 1: Pipe vs Filter Confusion

**What goes wrong:** Using `self.type = "filter"` causes the plugin to act as preprocessing middleware, still forwarding to an LLM after the inlet method. The Core API response never reaches the user.

**Why it happens:** The Open WebUI docs describe filters first and prominently; filter examples are easier to find.

**How to avoid:** Always set `self.type = "pipe"` when Core API is the terminal endpoint. A pipe's `pipe()` method return value IS the response to the user.

**Warning signs:** Response appears as if from LiteLLM model, not from Core API; or requests hit Core API but the response shown in Open WebUI is a default LLM response.

### Pitfall 2: OPENAI_API_KEYS Count Mismatch

**What goes wrong:** If `OPENAI_API_BASE_URLS` has 2 entries but `OPENAI_API_KEYS` has only 1, Open WebUI may fail silently or misroute authentication.

**Why it happens:** Existing Phase 1 config only had one entry for each.

**How to avoid:** Keep both env vars in sync — same number of semicolon-separated values. Add `PIPELINES_API_KEY` to `client.env` and reference it in docker-compose.yml.

**Warning signs:** Pipelines model doesn't appear in Open WebUI dropdown; 401 errors in Pipelines container logs.

### Pitfall 3: CrewAI Missing `openai/` Model Prefix

**What goes wrong:** `LLM(model="reasoning-model", base_url="http://litellm:4000/v1")` — CrewAI/LiteLLM tries to route using the bare model name and may attempt to validate against real OpenAI.

**Why it happens:** LiteLLM uses the provider prefix to determine routing. Without it, it defaults to OpenAI.

**How to avoid:** Always use `model="openai/reasoning-model"` when calling a custom OpenAI-compatible proxy.

**Warning signs:** AuthenticationError referencing api.openai.com in logs despite correct `base_url`.

### Pitfall 4: Blocking Async Event Loop

**What goes wrong:** `async def chat(...)` directly calls synchronous `crew.kickoff()` — blocks uvicorn's event loop, preventing concurrent health checks or other requests during inference.

**Why it happens:** CrewAI's standard `kickoff()` is synchronous. `kickoff_async()` exists but wraps sync code in a thread anyway.

**How to avoid:** Use `await loop.run_in_executor(None, lambda: run_freeform_crew(...))`. Alternatively, use `await crew.akickoff(inputs=...)` which is the native async path in CrewAI 1.x.

**Warning signs:** Docker health checks time out during active inference; `/health` endpoint unresponsive under load.

### Pitfall 5: max_execution_time Not Enforced

**What goes wrong:** In CrewAI versions before ~v0.55.2, `max_execution_time` was a no-op parameter — agents could run indefinitely.

**Why it happens:** Bug tracked in issue #2503, fixed March 2025.

**How to avoid:** Pin `crewai>=1.13.0` (the project standard). The fix is included. Additionally, set a FastAPI request timeout as a safety net (uvicorn default is sufficient for Phase 2).

**Warning signs:** Agent loops don't stop after 60 seconds even with `max_execution_time=60` set.

### Pitfall 6: Pipelines Volume Mount — Plugin Not Discovered

**What goes wrong:** Plugin file exists in `src/pipelines/` but Pipelines server doesn't load it. This happens if the filename doesn't end in `.py` or if the file has a syntax error that prevents import.

**Why it happens:** Pipelines server auto-discovers all `.py` files in `PIPELINES_DIR` (default `/app/pipelines`).

**How to avoid:** Name the file with `.py` extension. Ensure there are no import errors by testing locally before building the image. Confirm volume mount path is `/app/pipelines` in docker-compose.yml.

**Warning signs:** Pipelines container starts healthy but the MAAI Agent model doesn't appear in Open WebUI's model dropdown.

---

## Code Examples

### File Upload Handling in Pipe

```python
# Source: Open WebUI Pipelines pipe pattern — body dict inspection
async def pipe(self, user_message, model_id, messages, body, __event_emitter__=None):
    # Open WebUI passes file info in body["files"] when user uploads
    files = body.get("files", [])
    if files:
        # For Phase 2: acknowledge only, store if needed
        filenames = [f.get("name", "unknown") for f in files]
        return f"File received: {', '.join(filenames)}. Document processing will be available in a future update."

    # Normal chat path
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"status": "in_progress", "description": "Thinking...", "done": False}})

    async with httpx.AsyncClient(timeout=self.valves.timeout) as client:
        resp = await client.post(
            f"{self.valves.core_api_url}/chat",
            json={"messages": messages, "user_message": user_message},
        )
        resp.raise_for_status()

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"status": "complete", "description": "Done", "done": True}})

    return resp.json()["response"]
```

### Logging Setup (CLAUDE.md Requirement — No console.log / print)

```python
# src/core_api/logging_config.py
import logging
import sys

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# Usage in any module:
# from logging_config import get_logger
# logger = get_logger(__name__)
# logger.info("Agent invoked for user_message: %s", user_message[:50])
```

### Core API Dockerfile Pattern

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Container builds | Assumed (Phase 1 complete) | — | — |
| Python 3.11 | Core API image | Pulled at build time (FROM python:3.11-slim) | 3.11.x | — |
| LiteLLM proxy | CrewAI LLM calls | Deployed (Phase 1) | >=1.83.0 | — |
| Ollama | LLM inference | Deployed (Phase 1) | 0.20.x | — |
| Open WebUI | Chat interface | Deployed (Phase 1) | 0.8.x | — |
| `ghcr.io/open-webui/pipelines:main` | Pipelines server | Downloaded at `docker compose up` | main | — |

**Missing dependencies with no fallback:** None — all dependencies available from Phase 1 or fetched by Docker at startup.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x + pytest-asyncio 0.23+ |
| Config file | `pytest.ini` (exists) + `pyproject.toml` |
| Quick run command | `pytest tests/phase2/ -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | Open WebUI accessible via browser (port) | smoke | `pytest tests/phase2/test_webui_accessible.py -x` | Wave 0 |
| CHAT-02 | Chat history in body.messages array passed to Core API | unit | `pytest tests/phase2/test_core_api.py::test_message_history_forwarded -x` | Wave 0 |
| CHAT-03 | File upload returns acknowledgment string | unit | `pytest tests/phase2/test_core_api.py::test_file_upload_ack -x` | Wave 0 |
| CHAT-04 | Core API /chat returns non-empty response | integration | `pytest tests/phase2/test_core_api.py::test_chat_returns_response -x` | Wave 0 |
| CHAT-05 | Freeform question gets LLM response | integration | `pytest tests/phase2/test_core_api.py::test_freeform_question -x` | Wave 0 |
| CHAT-06 | Multi-turn: prior messages appear in context | unit | `pytest tests/phase2/test_core_api.py::test_multi_turn_context -x` | Wave 0 |
| AGNT-07 | Embedder config is Ollama, not OpenAI | unit | `pytest tests/phase2/test_crew_config.py::test_embedder_is_ollama -x` | Wave 0 |
| AGNT-08 | LLM initialized with stream=False | unit | `pytest tests/phase2/test_crew_config.py::test_stream_false -x` | Wave 0 |
| AGNT-09 | Agent has max_iter=5 and max_execution_time=60 | unit | `pytest tests/phase2/test_crew_config.py::test_agent_guardrails -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/phase2/ -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/phase2/__init__.py` — new phase test package
- [ ] `tests/phase2/conftest.py` — shared fixtures (mock LiteLLM, test client)
- [ ] `tests/phase2/test_core_api.py` — covers CHAT-02 through CHAT-06
- [ ] `tests/phase2/test_crew_config.py` — covers AGNT-07, AGNT-08, AGNT-09
- [ ] `tests/phase2/test_webui_accessible.py` — covers CHAT-01

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Open WebUI filter pipeline | Open WebUI pipe pipeline for terminal API routing | 2024 | Pipe is simpler; filter still forwards to LLM after processing |
| CrewAI `kickoff()` directly in FastAPI | `crew.akickoff()` or `run_in_executor` | CrewAI 1.x | Prevents event loop blocking in async FastAPI handlers |
| Hardcoded OpenAI in CrewAI embedder | Explicit `embedder={"provider": "ollama", ...}` | 2024 | CrewAI defaulted to OpenAI for embeddings; must now be set explicitly |
| `docker-compose` standalone binary | `docker compose` (V2 plugin) | 2024 | Standalone binary EOL'd |

**Deprecated/outdated:**
- `litellm==1.82.7` and `1.82.8`: Backdoored, yanked from PyPI — always pin `>=1.83.0`
- `ENABLE_OLLAMA_API=true` in Open WebUI: Phase 1 already set to `false`; all LLM traffic through LiteLLM
- Raw `imaplib` / `requests` in async contexts: use `httpx` (already in CLAUDE.md)

---

## Open Questions

1. **Does `OPENAI_API_BASE_URLS` semicolon extension automatically show the Pipelines model in Open WebUI without any admin UI step?**
   - What we know: Confirmed that `OPENAI_API_BASE_URLS` accepts semicolon-separated values and both LiteLLM and Pipelines are OpenAI-compatible
   - What's unclear: Whether the Pipelines server's model discovery (`GET /models`) is automatically polled by Open WebUI on startup, or requires a manual "refresh" in the admin UI on first run
   - Recommendation: Implement via env var (lowest friction); include a verification step in the plan to confirm the MAAI Agent model appears after `docker compose up`

2. **Does the Pipelines server's `/health` endpoint use the same path pattern as other services?**
   - What we know: The container runs on port 9099; healthcheck pattern from Phase 1 uses `urllib.request.urlopen`
   - What's unclear: Exact health endpoint path on `ghcr.io/open-webui/pipelines:main`
   - Recommendation: Try `/health` first; fallback to checking port availability with `nc` if that fails; verify during Wave 0

3. **`crew.akickoff()` vs `run_in_executor` — which is more stable in CrewAI 1.13?**
   - What we know: Both approaches work; `akickoff()` is CrewAI's native async path; `run_in_executor` is a general Python pattern
   - What's unclear: Whether `akickoff()` has any known issues in 1.13.x
   - Recommendation: Use `run_in_executor` as the conservative choice; it's simpler to reason about and always works regardless of CrewAI internal async implementation

---

## Sources

### Primary (HIGH confidence)

- [CrewAI LLMs docs](https://docs.crewai.com/en/concepts/llms) — LLM() constructor params, base_url, model format
- [CrewAI Agents docs](https://docs.crewai.com/en/concepts/agents) — max_iter, max_execution_time, memory params
- [CrewAI Tasks docs](https://docs.crewai.com/en/concepts/tasks) — kickoff(inputs={}), template variables
- [CrewAI Memory docs](https://docs.crewai.com/en/concepts/memory) — embedder config structure for Ollama
- [Open WebUI Pipelines overview](https://docs.openwebui.com/features/extensibility/pipelines/) — pipe vs filter, server setup
- [Open WebUI env config](https://docs.openwebui.com/reference/env-configuration/) — OPENAI_API_BASE_URLS semicolon format confirmed
- [DeepWiki Pipelines](https://deepwiki.com/open-webui/pipelines/7.1-creating-custom-pipelines) — pipe() method signature, Valves pattern
- [DeepWiki Pipelines Docker](https://deepwiki.com/open-webui/pipelines/7.2-docker-deployment) — volume mount approach for local files

### Secondary (MEDIUM confidence)

- [open-webui-n8n-pipe GitHub](https://github.com/sboily/open-webui-n8n-pipe) — Real-world pipe-to-external-API pattern with httpx and `__event_emitter__`
- [Pipelines discussion #310](https://github.com/open-webui/pipelines/discussions/310) — `__event_emitter__` status event format
- [CrewAI issue #2503](https://github.com/crewAIInc/crewAI/issues/2503) — max_execution_time bug (closed, fixed March 2025)
- [FastAPI async docs](https://fastapi.tiangolo.com/async/) — run_in_executor pattern for sync code in async handlers

### Tertiary (LOW confidence)

- [WebSearch: OPENAI_API_KEYS semicolon format](https://github.com/open-webui/open-webui/discussions/19684) — Multiple API keys format needs verification against actual Open WebUI behavior at startup

---

## Project Constraints (from CLAUDE.md)

All directives below are binding on the planner and implementer:

| Directive | Impact on Phase 2 |
|-----------|-------------------|
| No `console.log()` or `print()` for logging — use a logger service | All FastAPI and CrewAI code must use Python `logging` module via a `get_logger()` helper |
| Python 3.11 only | `FROM python:3.11-slim` in Core API Dockerfile |
| `litellm>=1.83.0` — NEVER use 1.82.7 or 1.82.8 | Not directly installed in Core API; but verify if CrewAI pins a LiteLLM dependency |
| `crewai>=1.13.0` with `pydantic>=2.0` | Pin in pyproject.toml for Core API |
| `fastapi>=0.115.0` with `pydantic>=2.0` | Pin in pyproject.toml for Core API |
| `httpx>=0.27.x` for async HTTP (not `requests`) | Use httpx in Pipelines pipe for calling Core API |
| `docker compose` (not `docker-compose`) | All docs and scripts use `docker compose` |
| All processing local — no data leaves machine | Core API never calls external APIs; only `http://litellm:4000/v1` (internal) |
| GSD workflow enforcement — no direct edits outside GSD | Enforced by workflow; not a code constraint |

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries from CLAUDE.md; versions verified
- Architecture patterns: HIGH — Pipe class structure from DeepWiki + real-world n8n-pipe example; CrewAI patterns from official docs
- Pitfalls: HIGH — most identified from GitHub issues with documented fixes; one (OPENAI_API_KEYS count) is common sense from semicolon-separator pattern
- Validation architecture: HIGH — existing pytest setup discovered; test commands derived from established patterns

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable APIs; Open WebUI Pipelines changes infrequently)
