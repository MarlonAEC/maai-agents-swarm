"""INFRA-02: All processing runs locally — no data leaves the client's machine."""
import os
import pytest
import yaml


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

CLOUD_KEY_PATTERNS = [
    "OPENAI_API_KEY=sk-",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "AZURE_API_KEY",
    "GOOGLE_API_KEY",
    "HUGGINGFACE_API_KEY",
]

CLOUD_URL_PATTERNS = [
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "api.cohere.ai",
    "huggingface.co",
    "azure.com",
]


def test_no_cloud_api_keys_in_env():
    """client.env.example must not contain any cloud provider API keys."""
    env_path = os.path.join(
        PROJECT_ROOT, "clients", "default", "client.env.example"
    )
    with open(env_path) as f:
        content = f.read()
    for pattern in CLOUD_KEY_PATTERNS:
        assert pattern not in content, (
            f"Cloud API key pattern '{pattern}' found in client.env.example"
        )


def test_litellm_config_points_to_ollama():
    """LiteLLM proxy_config.yaml must route to Ollama, not cloud endpoints."""
    config_path = os.path.join(
        PROJECT_ROOT, "config", "litellm", "proxy_config.yaml"
    )
    with open(config_path) as f:
        data = yaml.safe_load(f)
    model_list = data.get("model_list", [])
    for entry in model_list:
        params = entry.get("litellm_params", {})
        api_base = params.get("api_base", "")
        assert "ollama:11434" in api_base, (
            f"Model '{entry.get('model_name')}' api_base does not point to "
            f"ollama:11434: {api_base}"
        )
        for cloud_url in CLOUD_URL_PATTERNS:
            assert cloud_url not in api_base, (
                f"Cloud URL '{cloud_url}' found in api_base for "
                f"model '{entry.get('model_name')}'"
            )


def test_no_external_endpoints():
    """No network calls leave the Docker network during operation."""
    pytest.skip("Requires running Docker stack")
