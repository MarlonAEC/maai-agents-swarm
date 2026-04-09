"""
MAAI Agent Pipeline — Manifold pipe plugin for Open WebUI.

Routes all chat messages through the Core API's CrewAI freeform agent.
Appears as "MAAI Agent: Chat" in the Open WebUI model dropdown.

File upload flow:
  Open WebUI does NOT pass file metadata to pipes (body has no "files" key).
  Instead, it processes files with its own RAG and injects text into the message.

  To trigger our Qdrant-based ingestion, the pipe:
  1. Scans Open WebUI's uploads dir (mounted read-only at /app/webui-data/uploads/)
  2. Finds recently uploaded files (last 60s)
  3. Copies them to /app/uploads (shared maai-uploads volume)
  4. Calls POST /ingest on Core API to queue ARQ job
"""
from typing import Optional, Union, Generator, Iterator
from pydantic import BaseModel, Field
import httpx
import os
import logging
import time
import shutil
import glob as globmod
import re

# Logger setup (Pipelines server runs this file directly, not as a package)
logger = logging.getLogger("maai_pipe")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

# Track files we've already ingested to avoid re-processing
_ingested_files: set[str] = set()

# Supported file extensions for ingestion
_SUPPORTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


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
        self.type = "manifold"
        self.valves = self.Valves()
        self.pipelines = [
            {"id": "chat", "name": "Chat"},
        ]
        logger.info("MAAI Agent pipeline initialized (type=manifold)")

    async def on_startup(self):
        """Called when Pipelines server starts."""
        logger.info("MAAI Agent pipeline starting, Core API URL: %s", self.valves.CORE_API_URL)

    async def on_shutdown(self):
        """Called when Pipelines server shuts down."""
        logger.info("MAAI Agent pipeline shutting down")

    def _detect_ingest_intent(self, user_message: str) -> bool:
        """Check if the user wants to index/ingest a document."""
        ingest_keywords = [
            "index", "ingest", "process this", "add to knowledge",
            "store this document", "upload and index", "index this",
        ]
        lower = user_message.lower()
        return any(kw in lower for kw in ingest_keywords)

    def _find_new_webui_files(self, max_age_seconds: int = 120) -> list[str]:
        """Find recently uploaded files in Open WebUI's uploads directory.

        Open WebUI stores files at /app/webui-data/uploads/{uuid}_{filename}.
        Returns list of full paths to files newer than max_age_seconds.
        """
        webui_uploads = "/app/webui-data/uploads"
        if not os.path.isdir(webui_uploads):
            logger.warning("Open WebUI uploads dir not found: %s", webui_uploads)
            return []

        now = time.time()
        new_files = []
        for entry in os.listdir(webui_uploads):
            filepath = os.path.join(webui_uploads, entry)
            if not os.path.isfile(filepath):
                continue
            ext = os.path.splitext(entry)[1].lower()
            if ext not in _SUPPORTED_EXTS:
                continue
            # Check if recently created
            try:
                mtime = os.path.getmtime(filepath)
                if (now - mtime) < max_age_seconds and filepath not in _ingested_files:
                    new_files.append(filepath)
            except OSError:
                continue

        return new_files

    def _copy_and_ingest(self, webui_files: list[str]) -> list[str]:
        """Copy files from webui storage to shared volume and trigger ingestion.

        Returns list of human-readable status strings.
        """
        upload_dir = "/app/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        results = []

        for src_path in webui_files:
            original_name = os.path.basename(src_path)
            # Strip UUID prefix from filename (format: {uuid}_{filename})
            # e.g., "64d11d6d-7882-459f-8083-8acbec592b2c_AI_Course.pdf" → "AI_Course.pdf"
            parts = original_name.split("_", 1)
            display_name = parts[1] if len(parts) > 1 else original_name
            saved_name = f"{int(time.time())}_{display_name}"
            dst_path = os.path.join(upload_dir, saved_name)

            try:
                shutil.copy2(src_path, dst_path)
                logger.info("Copied %s → %s", src_path, dst_path)
            except Exception as e:
                logger.error("Failed to copy %s: %s", src_path, e)
                results.append(f"**{display_name}**: Copy failed — {e}")
                continue

            # Mark as ingested to avoid re-processing
            _ingested_files.add(src_path)

            # Call /ingest
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{self.valves.CORE_API_URL}/ingest",
                        json={"file_name": saved_name},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        job_id = data.get("job_id", "unknown")
                        results.append(
                            f"**{display_name}**: Queued for processing (Job ID: `{job_id}`)"
                        )
                        logger.info("Ingest queued: %s → job_id=%s", display_name, job_id)
                    else:
                        detail = ""
                        try:
                            detail = resp.json().get("detail", resp.text)
                        except Exception:
                            detail = resp.text
                        results.append(f"**{display_name}**: Could not queue — {detail}")
                        logger.warning("Ingest failed: %s → %d %s", saved_name, resp.status_code, detail)
            except Exception as e:
                results.append(f"**{display_name}**: Ingestion error — {e}")
                logger.error("Ingest error for %s: %s", saved_name, e)

        return results

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
        When the user requests document indexing, also scans for recently
        uploaded files in Open WebUI's storage and triggers ingestion.
        """
        logger.info(
            "Pipe called: user_message length=%d, messages=%d, body keys=%s",
            len(user_message), len(messages), list(body.keys()),
        )

        # --- Check for file ingestion intent ---
        wants_ingest = self._detect_ingest_intent(user_message)
        ingest_results = []

        if wants_ingest:
            new_files = self._find_new_webui_files(max_age_seconds=300)
            if new_files:
                logger.info("Found %d new files to ingest: %s", len(new_files), [os.path.basename(f) for f in new_files])
                ingest_results = self._copy_and_ingest(new_files)
            else:
                logger.info("Ingest requested but no new files found in webui uploads")

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
            logger.info("Core API response received, length=%d", len(agent_response))

        except httpx.TimeoutException:
            logger.error("Core API request timed out")
            agent_response = "I'm sorry, the request timed out. The model may be loading or processing a complex request. Please try again."
        except httpx.HTTPStatusError as e:
            logger.error("Core API returned error: %s - %s", e.response.status_code, e.response.text)
            agent_response = f"I encountered an error processing your request. (HTTP {e.response.status_code})"
        except Exception as e:
            logger.error("Unexpected error calling Core API: %s", e)
            agent_response = "I'm sorry, I encountered an unexpected error. Please try again."

        # --- Append ingestion results if files were processed ---
        if ingest_results:
            agent_response += "\n\n---\n**Document Ingestion:**\n" + "\n".join(f"- {r}" for r in ingest_results)
            agent_response += '\n\nYou can ask about your documents once processing completes, or check status by asking "what\'s the status of my document?"'

        return agent_response
