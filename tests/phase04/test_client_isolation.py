"""
Tests for DOCP-04 (per-client Qdrant collection isolation).

Covers:
- Collection naming follows maai_{client_id}_documents pattern
- Querying one client's collection cannot see another client's documents
"""

from unittest.mock import MagicMock, patch


def test_collection_naming_per_client():
    """_collection_name returns the correct maai_{client_id}_documents format."""
    from rag.pipeline import _collection_name

    assert _collection_name("client_a") == "maai_client_a_documents"
    assert _collection_name("client_b") == "maai_client_b_documents"
    assert _collection_name("acme_corp") == "maai_acme_corp_documents"
    assert _collection_name("default") == "maai_default_documents"


def test_query_returns_only_own_docs():
    """query_documents passes the correct client-scoped collection name to Qdrant.

    Verifies that a query for client_a uses 'maai_client_a_documents' and
    does not touch 'maai_client_b_documents', providing per-client isolation.
    """
    mock_node = MagicMock()
    mock_node.text = "client_a document content"
    mock_node.score = 0.95
    mock_node.metadata = {"file_name": "a.pdf", "page_label": "1"}

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [mock_node]

    mock_index = MagicMock()
    mock_index.as_retriever.return_value = mock_retriever

    mock_vector_store = MagicMock()

    with (
        patch("rag.pipeline.QdrantVectorStore", return_value=mock_vector_store) as mock_qs,
        patch("rag.pipeline.VectorStoreIndex") as mock_index_cls,
        patch("rag.pipeline._get_qdrant_client"),
        patch("rag.pipeline.Settings"),
    ):
        mock_index_cls.from_vector_store.return_value = mock_index

        from rag.pipeline import query_documents

        results = query_documents("client_a", "what is this about?", top_k=3)

        # Must use the client_a collection, not any other client's collection
        mock_qs.assert_called_once()
        call_kwargs = mock_qs.call_args.kwargs
        assert call_kwargs.get("collection_name") == "maai_client_a_documents", (
            "query_documents must scope retrieval to the requesting client's collection"
        )

        # Retriever must be called with similarity_top_k
        mock_index.as_retriever.assert_called_once_with(similarity_top_k=3)
        mock_retriever.retrieve.assert_called_once_with("what is this about?")

        # Results contain the expected fields
        assert len(results) == 1
        assert results[0]["text"] == "client_a document content"
        assert results[0]["score"] == 0.95
        assert results[0]["file_name"] == "a.pdf"
        assert results[0]["page_label"] == "1"
