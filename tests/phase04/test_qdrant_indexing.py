"""
Tests for DOCP-03 (semantic chunking) and DOCP-04 (Qdrant vector storage).

Covers:
- init_embed_model sets the correct 768-dim OllamaEmbedding model
- SemanticSplitterNodeParser called with breakpoint_percentile_threshold=95
- VectorStoreIndex created with the chunked nodes and storage context
- Embed model is nomic-embed-text (not the OpenAI default which causes dim mismatch)
"""

from unittest.mock import MagicMock, call, patch


def test_init_embed_model():
    """init_embed_model sets Settings.embed_model to an OllamaEmbedding instance."""
    mock_embedding = MagicMock()

    with (
        patch("rag.pipeline.OllamaEmbedding", return_value=mock_embedding) as mock_cls,
        patch("rag.pipeline.Settings") as mock_settings,
    ):
        from rag.pipeline import init_embed_model

        init_embed_model()

        # Settings.embed_model must be assigned (not left as OpenAI default)
        assert mock_settings.embed_model == mock_embedding
        # OllamaEmbedding must have been constructed
        mock_cls.assert_called_once()


def test_init_embed_model_768_dims():
    """OllamaEmbedding is configured with nomic-embed-text, NOT the OpenAI default.

    This test verifies the Research Pitfall 2 fix: if Settings.embed_model is
    not explicitly set, LlamaIndex defaults to OpenAI embeddings,
    causing Qdrant collection dimension mismatch errors.
    """
    with (
        patch("rag.pipeline.OllamaEmbedding") as mock_cls,
        patch("rag.pipeline.Settings"),
    ):
        import os

        os.environ.setdefault("EMBEDDING_MODEL", "nomic-embed-text")

        from rag.pipeline import init_embed_model

        init_embed_model()

        # Must use nomic-embed-text (768-dim), not the OpenAI default (wrong dim for Qdrant)
        call_kwargs = mock_cls.call_args
        assert call_kwargs is not None, "OllamaEmbedding was not constructed"
        model_name = call_kwargs.kwargs.get("model_name") or call_kwargs.args[0]
        assert model_name == "nomic-embed-text", (
            f"Expected 'nomic-embed-text' but got '{model_name}'. "
            "Using a different model risks Qdrant dimension mismatch."
        )


def test_semantic_chunking():
    """index_document uses SemanticSplitterNodeParser with breakpoint_percentile_threshold=95."""
    mock_node = MagicMock()
    mock_node.text = "chunk text"

    mock_splitter_instance = MagicMock()
    mock_splitter_instance.get_nodes_from_documents.return_value = [mock_node]

    with (
        patch("rag.pipeline.SemanticSplitterNodeParser", return_value=mock_splitter_instance) as mock_splitter_cls,
        patch("rag.pipeline.QdrantVectorStore"),
        patch("rag.pipeline.StorageContext"),
        patch("rag.pipeline.VectorStoreIndex"),
        patch("rag.pipeline._get_qdrant_client"),
        patch("rag.pipeline.Settings"),
    ):
        from rag.pipeline import index_document

        result = index_document("client1", [{"page_no": 1, "text": "hello world"}], "test.pdf")

        # Splitter must be called with breakpoint_percentile_threshold=95 (D-07)
        mock_splitter_cls.assert_called_once()
        call_kwargs = mock_splitter_cls.call_args.kwargs
        assert call_kwargs.get("breakpoint_percentile_threshold") == 95, (
            "breakpoint_percentile_threshold must be 95 to produce large coherent chunks"
        )
        assert call_kwargs.get("buffer_size") == 1

        # Splitter must be invoked with the documents
        mock_splitter_instance.get_nodes_from_documents.assert_called_once()

        # Returns number of nodes
        assert result == 1


def test_qdrant_vector_upsert():
    """index_document creates VectorStoreIndex with nodes and storage_context."""
    mock_node = MagicMock()
    mock_splitter = MagicMock()
    mock_splitter.get_nodes_from_documents.return_value = [mock_node, mock_node]

    mock_vector_store = MagicMock()
    mock_storage_ctx = MagicMock()

    with (
        patch("rag.pipeline.SemanticSplitterNodeParser", return_value=mock_splitter),
        patch("rag.pipeline.QdrantVectorStore", return_value=mock_vector_store) as mock_qs,
        patch("rag.pipeline.StorageContext") as mock_sc,
        patch("rag.pipeline.VectorStoreIndex") as mock_index_cls,
        patch("rag.pipeline._get_qdrant_client") as mock_client,
        patch("rag.pipeline.Settings"),
    ):
        mock_sc.from_defaults.return_value = mock_storage_ctx

        from rag.pipeline import index_document

        result = index_document(
            "client_test",
            [{"page_no": 1, "text": "page one"}, {"page_no": 2, "text": "page two"}],
            "doc.pdf",
        )

        # QdrantVectorStore must be created with the correct collection name
        mock_qs.assert_called_once()
        call_kwargs = mock_qs.call_args.kwargs
        assert call_kwargs.get("collection_name") == "maai_client_test_documents"

        # StorageContext.from_defaults must receive the vector_store
        mock_sc.from_defaults.assert_called_once_with(vector_store=mock_vector_store)

        # VectorStoreIndex must be constructed with nodes + storage_context
        mock_index_cls.assert_called_once()
        index_args = mock_index_cls.call_args
        assert index_args.args[0] == [mock_node, mock_node]
        assert index_args.kwargs.get("storage_context") == mock_storage_ctx

        # Returns chunk count
        assert result == 2


def test_index_document_creates_metadata():
    """index_document passes file_name, page_label, and client_id as metadata to Document.

    This metadata is used by query_documents to build citations in D-06 format.
    Verified by inspecting the kwargs passed to the Document() constructor.
    """
    mock_splitter = MagicMock()
    mock_splitter.get_nodes_from_documents.return_value = [MagicMock()]

    with (
        patch("rag.pipeline.SemanticSplitterNodeParser", return_value=mock_splitter),
        patch("rag.pipeline.QdrantVectorStore"),
        patch("rag.pipeline.StorageContext"),
        patch("rag.pipeline.VectorStoreIndex"),
        patch("rag.pipeline._get_qdrant_client"),
        patch("rag.pipeline.Settings"),
        patch("rag.pipeline.Document") as mock_doc_cls,
    ):
        mock_doc_cls.return_value = MagicMock()

        from rag.pipeline import index_document

        index_document(
            "my_client",
            [{"page_no": 3, "text": "document content here"}],
            "annual_report.pdf",
        )

    # Document() must have been called once with correct metadata kwargs
    mock_doc_cls.assert_called_once()
    call_kwargs = mock_doc_cls.call_args.kwargs
    metadata = call_kwargs.get("metadata", {})
    assert metadata["file_name"] == "annual_report.pdf", (
        f"Expected file_name='annual_report.pdf' in metadata but got: {metadata}"
    )
    assert metadata["page_label"] == "3", (
        f"Expected page_label='3' in metadata but got: {metadata}"
    )
    assert metadata["client_id"] == "my_client", (
        f"Expected client_id='my_client' in metadata but got: {metadata}"
    )
