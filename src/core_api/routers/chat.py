"""
Chat router — POST /chat endpoint.

Accepts a conversation history and the latest user message, runs the
CrewAI freeform crew in a thread-pool executor (to avoid blocking the
async event loop), and returns the agent's response.
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.freeform_crew import run_freeform_crew
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["chat"])


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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Any:
    """Invoke the CrewAI freeform agent and return its response.

    The crew is executed in a thread-pool executor so the async event loop
    is never blocked during the (potentially long-running) LLM call.
    """
    logger.info(
        "Incoming chat request — user_message length=%d messages=%d",
        len(request.user_message),
        len(request.messages),
    )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_freeform_crew(request.messages, request.user_message),
        )
        logger.info("Chat request completed successfully")
        return ChatResponse(response=result)
    except Exception as exc:
        logger.error("Chat request failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
