"""
MAAI Agent Pipeline — Manifold pipe plugin for Open WebUI.

Routes all chat messages through the Core API's CrewAI freeform agent.
Appears as "MAAI Agent: Chat" in the Open WebUI model dropdown.
"""
from typing import Optional, Union, Generator, Iterator
from pydantic import BaseModel, Field
import httpx
import os
import logging
import time

# Logger setup (Pipelines server runs this file directly, not as a package)
logger = logging.getLogger("maai_pipe")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)


class Pipeline:
    """MAAI Agent manifold pipe — forwards messages to Core API and returns agent response."""

    class Valves(BaseModel):
        """Configurable settings exposed in Open WebUI admin UI."""
        CORE_API_URL: str = Field(
            default="http://core-api:8000",
            description="Base URL of the MAAI Core API service",
        )
        REQUEST_TIMEOUT: float = Field(
            default=120.0,
            description="Timeout in seconds for Core API requests (agent inference can be slow on CPU)",
        )

    def __init__(self):
        self.name = "MAAI Agent: "
        self.type = "manifold"  # manifold type exposes pipelines[] as selectable models in Open WebUI
        self.valves = self.Valves()
        # Pipelines server reads this list to register models on /models endpoint
        # Name format: pipeline.name is prepended, so keep sub-name descriptive
        self.pipelines = [
            {"id": "chat", "name": "Chat"},
        ]
        logger.info("MAAI Agent pipeline initialized (type=manifold)")

    async def on_startup(self):
        """Called when Pipelines server starts."""
        logger.info(f"MAAI Agent pipeline starting, Core API URL: {self.valves.CORE_API_URL}")

    async def on_shutdown(self):
        """Called when Pipelines server shuts down."""
        logger.info("MAAI Agent pipeline shutting down")

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: list,
        body: dict,
    ) -> str:
        """
        Main pipe handler — called synchronously by the Pipelines server
        for every chat message routed to this manifold.

        Forwards the full message history to Core API's /chat endpoint.
        """
        logger.info(f"Pipe called: user_message length={len(user_message)}, messages={len(messages)}")

        # --- Handle file uploads ---
        files_info = body.get("files", [])
        file_acknowledgments = []
        if files_info:
            upload_dir = "/app/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            for file_entry in files_info:
                filename = "unknown"
                if isinstance(file_entry, dict):
                    filename = file_entry.get("filename", file_entry.get("name", "unknown"))
                    file_data = file_entry.get("data", file_entry.get("content"))
                    if file_data and filename != "unknown":
                        filepath = os.path.join(upload_dir, f"{int(time.time())}_{filename}")
                        try:
                            if isinstance(file_data, str):
                                import base64
                                with open(filepath, "wb") as f:
                                    f.write(base64.b64decode(file_data))
                            elif isinstance(file_data, bytes):
                                with open(filepath, "wb") as f:
                                    f.write(file_data)
                            logger.info(f"File saved: {filepath}")
                        except Exception as e:
                            logger.error(f"Failed to save file {filename}: {e}")
                file_acknowledgments.append(filename)

        # --- Forward full message history to Core API ---
        payload = {
            "messages": [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in messages
            ],
            "user_message": user_message,
        }

        try:
            with httpx.Client(timeout=self.valves.REQUEST_TIMEOUT) as client:
                response = client.post(
                    f"{self.valves.CORE_API_URL}/chat",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

            agent_response = result.get("response", "No response from agent.")
            logger.info(f"Core API response received, length={len(agent_response)}")

        except httpx.TimeoutException:
            logger.error("Core API request timed out")
            agent_response = "I'm sorry, the request timed out. The model may be loading or processing a complex request. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error(f"Core API returned error: {e.response.status_code} - {e.response.text}")
            agent_response = f"I encountered an error processing your request. (HTTP {e.response.status_code})"
        except Exception as e:
            logger.error(f"Unexpected error calling Core API: {e}")
            agent_response = "I'm sorry, I encountered an unexpected error. Please try again."

        # --- Append file acknowledgment if files were uploaded ---
        if file_acknowledgments:
            file_list = ", ".join(file_acknowledgments)
            agent_response += f"\n\n---\n**File received:** {file_list}. Document processing will be available in a future update."

        return agent_response
