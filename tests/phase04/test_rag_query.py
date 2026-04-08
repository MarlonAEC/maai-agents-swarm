"""
Tests for DOCP-05 (RAG query skill) — Plan 03 implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
import yaml


def test_qdrant_search_tool_citations():
    """RAG answer includes file_name and page_label citations from retrieved chunks."""
    from tools.qdrant_search_tool import QdrantSearchTool

    sample_results = [
        {
            "text": "The quarterly revenue grew by 15%.",
            "score": 0.923,
            "file_name": "q3_report.pdf",
            "page_label": "4",
        },
        {
            "text": "Operating expenses decreased by 8% year-over-year.",
            "score": 0.871,
            "file_name": "q3_report.pdf",
            "page_label": "7",
        },
    ]

    with patch("tools.qdrant_search_tool.query_documents", return_value=sample_results):
        tool = QdrantSearchTool()
        output = tool._run(query="revenue growth")

    # Must include citation format per D-06
    assert "Source:" in output
    assert "q3_report.pdf" in output
    assert "page 4" in output
    assert "15%" in output


def test_qdrant_search_tool_empty_results():
    """QdrantSearchTool returns a helpful message when no documents are found."""
    from tools.qdrant_search_tool import QdrantSearchTool

    with patch("tools.qdrant_search_tool.query_documents", return_value=[]):
        tool = QdrantSearchTool()
        output = tool._run(query="something not in knowledge base")

    assert "No relevant documents" in output


def test_qdrant_search_tool_name():
    """QdrantSearchTool has the correct tool name for registry discovery."""
    from tools.qdrant_search_tool import QdrantSearchTool

    tool = QdrantSearchTool()
    assert tool.name == "qdrant_search"


def test_rag_skill_routes_to_qdrant_search():
    """The ask_documents skill lists qdrant_search in its tools configuration."""
    from pathlib import Path

    skill_path = (
        Path(__file__).resolve().parent.parent.parent
        / "clients"
        / "default"
        / "skills"
        / "ask_documents.yaml"
    )
    assert skill_path.exists(), f"ask_documents.yaml not found at {skill_path}"

    skill_def = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
    assert skill_def["name"] == "ask_documents"
    assert "qdrant_search" in skill_def["tools"], (
        f"qdrant_search not in tools: {skill_def['tools']}"
    )
