"""
Three-zone skill matcher for MAAI user message routing.

Routes user messages to one of four outcomes:
  - LIST_SKILLS: user asked what skills/capabilities are available
  - AUTO_RUN: high confidence match on an auto-execute skill
  - CONFIRM_FIRST: high confidence match on a confirm-first skill, or
                   medium confidence match on any skill
  - FREEFORM: low confidence — fall through to open-ended agent reasoning

Thresholds are configurable via environment variables (D-06):
  SKILL_HIGH_THRESHOLD (default 0.7)
  SKILL_LOW_THRESHOLD  (default 0.5)
"""

import os

import numpy as np

from logging_config import get_logger
from skills.models import MatchResult, RoutingDecision
from skills.registry import _embed_texts, get_index

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HIGH_THRESHOLD = float(os.getenv("SKILL_HIGH_THRESHOLD", "0.7"))
LOW_THRESHOLD = float(os.getenv("SKILL_LOW_THRESHOLD", "0.5"))

# Keywords that trigger the "list skills" short-circuit (D-14)
LIST_SKILLS_KEYWORDS = frozenset(
    ["list skills", "what can you do", "show skills", "available skills"]
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route(user_message: str) -> MatchResult:
    """Route a user message to the appropriate handling decision.

    Algorithm:
    1. Check for "list skills" keywords — short-circuit to LIST_SKILLS.
    2. Load the skill index; if empty, fall through to FREEFORM.
    3. Embed the user message and compute cosine similarity against all skills.
    4. Apply three-zone threshold logic to determine the decision.

    Args:
        user_message: The raw user message text to route.

    Returns:
        A ``MatchResult`` with the routing decision, optional matched skill,
        and the best cosine similarity score.
    """
    lower = user_message.lower().strip()

    # Zone 0: "list skills" keyword detection (D-14)
    if any(kw in lower for kw in LIST_SKILLS_KEYWORDS):
        logger.info("Skill match: list_skills keyword detected")
        return MatchResult(RoutingDecision.LIST_SKILLS)

    # Zone check requires a populated index
    index = get_index()
    if index is None or len(index.skills) == 0:
        logger.info("Skill match: no index available — routing to freeform")
        return MatchResult(RoutingDecision.FREEFORM)

    # Embed the user message (single text, take first vector)
    query_vec = _embed_texts([user_message])[0]

    # Cosine similarity: dot product of L2-normalised vectors
    scores = index.embeddings @ query_vec

    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    skill = index.skills[best_idx]

    logger.info("Skill match: skill=%s score=%.3f", skill.name, best_score)

    # Three-zone routing logic (D-06)
    if best_score >= HIGH_THRESHOLD:
        if skill.autonomy == "auto-execute":
            return MatchResult(RoutingDecision.AUTO_RUN, skill, best_score)
        return MatchResult(RoutingDecision.CONFIRM_FIRST, skill, best_score)

    if best_score >= LOW_THRESHOLD:
        return MatchResult(RoutingDecision.CONFIRM_FIRST, skill, best_score)

    return MatchResult(RoutingDecision.FREEFORM, skill=None, score=best_score)
