"""
Unit tests for the skill matcher (AGNT-02, AGNT-03).

Tests verify that the matcher routes messages to the correct zones:
  - LIST_SKILLS for "list skills" / "what can you do" keywords
  - AUTO_RUN for high-confidence match on an auto-execute skill
  - CONFIRM_FIRST for high-confidence match on confirm-first skill or medium confidence
  - FREEFORM for low confidence or empty index

All tests mock both _embed_texts and get_index so no live Ollama is required.
When crewai is not installed, conftest.py injects a minimal stub so these
tests can run in any environment.
"""
import sys
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pytest

# Ensure core_api is on the path
_CORE_API = os.path.join(os.path.dirname(__file__), "..", "..", "src", "core_api")
if _CORE_API not in sys.path:
    sys.path.insert(0, _CORE_API)

from skills.models import MatchResult, RoutingDecision, SkillDef, SkillIndex
from skills.matcher import route


def _make_skill(autonomy: str = "confirm-first") -> SkillDef:
    """Create a minimal SkillDef for testing."""
    return SkillDef(
        name="test_skill",
        description="A test skill.",
        triggers=["run test"],
        autonomy=autonomy,
        tools=[],
        agent={"role": "Tester", "goal": "Test things.", "backstory": "Testing agent."},
        task={"description": "Do the test.", "expected_output": "Test result."},
    )


def _make_unit_vector(dim: int = 768, axis: int = 0) -> np.ndarray:
    """Return a unit vector along the given axis."""
    v = np.zeros(dim, dtype=np.float32)
    v[axis] = 1.0
    return v


def _make_index_with_score(target_score: float, autonomy: str = "confirm-first") -> SkillIndex:
    """Create a SkillIndex whose single skill has a known cosine similarity against query.

    The skill embedding is e0 (unit vector along axis 0).
    The query is designed so that dot(skill_vec, query_vec) == target_score.
    """
    skill = _make_skill(autonomy)
    skill_vec = _make_unit_vector(axis=0)
    embeddings = skill_vec.reshape(1, -1)
    return SkillIndex(skills=[skill], embeddings=embeddings)


def _query_vec_for_score(target_score: float, dim: int = 768) -> np.ndarray:
    """Return a normalised query vector whose dot product with e0 == target_score."""
    # skill_vec = e0 = [1, 0, 0, ...]
    # query_vec = [target_score, sqrt(1 - target_score^2), 0, 0, ...]
    # This ensures dot(skill_vec, query_vec) == target_score (both normalised)
    import math
    v = np.zeros(dim, dtype=np.float32)
    v[0] = target_score
    if target_score < 1.0:
        v[1] = math.sqrt(max(0.0, 1.0 - target_score ** 2))
    return v


class TestListSkillsKeyword:
    """Tests for the LIST_SKILLS keyword short-circuit (D-14)."""

    def test_list_skills_keyword(self) -> None:
        """'list skills' triggers LIST_SKILLS decision without consulting the index."""
        result = route("list skills")
        assert result.decision == RoutingDecision.LIST_SKILLS

    def test_what_can_you_do_keyword(self) -> None:
        """'what can you do' triggers LIST_SKILLS decision."""
        result = route("what can you do")
        assert result.decision == RoutingDecision.LIST_SKILLS

    def test_list_skills_case_insensitive(self) -> None:
        """Keyword detection is case-insensitive."""
        result = route("List Skills")
        assert result.decision == RoutingDecision.LIST_SKILLS


class TestHighScoreRouting:
    """Tests for routing decisions when similarity >= HIGH_THRESHOLD (0.7)."""

    def test_high_score_auto_execute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """High score (>=0.7) + auto-execute autonomy -> AUTO_RUN."""
        score = 0.85
        index = _make_index_with_score(score, autonomy="auto-execute")
        query_vec = _query_vec_for_score(score)

        monkeypatch.setattr("skills.matcher.get_index", lambda: index)
        monkeypatch.setattr(
            "skills.matcher._embed_texts", lambda texts: query_vec.reshape(1, -1)
        )

        result = route("trigger test skill")
        assert result.decision == RoutingDecision.AUTO_RUN, (
            f"Expected AUTO_RUN with score {score} and auto-execute, got {result.decision}"
        )
        assert result.skill is not None
        assert result.score >= 0.7

    def test_high_score_confirm_first(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """High score (>=0.7) + confirm-first autonomy -> CONFIRM_FIRST."""
        score = 0.85
        index = _make_index_with_score(score, autonomy="confirm-first")
        query_vec = _query_vec_for_score(score)

        monkeypatch.setattr("skills.matcher.get_index", lambda: index)
        monkeypatch.setattr(
            "skills.matcher._embed_texts", lambda texts: query_vec.reshape(1, -1)
        )

        result = route("trigger test skill")
        assert result.decision == RoutingDecision.CONFIRM_FIRST, (
            f"Expected CONFIRM_FIRST with score {score} and confirm-first, got {result.decision}"
        )
        assert result.skill is not None


class TestMediumScoreRouting:
    """Tests for medium confidence zone (0.5 <= score < 0.7)."""

    def test_medium_score_confirm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Medium score (0.5 <= score < 0.7) always routes to CONFIRM_FIRST."""
        score = 0.6
        index = _make_index_with_score(score, autonomy="auto-execute")
        query_vec = _query_vec_for_score(score)

        monkeypatch.setattr("skills.matcher.get_index", lambda: index)
        monkeypatch.setattr(
            "skills.matcher._embed_texts", lambda texts: query_vec.reshape(1, -1)
        )

        result = route("vaguely related request")
        assert result.decision == RoutingDecision.CONFIRM_FIRST, (
            f"Expected CONFIRM_FIRST with score {score}, got {result.decision}"
        )
        # Even auto-execute skills get CONFIRM_FIRST at medium confidence
        assert result.skill is not None


class TestLowScoreRouting:
    """Tests for low confidence zone (score < 0.5)."""

    def test_low_score_freeform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Low score (< 0.5) routes to FREEFORM with no skill attached."""
        score = 0.3
        index = _make_index_with_score(score)
        query_vec = _query_vec_for_score(score)

        monkeypatch.setattr("skills.matcher.get_index", lambda: index)
        monkeypatch.setattr(
            "skills.matcher._embed_texts", lambda texts: query_vec.reshape(1, -1)
        )

        result = route("completely unrelated topic")
        assert result.decision == RoutingDecision.FREEFORM, (
            f"Expected FREEFORM with score {score}, got {result.decision}"
        )
        assert result.skill is None, "FREEFORM result should have no skill"

    def test_no_skills_freeform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty skill index routes to FREEFORM regardless of the message."""
        empty_index = SkillIndex(
            skills=[], embeddings=np.empty((0, 768), dtype=np.float32)
        )

        monkeypatch.setattr("skills.matcher.get_index", lambda: empty_index)

        result = route("any message at all")
        assert result.decision == RoutingDecision.FREEFORM, (
            f"Expected FREEFORM with empty index, got {result.decision}"
        )

    def test_none_index_freeform(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """None index (not yet initialized) routes to FREEFORM."""
        monkeypatch.setattr("skills.matcher.get_index", lambda: None)

        result = route("any message at all")
        assert result.decision == RoutingDecision.FREEFORM
