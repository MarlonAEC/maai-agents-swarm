"""Call ingest tool — queues a document for background processing via the /ingest endpoint.

Per D-02: The document_ingest skill uses this tool to queue the ARQ job.
The skill itself triggers the job through this tool.
"""

import os
from typing import Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from logging_config import get_logger

logger = get_logger(__name__)


class CallIngestInput(BaseModel):
    """Input schema for CallIngestTool."""

    file_name: str = Field(
        ...,
        description=(
            "The name of the file to ingest (must already be uploaded to the uploads directory)."
        ),
    )


class CallIngestTool(BaseTool):
    name: str = "call_ingest"
    description: str = (
        "Queue a document for background processing and indexing into the knowledge base. "
        "Provide the file name of an uploaded document. Returns a job ID for status tracking."
    )
    args_schema: Type[BaseModel] = CallIngestInput

    def _run(self, file_name: str) -> str:
        client_id = os.getenv("CLIENT_ID", "default")
        # POST to the local /ingest endpoint (same core-api process)
        ingest_url = f"http://localhost:{os.getenv('CORE_API_PORT', '8000')}/ingest"
        logger.info("CallIngestTool file_name=%s client=%s", file_name, client_id)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    ingest_url,
                    json={"file_name": file_name, "client_id": client_id},
                )
                resp.raise_for_status()
                data = resp.json()
                job_id = data.get("job_id", "unknown")
                logger.info("Ingest job queued: job_id=%s file=%s", job_id, file_name)
                return (
                    f"Document '{file_name}' has been queued for processing.\n"
                    f"Job ID: {job_id}\n"
                    f"You can check the status by asking: 'What is the status of job {job_id}?'"
                )
        except httpx.HTTPStatusError as exc:
            detail = (
                exc.response.json().get("detail", str(exc)) if exc.response else str(exc)
            )
            logger.error("Ingest failed: %s", detail)
            return f"Failed to queue document: {detail}"
        except Exception as exc:
            logger.error("Ingest tool error: %s", exc)
            return f"Error queuing document: {exc}"
