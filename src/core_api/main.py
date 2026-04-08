"""
MAAI Core API — FastAPI application entrypoint.

Exposes:
  GET  /health  — liveness probe
  POST /chat    — CrewAI freeform chat (via routers.chat)
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from client.env (or .env) before anything else.
load_dotenv()

from logging_config import get_logger  # noqa: E402 — must come after load_dotenv
from routers.chat import router as chat_router  # noqa: E402

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
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
