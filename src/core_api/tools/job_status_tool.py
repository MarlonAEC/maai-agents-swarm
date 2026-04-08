"""Job status tool — checks the status of a background document processing job."""

import asyncio
import os
from typing import Type

from arq.connections import RedisSettings, create_pool
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from logging_config import get_logger

logger = get_logger(__name__)


class JobStatusInput(BaseModel):
    """Input schema for JobStatusTool."""

    job_id: str = Field(
        ...,
        description="The job ID returned when the document was submitted for processing.",
    )


class JobStatusTool(BaseTool):
    name: str = "job_status"
    description: str = (
        "Check the processing status of a document ingestion job. "
        "Provide the job ID that was returned when the document was submitted."
    )
    args_schema: Type[BaseModel] = JobStatusInput

    def _run(self, job_id: str) -> str:
        logger.info("JobStatusTool checking job_id=%s", job_id)
        try:
            result = asyncio.run(self._check_status(job_id))
            return result
        except Exception as exc:
            logger.error("Job status check failed: %s", exc)
            return f"Error checking job status: {exc}"

    async def _check_status(self, job_id: str) -> str:
        redis = await create_pool(
            RedisSettings(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
            )
        )
        try:
            from arq.jobs import Job

            j = Job(job_id=job_id, redis=redis)
            info = await j.info()
            if info is None:
                return f"Job {job_id}: not found (may have expired or invalid ID)"
            status = info.status if hasattr(info, "status") else "unknown"
            result = info.result if hasattr(info, "result") else None
            if result and isinstance(result, dict):
                if result.get("status") == "complete":
                    return (
                        f"Job {job_id}: Complete — {result.get('chunks', '?')} chunks indexed "
                        f"from {result.get('file_name', 'unknown')}"
                    )
                elif result.get("status") == "error":
                    return f"Job {job_id}: Failed — {result.get('detail', 'unknown error')}"
            return f"Job {job_id}: {status}"
        finally:
            await redis.close()
