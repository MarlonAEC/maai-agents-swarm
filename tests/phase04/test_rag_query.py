"""
Stub tests for DOCP-05 (RAG query skill).

These stubs will be filled in by Plan 03 (RAG skill and query endpoint).
"""

import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 03 (RAG skill)")
def test_rag_skill_returns_answer():
    """RAG skill returns a synthesized answer using retrieved document chunks."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 03 (RAG skill)")
def test_qdrant_search_tool_citations():
    """RAG answer includes file_name and page_label citations from retrieved chunks."""
    assert False
