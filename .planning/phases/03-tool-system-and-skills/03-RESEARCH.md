# Phase 3: Tool System and Skills - Research

**Researched:** 2026-04-08
**Domain:** CrewAI dynamic crew assembly, plugin tool registry, embedding-based skill routing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Each skill is a **self-contained YAML file** in `clients/<client>/skills/`. One file per skill. Adding a skill = drop a file, removing = delete it.
- **D-02:** Skill YAML includes everything inline: name, description, triggers, autonomy setting, tools list, agent config (role/goal/backstory), and task config (description/expected_output). No separate agents.yaml/tasks.yaml per skill.
- **D-03:** Skill registry **auto-discovers** all `.yaml` files in the skills directory at startup and builds the skill index.
- **D-04:** The existing **freeform agent stays hardcoded** in core_api as the built-in fallback. It is NOT a skill file. Clients cannot accidentally delete it.
- **D-05:** Skill Matcher uses **embedding similarity**. At startup, embed each skill's name + description + triggers using nomic-embed-text (already pulled via Ollama). At runtime, embed the user message and cosine-similarity match against all skill embeddings.
- **D-06:** **Three-zone routing**: score >= 0.7 auto-runs the matched skill; 0.5 <= score < 0.7 asks the user to confirm ("Did you mean [skill name]?"); score < 0.5 falls through to freeform agent.
- **D-07:** The LLM **never sees all skill definitions**. The Skill Matcher works from a lightweight in-memory index (name + description + triggers). Only the matched skill's agent + tools are loaded into the LLM context for execution.
- **D-08:** Tools live in `src/core_api/tools/`, one Python file per tool. Each file exports a CrewAI `BaseTool` subclass. Tool registry scans the directory at startup and builds the `{name: ToolClass}` map.
- **D-09:** Per-client tool enable/disable via **allowlist** in `clients/<client>/tools.yaml`. Only listed tools are available. If `tools.yaml` is missing, all discovered tools are enabled (sensible default).
- **D-10:** Skill YAML references tools by name (e.g., `tools: [docling_extract]`). At skill load time, names are resolved against the tool registry filtered by the client's allowlist.
- **D-11:** Each skill has an `autonomy` field: `auto-execute` or `confirm-first`.
- **D-12:** **Default is `confirm-first`** when the autonomy field is missing from YAML. Deployer must explicitly opt into `auto-execute`.
- **D-13:** Confirm-first works via **chat message confirmation**: agent describes what it will do and asks the user to confirm with "yes" or "go ahead". Next user message is interpreted as confirmation or cancellation. Works within existing Open WebUI chat flow.
- **D-14:** Users can type "list skills" or "what can you do?" and the system returns the available skill index as a chat message. Read-only, no admin UI. Enable/disable stays file-based.

### Claude's Discretion

- Embedding index storage format (in-memory dict, numpy array, etc.)
- Exact similarity thresholds (0.5/0.7 are starting points, can be tuned)
- Tool registry implementation details (importlib scanning pattern)
- Confirmation message phrasing and cancellation keyword handling
- CrewAI Crew assembly pattern for dynamically loaded skills
- How the "list skills" / "what can you do?" detection works (can be a simple keyword check or part of the skill matcher)

### Deferred Ideas (OUT OF SCOPE)

- **Admin UI for skill management in Open WebUI** -- Would require custom UI components. Not in Phase 3 scope.
- **Dry-run / action plan confirmation** -- Show detailed plan of what a skill will do before executing. Consider for Phase 5+.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGNT-01 | Agents, tasks, and tool assignments defined in YAML config files | D-01/D-02: self-contained skill YAML; D-08: BaseTool subclass per file |
| AGNT-02 | Pre-configured "skills" (named tasks) triggered by name or natural language match | D-05/D-06: embedding similarity three-zone routing |
| AGNT-03 | Skill Matcher routes user requests to the best matching skill or freeform fallback | D-06: score < 0.5 falls through; D-04: freeform fallback unchanged |
| AGNT-04 | Plugin-based tool system — tools enabled/disabled per client via YAML config | D-09: allowlist in clients/<client>/tools.yaml |
| AGNT-05 | Tool registry discovers and loads available plugins at startup | D-08: importlib scan of src/core_api/tools/ at FastAPI lifespan startup |
| AGNT-06 | Per-workflow autonomy control (auto-execute vs confirm-first) configurable in YAML | D-11/D-12/D-13: autonomy field; confirm-first via chat confirmation message |
</phase_requirements>

---

## Summary

Phase 3 adds three new subsystems on top of the existing FastAPI + CrewAI + Ollama stack established in Phases 1 and 2: (1) a plugin-based tool registry that discovers `BaseTool` subclasses from `src/core_api/tools/` using `importlib`, (2) a skill registry that auto-discovers per-client YAML files and builds an in-memory embedding index using nomic-embed-text via Ollama's REST API, and (3) a Skill Matcher that intercepts the `/chat` endpoint before the freeform fallback and routes to the best-matching skill crew.

The critical implementation insight is that CrewAI tools cannot be declared by name in YAML files — the framework requires actual instantiated tool objects passed to `Agent(tools=[...])` at runtime. This means the skill YAML stores tool names as strings, and the skill executor resolves those names against the live tool registry to get instantiated objects before assembling the crew. Crew assembly for skills happens entirely in Python without `@CrewBase` — using direct `Agent`, `Task`, and `Crew` constructors, which is the supported non-decorator pattern.

The Ollama embedding API now has two endpoints: the legacy `/api/embeddings` (single input, float64, deprecated) and the recommended `/api/embed` (batch input, float32, L2-normalized). The existing `freeform_crew.py` references `/api/embeddings` for the CrewAI embedder config — that embedded path is inside CrewAI's ollama provider and is not the same endpoint the Skill Matcher will call directly. The Skill Matcher should call `/api/embed` directly via `httpx` for runtime embedding generation.

**Primary recommendation:** Build SkillRegistry and ToolRegistry as singleton modules initialized at FastAPI `lifespan` startup. Insert a `SkillRouter` function at the top of the `/chat` handler that checks for "list skills" keywords first, then runs the embedding match, and returns a `RoutingDecision` enum to the handler (AUTO_RUN, CONFIRM_FIRST, FREEFORM, LIST_SKILLS).

---

## Standard Stack

### Core (already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| crewai[litellm] | >=1.13.0 | Agent/task/crew assembly + BaseTool base class | Project-locked; `from crewai.tools import BaseTool` |
| fastapi | >=0.115.0 | API layer, lifespan startup hook | Project-locked |
| pydantic | >=2.0 | Skill YAML schema validation | Project-locked; CrewAI requires v2 |
| pyyaml | >=6.0 | YAML file parsing | Already in pyproject.toml |
| httpx | >=0.27.0 | Call Ollama /api/embed for Skill Matcher | Already in pyproject.toml |
| python-dotenv | >=1.0 | Read EMBEDDING_MODEL env var | Already in pyproject.toml |

### New Dependency
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| numpy | >=1.26 | Cosine similarity dot products on embedding vectors | nomic-embed-text outputs 768-dim float vectors; numpy is fastest for normalized dot product; already a transitive dep of crewai but should be declared explicitly |

**Installation:**
```bash
# Inside src/core_api/ with uv:
uv add numpy
```

**Version verification (run before locking):**
```bash
npm view numpy version  # wrong tool -- use:
uv pip show numpy | grep Version
```
numpy >=1.26 is safe for Python 3.11 and is already a transitive dependency of crewai.

---

## Architecture Patterns

### Recommended Project Structure (additions to existing src/core_api/)
```
src/core_api/
├── agents/
│   ├── freeform_crew.py          # UNCHANGED (Phase 2 baseline)
│   └── config/
│       ├── agents.yaml           # UNCHANGED
│       └── tasks.yaml            # UNCHANGED
├── tools/                        # NEW — one file per tool plugin
│   ├── __init__.py
│   └── echo_tool.py              # Placeholder/example tool for Phase 3
├── skills/                       # NEW — skill system modules
│   ├── __init__.py
│   ├── registry.py               # SkillRegistry: YAML discovery + embedding index
│   ├── tool_registry.py          # ToolRegistry: importlib scan of tools/
│   ├── matcher.py                # SkillMatcher: embed query, cosine similarity, routing
│   ├── executor.py               # SkillExecutor: assemble Crew from matched skill YAML
│   └── models.py                 # Pydantic models: SkillDef, RoutingDecision, ToolAllowlist
├── routers/
│   └── chat.py                   # MODIFIED — insert SkillRouter before freeform fallback
├── main.py                       # MODIFIED — register SkillRegistry/ToolRegistry at lifespan

clients/
└── default/
    ├── skills/                   # NEW — per-client skill YAML files
    │   └── example_skill.yaml    # Demo skill for Phase 3 testing
    └── tools.yaml                # NEW — per-client tool allowlist (optional)
```

### Pattern 1: CrewAI BaseTool Subclass (Tool Plugin)
**What:** Each tool is a standalone Python file exporting exactly one `BaseTool` subclass with `name`, `description`, `args_schema`, and `_run`.
**When to use:** For every piece of reusable capability (file ops, API calls, data transformations).

```python
# Source: https://docs.crewai.com/en/learn/create-custom-tools
# File: src/core_api/tools/echo_tool.py
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from logging_config import get_logger

logger = get_logger(__name__)


class EchoInput(BaseModel):
    """Input schema for EchoTool."""
    message: str = Field(..., description="The message to echo back.")


class EchoTool(BaseTool):
    name: str = "echo"
    description: str = "Echoes back the provided message. Used for testing."
    args_schema: Type[BaseModel] = EchoInput

    def _run(self, message: str) -> str:
        logger.info("EchoTool called with message length=%d", len(message))
        return f"Echo: {message}"
```

**Registration contract:** The tool registry discovers this class by scanning `tools/`, importing the module, and looking for any class that is a non-abstract subclass of `BaseTool`. The `name` attribute becomes the registry key. Skill YAML references it as `tools: [echo]`.

### Pattern 2: Tool Registry via importlib
**What:** Scan `src/core_api/tools/` at startup, import each `.py` file, find `BaseTool` subclasses.
**When to use:** At FastAPI `lifespan` startup. Not at request time.

```python
# Source: Python stdlib docs + https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view
# File: src/core_api/skills/tool_registry.py
import importlib.util
import inspect
from pathlib import Path
from crewai.tools import BaseTool
from logging_config import get_logger

logger = get_logger(__name__)

_REGISTRY: dict[str, type[BaseTool]] = {}


def load_tools(tools_dir: Path) -> dict[str, type[BaseTool]]:
    """Scan tools_dir, import each .py module, register BaseTool subclasses."""
    registry: dict[str, type[BaseTool]] = {}
    for path in sorted(tools_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseTool) and obj is not BaseTool and not inspect.isabstract(obj):
                registry[obj.name] = obj
                logger.info("Registered tool: %s from %s", obj.name, path.name)
    return registry


def get_registry() -> dict[str, type[BaseTool]]:
    return _REGISTRY


def initialize(tools_dir: Path) -> None:
    global _REGISTRY
    _REGISTRY = load_tools(tools_dir)
    logger.info("Tool registry initialized: %d tools", len(_REGISTRY))
```

### Pattern 3: Skill YAML Schema
**What:** A single YAML file that is the complete definition of one skill.
**When to use:** One file per client skill. Drop-in to enable, delete to remove.

```yaml
# File: clients/default/skills/example_skill.yaml
name: example_skill
description: "An example skill that echoes back what you say."
triggers:
  - "echo this"
  - "repeat after me"
  - "say it back"
autonomy: confirm-first   # or auto-execute; omit to default to confirm-first
tools:
  - echo
agent:
  role: "Echo Agent"
  goal: "Echo back the user's message exactly as provided."
  backstory: >
    You are a simple demonstration agent. You receive a message
    and return it verbatim to confirm the skill system is working.
task:
  description: >
    Echo the following user message back exactly:
    {user_message}
  expected_output: "The user's message echoed back verbatim."
```

**Key design notes:**
- `tools` is a list of strings matching `BaseTool.name` values in the tool registry.
- `autonomy` defaults to `confirm-first` when absent (D-12).
- `triggers` are short natural language phrases used to build the embedding representation alongside `name` and `description`.

### Pattern 4: Skill Registry and Embedding Index
**What:** Load all skill YAML files at startup, embed `name + " " + description + " " + triggers.join(" ")` using nomic-embed-text, store in a normalized numpy matrix.
**When to use:** At FastAPI `lifespan` startup, after tool registry is ready.

```python
# File: src/core_api/skills/registry.py
import os
from dataclasses import dataclass
from pathlib import Path
import httpx
import numpy as np
import yaml
from pydantic import BaseModel, Field
from typing import Optional
from logging_config import get_logger

logger = get_logger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


class SkillDef(BaseModel):
    name: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    autonomy: str = "confirm-first"
    tools: list[str] = Field(default_factory=list)
    agent: dict
    task: dict


@dataclass
class SkillIndex:
    skills: list[SkillDef]
    embeddings: np.ndarray  # shape (N, D), L2-normalized


_INDEX: Optional[SkillIndex] = None


def _embed_text(text: str) -> np.ndarray:
    """Call Ollama /api/embed synchronously. Returns L2-normalized vector."""
    response = httpx.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=30.0,
    )
    response.raise_for_status()
    vec = np.array(response.json()["embeddings"][0], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def load_skills(skills_dir: Path, allowed_tools: Optional[set[str]] = None) -> SkillIndex:
    """Discover and embed all skill YAML files in skills_dir."""
    skills = []
    vectors = []
    for path in sorted(skills_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        skill = SkillDef(**raw)
        # Filter tools against allowlist
        if allowed_tools is not None:
            skill.tools = [t for t in skill.tools if t in allowed_tools]
        embed_text = skill.name + " " + skill.description + " " + " ".join(skill.triggers)
        vec = _embed_text(embed_text)
        skills.append(skill)
        vectors.append(vec)
        logger.info("Indexed skill: %s", skill.name)
    matrix = np.stack(vectors) if vectors else np.empty((0, 768), dtype=np.float32)
    return SkillIndex(skills=skills, embeddings=matrix)


def get_index() -> Optional[SkillIndex]:
    return _INDEX


def initialize(skills_dir: Path, allowed_tools: Optional[set[str]] = None) -> None:
    global _INDEX
    _INDEX = load_skills(skills_dir, allowed_tools)
    logger.info("Skill registry initialized: %d skills", len(_INDEX.skills))
```

### Pattern 5: Skill Matcher — Three-Zone Routing
**What:** Embed user message, compute cosine similarity against skill matrix, return routing decision.

```python
# File: src/core_api/skills/matcher.py
from enum import Enum
import numpy as np
import httpx
import os
from logging_config import get_logger
from skills.registry import get_index, _embed_text, SkillDef
from typing import Optional

logger = get_logger(__name__)

HIGH_THRESHOLD = float(os.getenv("SKILL_HIGH_THRESHOLD", "0.7"))
LOW_THRESHOLD = float(os.getenv("SKILL_LOW_THRESHOLD", "0.5"))

LIST_SKILLS_KEYWORDS = frozenset(["list skills", "what can you do", "show skills", "available skills"])


class RoutingDecision(Enum):
    AUTO_RUN = "auto_run"
    CONFIRM_FIRST = "confirm_first"
    FREEFORM = "freeform"
    LIST_SKILLS = "list_skills"


class MatchResult:
    def __init__(self, decision: RoutingDecision, skill: Optional[SkillDef] = None, score: float = 0.0):
        self.decision = decision
        self.skill = skill
        self.score = score


def route(user_message: str) -> MatchResult:
    """Return routing decision for user_message."""
    lower = user_message.lower().strip()
    if any(kw in lower for kw in LIST_SKILLS_KEYWORDS):
        logger.info("Routing: LIST_SKILLS (keyword match)")
        return MatchResult(RoutingDecision.LIST_SKILLS)

    index = get_index()
    if index is None or len(index.skills) == 0:
        logger.info("Routing: FREEFORM (no skills indexed)")
        return MatchResult(RoutingDecision.FREEFORM)

    query_vec = _embed_text(user_message)
    scores = index.embeddings @ query_vec  # dot product of normalized vecs = cosine sim
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    skill = index.skills[best_idx]

    logger.info("Skill match: skill=%s score=%.3f", skill.name, best_score)

    if best_score >= HIGH_THRESHOLD:
        if skill.autonomy == "auto-execute":
            return MatchResult(RoutingDecision.AUTO_RUN, skill, best_score)
        else:
            return MatchResult(RoutingDecision.CONFIRM_FIRST, skill, best_score)
    elif best_score >= LOW_THRESHOLD:
        return MatchResult(RoutingDecision.CONFIRM_FIRST, skill, best_score)
    else:
        return MatchResult(RoutingDecision.FREEFORM, skill=None, score=best_score)
```

### Pattern 6: Dynamic Crew Assembly (no @CrewBase)
**What:** Assemble a CrewAI Crew from a matched SkillDef entirely in Python, passing resolved tool instances.
**When to use:** At skill execution time, after routing decision is AUTO_RUN or confirmed.

```python
# Source: https://docs.crewai.com/en/concepts/crews
# File: src/core_api/skills/executor.py
import os
from crewai import LLM, Agent, Crew, Process, Task
from skills.registry import SkillDef
from skills.tool_registry import get_registry
from logging_config import get_logger

logger = get_logger(__name__)


def run_skill(skill: SkillDef, user_message: str, messages: list) -> str:
    """Assemble and execute a skill crew. Returns response string."""
    tool_registry = get_registry()
    tool_instances = []
    for tool_name in skill.tools:
        if tool_name in tool_registry:
            tool_instances.append(tool_registry[tool_name]())  # instantiate
        else:
            logger.warning("Tool '%s' not found in registry — skipping", tool_name)

    llm = LLM(
        model="openai/reasoning-model",
        base_url=os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1"),
        api_key=os.getenv("LITELLM_MASTER_KEY", "sk-maai-local"),
        stream=False,
        timeout=60.0,
    )

    agent = Agent(
        role=skill.agent["role"],
        goal=skill.agent["goal"],
        backstory=skill.agent.get("backstory", ""),
        llm=llm,
        tools=tool_instances,
        max_iter=5,
        max_execution_time=60,
        memory=False,
        verbose=False,
    )

    task = Task(
        description=skill.task["description"].format(user_message=user_message),
        expected_output=skill.task["expected_output"],
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        embedder={
            "provider": "ollama",
            "config": {
                "model_name": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                "url": "http://ollama:11434/api/embeddings",  # CrewAI uses legacy path
            },
        },
    )

    logger.info("Executing skill: %s", skill.name)
    result = crew.kickoff(inputs={"user_message": user_message})
    logger.info("Skill execution complete: %s", skill.name)
    return str(result)
```

**Important note on Ollama embed endpoints:** CrewAI's built-in ollama embedder provider hardcodes the legacy `/api/embeddings` path internally. The Skill Matcher's own embedding calls go directly to `/api/embed` (the current endpoint). These two code paths are separate and both work — CrewAI's internal embedder path is not controlled by this codebase.

### Pattern 7: Modified /chat Endpoint (Routing Insertion)
**What:** Insert skill routing at the top of the existing `/chat` handler before the freeform fallback. Maintain pending confirmation state per conversation.

```python
# File: src/core_api/routers/chat.py (modified)
# Routing logic inserted before run_freeform_crew call:
#
# 1. Check for pending confirmation in conversation history
# 2. Check "list skills" keyword
# 3. Run embedding match
# 4. Based on RoutingDecision: run skill, return confirm prompt, or fall through
```

**Confirmation state tracking:** Because Open WebUI does not expose server-side session state, pending confirmations are detected by inspecting the last N messages in the conversation history for the pattern: assistant asked a confirm-first question, user replied "yes"/"go ahead"/"no"/"cancel". This is stateless from the server's perspective — no Redis or session store needed for Phase 3.

### Pattern 8: Lifespan Registration
**What:** Initialize tool registry and skill registry during FastAPI app startup.

```python
# File: src/core_api/main.py (modified)
@asynccontextmanager
async def lifespan(app: FastAPI):
    from pathlib import Path
    import skills.tool_registry as tool_reg
    import skills.registry as skill_reg

    client_id = os.getenv("CLIENT_ID", "default")
    tools_dir = Path("src/core_api/tools")
    skills_dir = Path(f"clients/{client_id}/skills")

    tool_reg.initialize(tools_dir)
    
    # Load allowlist from clients/<client>/tools.yaml if present
    allowlist_path = Path(f"clients/{client_id}/tools.yaml")
    allowed_tools = None
    if allowlist_path.exists():
        data = yaml.safe_load(allowlist_path.read_text())
        allowed_tools = set(data.get("enabled_tools", []))

    if skills_dir.exists():
        skill_reg.initialize(skills_dir, allowed_tools)
    else:
        logger.warning("No skills directory found at %s", skills_dir)
    
    logger.info("MAAI Core API started")
    yield
    logger.info("MAAI Core API shutting down")
```

### Anti-Patterns to Avoid

- **Storing tool names in YAML and resolving in YAML parsers:** CrewAI cannot resolve tool names from YAML strings — tools must be Python objects. Always resolve in `executor.py`.
- **Calling Ollama embeddings at request time without timeout:** `httpx.post` to Ollama can hang during model load. Always set a timeout (30s minimum). Embedding calls at startup are acceptable as a blocking operation since they prevent a broken index from serving requests.
- **Embedding all skill content (full task description) for matching:** Only embed `name + description + triggers`. Full task descriptions add noise and increase token count without improving routing accuracy.
- **Holding `@CrewBase` pattern for dynamic skills:** `@CrewBase` resolves YAML paths relative to the decorated class file location — it cannot load from arbitrary runtime paths. Use the direct constructor pattern (Pattern 6) for dynamic skill crews.
- **Re-scanning the tools directory on every request:** Tool and skill registries are startup-only. Adding a new tool requires a container restart. This is by design (no hot-reload in Phase 3).
- **Using `asyncio.run()` inside `run_skill()`:** The function runs inside `loop.run_in_executor()` from the async handler — the event loop is already running. Keep `run_skill` fully synchronous.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool input validation | Custom arg parsers | `BaseTool` + `args_schema: Type[BaseModel]` | CrewAI validates inputs against the Pydantic schema automatically before calling `_run` |
| Embedding computation | Local sentence-transformers, custom model | Ollama `/api/embed` with nomic-embed-text | Model already running, returns L2-normalized vectors, no extra dependency |
| YAML schema validation | Manual key checking | Pydantic `SkillDef(BaseModel)` on `yaml.safe_load()` output | Fails fast with clear errors at startup, not at runtime |
| HTTP calls in tool `_run` | `requests.get()` | `httpx.get()` (sync inside `_run` is fine) | Tools run in executor threads, not in the async event loop; `requests` is acceptable in `_run` but `httpx` sync is already a dep |
| Vector similarity | Custom cosine loop | `np.ndarray @ query_vec` after L2 normalization | For N < 1000 skills, matrix-vector dot product with numpy is instantaneous; no need for FAISS or Qdrant |

**Key insight:** For skill matching at this scale (< 100 skills per client), a numpy in-memory dot product on pre-normalized vectors is faster and simpler than any vector database. Qdrant is reserved for document RAG in Phase 4, not skill routing.

---

## Common Pitfalls

### Pitfall 1: Tool Names Not Discoverable from YAML
**What goes wrong:** Developer declares `tools: [docling_extract]` in skill YAML, but the tool class has `name: str = "DoclingExtract"` (capitalization mismatch). Tool lookup returns None silently, skill runs with no tools.
**Why it happens:** YAML is case-sensitive. Tool registry key is `BaseTool.name` attribute value verbatim.
**How to avoid:** Convention — all `BaseTool.name` values must be `snake_case`. Validate at skill load time: log a WARNING if a skill references a tool name not in the registry.
**Warning signs:** Skill runs but produces poor results because no tools were injected.

### Pitfall 2: Embedding Call Blocks Startup for Minutes
**What goes wrong:** `load_skills()` calls `_embed_text()` synchronously for each skill. If Ollama is still loading nomic-embed-text on first call, the embedding request takes 30-60s. With 10 skills, startup takes 5-10 minutes.
**Why it happens:** Ollama loads the embedding model lazily on first request.
**How to avoid:** Warm up the embedding model with a single dummy request in the lifespan hook before building the index. Alternatively, call `/api/embed` with `input: ["warmup"]` before the skill loop.
**Warning signs:** Core API health check times out during startup.

### Pitfall 3: Confirm-First State Lost Between Requests
**What goes wrong:** User sends a message, gets a confirm-first prompt. Sends "yes". The `/chat` handler receives "yes" with no memory of what was being confirmed.
**Why it happens:** The handler is stateless — each request is independent.
**How to avoid:** The handler must inspect `request.messages` (conversation history) to detect the pending confirmation pattern: last assistant message contains the confirmation prompt phrase, and current user message is an affirmative. Store the pending skill name in the assistant's confirmation message text itself (e.g., "Shall I run the **example_skill** skill? Reply yes to proceed.") so it can be parsed from history.
**Warning signs:** User confirms but gets freeform fallback response instead of skill execution.

### Pitfall 4: `@CrewBase` Cannot Load Arbitrary YAML Paths
**What goes wrong:** Developer tries to adapt `FreeformCrew` pattern (which uses `@CrewBase` with `agents_config = "config/agents.yaml"`) for dynamic skills by changing the YAML path at runtime. This fails because `@CrewBase` resolves paths relative to the class file location using `__file__` — it does not accept absolute paths or runtime-computed paths.
**Why it happens:** `@CrewBase` is a convenience decorator for static, file-based crews. It is not designed for dynamic loading.
**How to avoid:** Use direct `Agent`, `Task`, `Crew` constructors for all skill-crew assembly (Pattern 6).
**Warning signs:** `FileNotFoundError` or `KeyError` at skill execution time when paths are correct on disk.

### Pitfall 5: `asyncio.get_event_loop()` Deprecation in Python 3.10+
**What goes wrong:** `chat.py` currently uses `loop = asyncio.get_event_loop()`. In Python 3.12 this will warn; in newer contexts it can fail.
**Why it happens:** The correct idiom in async FastAPI handlers is `asyncio.get_running_loop()`.
**How to avoid:** Replace `asyncio.get_event_loop()` with `asyncio.get_running_loop()` when modifying `chat.py` for Phase 3.
**Warning signs:** DeprecationWarnings in logs; test failures in future Python versions.

### Pitfall 6: Ollama /api/embed vs /api/embeddings Confusion
**What goes wrong:** The Skill Matcher calls `/api/embeddings` (legacy, single input, float64) while expecting L2-normalized float32 vectors. The legacy endpoint does NOT guarantee L2 normalization — manual normalization is needed.
**Why it happens:** Old documentation and existing code (`freeform_crew.py` embedder config) reference `/api/embeddings`.
**How to avoid:** Skill Matcher's `_embed_text()` MUST call `/api/embed` (current, batch-capable, float32, L2-normalized). CrewAI's internal ollama embedder (in `Crew(embedder=...)`) still calls the legacy path internally — that is acceptable since it is handled by the CrewAI library.
**Warning signs:** Cosine similarity scores are unexpectedly low (< 0.3 for clear matches) due to unnormalized vectors.

---

## Code Examples

### tools.yaml allowlist format
```yaml
# File: clients/default/tools.yaml
# Omit this file entirely to enable all discovered tools.
enabled_tools:
  - echo
  # - docling_extract  # will be enabled when Phase 4 tools are ready
```

### Skill YAML with autonomy
```yaml
# File: clients/default/skills/example_skill.yaml
name: example_skill
description: "An example skill that echoes back what you say."
triggers:
  - "echo this"
  - "repeat after me"
autonomy: confirm-first
tools:
  - echo
agent:
  role: "Echo Agent"
  goal: "Echo back the user's message exactly."
  backstory: "You are a demonstration agent that confirms the skill system works."
task:
  description: "Echo the following message back exactly: {user_message}"
  expected_output: "The user's message echoed back verbatim."
```

### httpx embedding call to /api/embed
```python
# Direct call to current Ollama embed endpoint
response = httpx.post(
    "http://ollama:11434/api/embed",
    json={"model": "nomic-embed-text", "input": "some text to embed"},
    timeout=30.0,
)
embeddings = response.json()["embeddings"][0]  # list of floats, L2-normalized
```

### Cosine similarity with pre-normalized numpy vectors
```python
# After normalization (done once at index build time):
# index.embeddings shape: (N_skills, D)
# query_vec shape: (D,), L2-normalized
scores = index.embeddings @ query_vec  # shape: (N_skills,)
best_idx = int(np.argmax(scores))
best_score = float(scores[best_idx])
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/api/embeddings` (single input, float64) | `/api/embed` (batch, float32, L2-normalized) | Ollama 0.3.x (late 2024) | Skill Matcher should use `/api/embed`; CrewAI embedder config still uses legacy path (managed by library) |
| `asyncio.get_event_loop()` in async handlers | `asyncio.get_running_loop()` | Python 3.10 | Fix in chat.py while modifying it for Phase 3 |
| Tools declared in YAML by name (attempted pattern) | Tools passed as Python objects to `Agent(tools=[...])` | CrewAI 0.x → 1.x | Skill executor must resolve names to instances before crew assembly |
| `@CrewBase` for all crews | Direct `Agent`/`Task`/`Crew` constructors for dynamic crews | CrewAI 1.x (design decision) | Skill crews cannot use `@CrewBase` |

---

## Environment Availability

Phase 3 is code-only changes to `src/core_api/` — all required services are already running from Phases 1 and 2.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Ollama `/api/embed` | SkillMatcher embedding | Assumed via Phase 1 | 0.20.x | Startup warning if unreachable; skill matching disabled |
| nomic-embed-text model | SkillMatcher embedding | Bootstrapped in Phase 1 | — | None — must be pulled |
| LiteLLM proxy | Skill crew LLM calls | Running from Phase 1 | >=1.83.0 | None |
| Core API container | Host for all new code | Running from Phase 2 | — | None |
| numpy | Cosine similarity | Must be added to pyproject.toml | >=1.26 | None (small dep, always available) |

**Missing dependencies with no fallback:**
- None that aren't already part of the stack.

**Missing dependencies with fallback:**
- numpy must be added to `src/core_api/pyproject.toml` — it is likely already a transitive dependency of crewai but must be declared explicitly for clarity.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) and `pytest.ini` (top-level) |
| Quick run command | `pytest tests/phase3/ -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-01 | Skill YAML with all required fields is loadable and validates against SkillDef | unit | `pytest tests/phase3/test_skill_registry.py::test_skill_yaml_loads -x` | Wave 0 |
| AGNT-01 | Tool BaseTool subclass exported from tools/ is discoverable | unit | `pytest tests/phase3/test_tool_registry.py::test_tool_discovered -x` | Wave 0 |
| AGNT-02 | Skill triggered by name match routes to AUTO_RUN | unit | `pytest tests/phase3/test_matcher.py::test_name_match_routes_auto_run -x` | Wave 0 |
| AGNT-02 | Skill triggered by natural language match routes correctly | unit (mock embeddings) | `pytest tests/phase3/test_matcher.py::test_natural_language_match -x` | Wave 0 |
| AGNT-03 | Low-score message falls through to FREEFORM decision | unit | `pytest tests/phase3/test_matcher.py::test_low_score_freeform -x` | Wave 0 |
| AGNT-03 | "list skills" keyword returns LIST_SKILLS decision | unit | `pytest tests/phase3/test_matcher.py::test_list_skills_keyword -x` | Wave 0 |
| AGNT-04 | Tool disabled in tools.yaml is not in resolved tool set | unit | `pytest tests/phase3/test_tool_registry.py::test_allowlist_filtering -x` | Wave 0 |
| AGNT-04 | Missing tools.yaml enables all tools | unit | `pytest tests/phase3/test_tool_registry.py::test_missing_allowlist_enables_all -x` | Wave 0 |
| AGNT-05 | ToolRegistry discovers EchoTool from tools/ directory | unit | `pytest tests/phase3/test_tool_registry.py::test_discovery -x` | Wave 0 |
| AGNT-06 | confirm-first skill returns confirmation prompt, not execution | unit | `pytest tests/phase3/test_chat_router.py::test_confirm_first_returns_prompt -x` | Wave 0 |
| AGNT-06 | auto-execute skill runs immediately without confirmation | unit | `pytest tests/phase3/test_chat_router.py::test_auto_execute_runs -x` | Wave 0 |
| AGNT-06 | Missing autonomy field defaults to confirm-first | unit | `pytest tests/phase3/test_skill_registry.py::test_autonomy_defaults_confirm_first -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/phase3/ -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/phase3/__init__.py` — package init
- [ ] `tests/phase3/conftest.py` — fixtures: mock skill YAML, mock tool dir, patched httpx for embedding calls
- [ ] `tests/phase3/test_skill_registry.py` — covers AGNT-01, AGNT-06 (autonomy default)
- [ ] `tests/phase3/test_tool_registry.py` — covers AGNT-01, AGNT-04, AGNT-05
- [ ] `tests/phase3/test_matcher.py` — covers AGNT-02, AGNT-03 (mock `_embed_text` to return fixed vectors)
- [ ] `tests/phase3/test_chat_router.py` — covers AGNT-06 (mock skill executor, check response format)

**Testing strategy note:** `_embed_text` should be mockable (importable function, not method) so matcher tests never hit a live Ollama instance. Use `unittest.mock.patch` on `skills.registry._embed_text`.

---

## Open Questions

1. **CLIENT_ID resolution at runtime**
   - What we know: `clients/default/` is the current client folder. Phase 1 introduced per-client isolation.
   - What's unclear: Is `CLIENT_ID` already in `client.env`? The current env file does not have a `CLIENT_ID` key.
   - Recommendation: Add `CLIENT_ID=default` to `clients/default/client.env` and read it in `main.py` lifespan. The skill and tool paths become `clients/{CLIENT_ID}/skills/` and `clients/{CLIENT_ID}/tools.yaml`.

2. **Confirmation state: conversation history inspection depth**
   - What we know: The pending confirmation must be detected from `request.messages` (the full history sent from Open WebUI).
   - What's unclear: How many messages back to look. Open WebUI sends the full thread, so looking at the last 2 messages (assistant prompt + user response) is sufficient.
   - Recommendation: Check only `messages[-2]` (last assistant message) for the confirmation phrase pattern. If it contains the magic phrase, interpret `messages[-1]` (current user message) as the confirmation response.

3. **Skill execution uses `run_in_executor` — is the executor pool large enough?**
   - What we know: `FreeformCrew` uses `loop.run_in_executor(None, lambda: ...)` which uses the default `ThreadPoolExecutor`.
   - What's unclear: If a skill and freeform are running concurrently (two browser tabs), they compete for the same executor pool.
   - Recommendation: This is acceptable for Phase 3 (single-user deployments). Flag for Phase 6 if multi-session concurrency becomes a requirement.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 3 |
|-----------|-------------------|
| Never use `console.log()` / always use logger | All new modules (`registry.py`, `tool_registry.py`, `matcher.py`, `executor.py`) MUST use `logging_config.get_logger(__name__)` |
| Python 3.11 only | Confirmed — `pyproject.toml` already pins `>=3.11,<3.12` |
| `litellm>=1.83.0` | Already in stack from Phase 1; skill executor uses same LiteLLM proxy URL |
| `docker compose` (not `docker-compose`) | No Compose changes in Phase 3; constraint noted |
| No paid APIs / local-only | Embedding calls go to Ollama (local), LLM calls go to LiteLLM→Ollama (local) |
| All tools MIT/Apache 2.0/BSD licensed | numpy (BSD), pyyaml (MIT), httpx (BSD), crewai.tools (Apache 2.0) — all compliant |
| Pydantic v2 | `SkillDef(BaseModel)` must use Pydantic v2 syntax (no `validator`, use `field_validator`) |
| `crewai>=1.13.0` | `BaseTool` import: `from crewai.tools import BaseTool` (confirmed current import path) |
| `asyncio.get_event_loop()` pattern in existing `chat.py` | Fix to `asyncio.get_running_loop()` while modifying `chat.py` for Phase 3 routing |

---

## Sources

### Primary (HIGH confidence)
- [CrewAI Custom Tools docs](https://docs.crewai.com/en/learn/create-custom-tools) — `BaseTool` subclass pattern, `args_schema`, `_run` signature confirmed
- [CrewAI Crews docs](https://docs.crewai.com/en/concepts/crews) — programmatic `Agent`/`Task`/`Crew` constructor pattern without `@CrewBase` confirmed
- [Ollama Embedding API DeepWiki](https://deepwiki.com/ollama/ollama/3.3-embedding-api) — `/api/embed` vs `/api/embeddings` deprecation, L2-normalization, batch input confirmed
- [Ollama Embeddings official docs](https://docs.ollama.com/capabilities/embeddings) — current `/api/embed` endpoint format confirmed
- Existing codebase: `src/core_api/agents/freeform_crew.py`, `src/core_api/routers/chat.py`, `src/core_api/main.py` — patterns read directly

### Secondary (MEDIUM confidence)
- [Python importlib plugin pattern](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view) — importlib.util.spec_from_file_location scan pattern; consistent with Python stdlib docs
- [CrewAI community — tools in YAML](https://community.crewai.com/t/how-to-add-tools-to-agents-and-tasks-yaml-files-proper-format-syntax/3321) — tools cannot be resolved from YAML strings; must be Python objects; confirmed from docs
- [Cosine similarity with numpy](https://www.tigerdata.com/learn/implementing-cosine-similarity-in-python) — dot product on L2-normalized vectors equals cosine similarity; standard NumPy pattern

### Tertiary (LOW confidence)
- None — all critical claims verified against official sources or existing codebase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are project-locked from CLAUDE.md; numpy is the only new dep
- Architecture: HIGH — patterns verified from CrewAI docs and existing codebase; no speculation
- Pitfalls: HIGH — CrewAI YAML tool limitation verified from community thread; Ollama endpoint deprecation verified from official docs
- Test architecture: HIGH — test infrastructure (pytest, asyncio_mode=auto) confirmed from existing pyproject.toml

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days — CrewAI and Ollama are stable in this period)
