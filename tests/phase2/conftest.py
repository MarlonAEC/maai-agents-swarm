"""Phase 2 test fixtures."""
import pytest
import yaml
import os


@pytest.fixture
def compose_config():
    """Load docker-compose.yml as parsed YAML."""
    project_root = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    with open(os.path.join(project_root, "docker-compose.yml")) as f:
        return yaml.safe_load(f)


@pytest.fixture
def client_env():
    """Load client.env as a dict."""
    project_root = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    env = {}
    env_path = os.path.join(project_root, "clients", "default", "client.env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


@pytest.fixture
def core_api_url():
    """Core API base URL for live tests."""
    return os.getenv("CORE_API_URL", "http://localhost:8000")


@pytest.fixture
def pipelines_url():
    """Pipelines server base URL for live tests."""
    return os.getenv("PIPELINES_URL", "http://localhost:9099")
