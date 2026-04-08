"""Tests for skill executor -- dynamic crew assembly."""
import importlib
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# conftest.py has already added core_api to sys.path and injected the crewai stub
# Import the module under test so it can be patched via skills.executor.*
import skills.executor  # noqa: E402 — must come after conftest path setup
from skills.models import SkillDef


def _make_skill(**overrides) -> SkillDef:
    """Create a test SkillDef with sensible defaults."""
    defaults = {
        "name": "test_skill",
        "description": "A test skill",
        "triggers": ["test"],
        "autonomy": "auto-execute",
        "tools": ["echo"],
        "agent": {"role": "Tester", "goal": "Test things", "backstory": "A tester."},
        "task": {"description": "Do {user_message}", "expected_output": "Done"},
    }
    defaults.update(overrides)
    return SkillDef(**defaults)


def test_run_skill_assembles_crew():
    """Crew is constructed and kickoff() is called, returning the result string."""
    mock_kickoff_result = MagicMock()
    mock_kickoff_result.raw = "mocked result"
    mock_kickoff_result.__str__ = lambda self: "mocked result"
    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = mock_kickoff_result

    mock_tool_cls = MagicMock(return_value=MagicMock())

    with (
        patch("skills.executor.Crew", return_value=mock_crew_instance) as mock_crew_cls,
        patch("skills.executor.get_registry", return_value={"echo": mock_tool_cls}),
        patch("skills.executor.Agent"),
        patch("skills.executor.Task"),
        patch("skills.executor.LLM"),
    ):
        from skills.executor import run_skill

        skill = _make_skill()
        result = run_skill(skill, "hello", [])

    mock_crew_cls.assert_called_once()
    mock_crew_instance.kickoff.assert_called_once()
    assert "mocked result" in result


def test_run_skill_resolves_tools():
    """Agent is created with instantiated tool instances from the registry."""
    mock_tool_instance = MagicMock()
    mock_tool_cls = MagicMock(return_value=mock_tool_instance)

    captured_agent_kwargs = {}

    def capture_agent(**kwargs):
        captured_agent_kwargs.update(kwargs)
        return MagicMock()

    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = MagicMock(raw="done")

    with (
        patch("skills.executor.Crew", return_value=mock_crew_instance),
        patch("skills.executor.get_registry", return_value={"echo": mock_tool_cls}),
        patch("skills.executor.Agent", side_effect=capture_agent),
        patch("skills.executor.Task"),
        patch("skills.executor.LLM"),
    ):
        from skills.executor import run_skill

        skill = _make_skill(tools=["echo"])
        run_skill(skill, "hello", [])

    assert "tools" in captured_agent_kwargs
    assert mock_tool_instance in captured_agent_kwargs["tools"]
    mock_tool_cls.assert_called_once()


def test_run_skill_missing_tool_warning(caplog):
    """Missing tool logs a warning and Crew.kickoff still executes (graceful degradation).

    Because get_logger() sets propagate=False and adds its own StreamHandler,
    caplog cannot capture via root logger propagation. We inject caplog's handler
    directly into the skills.executor logger to capture its records.
    """
    import logging as _logging

    executor_logger = _logging.getLogger("skills.executor")
    executor_logger.addHandler(caplog.handler)
    try:
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = MagicMock(raw="done")

        with (
            patch("skills.executor.Crew", return_value=mock_crew_instance),
            patch("skills.executor.get_registry", return_value={}),  # empty registry
            patch("skills.executor.Agent"),
            patch("skills.executor.Task"),
            patch("skills.executor.LLM"),
        ):
            from skills.executor import run_skill

            skill = _make_skill(tools=["nonexistent"])
            run_skill(skill, "hello", [])
    finally:
        executor_logger.removeHandler(caplog.handler)

    assert "not found in registry" in caplog.text
    mock_crew_instance.kickoff.assert_called_once()


def test_run_skill_formats_user_message():
    """Task description's {user_message} placeholder is replaced with the actual user message."""
    captured_task_kwargs = {}

    def capture_task(**kwargs):
        captured_task_kwargs.update(kwargs)
        return MagicMock()

    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.return_value = MagicMock(raw="done")

    with (
        patch("skills.executor.Crew", return_value=mock_crew_instance),
        patch("skills.executor.get_registry", return_value={}),
        patch("skills.executor.Agent"),
        patch("skills.executor.Task", side_effect=capture_task),
        patch("skills.executor.LLM"),
    ):
        from skills.executor import run_skill

        skill = _make_skill(
            tools=[],
            task={"description": "Process: {user_message}", "expected_output": "Done"},
        )
        run_skill(skill, "my request", [])

    assert captured_task_kwargs.get("description") == "Process: my request"
