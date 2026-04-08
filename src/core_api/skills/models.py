"""
Pydantic and dataclass models for the MAAI skill system.

Defines the core data structures used across the skill pipeline:
skill definitions loaded from YAML, routing decisions, match results,
and the in-memory embedding index.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field


class SkillDef(BaseModel):
    """Schema for a single skill YAML file.

    Per D-02, includes everything inline: name, description, triggers,
    autonomy policy, required tools, and the CrewAI agent/task configs.
    """

    name: str
    description: str
    triggers: list[str] = Field(default_factory=list)
    autonomy: str = "confirm-first"  # Per D-12: default is confirm-first
    tools: list[str] = Field(default_factory=list)
    agent: dict
    task: dict


class RoutingDecision(Enum):
    """The four possible outcomes from the skill matcher."""

    AUTO_RUN = "auto_run"
    CONFIRM_FIRST = "confirm_first"
    FREEFORM = "freeform"
    LIST_SKILLS = "list_skills"


class MatchResult:
    """Result returned by the skill matcher after routing a user message."""

    def __init__(
        self,
        decision: RoutingDecision,
        skill: Optional[SkillDef] = None,
        score: float = 0.0,
    ) -> None:
        self.decision = decision
        self.skill = skill
        self.score = score


@dataclass
class SkillIndex:
    """In-memory embedding index for all loaded skills.

    ``embeddings`` is an L2-normalised numpy array of shape (N, D)
    where N is the number of skills and D is the embedding dimension.
    """

    skills: list[SkillDef]
    embeddings: np.ndarray  # shape (N, D), L2-normalized
