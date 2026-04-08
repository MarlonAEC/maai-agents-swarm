"""Echo tool — demonstration BaseTool plugin for testing the skill system."""

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from logging_config import get_logger

logger = get_logger(__name__)


class EchoInput(BaseModel):
    """Input schema for EchoTool."""

    message: str = Field(..., description="The message to echo back.")


class EchoTool(BaseTool):
    name: str = "echo"
    description: str = "Echoes back the provided message. Used for testing."
    args_schema: Type[BaseModel] = EchoInput

    def _run(self, message: str) -> str:
        logger.info("EchoTool called with message length=%d", len(message))
        return f"Echo: {message}"
