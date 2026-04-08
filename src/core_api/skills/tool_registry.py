"""
Tool plugin registry for the MAAI skill system.

Discovers BaseTool subclasses from Python files in the configured tools
directory using importlib. Supports optional allowlist filtering so
per-client config can restrict which tools are available to skills.
"""

import importlib.util
import inspect
from pathlib import Path
from typing import Optional

from crewai.tools import BaseTool

from logging_config import get_logger

logger = get_logger(__name__)

# Module-level tool registry: maps tool name to its class
_REGISTRY: dict[str, type[BaseTool]] = {}


def load_tools(tools_dir: Path) -> dict[str, type[BaseTool]]:
    """Scan ``tools_dir`` for ``.py`` files and import all BaseTool subclasses.

    Files whose names start with ``_`` are skipped (private/helper modules).
    Each non-abstract BaseTool subclass is registered under its ``.name``
    attribute as the key.

    Args:
        tools_dir: Directory to scan for tool plugin files.

    Returns:
        Dictionary mapping tool name strings to their BaseTool subclasses.
    """
    registry: dict[str, type[BaseTool]] = {}

    if not tools_dir.exists():
        logger.info("Tools directory does not exist, skipping: %s", tools_dir)
        return registry

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            # Skip private/helper modules
            continue

        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            logger.warning("Could not create module spec for: %s", py_file)
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception:
            logger.exception("Failed to import tool module: %s", py_file)
            continue

        for _member_name, member_cls in inspect.getmembers(module, inspect.isclass):
            # Must be a BaseTool subclass (not BaseTool itself), defined in
            # this module, and not abstract (must have _run implemented).
            if (
                issubclass(member_cls, BaseTool)
                and member_cls is not BaseTool
                and member_cls.__module__ == module.__name__
                and not inspect.isabstract(member_cls)
            ):
                tool_name: str = member_cls.name  # type: ignore[assignment]
                registry[tool_name] = member_cls
                logger.info("Registered tool: %s from %s", tool_name, py_file)

    logger.info("Tool registry initialized: %d tools", len(registry))
    return registry


def get_registry() -> dict[str, type[BaseTool]]:
    """Return the current module-level tool registry.

    Returns:
        Dictionary mapping tool name strings to BaseTool subclasses.
    """
    return _REGISTRY


def initialize(tools_dir: Path) -> None:
    """Populate the module-level registry by scanning ``tools_dir``.

    This should be called once at application startup before any skill
    matching occurs.

    Args:
        tools_dir: Directory containing tool plugin ``.py`` files.
    """
    global _REGISTRY
    _REGISTRY = load_tools(tools_dir)


def filter_by_allowlist(
    allowed: Optional[set[str]] = None,
) -> dict[str, type[BaseTool]]:
    """Return tools from the registry filtered by an optional allowlist.

    Args:
        allowed: Set of tool name strings to allow. If ``None``, the full
                 registry is returned without filtering.

    Returns:
        Filtered dictionary of tool name -> BaseTool class mappings.
    """
    if allowed is None:
        return _REGISTRY
    return {name: cls for name, cls in _REGISTRY.items() if name in allowed}
