# Phase 3: Tool System and Skills - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

YAML-defined skills are triggerable by name or natural language, tools load from a plugin registry, and per-client tool enable/disable works without code changes. The Skill Matcher routes user messages to the best matching skill or falls through to the existing freeform agent.

This phase does NOT include: document processing tools (Phase 4), business-specific tools like email/file classification (Phase 5), Redis/ARQ task queuing, or any admin UI for skill management.

</domain>

<decisions>
## Implementation Decisions

### Skill Definition Format
- **D-01:** Each skill is a **self-contained YAML file** in `clients/<client>/skills/`. One file per skill. Adding a skill = drop a file, removing = delete it.
- **D-02:** Skill YAML includes everything inline: name, description, triggers, autonomy setting, tools list, agent config (role/goal/backstory), and task config (description/expected_output). No separate agents.yaml/tasks.yaml per skill.
- **D-03:** Skill registry **auto-discovers** all `.yaml` files in the skills directory at startup and builds the skill index.
- **D-04:** The existing **freeform agent stays hardcoded** in core_api as the built-in fallback. It is NOT a skill file. Clients cannot accidentally delete it.

### Skill Matching Strategy
- **D-05:** Skill Matcher uses **embedding similarity**. At startup, embed each skill's name + description + triggers using nomic-embed-text (already pulled via Ollama). At runtime, embed the user message and cosine-similarity match against all skill embeddings.
- **D-06:** **Three-zone routing**: score >= 0.7 auto-runs the matched skill; 0.5 <= score < 0.7 asks the user to confirm ("Did you mean [skill name]?"); score < 0.5 falls through to freeform agent.
- **D-07:** The LLM **never sees all skill definitions**. The Skill Matcher works from a lightweight in-memory index (name + description + triggers). Only the matched skill's agent + tools are loaded into the LLM context for execution.

### Tool Plugin Architecture
- **D-08:** Tools live in `src/core_api/tools/`, one Python file per tool. Each file exports a CrewAI `BaseTool` subclass. Tool registry scans the directory at startup and builds the `{name: ToolClass}` map.
- **D-09:** Per-client tool enable/disable via **allowlist** in `clients/<client>/tools.yaml`. Only listed tools are available. If `tools.yaml` is missing, all discovered tools are enabled (sensible default).
- **D-10:** Skill YAML references tools by name (e.g., `tools: [docling_extract]`). At skill load time, names are resolved against the tool registry filtered by the client's allowlist.

### Autonomy Control
- **D-11:** Each skill has an `autonomy` field: `auto-execute` or `confirm-first`.
- **D-12:** **Default is `confirm-first`** when the autonomy field is missing from YAML. Deployer must explicitly opt into `auto-execute`.
- **D-13:** Confirm-first works via **chat message confirmation**: agent describes what it will do and asks the user to confirm with "yes" or "go ahead". Next user message is interpreted as confirmation or cancellation. Works within existing Open WebUI chat flow.

### Skill Visibility
- **D-14:** Users can type "list skills" or "what can you do?" and the system returns the available skill index as a chat message. Read-only, no admin UI. Enable/disable stays file-based.

### Claude's Discretion
- Embedding index storage format (in-memory dict, numpy array, etc.)
- Exact similarity thresholds (0.5/0.7 are starting points, can be tuned)
- Tool registry implementation details (importlib scanning pattern)
- Confirmation message phrasing and cancellation keyword handling
- CrewAI Crew assembly pattern for dynamically loaded skills
- How the "list skills" / "what can you do?" detection works (can be a simple keyword check or part of the skill matcher)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Documentation
- `.planning/PROJECT.md` -- Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` -- AGNT-01 through AGNT-06 acceptance criteria
- `.planning/ROADMAP.md` -- Phase 3 success criteria and dependencies
- `CLAUDE.md` -- Technology stack, version compatibility, CrewAI YAML config patterns

### Phase 1 & 2 Artifacts
- `.planning/phases/01-infrastructure-foundation/01-CONTEXT.md` -- Service topology, client config layout, model bootstrapping
- `.planning/phases/02-core-api-and-end-to-end-chat/02-CONTEXT.md` -- Core API architecture, Pipeline integration, freeform agent design
- `src/core_api/agents/freeform_crew.py` -- Existing CrewAI crew pattern (FreeformCrew with @CrewBase, YAML config, LiteLLM routing)
- `src/core_api/agents/config/agents.yaml` -- Existing freeform agent YAML config
- `src/core_api/agents/config/tasks.yaml` -- Existing freeform task YAML config
- `src/core_api/routers/chat.py` -- Existing /chat endpoint (entry point for skill routing)
- `src/core_api/main.py` -- FastAPI app entrypoint
- `src/pipelines/maai_pipe.py` -- Manifold pipe plugin (upstream caller)
- `docker-compose.yml` -- Current Docker stack
- `config/litellm/proxy_config.yaml` -- LiteLLM model aliases (embedding-model for nomic-embed-text)
- `clients/default/client.env` -- Current client config variables

### Technology References (from CLAUDE.md)
- CrewAI >= 1.13.0 with Pydantic v2, YAML-driven agent/task/tool config
- CrewAI `BaseTool` subclass pattern for custom tools
- nomic-embed-text for embeddings (already pulled via Ollama bootstrap)
- FastAPI >= 0.115.x with Pydantic v2

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FreeformCrew` class (`src/core_api/agents/freeform_crew.py`) -- Pattern for assembling CrewAI crews with YAML config, LLM routing through LiteLLM, and Ollama embedder. New skill crews should follow this pattern.
- `run_freeform_crew()` function -- Shows how to kickoff a crew with inputs. Skill execution will follow a similar pattern.
- `/chat` endpoint (`src/core_api/routers/chat.py`) -- Entry point where the Skill Matcher will be inserted before the freeform fallback.
- Logging via `logging_config.get_logger()` -- Established logging pattern, use for all new modules.

### Established Patterns
- CrewAI `@CrewBase` decorator with `agents_config` and `tasks_config` pointing to YAML files
- `LLM()` constructor with LiteLLM proxy URL and model alias
- `loop.run_in_executor()` for running synchronous CrewAI crews in async FastAPI handlers
- Pydantic `BaseModel` for request/response schemas

### Integration Points
- `/chat` endpoint is the insertion point for skill routing (before freeform fallback)
- `clients/<client>/skills/` is a new directory for skill YAML files
- `clients/<client>/tools.yaml` is a new file for tool allowlists
- `src/core_api/tools/` is a new directory for tool Python files
- Ollama embeddings endpoint (`http://ollama:11434/api/embeddings`) for skill matching
- LiteLLM proxy (`http://litellm:4000/v1`) for skill agent LLM calls

</code_context>

<specifics>
## Specific Ideas

- User explicitly wants **context-efficient routing**: the LLM never sees all skills, only the matched skill's tools. This was a primary design concern.
- Skill files should be **drop-in/drop-out** with zero code changes -- the whole point is easy configurability per client.
- "What can you do?" / "list skills" should work as a chat query returning the skill index.

</specifics>

<deferred>
## Deferred Ideas

- **Admin UI for skill management in Open WebUI** -- Would require custom UI components. Not in Phase 3 scope. Could be a future enhancement.
- **Dry-run / action plan confirmation** -- Show detailed plan of what a skill will do before executing (e.g., list of files to move). Adds complexity requiring skills to implement a preview mode. Consider for Phase 5+ when business tools are implemented.

</deferred>

---

*Phase: 03-tool-system-and-skills*
*Context gathered: 2026-04-08*
