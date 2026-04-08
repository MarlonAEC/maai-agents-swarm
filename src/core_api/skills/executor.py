"""
Skill executor — assembles a CrewAI Crew from a SkillDef at runtime.

Per D-07 and Research Pattern 6, this module uses direct Agent/Task/Crew
constructors instead of the @CrewBase decorator (Research Pitfall 4:
@CrewBase cannot load arbitrary runtime YAML paths).

This function is intentionally synchronous so it can be invoked via
``loop.run_in_executor()`` from the async chat handler, matching the
pattern used by ``run_freeform_crew``.
"""

import os

from crewai import LLM, Agent, Crew, Process, Task

from logging_config import get_logger
from skills.models import SkillDef
from skills.tool_registry import get_registry

logger = get_logger(__name__)


def run_skill(skill: SkillDef, user_message: str, messages: list) -> str:
    """Assemble and execute a CrewAI Crew from the given SkillDef.

    Resolves tool instances from the tool registry, constructs an Agent and
    Task from the skill's YAML-sourced configuration, and runs the crew
    synchronously.

    Args:
        skill: The matched skill definition loaded from YAML.
        user_message: The user's raw message, formatted into the task
                      description via the ``{user_message}`` placeholder.
        messages: Full conversation history (unused by the crew directly,
                  included for API consistency with run_freeform_crew).

    Returns:
        The agent's response as a string.

    Note:
        Do NOT call ``asyncio.run()`` inside this function — it is already
        running in a thread-pool executor and must remain synchronous.
    """
    # Step 1: Resolve tool instances from the tool registry
    tool_registry = get_registry()
    tool_instances = []
    for tool_name in skill.tools:
        if tool_name in tool_registry:
            tool_instances.append(tool_registry[tool_name]())  # instantiate the class
        else:
            logger.warning(
                "Tool '%s' referenced by skill '%s' not found in registry -- skipping",
                tool_name,
                skill.name,
            )

    # Step 2: Create LLM instance (same pattern as freeform_crew.py)
    llm = LLM(
        model="openai/reasoning-model",
        base_url=os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1"),
        api_key=os.getenv("LITELLM_MASTER_KEY", "sk-maai-local"),
        stream=False,
        timeout=60.0,
    )

    # Step 3: Create Agent from skill YAML fields
    agent = Agent(
        role=skill.agent["role"],
        goal=skill.agent["goal"],
        backstory=skill.agent.get("backstory", ""),
        llm=llm,
        tools=tool_instances,
        max_iter=5,
        max_execution_time=60,
        memory=False,
        verbose=False,
    )

    # Step 4: Create Task, formatting {user_message} placeholder
    task = Task(
        description=skill.task["description"].format(user_message=user_message),
        expected_output=skill.task["expected_output"],
        agent=agent,
    )

    # Step 5: Assemble and execute Crew
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        embedder={
            "provider": "ollama",
            "config": {
                "model_name": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                "url": "http://ollama:11434/api/embeddings",  # CrewAI uses legacy path internally
            },
        },
    )

    logger.info("Executing skill: %s with %d tools", skill.name, len(tool_instances))
    result = crew.kickoff(inputs={"user_message": user_message})
    logger.info("Skill execution complete: %s", skill.name)
    return str(result)
