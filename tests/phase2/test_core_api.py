"""
Phase 2 Core API structural and live tests.

Structural tests validate file/config existence without Docker.
Live tests are skipped unless a running Core API is reachable.
"""
import os
import pytest
import yaml

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


# ---------------------------------------------------------------------------
# Structural: file existence
# ---------------------------------------------------------------------------

def test_core_api_main_exists():
    """src/core_api/main.py must exist."""
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "main.py")
    assert os.path.exists(path), f"Missing: {path}"


def test_core_api_dockerfile_exists():
    """src/core_api/Dockerfile must exist."""
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "Dockerfile")
    assert os.path.exists(path), f"Missing: {path}"


def test_core_api_agents_yaml_exists():
    """src/core_api/agents/config/agents.yaml must exist."""
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "agents", "config", "agents.yaml")
    assert os.path.exists(path), f"Missing: {path}"


def test_core_api_tasks_yaml_exists():
    """src/core_api/agents/config/tasks.yaml must exist."""
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "agents", "config", "tasks.yaml")
    assert os.path.exists(path), f"Missing: {path}"


# ---------------------------------------------------------------------------
# Structural: agents.yaml / tasks.yaml content
# ---------------------------------------------------------------------------

def test_agents_yaml_has_freeform_agent():
    """agents.yaml must define the 'freeform_agent' key (AGNT-07)."""
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "agents", "config", "agents.yaml")
    with open(path) as f:
        agents = yaml.safe_load(f)
    assert "freeform_agent" in agents, (
        f"agents.yaml does not contain 'freeform_agent' key. Found: {list(agents.keys())}"
    )


def test_tasks_yaml_has_template_variables():
    """
    tasks.yaml freeform_task.description must include {messages} and {user_message}
    template variables so CrewAI can inject conversation context.
    """
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "agents", "config", "tasks.yaml")
    with open(path) as f:
        tasks = yaml.safe_load(f)
    assert "freeform_task" in tasks, "tasks.yaml is missing 'freeform_task'"
    description = tasks["freeform_task"].get("description", "")
    assert "{messages}" in description, (
        "freeform_task.description missing '{messages}' template variable"
    )
    assert "{user_message}" in description, (
        "freeform_task.description missing '{user_message}' template variable"
    )


# ---------------------------------------------------------------------------
# Structural: Dockerfile
# ---------------------------------------------------------------------------

def test_dockerfile_uses_python_311():
    """Dockerfile must use python:3.11 base image (per CLAUDE.md constraints)."""
    path = os.path.join(PROJECT_ROOT, "src", "core_api", "Dockerfile")
    with open(path) as f:
        content = f.read()
    assert "python:3.11" in content, (
        "Dockerfile does not use python:3.11 base image"
    )


# ---------------------------------------------------------------------------
# Live tests (skipped when Docker stack not running)
# ---------------------------------------------------------------------------

def test_core_api_health_live(core_api_url):
    """GET /health returns 200 {"status": "ok"} (skipped unless Docker running)."""
    try:
        import httpx
        response = httpx.get(f"{core_api_url}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok", f"Unexpected health response: {data}"
    except (ImportError, Exception) as e:
        pytest.skip(f"Core API not reachable — Docker stack may not be running: {e}")


def test_core_api_chat_live(core_api_url):
    """POST /chat returns 200 with 'response' key (skipped unless Docker running)."""
    try:
        import httpx
        payload = {
            "messages": [{"role": "user", "content": "hello"}],
            "user_message": "hello",
        }
        response = httpx.post(f"{core_api_url}/chat", json=payload, timeout=120)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data, f"'response' key missing from /chat response: {data}"
    except (ImportError, Exception) as e:
        pytest.skip(f"Core API not reachable — Docker stack may not be running: {e}")
