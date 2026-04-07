"""INFRA-05: LiteLLM proxy routes requests to different models per task type."""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _load_proxy_config():
    config_path = os.path.join(
        PROJECT_ROOT, "config", "litellm", "proxy_config.yaml"
    )
    with open(config_path) as f:
        return yaml.safe_load(f)


def test_proxy_config_has_model_aliases():
    """proxy_config.yaml must define reasoning-model, classifier-model, embedding-model."""
    data = _load_proxy_config()
    model_names = [
        entry.get("model_name") for entry in data.get("model_list", [])
    ]
    required_aliases = ["reasoning-model", "classifier-model", "embedding-model"]
    for alias in required_aliases:
        assert alias in model_names, (
            f"Required model alias '{alias}' missing from proxy_config.yaml"
        )


def test_proxy_config_uses_ollama_chat_prefix():
    """Chat models must use ollama_chat/ prefix; embedding model must use ollama/ prefix."""
    data = _load_proxy_config()
    for entry in data.get("model_list", []):
        name = entry.get("model_name", "")
        model = entry.get("litellm_params", {}).get("model", "")
        if name == "embedding-model":
            assert model.startswith("ollama/"), (
                f"embedding-model must use 'ollama/' prefix, got: {model}"
            )
        else:
            assert model.startswith("ollama_chat/"), (
                f"Model '{name}' must use 'ollama_chat/' prefix, got: {model}"
            )


def test_litellm_routes_to_correct_model():
    """LiteLLM routes each alias to the correct Ollama model at runtime."""
    pytest.skip("Requires running Docker stack")
