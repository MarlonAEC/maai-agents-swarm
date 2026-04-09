"""
MAAI Agent Pipeline — Manifold pipe plugin for Open WebUI.

Routes all chat messages through the Core API's CrewAI freeform agent.
Appears as "MAAI Agent: Chat" in the Open WebUI model dropdown.

File upload flow:
  1. User uploads file in Open WebUI → Open WebUI stores it and passes metadata to pipe
  2. Pipe downloads file from Open WebUI's file API → saves to /app/uploads (shared volume)
  3. Pipe calls POST /ingest on Core API → ARQ job queued for docproc + Qdrant indexing
  4. Pipe appends ingestion status to the agent response
"""
from typing import Optional, Union, Generator, Iterator
from pydantic import BaseModel, Field
import httpx
import os
import logging
import time
import json

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
        WEBUI_URL: str = Field(
            default="http://open-webui:8080",
            description="Internal URL of Open WebUI (for file downloads)",
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

    def _extract_and_save_files(self, body: dict) -> list[dict]:
        """Extract uploaded files from the Open WebUI body and save to shared volume.

        Open WebUI passes file metadata in body["files"] — the actual bytes are
        in Open WebUI's storage, accessible via its file API.

        Returns list of dicts: [{"original_name": str, "saved_name": str, "ok": bool, "error": str|None}]
        """
        files_info = body.get("files", [])
        if not files_info:
            return []

        logger.info("Files detected in body: %s", json.dumps(files_info, default=str)[:500])

        upload_dir = "/app/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        results = []

        # Supported extensions for ingestion
        supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

        for file_entry in files_info:
            if not isinstance(file_entry, dict):
                logger.warning("Unexpected file entry type: %s", type(file_entry))
                continue

            # Open WebUI file format: {"type": "file", "id": "...", "filename": "...", "url": "...", ...}
            # Some versions use "name" instead of "filename"
            filename = file_entry.get("filename") or file_entry.get("name") or "unknown"
            file_id = file_entry.get("id", "")
            file_url = file_entry.get("url", "")

            # Check if this is a supported file type
            ext = os.path.splitext(filename)[1].lower()
            if ext not in supported_exts:
                logger.info("Skipping unsupported file type: %s (%s)", filename, ext)
                results.append({"original_name": filename, "saved_name": "", "ok": False, "error": f"Unsupported type: {ext}"})
                continue

            saved_name = f"{int(time.time())}_{filename}"
            filepath = os.path.join(upload_dir, saved_name)
            file_bytes = None

            # Strategy 1: Raw data in the entry (legacy/custom format)
            raw_data = file_entry.get("data") or file_entry.get("content")
            if raw_data:
                try:
                    if isinstance(raw_data, str):
                        import base64
                        file_bytes = base64.b64decode(raw_data)
                    elif isinstance(raw_data, bytes):
                        file_bytes = raw_data
                except Exception as e:
                    logger.warning("Failed to decode inline file data for %s: %s", filename, e)

            # Strategy 2: Download from Open WebUI file API using file_id
            if file_bytes is None and file_id:
                try:
                    api_url = f"{self.valves.WEBUI_URL}/api/v1/files/{file_id}/content"
                    logger.info("Downloading file from Open WebUI: %s", api_url)
                    with httpx.Client(timeout=60.0) as dl_client:
                        resp = dl_client.get(api_url)
                        if resp.status_code == 200:
                            file_bytes = resp.content
                            logger.info("Downloaded %d bytes for %s", len(file_bytes), filename)
                        else:
                            logger.warning("Open WebUI file API returned %d for %s", resp.status_code, filename)
                except Exception as e:
                    logger.warning("Failed to download file %s from Open WebUI: %s", filename, e)

            # Strategy 3: Download from URL if provided
            if file_bytes is None and file_url and file_url.startswith("http"):
                try:
                    logger.info("Downloading file from URL: %s", file_url[:200])
                    with httpx.Client(timeout=60.0) as dl_client:
                        resp = dl_client.get(file_url)
                        if resp.status_code == 200:
                            file_bytes = resp.content
                            logger.info("Downloaded %d bytes for %s from URL", len(file_bytes), filename)
                except Exception as e:
                    logger.warning("Failed to download file %s from URL: %s", filename, e)

            # Save to shared volume
            if file_bytes:
                try:
                    with open(filepath, "wb") as f:
                        f.write(file_bytes)
                    logger.info("File saved: %s (%d bytes)", filepath, len(file_bytes))
                    results.append({"original_name": filename, "saved_name": saved_name, "ok": True, "error": None})
                except Exception as e:
                    logger.error("Failed to save file %s: %s", filename, e)
                    results.append({"original_name": filename, "saved_name": "", "ok": False, "error": str(e)})
            else:
                logger.warning(
                    "Could not obtain file bytes for %s (id=%s, url=%s, has_data=%s)",
                    filename, file_id, bool(file_url), bool(raw_data),
                )
                results.append({"original_name": filename, "saved_name": "", "ok": False, "error": "Could not obtain file content"})

        return results

    def _trigger_ingestion(self, saved_files: list[dict]) -> list[str]:
        """Call /ingest on Core API for each successfully saved file.

        Returns list of human-readable status strings.
        """
        ingest_results = []
        for f in saved_files:
            if not f["ok"]:
                ingest_results.append(f"**{f['original_name']}**: Skipped — {f['error']}")
                continue

            try:
                with httpx.Client(timeout=30.0) as ingest_client:
                    resp = ingest_client.post(
                        f"{self.valves.CORE_API_URL}/ingest",
                        json={"file_name": f["saved_name"]},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        job_id = data.get("job_id", "unknown")
                        ingest_results.append(
                            f"**{f['original_name']}**: Queued for processing (Job ID: `{job_id}`)"
                        )
                        logger.info("Ingest queued: %s job_id=%s", f["saved_name"], job_id)
                    else:
                        detail = ""
                        try:
                            detail = resp.json().get("detail", resp.text)
                        except Exception:
                            detail = resp.text
                        ingest_results.append(f"**{f['original_name']}**: Could not queue — {detail}")
                        logger.warning("Ingest failed for %s: %d %s", f["saved_name"], resp.status_code, detail)
            except Exception as e:
                ingest_results.append(f"**{f['original_name']}**: Ingestion error — {e}")
                logger.error("Ingest error for %s: %s", f["saved_name"], e)

        return ingest_results

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
        logger.info(
            "Pipe called: user_message length=%d, messages=%d, body keys=%s",
            len(user_message), len(messages), list(body.keys()),
        )

        # --- Handle file uploads ---
        saved_files = self._extract_and_save_files(body)

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

        # --- Trigger document ingestion for uploaded files ---
        if saved_files:
            ingest_results = self._trigger_ingestion(saved_files)
            if ingest_results:
                agent_response += "\n\n---\n**Document Ingestion:**\n" + "\n".join(f"- {r}" for r in ingest_results)
                agent_response += '\n\nYou can ask about your documents once processing completes, or check status by asking "what\'s the status of my document?"'

        return agent_response
