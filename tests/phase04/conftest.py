"""Phase 4 test fixtures — document ingestion and RAG."""

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src/core_api and src/docproc to sys.path for imports
CORE_API_DIR = str(Path(__file__).resolve().parent.parent.parent / "src" / "core_api")
DOCPROC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src" / "docproc")
if CORE_API_DIR not in sys.path:
    sys.path.insert(0, CORE_API_DIR)
if DOCPROC_DIR not in sys.path:
    sys.path.insert(0, DOCPROC_DIR)

# ---------------------------------------------------------------------------
# CrewAI stub — same pattern as tests/phase3/conftest.py
# Injected when crewai is not installed in the test environment.
# ---------------------------------------------------------------------------


def _inject_crewai_stub() -> None:
    """Inject a minimal crewai stub into sys.modules.

    Provides just enough surface area for tool tests to work:
      - BaseTool with name, description, args_schema, _run
      - Agent, Task, Crew, LLM, Process stubs
    """

    class BaseTool:
        """Minimal BaseTool stub matching CrewAI's interface."""

        name: str = ""
        description: str = ""

        def _run(self, **kwargs) -> str:  # noqa: D401
            raise NotImplementedError

    class Agent:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Task:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Process:
        sequential = "sequential"

    class Crew:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def kickoff(self, inputs=None):
            result = types.SimpleNamespace()
            result.raw = "stub result"
            return result

    class LLM:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _identity_decorator(fn):
        return fn

    def _crewbase_decorator(cls):
        return cls

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
    import crewai  # noqa: F401
except ModuleNotFoundError:
    _inject_crewai_stub()

# Stub heavy dependencies that may not be installed in test env
# (same pattern as tests/conftest.py from Phase 3)
for mod_name in [
    "docling",
    "docling.document_converter",
    "docling.datamodel.pipeline_options",
    "docling.datamodel.base_models",
    "easyocr",
    "llama_index",
    "llama_index.core",
    "llama_index.core.node_parser",
    "llama_index.embeddings.ollama",
    "llama_index.vector_stores.qdrant",
    "qdrant_client",
    "arq",
    "arq.connections",
    "arq.jobs",
    "redis",
    "redis.asyncio",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()


@pytest.fixture
def sample_pages():
    """Sample docproc response pages for testing."""
    return [
        {"page_no": 1, "text": "This is page one content.", "has_ocr": False},
        {"page_no": 2, "text": "This is page two with OCR text.", "has_ocr": True},
    ]


@pytest.fixture
def test_client_id():
    """Test client ID for per-client isolation tests."""
    return "test_client_01"


@pytest.fixture
def sample_file_name():
    """Sample file name for ingestion tests."""
    return "test_document.pdf"
