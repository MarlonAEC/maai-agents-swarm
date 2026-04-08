"""Ingest router — POST /ingest endpoint for queueing document processing jobs."""

import os
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request body for POST /ingest."""

    file_name: str  # Relative filename in /app/uploads/
    client_id: str | None = None  # Defaults to CLIENT_ID env var


class IngestResponse(BaseModel):
    """Response body for POST /ingest."""

    job_id: str
    status: str
    message: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """Queue a document for background processing via ARQ.

    Per D-01: Returns immediately with job ID. Background worker handles
    Docling -> LlamaIndex -> Qdrant pipeline.
    Per Pitfall 3: file_path uses container path /app/uploads/, not host path.
    """
    client_id = request.client_id or os.getenv("CLIENT_ID", "default")
    file_path = f"/app/uploads/{request.file_name}"

    # Validate file exists (inside container)
    if not Path(file_path).exists():
        raise HTTPException(
            status_code=404, detail=f"File not found: {request.file_name}"
        )

    # Validate supported extension per D-04
    valid_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    ext = Path(request.file_name).suffix.lower()
    if ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {ext}. "
                f"Supported: {', '.join(sorted(valid_extensions))}"
            ),
        )

    redis = await create_pool(
        RedisSettings(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
        )
    )
    try:
        job = await redis.enqueue_job(
            "process_document",
            file_path,
            client_id,
            request.file_name,
        )
        job_id = job.job_id
    finally:
        await redis.close()

    logger.info(
        "Queued ingestion job=%s file=%s client=%s", job_id, request.file_name, client_id
    )
    return IngestResponse(
        job_id=job_id,
        status="queued",
        message=f"Document '{request.file_name}' queued for processing. Job ID: {job_id}",
    )
