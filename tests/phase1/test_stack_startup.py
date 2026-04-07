"""INFRA-01: Platform deploys via single docker compose up command per client."""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def test_compose_file_exists():
    """docker-compose.yml must exist at project root."""
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), (
        f"docker-compose.yml not found at {compose_path}"
    )


def test_compose_file_has_required_services():
    """docker-compose.yml must define all four service entries."""
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(compose_path) as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    required = ["ollama-gpu", "ollama-cpu", "litellm", "open-webui"]
    for svc in required:
        assert svc in services, f"Service '{svc}' missing from docker-compose.yml"


def test_stack_starts_all_services():
    """All services come up healthy after docker compose up."""
    pytest.skip("Requires running Docker stack")
