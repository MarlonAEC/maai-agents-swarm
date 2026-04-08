"""RAG crew — answers questions about indexed documents using vector search."""

import os

from crewai import LLM, Agent, Crew, Process, Task

from logging_config import get_logger

logger = get_logger(__name__)


def run_rag_crew(user_message: str, context_chunks: str) -> str:
    """Run a CrewAI crew to answer a question using retrieved document context.

    Args:
        user_message: The user's question.
        context_chunks: Pre-formatted context from QdrantSearchTool output.

    Returns:
        The agent's answer with citations.
    """
    llm = LLM(
        model="openai/reasoning-model",
        base_url=os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1"),
        api_key=os.getenv("LITELLM_MASTER_KEY", "sk-maai-local"),
        stream=False,
        timeout=60.0,
    )

    agent = Agent(
        role="Document Knowledge Expert",
        goal="Answer questions accurately using only the provided document context. Always cite sources.",
        backstory=(
            "You are an expert at reading and synthesizing information from documents. "
            "You only answer based on the provided context and always cite the source "
            "document and page number. If the context doesn't contain enough information "
            "to answer, you say so honestly."
        ),
        llm=llm,
        tools=[],
        max_iter=3,
        max_execution_time=60,
        memory=False,
        verbose=False,
    )

    task = Task(
        description=(
            f"Answer the following question using ONLY the document context below.\n\n"
            f"Question: {user_message}\n\n"
            f"Document Context:\n{context_chunks}\n\n"
            f"Instructions:\n"
            f"- Answer based solely on the provided context\n"
            f"- At the end of your answer, list citations in the format: "
            f"Source: filename.pdf, page N\n"
            f"- If the context is insufficient, state that clearly"
        ),
        expected_output="A clear answer to the question with source citations at the end.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        embedder={
            "provider": "ollama",
            "config": {
                "model_name": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                "url": "http://ollama:11434/api/embeddings",
            },
        },
    )

    logger.info("Running RAG crew for question length=%d", len(user_message))
    result = crew.kickoff()
    logger.info("RAG crew complete")
    return str(result)
