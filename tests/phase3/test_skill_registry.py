"""
Unit tests for the skill registry (AGNT-01).

Tests verify that the skill registry:
- Loads example_skill.yaml into a valid SkillDef
- Applies correct defaults (autonomy=confirm-first)
- Filters tool lists against the allowlist
- Builds an embedding index of the correct shape

All tests mock _embed_texts so no live Ollama is required.
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

from skills.models import SkillDef, SkillIndex
from skills.registry import load_skills


def _make_mock_embed(n_dims: int = 768):
    """Return a mock _embed_texts function that produces normalised unit vectors."""
    rng = np.random.RandomState(42)

    def _mock_embed(texts: list[str]) -> np.ndarray:
        n = len(texts)
        vecs = rng.randn(n, n_dims).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        return vecs / norms

    return _mock_embed


class TestSkillYamlLoading:
    """Tests for loading and validating skill YAML files."""

    def test_skill_yaml_loads(self, example_skill_yaml: dict) -> None:
        """example_skill.yaml parses into a valid SkillDef with expected values."""
        skill = SkillDef(**example_skill_yaml)

        assert skill.name == "example_skill"
        assert skill.autonomy == "confirm-first"
        assert skill.tools == ["echo"]
        assert skill.description != ""
        assert len(skill.triggers) > 0
        assert "role" in skill.agent
        assert "goal" in skill.agent
        assert "backstory" in skill.agent
        assert "description" in skill.task
        assert "expected_output" in skill.task

    def test_autonomy_defaults_confirm_first(self) -> None:
        """SkillDef without autonomy field defaults to 'confirm-first'."""
        data = {
            "name": "minimal_skill",
            "description": "A minimal skill for testing.",
            "agent": {"role": "Agent", "goal": "Do things.", "backstory": "A test."},
            "task": {"description": "Do this.", "expected_output": "Done."},
        }
        skill = SkillDef(**data)
        assert skill.autonomy == "confirm-first"
        assert skill.tools == []
        assert skill.triggers == []


class TestSkillToolFiltering:
    """Tests for tool allowlist filtering during skill loading."""

    def test_skill_tools_filtered_by_allowlist_keeps_matching(
        self, skills_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_skills with allowed_tools={'echo'} keeps 'echo' in skill.tools."""
        monkeypatch.setattr("skills.registry._embed_texts", _make_mock_embed())

        index = load_skills(Path(skills_dir), allowed_tools={"echo"})

        assert len(index.skills) >= 1
        example = next((s for s in index.skills if s.name == "example_skill"), None)
        assert example is not None, "example_skill should be in the index"
        assert "echo" in example.tools

    def test_skill_tools_filtered_by_allowlist_removes_unmatched(
        self, skills_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_skills with allowed_tools={'other'} removes 'echo' from skill.tools."""
        monkeypatch.setattr("skills.registry._embed_texts", _make_mock_embed())

        index = load_skills(Path(skills_dir), allowed_tools={"other"})

        assert len(index.skills) >= 1
        example = next((s for s in index.skills if s.name == "example_skill"), None)
        assert example is not None
        assert "echo" not in example.tools, (
            "'echo' should be filtered out when allowed_tools={'other'}"
        )


class TestEmbeddingIndex:
    """Tests for the embedding index shape produced by load_skills."""

    def test_skill_embedding_index_shape(
        self, skills_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Embedding index shape is (N_skills, 768) for skills found in skills_dir."""
        monkeypatch.setattr("skills.registry._embed_texts", _make_mock_embed(768))

        index = load_skills(Path(skills_dir))

        n_skills = len(index.skills)
        assert n_skills >= 1, "At least one skill must be indexed"
        assert index.embeddings.shape == (n_skills, 768), (
            f"Expected shape ({n_skills}, 768), got {index.embeddings.shape}"
        )
        # Verify vectors are L2-normalised (norms should be ~1.0)
        norms = np.linalg.norm(index.embeddings, axis=1)
        np.testing.assert_allclose(norms, np.ones(n_skills), atol=1e-5)
