"""
Freeform crew — a single-agent CrewAI crew for general conversational tasks.

The agent uses the ``openai/reasoning-model`` alias routed through the
LiteLLM proxy at ``http://litellm:4000/v1``.  Embeddings use Ollama
directly (``http://ollama:11434/api/embeddings``) because CrewAI's built-in
ollama embedder provider calls the Ollama HTTP API natively and does not
support routing through a LiteLLM proxy.
"""

import os

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from logging_config import get_logger

logger = get_logger(__name__)


@CrewBase
class FreeformCrew:
    """Single-agent conversational crew backed by LiteLLM proxy."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def _llm(self) -> LLM:
        """Return the LLM instance routed through LiteLLM.

        - model: ``openai/reasoning-model`` — alias resolves to Qwen3 14B via
          LiteLLM proxy (D-07 / CHAT-05).
        - stream=False — required per AGNT-08; CrewAI does not stream agent
          responses in this configuration.
        - timeout=60.0 — generous timeout for local LLM inference.
        """
        return LLM(
            model="openai/reasoning-model",
            base_url=os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1"),
            api_key=os.getenv("LITELLM_MASTER_KEY", "sk-maai-local"),
            stream=False,
            timeout=60.0,
        )

    @agent
    def freeform_agent(self) -> Agent:
        """Freeform conversational agent with guardrails (AGNT-09)."""
        return Agent(
            config=self.agents_config["freeform_agent"],
            llm=self._llm(),
            max_iter=5,
            max_execution_time=60,
            memory=False,
            verbose=False,
        )

    @task
    def freeform_task(self) -> Task:
        """Single task that formulates a response given message history."""
        return Task(config=self.tasks_config["freeform_task"])

    @crew
    def crew(self) -> Crew:
        """Assemble the crew with sequential processing and Ollama embedder.

        The embedder is configured to call Ollama directly (AGNT-07 / D-10).
        LiteLLM proxy is not used for embeddings because CrewAI's ollama
        embedder provider speaks the Ollama HTTP API natively.
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            embedder={
                "provider": "ollama",
                "config": {
                    "model_name": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                    "url": "http://ollama:11434/api/embeddings",
                },
            },
        )


def run_freeform_crew(messages: list, user_message: str) -> str:
    """Execute the freeform crew and return the agent's response as a string.

    Args:
        messages: Full conversation history (list of Message-like objects with
                  ``role`` and ``content`` attributes).
        user_message: The current user message to respond to.

    Returns:
        The agent's response text.
    """
    logger.info(
        "Running freeform crew — message_count=%d user_message_length=%d",
        len(messages),
        len(user_message),
    )

    crew_instance = FreeformCrew().crew()

    # Format prior history, excluding the latest user message (already passed
    # separately as ``user_message`` to avoid duplication in the prompt).
    prior_messages = messages[:-1] if messages else []
    history = "\n".join(
        f"{m.role}: {m.content}" for m in prior_messages
    ) or "(no prior messages)"

    result = crew_instance.kickoff(
        inputs={
            "messages": history,
            "user_message": user_message,
        }
    )

    logger.info("Freeform crew completed successfully")
    return str(result)
