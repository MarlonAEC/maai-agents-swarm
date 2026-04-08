"""
MAAI Core API — FastAPI application entrypoint.

Exposes:
  GET  /health  — liveness probe
  POST /chat    — skill-aware chat routing (skills → freeform fallback)

Lifespan (D-08, D-09, AGNT-02, AGNT-04, AGNT-05):
  1. Initialize tool registry by scanning /app/tools
  2. Load per-client tool allowlist from /app/clients/{CLIENT_ID}/tools.yaml
  3. Initialize skill registry with embeddings from /app/clients/{CLIENT_ID}/skills
"""

import os
import yaml
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from client.env (or .env) before anything else.
load_dotenv()

import skills.registry as skill_reg  # noqa: E402 — must come after load_dotenv
import skills.tool_registry as tool_reg  # noqa: E402 — must come after load_dotenv
from logging_config import get_logger  # noqa: E402 — must come after load_dotenv
from routers.chat import router as chat_router  # noqa: E402

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # Initialize tool registry (D-08, AGNT-05)
    # /app/tools maps to src/core_api/tools/ copied during Docker build
    tools_dir = Path("/app/tools")
    tool_reg.initialize(tools_dir)

    # Load per-client tool allowlist (D-09, AGNT-04)
    client_id = os.getenv("CLIENT_ID", "default")
    allowlist_path = Path(f"/app/clients/{client_id}/tools.yaml")
    allowed_tools = None
    if allowlist_path.exists():
        data = yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))
        allowed_tools = set(data.get("enabled_tools", []))
        logger.info("Tool allowlist loaded: %s", allowed_tools)

    # Initialize skill registry with embedding index (D-03, D-05, AGNT-02)
    # clients/ is bind-mounted into the container at /app/clients/ via Docker Compose (Plan 04)
    skills_dir = Path(f"/app/clients/{client_id}/skills")
    if skills_dir.exists():
        skill_reg.initialize(skills_dir, allowed_tools)
    else:
        logger.warning(
            "No skills directory found at %s -- skill matching disabled", skills_dir
        )

    logger.info("MAAI Core API started")
    yield
    logger.info("MAAI Core API shutting down")


app = FastAPI(
    title="MAAI Core API",
    description="Core AI agent API for the MAAI Agent Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat_router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness probe — returns 200 OK when the API is ready."""
    return {"status": "ok"}
