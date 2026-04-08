"""Stub tests for DOCP-03 and DOCP-04 — semantic chunking and Qdrant vector storage.

Covers:
  - DOCP-03: Text is chunked semantically before indexing
  - DOCP-04: Chunks are upserted into Qdrant as vectors
  - DOCP-03: Embedding model produces 768-dimensional vectors (nomic-embed-text)

These stubs will be filled in by Plan 02 (LlamaIndex + Qdrant indexer).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 02")
def test_semantic_chunking():
    """Pages are split into semantic chunks using LlamaIndex SentenceSplitter."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 02")
def test_qdrant_vector_upsert():
    """Chunks are embedded and upserted into the Qdrant collection as vectors."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 02")
def test_init_embed_model_768_dims():
    """Embedding model is initialised with 768 dimensions (nomic-embed-text default)."""
    assert False
