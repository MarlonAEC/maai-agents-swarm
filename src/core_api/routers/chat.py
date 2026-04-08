"""
Chat router — POST /chat endpoint.

Accepts a conversation history and the latest user message, routes through
the skill matcher before falling back to the freeform CrewAI crew.

Routing logic (D-05, D-06, D-11, D-12, D-13, D-14):
  1. Check for pending confirm-first confirmation from prior assistant message
  2. Run skill matcher to get a RoutingDecision
  3. Handle decision:
     - LIST_SKILLS  → return formatted skill list
     - AUTO_RUN     → execute skill immediately
     - CONFIRM_FIRST → return confirmation prompt (skill name embedded in **bold**)
     - FREEFORM     → delegate to run_freeform_crew (default fallback)
"""

import asyncio
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.freeform_crew import run_freeform_crew
from logging_config import get_logger
from skills.executor import run_skill
from skills.matcher import route as match_skill
from skills.models import RoutingDecision
from skills.registry import get_index

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["chat"])

# ---------------------------------------------------------------------------
# Confirmation detection helpers
# ---------------------------------------------------------------------------

# Per D-13: confirmation keywords the user can type to approve a confirm-first skill
_CONFIRM_KEYWORDS = frozenset(["yes", "y", "go ahead", "proceed", "confirm", "do it", "ok"])
_CANCEL_KEYWORDS = frozenset(["no", "n", "cancel", "stop", "nevermind", "never mind"])

# Pattern to extract skill name from assistant's confirmation message.
# The confirmation message will contain: "**skill_name_here**"
# Per Research Pitfall 3: skill name is embedded so it can be parsed from
# history statelessly without server-side session storage.
_PENDING_SKILL_RE = re.compile(r"\*\*(\w+)\*\*")


def _detect_pending_confirmation(messages: list["Message"]) -> str | None:
    """Check if the last assistant message was a confirm-first prompt.

    Returns the skill name if a pending confirmation is detected, else None.
    Per Research Pitfall 3: the skill name is embedded in the assistant's
    confirmation message so it can be parsed from history statelessly.
    """
    if len(messages) < 2:
        return None
    # Find the last assistant message (excluding the current user message)
    for msg in reversed(messages[:-1]):
        if msg.role == "assistant":
            match = _PENDING_SKILL_RE.search(msg.content)
            if match and "confirm" in msg.content.lower():
                return match.group(1)
            break
    return None


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """A single message in the conversation history."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    messages: list[Message]
    user_message: str


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    response: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Any:
    """Route the user message through skill matching before freeform fallback.

    Execution path:
    1. Confirm-first pending check — if the prior assistant message was a
       skill confirmation prompt, handle yes/no responses directly.
    2. Skill matcher — classify the message into one of four routing decisions.
    3. Decision handling — LIST_SKILLS, AUTO_RUN, CONFIRM_FIRST, or FREEFORM.

    The synchronous crew/skill functions are offloaded via run_in_executor so
    the async event loop is never blocked during LLM calls.
    """
    logger.info(
        "Incoming chat request -- user_message length=%d messages=%d",
        len(request.user_message),
        len(request.messages),
    )

    try:
        loop = asyncio.get_running_loop()  # Per Pitfall 5: use get_running_loop not get_event_loop

        # Step 1: Check for pending confirm-first confirmation (D-13)
        pending_skill_name = _detect_pending_confirmation(request.messages)
        if pending_skill_name:
            lower_msg = request.user_message.lower().strip()
            if lower_msg in _CONFIRM_KEYWORDS:
                # User confirmed -- find and execute the pending skill
                index = get_index()
                if index:
                    skill = next((s for s in index.skills if s.name == pending_skill_name), None)
                    if skill:
                        logger.info("Executing confirmed skill: %s", skill.name)
                        result = await loop.run_in_executor(
                            None,
                            lambda: run_skill(skill, request.user_message, request.messages),
                        )
                        return ChatResponse(response=result)
                # Skill not found in index -- fall through to freeform
                logger.warning("Pending skill '%s' not found in index", pending_skill_name)
            elif lower_msg in _CANCEL_KEYWORDS:
                logger.info("User cancelled pending skill: %s", pending_skill_name)
                return ChatResponse(response="Got it, I've cancelled that. How else can I help?")
            # If neither confirm nor cancel, treat as a new message (fall through to routing)

        # Step 2: Run skill matcher (D-05, D-06)
        match_result = match_skill(request.user_message)

        # Step 3: Handle routing decision
        if match_result.decision == RoutingDecision.LIST_SKILLS:
            # D-14: Return available skill list
            index = get_index()
            if index and index.skills:
                lines = ["Here are the available skills:\n"]
                for s in index.skills:
                    lines.append(f"- **{s.name}**: {s.description}")
                return ChatResponse(response="\n".join(lines))
            return ChatResponse(response="No skills are currently configured.")

        if match_result.decision == RoutingDecision.AUTO_RUN:
            # D-11: auto-execute skill directly
            logger.info(
                "Auto-executing skill: %s (score=%.3f)", match_result.skill.name, match_result.score
            )
            result = await loop.run_in_executor(
                None,
                lambda: run_skill(match_result.skill, request.user_message, request.messages),
            )
            return ChatResponse(response=result)

        if match_result.decision == RoutingDecision.CONFIRM_FIRST:
            # D-13: Ask user to confirm before executing.
            # Embed skill name in **bold** so _detect_pending_confirmation can parse it
            # from history statelessly (Research Pitfall 3).
            skill = match_result.skill
            logger.info(
                "Requesting confirmation for skill: %s (score=%.3f)",
                skill.name,
                match_result.score,
            )
            return ChatResponse(
                response=(
                    f"I think you want to run the **{skill.name}** skill: {skill.description}\n\n"
                    f"Reply **yes** to confirm or **no** to cancel."
                )
            )

        # Step 4: FREEFORM fallback (D-04)
        logger.info("Routing to freeform agent (score=%.3f)", match_result.score)
        result = await loop.run_in_executor(
            None,
            lambda: run_freeform_crew(request.messages, request.user_message),
        )
        return ChatResponse(response=result)

    except Exception as exc:
        logger.error("Chat request failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
