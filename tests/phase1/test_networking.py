"""INFRA-06: Docker Compose networking resolves service names correctly."""
import os
import re
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _load_compose():
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(compose_path) as f:
        return yaml.safe_load(f)


def test_compose_uses_named_network():
    """docker-compose.yml top-level networks must contain 'maai-net'."""
    data = _load_compose()
    networks = data.get("networks", {})
    assert "maai-net" in networks, (
        "Top-level networks section must define 'maai-net'"
    )


def test_all_services_on_named_network():
    """Every service must include 'maai-net' in its networks list."""
    data = _load_compose()
    services = data.get("services", {})
    for svc_name, svc_config in services.items():
        svc_networks = svc_config.get("networks", [])
        # networks can be a list or a dict
        if isinstance(svc_networks, dict):
            net_names = list(svc_networks.keys())
        else:
            net_names = svc_networks
        assert "maai-net" in net_names, (
            f"Service '{svc_name}' is not connected to 'maai-net'"
        )


def test_no_localhost_in_service_config():
    """Service environment sections must not use localhost to reference other services."""
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(compose_path) as f:
        data = yaml.safe_load(f)

    services = data.get("services", {})
    for svc_name, svc_config in services.items():
        env = svc_config.get("environment", {})
        if isinstance(env, dict):
            env_items = env.items()
        elif isinstance(env, list):
            # list of "KEY=VALUE" strings
            env_items = []
            for item in env:
                if "=" in item:
                    k, v = item.split("=", 1)
                    env_items.append((k, v))
        else:
            env_items = []

        for key, value in env_items:
            # localhost in OPENAI_API_BASE_URL or similar inter-service references
            # is a sign of broken networking — only healthchecks (wget localhost) are correct
            if "localhost" in str(value):
                # Check it's not a URL that should be referencing another service by name
                if any(
                    other in str(value)
                    for other in ["11434", "4000", "8080"]
                ):
                    pytest.fail(
                        f"Service '{svc_name}' env var '{key}' uses 'localhost' "
                        f"to reference another service — use container name instead: {value}"
                    )


def test_services_resolve_each_other():
    """Services can reach each other by container name within maai-net."""
    pytest.skip("Requires running Docker stack")
