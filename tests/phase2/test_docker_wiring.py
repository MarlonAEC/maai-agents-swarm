"""
Phase 2 Docker Compose structural tests.

Validates that docker-compose.yml contains the correct service definitions,
volume mounts, network assignments, and environment configuration added in
Phase 2 (Plan 02-03). All tests are structural — no running Docker required.
"""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _compose():
    """Load docker-compose.yml as parsed YAML (module-level helper)."""
    with open(os.path.join(PROJECT_ROOT, "docker-compose.yml")) as f:
        return yaml.safe_load(f)


def _client_env():
    """Load clients/default/client.env as a dict (module-level helper)."""
    env = {}
    env_path = os.path.join(PROJECT_ROOT, "clients", "default", "client.env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


# ---------------------------------------------------------------------------
# Service existence
# ---------------------------------------------------------------------------

def test_core_api_service_exists(compose_config):
    """core-api service must be defined in docker-compose.yml."""
    assert "core-api" in compose_config.get("services", {}), (
        "Missing 'core-api' service in docker-compose.yml"
    )


def test_pipelines_service_exists(compose_config):
    """pipelines service must be defined in docker-compose.yml."""
    assert "pipelines" in compose_config.get("services", {}), (
        "Missing 'pipelines' service in docker-compose.yml"
    )


# ---------------------------------------------------------------------------
# Shared volume
# ---------------------------------------------------------------------------

def test_maai_uploads_volume_exists(compose_config):
    """maai-uploads volume must be declared at the top-level volumes section."""
    assert "maai-uploads" in compose_config.get("volumes", {}), (
        "Missing 'maai-uploads' volume in docker-compose.yml volumes section"
    )


# ---------------------------------------------------------------------------
# Network membership
# ---------------------------------------------------------------------------

def test_core_api_on_maai_net(compose_config):
    """core-api must be attached to maai-net network."""
    networks = compose_config["services"]["core-api"].get("networks", [])
    assert "maai-net" in networks, "core-api is not on maai-net"


def test_pipelines_on_maai_net(compose_config):
    """pipelines must be attached to maai-net network."""
    networks = compose_config["services"]["pipelines"].get("networks", [])
    assert "maai-net" in networks, "pipelines is not on maai-net"


# ---------------------------------------------------------------------------
# Service dependencies
# ---------------------------------------------------------------------------

def test_core_api_depends_on_litellm(compose_config):
    """core-api must declare a depends_on relationship with litellm."""
    depends = compose_config["services"]["core-api"].get("depends_on", {})
    assert "litellm" in depends, "core-api does not depend_on litellm"


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def test_core_api_healthcheck_defined(compose_config):
    """core-api must have a healthcheck defined."""
    hc = compose_config["services"]["core-api"].get("healthcheck")
    assert hc is not None, "core-api is missing a healthcheck"


def test_pipelines_healthcheck_defined(compose_config):
    """pipelines must have a healthcheck defined."""
    hc = compose_config["services"]["pipelines"].get("healthcheck")
    assert hc is not None, "pipelines is missing a healthcheck"


# ---------------------------------------------------------------------------
# Volume mounts
# ---------------------------------------------------------------------------

def test_core_api_uploads_volume_mount(compose_config):
    """core-api must mount maai-uploads at /app/uploads."""
    vols = compose_config["services"]["core-api"].get("volumes", [])
    assert any("maai-uploads:/app/uploads" in str(v) for v in vols), (
        "core-api is missing 'maai-uploads:/app/uploads' volume mount"
    )


def test_pipelines_uploads_volume_mount(compose_config):
    """pipelines must mount maai-uploads at /app/uploads."""
    vols = compose_config["services"]["pipelines"].get("volumes", [])
    assert any("maai-uploads:/app/uploads" in str(v) for v in vols), (
        "pipelines is missing 'maai-uploads:/app/uploads' volume mount"
    )


def test_pipelines_source_mount(compose_config):
    """pipelines must bind-mount ./src/pipelines into /app/pipelines."""
    vols = compose_config["services"]["pipelines"].get("volumes", [])
    assert any("src/pipelines" in str(v) and "/app/pipelines" in str(v) for v in vols), (
        "pipelines is missing './src/pipelines:/app/pipelines' bind mount"
    )


# ---------------------------------------------------------------------------
# Open WebUI environment wiring
# ---------------------------------------------------------------------------

def test_open_webui_base_urls_has_pipelines(compose_config):
    """open-webui OPENAI_API_BASE_URLS must include the pipelines endpoint."""
    env_list = compose_config["services"]["open-webui"].get("environment", [])
    base_urls_entries = [e for e in env_list if "OPENAI_API_BASE_URLS" in str(e)]
    assert len(base_urls_entries) > 0, "open-webui is missing OPENAI_API_BASE_URLS"
    assert any("pipelines:9099" in str(e) for e in base_urls_entries), (
        "open-webui OPENAI_API_BASE_URLS does not include 'http://pipelines:9099'"
    )


def test_open_webui_api_keys_count_matches_urls(compose_config):
    """
    OPENAI_API_BASE_URLS and OPENAI_API_KEYS must have the same number of
    semicolon-separated entries. A mismatch causes silent routing failures.
    (Pitfall 2 from Phase 2 research.)
    """
    env_list = compose_config["services"]["open-webui"].get("environment", [])
    base_urls_str = ""
    api_keys_str = ""
    for e in env_list:
        if isinstance(e, str):
            if e.startswith("OPENAI_API_BASE_URLS="):
                base_urls_str = e.split("=", 1)[1]
            elif e.startswith("OPENAI_API_KEYS="):
                api_keys_str = e.split("=", 1)[1]
        elif isinstance(e, dict):
            if "OPENAI_API_BASE_URLS" in e:
                base_urls_str = e["OPENAI_API_BASE_URLS"]
            if "OPENAI_API_KEYS" in e:
                api_keys_str = e["OPENAI_API_KEYS"]

    assert base_urls_str, "OPENAI_API_BASE_URLS not found in open-webui environment"
    assert api_keys_str, "OPENAI_API_KEYS not found in open-webui environment"

    url_count = len(base_urls_str.split(";"))
    key_count = len(api_keys_str.split(";"))
    assert url_count == key_count, (
        f"OPENAI_API_BASE_URLS has {url_count} entries but OPENAI_API_KEYS has {key_count} — "
        "counts MUST match to avoid silent routing failures"
    )


# ---------------------------------------------------------------------------
# open-webui depends_on pipelines
# ---------------------------------------------------------------------------

def test_open_webui_depends_on_pipelines(compose_config):
    """open-webui must declare depends_on pipelines so it waits for the plugin server."""
    depends = compose_config["services"]["open-webui"].get("depends_on", {})
    assert "pipelines" in depends, "open-webui does not depend_on pipelines"


# ---------------------------------------------------------------------------
# client.env variables
# ---------------------------------------------------------------------------

def test_client_env_has_pipelines_key(client_env):
    """clients/default/client.env must define PIPELINES_API_KEY."""
    assert "PIPELINES_API_KEY" in client_env, (
        "Missing PIPELINES_API_KEY in clients/default/client.env"
    )


def test_client_env_has_core_api_port(client_env):
    """clients/default/client.env must define CORE_API_PORT."""
    assert "CORE_API_PORT" in client_env, (
        "Missing CORE_API_PORT in clients/default/client.env"
    )
