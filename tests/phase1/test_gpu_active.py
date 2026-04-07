"""INFRA-04: Ollama serves local LLMs with GPU acceleration when available."""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _load_compose():
    compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(compose_path) as f:
        return yaml.safe_load(f)


def test_compose_has_gpu_profile():
    """ollama-gpu service must have gpu profile and NVIDIA deploy reservation."""
    data = _load_compose()
    gpu_svc = data["services"]["ollama-gpu"]

    assert "profiles" in gpu_svc, "ollama-gpu missing profiles key"
    assert "gpu" in gpu_svc["profiles"], "ollama-gpu profiles must contain 'gpu'"

    deploy = gpu_svc.get("deploy", {})
    resources = deploy.get("resources", {})
    reservations = resources.get("reservations", {})
    devices = reservations.get("devices", [])
    assert len(devices) > 0, "ollama-gpu missing deploy.resources.reservations.devices"

    drivers = [d.get("driver", "") for d in devices]
    assert "nvidia" in drivers, (
        "ollama-gpu deploy.resources.reservations.devices must use nvidia driver"
    )


def test_compose_has_cpu_profile():
    """ollama-cpu service must have cpu profile and NO deploy section."""
    data = _load_compose()
    cpu_svc = data["services"]["ollama-cpu"]

    assert "profiles" in cpu_svc, "ollama-cpu missing profiles key"
    assert "cpu" in cpu_svc["profiles"], "ollama-cpu profiles must contain 'cpu'"

    assert "deploy" not in cpu_svc, (
        "ollama-cpu must NOT have a deploy section (no GPU reservation)"
    )


def test_gpu_detected_in_ollama_logs():
    """GPU device line appears in Ollama logs when GPU profile is active."""
    pytest.skip("Requires running Docker stack with GPU")
