"""
Phase 2 Pipelines plugin structural tests.

Validates that src/pipelines/maai_pipe.py implements the required
pipe-type plugin structure from Plan 02-02.
"""
import os
import pytest


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

PIPE_FILE = os.path.join(PROJECT_ROOT, "src", "pipelines", "maai_pipe.py")


def _pipe_content():
    """Read maai_pipe.py content."""
    with open(PIPE_FILE) as f:
        return f.read()


def test_pipeline_file_exists():
    """src/pipelines/maai_pipe.py must exist."""
    assert os.path.exists(PIPE_FILE), f"Missing pipeline file: {PIPE_FILE}"


def test_pipeline_is_pipe_type():
    """
    Plugin must set self.type = 'pipe' (NOT 'filter').

    A pipe-type plugin appears as a selectable model in the Open WebUI
    dropdown. A filter would forward to LiteLLM instead — wrong for this
    use case (per D-01).
    """
    content = _pipe_content()
    assert 'self.type = "pipe"' in content or "self.type = 'pipe'" in content, (
        "maai_pipe.py does not set self.type = 'pipe' — "
        "must be pipe type, not filter, to appear as selectable model"
    )


def test_pipeline_has_event_emitter():
    """
    Plugin must accept and use __event_emitter__ for intermediate status events.
    Required for 'Thinking...', 'Processing...', 'Done' status feedback (D-03).
    """
    content = _pipe_content()
    assert "__event_emitter__" in content, (
        "maai_pipe.py does not use __event_emitter__ for status events"
    )


def test_pipeline_targets_core_api():
    """Plugin Valves default URL must target the core-api container (core-api:8000)."""
    content = _pipe_content()
    assert "core-api:8000" in content, (
        "maai_pipe.py does not reference 'core-api:8000' as the Core API URL"
    )


def test_pipeline_has_upload_handling():
    """Plugin must handle file uploads via the /app/uploads directory (D-14/D-16)."""
    content = _pipe_content()
    assert "/app/uploads" in content, (
        "maai_pipe.py does not reference '/app/uploads' for file upload handling"
    )


def test_pipeline_has_valves():
    """Plugin must define a Valves inner class for admin-configurable settings."""
    content = _pipe_content()
    assert "class Valves" in content, (
        "maai_pipe.py does not define a Valves class for pipeline configuration"
    )
