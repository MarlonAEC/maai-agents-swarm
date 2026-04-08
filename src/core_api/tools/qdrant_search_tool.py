"""Qdrant search tool — retrieves relevant document chunks from the RAG knowledge base."""

import os
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from logging_config import get_logger
from rag.pipeline import query_documents

logger = get_logger(__name__)


class QdrantSearchInput(BaseModel):
    """Input schema for QdrantSearchTool."""

    query: str = Field(..., description="The search query to find relevant document chunks.")
    top_k: int = Field(default=5, description="Number of top results to return.")


class QdrantSearchTool(BaseTool):
    name: str = "qdrant_search"
    description: str = (
        "Search the client's document knowledge base. Returns relevant text chunks "
        "with source file name and page number. Use for answering questions about "
        "indexed documents."
    )
    args_schema: Type[BaseModel] = QdrantSearchInput

    def _run(self, query: str, top_k: int = 5) -> str:
        client_id = os.getenv("CLIENT_ID", "default")
        logger.info(
            "QdrantSearchTool query=%s top_k=%d client=%s",
            query[:80],
            top_k,
            client_id,
        )
        results = query_documents(client_id=client_id, question=query, top_k=top_k)
        if not results:
            return "No relevant documents found in the knowledge base."
        # Format results with citations per D-06
        output_parts = []
        for i, r in enumerate(results, 1):
            output_parts.append(
                f"[{i}] (Score: {r['score']:.3f}) {r['text']}\n"
                f"    Source: {r['file_name']}, page {r['page_label']}"
            )
        return "\n\n".join(output_parts)
