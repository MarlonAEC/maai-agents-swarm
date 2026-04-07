"""Shared fixtures for Phase 1 tests."""
import os
import pytest
import httpx


@pytest.fixture
def stack_base_url():
    """Base URL for tests that run against the live stack."""
    return "http://localhost"


@pytest.fixture
def ollama_url():
    """Ollama API base URL."""
    return "http://localhost:11434"


@pytest.fixture
def litellm_url():
    """LiteLLM proxy base URL."""
    return "http://localhost:4000"


@pytest.fixture
def webui_port():
    """Read WEBUI_PORT from clients/default/client.env, defaulting to 3000."""
    env_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "clients", "default", "client.env"
    )
    env_path = os.path.normpath(env_path)
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("WEBUI_PORT="):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return int(value)
    return 3000


@pytest.fixture
async def async_client():
    """Async HTTP client with 30-second timeout."""
    async with httpx.AsyncClient(timeout=30) as client:
        yield client
