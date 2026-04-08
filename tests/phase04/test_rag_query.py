"""Stub tests for DOCP-05 — RAG query skill.

Covers:
  - rag_query skill retrieves context from Qdrant and returns a grounded answer
  - Qdrant search tool includes source citations (file name, page number)

These stubs will be filled in by Plan 03 (RAG query skill + Core API integration).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 03")
def test_rag_skill_returns_answer():
    """rag_query skill returns a non-empty answer grounded in retrieved document context."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 03")
def test_qdrant_search_tool_citations():
    """Qdrant search tool result includes source file name and page number citations."""
    assert False
