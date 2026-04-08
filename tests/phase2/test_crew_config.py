"""
Phase 2 CrewAI configuration tests.

Validates that freeform_crew.py implements the architectural decisions
recorded in the Phase 2 SUMMARY:

- AGNT-07: Embedder uses direct Ollama (not LiteLLM proxy)
- AGNT-08: stream=False to avoid unsupported streaming
- AGNT-09: max_iter=5 and max_execution_time=60 guardrails
"""
import os
import pytest


PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

CREW_FILE = os.path.join(PROJECT_ROOT, "src", "core_api", "agents", "freeform_crew.py")


def _crew_content():
    """Read freeform_crew.py content (cached per test run)."""
    with open(CREW_FILE) as f:
        return f.read()


def test_crew_file_exists():
    """src/core_api/agents/freeform_crew.py must exist."""
    assert os.path.exists(CREW_FILE), f"Missing: {CREW_FILE}"


def test_embedder_is_ollama():
    """
    Embedder must use the Ollama provider pointing directly at ollama:11434,
    NOT routing through LiteLLM. CrewAI's ollama provider cannot use the
    LiteLLM proxy endpoint (AGNT-07).
    """
    content = _crew_content()
    assert '"provider": "ollama"' in content or "'provider': 'ollama'" in content, (
        "freeform_crew.py does not configure embedder with provider='ollama'"
    )
    assert "ollama:11434" in content, (
        "freeform_crew.py embedder does not reference 'ollama:11434' — "
        "must use direct Ollama URL, not LiteLLM proxy"
    )


def test_stream_false():
    """
    LLM must be configured with stream=False (AGNT-08).
    CrewAI sequential crews do not support streaming — enabling it causes errors.
    """
    content = _crew_content()
    assert "stream=False" in content, (
        "freeform_crew.py does not set stream=False on LLM — "
        "CrewAI does not support streaming agent responses (AGNT-08)"
    )


def test_agent_guardrails():
    """
    Agent must have max_iter=5 and max_execution_time=60 guardrails (AGNT-09).
    These prevent runaway inference on consumer hardware.
    """
    content = _crew_content()
    assert "max_iter=5" in content, (
        "freeform_crew.py is missing max_iter=5 guardrail (AGNT-09)"
    )
    assert "max_execution_time=60" in content, (
        "freeform_crew.py is missing max_execution_time=60 guardrail (AGNT-09)"
    )
