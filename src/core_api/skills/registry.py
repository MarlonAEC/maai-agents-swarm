"""
Skill YAML registry with Ollama embedding index.

Discovers skill YAML files from the configured skills directory, validates
them against SkillDef, and builds a batched L2-normalised embedding index
via the Ollama /api/embed endpoint (NOT /api/embeddings — see Research
Pitfall 6).

The module-level ``_INDEX`` is populated by ``initialize()`` at startup.
"""

import os
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
import yaml

from logging_config import get_logger
from skills.models import SkillDef, SkillIndex

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# Module-level skill index populated by initialize()
_INDEX: Optional[SkillIndex] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts via Ollama /api/embed and return L2-normalised vectors.

    Uses the batch endpoint so all texts are embedded in a single HTTP call.

    Args:
        texts: List of strings to embed.

    Returns:
        L2-normalised numpy array of shape ``(len(texts), D)`` where D is the
        embedding dimension (768 for nomic-embed-text).
    """
    response = httpx.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=30.0,
    )
    response.raise_for_status()

    raw: list[list[float]] = response.json()["embeddings"]
    vectors = np.array(raw, dtype=np.float32)

    # L2-normalise each row so dot product == cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Avoid division by zero for zero-vectors (shouldn't happen with real text)
    norms = np.where(norms == 0.0, 1.0, norms)
    return vectors / norms


def _warmup_embedding_model() -> None:
    """Force Ollama to load the embedding model before processing skills.

    Per Research Pitfall 2, the first embedding call on a cold Ollama instance
    can be very slow (model load + VRAM allocation). Warming up at startup
    ensures the first real skill match does not time out.
    """
    try:
        _embed_texts(["warmup"])
        logger.info("Embedding model warmup complete")
    except Exception:
        logger.warning(
            "Embedding model warmup failed — model may not be loaded yet",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_skills(
    skills_dir: Path,
    allowed_tools: Optional[set[str]] = None,
) -> SkillIndex:
    """Discover and index all skill YAML files in ``skills_dir``.

    Each YAML file is validated against ``SkillDef``. If ``allowed_tools``
    is provided, ``skill.tools`` entries not in the allowlist are removed
    (the skill is still indexed; only its tool list is filtered).

    Embedding texts are built as::

        "{name} {description} {trigger_0} {trigger_1} ..."

    All texts are embedded in a single batched Ollama call for efficiency.

    Args:
        skills_dir: Directory containing ``*.yaml`` skill definition files.
        allowed_tools: Optional set of permitted tool names. Skills with
                       unlisted tools have those tools silently removed.

    Returns:
        ``SkillIndex`` with the validated skills and their L2-normalised
        embedding matrix.
    """
    if not skills_dir.exists():
        logger.warning("Skills directory does not exist: %s", skills_dir)
        return SkillIndex(skills=[], embeddings=np.empty((0, 768), dtype=np.float32))

    yaml_files = sorted(skills_dir.glob("*.yaml"))
    if not yaml_files:
        logger.info("No skill YAML files found in: %s", skills_dir)
        return SkillIndex(skills=[], embeddings=np.empty((0, 768), dtype=np.float32))

    skills: list[SkillDef] = []
    embed_texts: list[str] = []

    for yaml_file in yaml_files:
        try:
            with yaml_file.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
            skill = SkillDef(**raw)
        except Exception:
            logger.exception("Failed to load skill YAML: %s", yaml_file)
            continue

        # Filter tool list to allowlist if provided
        if allowed_tools is not None:
            skill.tools = [t for t in skill.tools if t in allowed_tools]

        skills.append(skill)

        embed_text = (
            skill.name
            + " "
            + skill.description
            + " "
            + " ".join(skill.triggers)
        )
        embed_texts.append(embed_text)

        logger.info("Indexed skill: %s from %s", skill.name, yaml_file.name)

    if not skills:
        return SkillIndex(skills=[], embeddings=np.empty((0, 768), dtype=np.float32))

    # Batch-embed all skill texts in a single Ollama call
    embeddings = _embed_texts(embed_texts)

    return SkillIndex(skills=skills, embeddings=embeddings)


def get_index() -> Optional[SkillIndex]:
    """Return the current module-level skill index.

    Returns:
        The populated ``SkillIndex`` or ``None`` if ``initialize()`` has not
        been called yet.
    """
    return _INDEX


def initialize(
    skills_dir: Path,
    allowed_tools: Optional[set[str]] = None,
) -> None:
    """Populate the module-level skill index at application startup.

    Warms up the Ollama embedding model first to prevent slow first-match
    timeouts, then loads and indexes all skills.

    Args:
        skills_dir: Directory containing ``*.yaml`` skill definition files.
        allowed_tools: Optional set of permitted tool names passed through to
                       ``load_skills()``.
    """
    global _INDEX

    _warmup_embedding_model()
    _INDEX = load_skills(skills_dir, allowed_tools)

    logger.info("Skill registry initialized: %d skills", len(_INDEX.skills))
