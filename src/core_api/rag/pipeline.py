"""
RAG pipeline helpers — LlamaIndex + Qdrant for document indexing and retrieval.

CRITICAL (Research Pitfall 2): Settings.embed_model MUST be set via init_embed_model()
at application startup BEFORE any Qdrant operations. nomic-embed-text produces 768-dim
vectors; if Settings.embed_model is not set, LlamaIndex defaults to 1536 dims (OpenAI)
causing Qdrant dimension mismatch errors.

Per-client isolation: each client gets a dedicated collection named maai_{client_id}_documents.
"""

import os

from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

from logging_config import get_logger

logger = get_logger(__name__)


def init_embed_model() -> None:
    """Set the global LlamaIndex embed model to OllamaEmbedding with nomic-embed-text.

    MUST be called at application startup BEFORE any Qdrant operations.
    nomic-embed-text produces 768-dim vectors; the OpenAI default is 1536-dim,
    which causes Qdrant collection dimension mismatch errors.
    """
    model_name = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    Settings.embed_model = OllamaEmbedding(model_name=model_name, base_url=base_url)
    logger.info("LlamaIndex embed_model set to %s at %s", model_name, base_url)


def _get_qdrant_client() -> qdrant_client.QdrantClient:
    """Create and return a QdrantClient from environment config."""
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return qdrant_client.QdrantClient(host=host, port=port)


def _collection_name(client_id: str) -> str:
    """Return the Qdrant collection name for a given client (DOCP-04 isolation).

    Per-client isolation: each client has a dedicated collection so queries
    never return documents belonging to a different client.
    """
    return f"maai_{client_id}_documents"


def index_document(client_id: str, pages: list[dict], file_name: str) -> int:
    """Chunk and index document pages into the client's Qdrant collection.

    Args:
        client_id: Identifier for the client — determines the Qdrant collection.
        pages: List of page dicts from docproc response: [{"page_no": int, "text": str}, ...].
        file_name: Original file name stored as metadata on every chunk.

    Returns:
        Number of semantic chunks indexed (nodes created by the splitter).

    Note:
        Settings.embed_model must already be set (via init_embed_model()) before
        calling this function.  SemanticSplitterNodeParser uses the embed model
        to compute sentence embeddings for breakpoint detection.
    """
    collection = _collection_name(client_id)

    # Build LlamaIndex Document objects from docproc pages.
    documents = [
        Document(
            text=page["text"],
            metadata={
                "file_name": file_name,
                "page_label": str(page["page_no"]),
                "client_id": client_id,
            },
        )
        for page in pages
        if page.get("text")
    ]

    # Semantic splitting — uses embedding similarity to find natural breakpoints.
    # breakpoint_percentile_threshold=95 keeps large coherent chunks (D-07).
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=Settings.embed_model,
    )
    nodes = splitter.get_nodes_from_documents(documents)

    # Build storage context pointing at the client-specific Qdrant collection.
    vector_store = QdrantVectorStore(
        client=_get_qdrant_client(),
        collection_name=collection,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Index nodes — Qdrant collection is created automatically on first write.
    VectorStoreIndex(nodes, storage_context=storage_context)

    n = len(nodes)
    logger.info(
        "Indexed %d chunks for file=%s client=%s collection=%s",
        n,
        file_name,
        client_id,
        collection,
    )
    return n


def query_documents(client_id: str, question: str, top_k: int = 5) -> list[dict]:
    """Retrieve top-k relevant chunks from the client's Qdrant collection.

    Args:
        client_id: Identifier for the client — scopes the retrieval to their collection.
        question: Natural language query for semantic similarity search.
        top_k: Number of most relevant chunks to return (default: 5).

    Returns:
        List of dicts with keys: text, score, file_name, page_label.
    """
    collection = _collection_name(client_id)

    vector_store = QdrantVectorStore(
        client=_get_qdrant_client(),
        collection_name=collection,
    )
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    retriever = index.as_retriever(similarity_top_k=top_k)
    raw_nodes = retriever.retrieve(question)

    results = [
        {
            "text": node.text,
            "score": node.score,
            "file_name": node.metadata.get("file_name", "unknown"),
            "page_label": node.metadata.get("page_label", "?"),
        }
        for node in raw_nodes
    ]

    logger.info(
        "Retrieved %d chunks for client=%s question length=%d",
        len(results),
        client_id,
        len(question),
    )
    return results
