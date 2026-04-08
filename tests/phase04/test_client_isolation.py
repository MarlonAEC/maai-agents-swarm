"""Stub tests for DOCP-04 — per-client Qdrant collection isolation.

Covers:
  - Each client gets a dedicated Qdrant collection named after their client_id
  - Queries against one client's collection do not return documents from another client

These stubs will be filled in by Plan 02 (LlamaIndex + Qdrant indexer).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 02")
def test_collection_naming_per_client():
    """Qdrant collection name is derived from client_id (e.g., 'docs_test_client_01')."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 02")
def test_query_returns_only_own_docs():
    """A RAG query for client A does not return documents indexed for client B."""
    assert False
