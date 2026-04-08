"""Tests for chat router -- skill routing integration."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "core_api"))

import numpy as np

from skills.models import MatchResult, RoutingDecision, SkillDef, SkillIndex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(**overrides) -> SkillDef:
    """Create a test SkillDef with sensible defaults."""
    defaults = {
        "name": "example_skill",
        "description": "An example skill",
        "triggers": ["example"],
        "autonomy": "auto-execute",
        "tools": [],
        "agent": {"role": "Tester", "goal": "Test", "backstory": "A tester."},
        "task": {"description": "Do {user_message}", "expected_output": "Done"},
    }
    defaults.update(overrides)
    return SkillDef(**defaults)


def _make_index(*skills: SkillDef) -> SkillIndex:
    """Build a minimal SkillIndex for the given skills."""
    n = len(skills)
    embeddings = np.zeros((n, 768), dtype=np.float32) if n > 0 else np.zeros((0, 768), dtype=np.float32)
    return SkillIndex(skills=list(skills), embeddings=embeddings)


# ---------------------------------------------------------------------------
# Unit tests for _detect_pending_confirmation (no HTTP, no app needed)
# ---------------------------------------------------------------------------


def test_detect_pending_confirmation_found():
    """Last assistant message with 'confirm' and **skill_name** returns the skill name."""
    from routers.chat import Message, _detect_pending_confirmation

    messages = [
        Message(
            role="assistant",
            content="I think you want to run the **example_skill** skill. Reply yes to confirm or no to cancel.",
        ),
        Message(role="user", content="yes"),
    ]
    result = _detect_pending_confirmation(messages)
    assert result == "example_skill"


def test_detect_pending_confirmation_none():
    """No assistant confirm message returns None."""
    from routers.chat import Message, _detect_pending_confirmation

    messages = [
        Message(role="user", content="hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="yes"),
    ]
    result = _detect_pending_confirmation(messages)
    assert result is None


def test_detect_pending_confirmation_empty():
    """Empty messages list returns None."""
    from routers.chat import _detect_pending_confirmation

    assert _detect_pending_confirmation([]) is None


# ---------------------------------------------------------------------------
# HTTP tests via FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_lifespan_registries(monkeypatch):
    """Prevent lifespan from calling Ollama or filesystem during tests."""
    monkeypatch.setattr("skills.tool_registry.initialize", lambda *a, **kw: None)
    monkeypatch.setattr("skills.registry.initialize", lambda *a, **kw: None)


@pytest.fixture()
def client():
    """FastAPI TestClient with lifespan skipped via mock."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc


def test_chat_list_skills(client):
    """LIST_SKILLS decision returns skill names in the response."""
    skill = _make_skill()
    index = _make_index(skill)

    with (
        patch("routers.chat.match_skill", return_value=MatchResult(RoutingDecision.LIST_SKILLS)),
        patch("routers.chat.get_index", return_value=index),
    ):
        resp = client.post("/chat", json={"messages": [], "user_message": "list skills"})

    assert resp.status_code == 200
    assert "example_skill" in resp.json()["response"]


def test_chat_freeform_fallback(client):
    """FREEFORM decision calls run_freeform_crew and returns its result."""
    with (
        patch("routers.chat.match_skill", return_value=MatchResult(RoutingDecision.FREEFORM, score=0.1)),
        patch("routers.chat.run_freeform_crew", return_value="freeform response"),
    ):
        resp = client.post("/chat", json={"messages": [], "user_message": "tell me a joke"})

    assert resp.status_code == 200
    assert "freeform response" in resp.json()["response"]


def test_chat_auto_run(client):
    """AUTO_RUN decision calls run_skill and returns the skill result."""
    skill = _make_skill()

    with (
        patch(
            "routers.chat.match_skill",
            return_value=MatchResult(RoutingDecision.AUTO_RUN, skill, 0.85),
        ),
        patch("routers.chat.run_skill", return_value="skill result"),
    ):
        resp = client.post("/chat", json={"messages": [], "user_message": "run example skill"})

    assert resp.status_code == 200
    assert "skill result" in resp.json()["response"]


def test_chat_confirm_first_prompt(client):
    """CONFIRM_FIRST decision returns a confirmation prompt containing the skill name."""
    skill = _make_skill()

    with patch(
        "routers.chat.match_skill",
        return_value=MatchResult(RoutingDecision.CONFIRM_FIRST, skill, 0.65),
    ):
        resp = client.post("/chat", json={"messages": [], "user_message": "maybe run example"})

    assert resp.status_code == 200
    body = resp.json()["response"]
    assert "confirm" in body.lower()
    assert "example_skill" in body


def test_chat_confirm_yes(client):
    """User says 'yes' after a confirmation prompt — run_skill is called."""
    skill = _make_skill()
    index = _make_index(skill)

    messages = [
        {
            "role": "assistant",
            "content": "I think you want to run the **example_skill** skill. Reply yes to confirm or no to cancel.",
        },
        {"role": "user", "content": "yes"},
    ]

    with (
        patch("routers.chat.get_index", return_value=index),
        patch("routers.chat.run_skill", return_value="executed"),
    ):
        resp = client.post("/chat", json={"messages": messages, "user_message": "yes"})

    assert resp.status_code == 200
    assert "executed" in resp.json()["response"]


def test_chat_cancel(client):
    """User says 'no' after a confirmation prompt — response contains 'cancelled'."""
    messages = [
        {
            "role": "assistant",
            "content": "I think you want to run the **example_skill** skill. Reply yes to confirm or no to cancel.",
        },
        {"role": "user", "content": "no"},
    ]

    resp = client.post("/chat", json={"messages": messages, "user_message": "no"})

    assert resp.status_code == 200
    assert "cancelled" in resp.json()["response"].lower()
