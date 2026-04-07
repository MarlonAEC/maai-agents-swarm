"""INFRA-03: Each client has isolated config folder with all required variables."""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

REQUIRED_ENV_VARS = [
    "WEBUI_PORT",
    "OLLAMA_GPU_ENABLED",
    "REASONING_MODEL",
    "CLASSIFIER_MODEL",
    "EMBEDDING_MODEL",
    "LITELLM_MASTER_KEY",
    "WEBUI_SECRET_KEY",
]


def test_default_client_folder_exists():
    """clients/default/ directory must exist."""
    client_dir = os.path.join(PROJECT_ROOT, "clients", "default")
    assert os.path.isdir(client_dir), (
        f"clients/default/ directory not found at {client_dir}"
    )


def test_client_env_has_required_vars():
    """client.env.example must define all required Phase 1 variables."""
    env_path = os.path.join(
        PROJECT_ROOT, "clients", "default", "client.env.example"
    )
    with open(env_path) as f:
        content = f.read()
    for var in REQUIRED_ENV_VARS:
        assert var in content, (
            f"Required variable '{var}' missing from client.env.example"
        )


def test_models_yaml_has_required_keys():
    """models.yaml must define reasoning, classifier, and embedding keys."""
    models_path = os.path.join(
        PROJECT_ROOT, "clients", "default", "models.yaml"
    )
    with open(models_path) as f:
        data = yaml.safe_load(f)
    models = data.get("models", {})
    required_keys = ["reasoning", "classifier", "embedding"]
    for key in required_keys:
        assert key in models, (
            f"Required model key '{key}' missing from models.yaml"
        )
