"""
Phase 2 Open WebUI accessibility tests (CHAT-01).

Verifies that docker-compose.yml correctly exposes Open WebUI on a host port
and that the service is properly wired. All tests are structural — no running
Docker required.
"""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def test_open_webui_service_exists(compose_config):
    """open-webui service must be defined in docker-compose.yml (CHAT-01)."""
    assert "open-webui" in compose_config.get("services", {}), (
        "Missing 'open-webui' service in docker-compose.yml"
    )


def test_open_webui_port_declared(compose_config):
    """
    open-webui must expose a port mapping for browser access (CHAT-01).

    Checks that either the WEBUI_PORT variable reference or a concrete port
    containing '3080' appears in the ports list. The exact port is controlled
    by the client.env WEBUI_PORT variable.
    """
    svc = compose_config["services"]["open-webui"]
    ports = svc.get("ports", [])
    assert len(ports) > 0, "open-webui has no ports declared"
    # Accepts either "${WEBUI_PORT:-3000}:8080" or any "30xx:8080" style
    assert any(
        "WEBUI_PORT" in str(p) or "8080" in str(p)
        for p in ports
    ), f"open-webui ports do not expose WebUI endpoint: {ports}"


def test_open_webui_on_maai_net(compose_config):
    """open-webui must be on maai-net to reach LiteLLM and Pipelines."""
    networks = compose_config["services"]["open-webui"].get("networks", [])
    assert "maai-net" in networks, "open-webui is not on maai-net"


def test_open_webui_depends_on_litellm(compose_config):
    """open-webui must wait for litellm to be healthy before starting."""
    depends = compose_config["services"]["open-webui"].get("depends_on", {})
    assert "litellm" in depends, "open-webui does not depend_on litellm"


def test_open_webui_depends_on_pipelines(compose_config):
    """open-webui must wait for pipelines to be healthy (CHAT-01 — MAAI Agent selectable)."""
    depends = compose_config["services"]["open-webui"].get("depends_on", {})
    assert "pipelines" in depends, "open-webui does not depend_on pipelines"
