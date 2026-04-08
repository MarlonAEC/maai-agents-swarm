"""
Unit tests for the tool registry (AGNT-04, AGNT-05).

Tests verify that the tool registry:
- Discovers BaseTool subclasses from Python files in the tools directory
- Skips dunder files (__init__.py, etc.)
- Applies allowlist filtering correctly

When crewai is not installed, conftest.py injects a minimal stub so these
tests can run in any environment (including Python 3.14 dev machines).
"""
import sys
import os

import pytest
from pathlib import Path

from crewai.tools import BaseTool

# Ensure core_api is on the path (conftest sets this, but be explicit)
_CORE_API = os.path.join(os.path.dirname(__file__), "..", "..", "src", "core_api")
if _CORE_API not in sys.path:
    sys.path.insert(0, _CORE_API)

from skills.tool_registry import filter_by_allowlist, initialize, load_tools


class TestToolDiscovery:
    """Tests for load_tools() discovering BaseTool plugins."""

    def test_tool_discovered(self, tools_dir: str) -> None:
        """load_tools finds EchoTool and registers it under key 'echo'."""
        registry = load_tools(Path(tools_dir))
        assert "echo" in registry, (
            f"Expected 'echo' in registry keys, got: {list(registry.keys())}"
        )

    def test_tool_is_basetool_subclass(self, tools_dir: str) -> None:
        """Discovered echo tool class is a subclass of BaseTool."""
        registry = load_tools(Path(tools_dir))
        assert "echo" in registry
        assert issubclass(registry["echo"], BaseTool), (
            f"registry['echo'] must be a BaseTool subclass, got: {registry['echo']}"
        )

    def test_skip_dunder_files(self, tools_dir: str) -> None:
        """__init__.py is not treated as a tool module (dunder files are skipped)."""
        registry = load_tools(Path(tools_dir))
        assert "__init__" not in registry, (
            "'__init__' should not appear as a tool name — dunder files must be skipped"
        )

    def test_missing_tools_dir_returns_empty(self, tmp_path: Path) -> None:
        """load_tools on a non-existent directory returns an empty dict."""
        result = load_tools(tmp_path / "nonexistent")
        assert result == {}


class TestAllowlistFiltering:
    """Tests for filter_by_allowlist() allowlist enforcement."""

    def setup_method(self) -> None:
        """Reset the module-level registry before each test."""
        # We call initialize() in each test to set state deterministically
        pass

    def test_allowlist_filtering(self, tools_dir: str) -> None:
        """filter_by_allowlist with matching name returns that tool; nonexistent returns empty."""
        initialize(Path(tools_dir))

        matched = filter_by_allowlist({"echo"})
        assert "echo" in matched, f"Expected 'echo' in matched, got: {list(matched.keys())}"
        assert len(matched) == 1

        empty = filter_by_allowlist({"nonexistent"})
        assert empty == {}, f"Expected empty dict, got: {empty}"

    def test_missing_allowlist_enables_all(self, tools_dir: str) -> None:
        """filter_by_allowlist(None) returns the full registry including 'echo'."""
        initialize(Path(tools_dir))

        all_tools = filter_by_allowlist(None)
        assert "echo" in all_tools, (
            f"Expected 'echo' in all_tools when allowlist is None, got: {list(all_tools.keys())}"
        )
