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


def test_pipeline_is_manifold_type():
    """
    Plugin must set self.type = 'manifold' to appear as a selectable model.

    The Pipelines server only registers manifold-type plugins on the /models
    endpoint. A 'pipe' type is not listed; a 'filter' would intercept other
    models instead of appearing as its own model.
    """
    content = _pipe_content()
    assert 'self.type = "manifold"' in content or "self.type = 'manifold'" in content, (
        "maai_pipe.py does not set self.type = 'manifold' — "
        "must be manifold type to appear as selectable model in Open WebUI"
    )


def test_pipeline_has_pipelines_list():
    """
    Manifold plugins must define self.pipelines list for model registration.
    The Pipelines server reads this list to expose models on /models endpoint.
    """
    content = _pipe_content()
    assert "self.pipelines" in content, (
        "maai_pipe.py does not define self.pipelines list — "
        "manifold type requires this for model registration"
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
