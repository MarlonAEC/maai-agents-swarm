# Phase 2: Core API and End-to-End Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 02-core-api-and-end-to-end-chat
**Areas discussed:** WebUI-to-API integration, CrewAI agent design, Service architecture, File upload handling

---

## WebUI-to-API Integration

### Q1: How should Open WebUI route messages to Core API?

| Option | Description | Selected |
|--------|-------------|----------|
| Pipelines plugin | Open WebUI Pipelines — Python filter/pipe plugin that intercepts chat messages and forwards to FastAPI Core API. Native feature, supports streaming. Matches roadmap wording. | ✓ |
| Open WebUI Function | Register Core API as Open WebUI Function (tool). User explicitly invokes or auto-triggers. Less transparent. | |
| Replace LiteLLM endpoint | Point Open WebUI directly at Core API instead of LiteLLM. Core API becomes the proxy layer. | |

**User's choice:** Pipelines plugin (Recommended)
**Notes:** None

### Q2: Should ALL chat messages route through Core API, or pattern-matched only?

| Option | Description | Selected |
|--------|-------------|----------|
| All messages | Every message goes through Pipeline -> Core API -> CrewAI. Agent decides response. Consistent UX. | ✓ |
| Pattern-matched only | Pipeline inspects and only routes skill-like requests. Plain chat direct to LiteLLM. | |
| User-toggled | User switches between 'agent mode' and 'direct chat'. | |

**User's choice:** All messages (Recommended)
**Notes:** None

### Q3: What should user see during agent processing?

| Option | Description | Selected |
|--------|-------------|----------|
| Typing indicator only | Standard 'typing...' indicator. Simple, no extra work. | |
| Status messages | Pipeline sends intermediate status updates as partial responses. User sees progress. | ✓ |
| You decide | Claude's discretion. | |

**User's choice:** Status messages (Recommended)
**Notes:** None

### Q4: Where should the Pipelines plugin run?

| Option | Description | Selected |
|--------|-------------|----------|
| Pipelines Docker container | Separate container running Pipelines server. Plugin mounted as volume. Standard deployment pattern. | ✓ |
| Embedded in Core API | Core API implements Pipelines protocol. One fewer container but tight coupling. | |
| Open WebUI built-in | Upload pipeline via admin UI. No extra container, harder to version control. | |

**User's choice:** Pipelines Docker container (Recommended)
**Notes:** None

---

## CrewAI Agent Design

### Q1: What should Phase 2 freeform agent be capable of?

| Option | Description | Selected |
|--------|-------------|----------|
| Pure conversational | Reasoning-capable LLM wrapper, good system prompt, no tools. Gracefully declines tasks it can't do yet. | ✓ |
| Minimal tools | Include 1-2 basic tools to demonstrate tool-calling works end-to-end. | |
| Stub tools | Placeholder tools returning canned responses. Validates pipeline without real implementations. | |

**User's choice:** Pure conversational (Recommended)
**Notes:** None

### Q2: How should multi-turn conversation context reach the agent?

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline passes history | Open WebUI tracks history. Pipeline forwards full message array to Core API, which injects into agent context. | ✓ |
| Core API tracks sessions | Core API maintains own session store in Redis. Receives only latest message, looks up history. | |
| You decide | Claude's discretion. | |

**User's choice:** Pipeline passes history (Recommended)
**Notes:** None

### Q3: Which LLM model alias for the freeform agent?

| Option | Description | Selected |
|--------|-------------|----------|
| reasoning-model | Use 'reasoning-model' alias from LiteLLM (Qwen3 14B). Consistent with Phase 1 setup. | ✓ |
| Configurable per-agent | Agent YAML config specifies model alias. More flexible but adds complexity. | |
| You decide | Claude's discretion. | |

**User's choice:** reasoning-model (Recommended)
**Notes:** None

### Q4: Max iteration and execution time limits?

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative | max_iter=5, max_execution_time=60s. Prevents runaway loops. Sufficient for conversational use. | ✓ |
| Generous | max_iter=15, max_execution_time=180s. More room for complex reasoning. | |
| You decide | Claude's discretion. | |

**User's choice:** Conservative (Recommended)
**Notes:** None

---

## Service Architecture

### Q1: Should CrewAI run in-process or via ARQ worker?

| Option | Description | Selected |
|--------|-------------|----------|
| In-process | FastAPI calls CrewAI directly. No Redis/ARQ needed yet. Add when async tasks needed (Phase 4/5). | ✓ |
| ARQ worker from start | FastAPI enqueues to Redis/ARQ. Separate worker. More scalable but adds complexity now. | |
| You decide | Claude's discretion. | |

**User's choice:** In-process (Recommended)
**Notes:** None

### Q2: What new Docker services for Phase 2?

| Option | Description | Selected |
|--------|-------------|----------|
| Core API + Pipelines only | Two new services. No Redis yet. | ✓ |
| Core API + Pipelines + Redis | Three new services. Redis established early. | |
| You decide | Claude's discretion. | |

**User's choice:** Core API + Pipelines only (Recommended)
**Notes:** None

### Q3: Where should Core API Python code live?

| Option | Description | Selected |
|--------|-------------|----------|
| src/core_api/ | Top-level src/ directory. Standard Python layout. Dockerfile at src/core_api/Dockerfile. Pipelines at src/pipelines/. | ✓ |
| services/core-api/ | Each Docker service gets own top-level directory under services/. | |
| You decide | Claude's discretion. | |

**User's choice:** src/core_api/ (Recommended)
**Notes:** None

---

## File Upload Handling

### Q1: What should Phase 2 do with uploaded files?

| Option | Description | Selected |
|--------|-------------|----------|
| Accept and acknowledge | Store in shared volume, respond with receipt message. No parsing. Phase 4 adds processing. | ✓ |
| Basic metadata extraction | Read file type, size, page count. More useful feedback without heavy deps. | |
| Pass-through to agent | Forward file reference to agent. Agent mentions file but can't process. | |

**User's choice:** Accept and acknowledge (Recommended)
**Notes:** None

### Q2: Where should uploaded files be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| Shared Docker volume | Named volume 'maai-uploads' mounted in Pipelines and Core API. Phase 4 adds Docling from same volume. | ✓ |
| Client config folder | Store in clients/<client>/uploads/. Ties files to client identity. | |
| You decide | Claude's discretion. | |

**User's choice:** Shared Docker volume (Recommended)
**Notes:** None

---

## Claude's Discretion

- Pipelines plugin implementation details (filter vs pipe type, exact protocol)
- FastAPI endpoint design (routes, request/response schemas)
- CrewAI agent system prompt content
- Docker health check configuration for new services
- Exact Pipelines server image and configuration

## Deferred Ideas

None -- discussion stayed within phase scope.
