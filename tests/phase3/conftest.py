"""Phase 3 test fixtures.

Sets up the Python path and provides common fixtures for Phase 3 tests.
When crewai is not installed (e.g., dev machine running Python 3.14),
a minimal stub is injected into sys.modules so tests can still be
collected and run without the full crewai dependency.
"""
import os
import sys
import types

import pytest
import yaml

# Add core_api to path for imports
_CORE_API = os.path.join(os.path.dirname(__file__), "..", "..", "src", "core_api")
sys.path.insert(0, _CORE_API)

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Crewai stub — injected when crewai is not installed
# ---------------------------------------------------------------------------

def _inject_crewai_stub() -> None:
    """Inject a minimal crewai stub into sys.modules.

    This allows Phase 3 tests to run in environments where crewai is not
    installed (e.g., dev machines running Python 3.14). The stub provides
    just enough surface area for tool registry and executor tests to work:
      - BaseTool base class with name, description, args_schema, and _run
      - Agent, Task, Crew, LLM, Process stubs for executor imports
      - Correct subclassing behaviour so issubclass() checks pass
      - Class-level attribute access for name/description (mirrors real crewai)

    NOTE: The stub uses a plain class (not Pydantic BaseModel) so that
    subclasses can set name/description as class variables and they remain
    accessible at the class level (e.g. ``EchoTool.name == 'echo'``).
    The real crewai BaseTool exposes these as class-level attributes.
    """

    class BaseTool:
        """Minimal BaseTool stub matching CrewAI's interface."""

        name: str = ""
        description: str = ""

        def _run(self, **kwargs) -> str:  # noqa: D401
            raise NotImplementedError

    class Agent:
        """Minimal Agent stub for executor tests."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Task:
        """Minimal Task stub for executor tests."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Process:
        """Minimal Process stub."""

        sequential = "sequential"

    class Crew:
        """Minimal Crew stub for executor tests."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def kickoff(self, inputs=None):
            result = types.SimpleNamespace()
            result.raw = "stub result"
            return result

    class LLM:
        """Minimal LLM stub for executor tests."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # Stub decorators for crewai.project
    def _identity_decorator(fn):
        """Identity decorator stub for @agent, @task, @crew."""
        return fn

    def _crewbase_decorator(cls):
        """Identity decorator stub for @CrewBase."""
        return cls

    # Build the crewai package hierarchy in sys.modules
    crewai_pkg = types.ModuleType("crewai")
    crewai_tools_pkg = types.ModuleType("crewai.tools")
    crewai_project_pkg = types.ModuleType("crewai.project")

    crewai_tools_pkg.BaseTool = BaseTool  # type: ignore[attr-defined]
    crewai_pkg.tools = crewai_tools_pkg  # type: ignore[attr-defined]
    crewai_pkg.Agent = Agent  # type: ignore[attr-defined]
    crewai_pkg.Task = Task  # type: ignore[attr-defined]
    crewai_pkg.Crew = Crew  # type: ignore[attr-defined]
    crewai_pkg.LLM = LLM  # type: ignore[attr-defined]
    crewai_pkg.Process = Process  # type: ignore[attr-defined]

    crewai_project_pkg.CrewBase = _crewbase_decorator  # type: ignore[attr-defined]
    crewai_project_pkg.agent = _identity_decorator  # type: ignore[attr-defined]
    crewai_project_pkg.task = _identity_decorator  # type: ignore[attr-defined]
    crewai_project_pkg.crew = _identity_decorator  # type: ignore[attr-defined]
    crewai_pkg.project = crewai_project_pkg  # type: ignore[attr-defined]

    sys.modules.setdefault("crewai", crewai_pkg)
    sys.modules.setdefault("crewai.tools", crewai_tools_pkg)
    sys.modules.setdefault("crewai.project", crewai_project_pkg)


try:
    import crewai  # noqa: F401 — check if available
except ModuleNotFoundError:
    _inject_crewai_stub()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root() -> str:
    return PROJECT_ROOT


@pytest.fixture
def tools_dir() -> str:
    return os.path.join(PROJECT_ROOT, "src", "core_api", "tools")


@pytest.fixture
def skills_dir() -> str:
    return os.path.join(PROJECT_ROOT, "clients", "default", "skills")


@pytest.fixture
def example_skill_yaml() -> dict:
    path = os.path.join(PROJECT_ROOT, "clients", "default", "skills", "example_skill.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def tools_yaml() -> dict:
    path = os.path.join(PROJECT_ROOT, "clients", "default", "tools.yaml")
    with open(path) as f:
        return yaml.safe_load(f)
