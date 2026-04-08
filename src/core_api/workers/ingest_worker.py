"""
ARQ background worker for document ingestion.

Per D-01: documents are processed asynchronously via ARQ + Redis.
Per D-10: max_jobs=1 ensures documents are processed one at a time for GPU sequencing.
Per D-03: keep_result=3600 retains job results 1 hour for status polling.

Worker lifecycle:
  startup  → create HTTP client + Redis connection
  process_document → acquire GPU lock → call docproc HTTP → release lock → index via pipeline
  shutdown → close HTTP client + Redis connection
"""

import os

import httpx
import redis.asyncio as aioredis
from arq.connections import RedisSettings

from logging_config import get_logger
from rag.gpu_lock import acquire_gpu_lock, release_gpu_lock
from rag.pipeline import index_document

logger = get_logger(__name__)


async def startup(ctx: dict) -> None:
    """Initialise shared resources for the ARQ worker.

    Creates:
    - ctx["http_client"]: httpx.AsyncClient with 5-minute timeout for large doc uploads
    - ctx["redis"]: aioredis client for GPU lock operations
    """
    ctx["http_client"] = httpx.AsyncClient(timeout=300.0)
    ctx["redis"] = aioredis.from_url(
        f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}"
    )
    logger.info("Ingest worker started")


async def shutdown(ctx: dict) -> None:
    """Clean up shared resources on worker shutdown."""
    await ctx["http_client"].aclose()
    await ctx["redis"].aclose()
    logger.info("Ingest worker shut down")


async def process_document(
    ctx: dict,
    file_path: str,
    client_id: str,
    file_name: str,
) -> dict:
    """ARQ job: process a document through docproc and index into Qdrant.

    Steps:
    1. Acquire GPU lock (OCR in docproc runs on GPU — serialize with LLM inference)
    2. POST to docproc /process to extract text (and optionally run OCR)
    3. Release GPU lock in a finally block (always released even on error)
    4. Parse docproc response
    5. Index document pages into Qdrant via pipeline.index_document
    6. Return job result dict

    Args:
        ctx: ARQ context dict (populated by startup).
        file_path: Absolute path to the file inside the container (e.g. /app/uploads/doc.pdf).
        client_id: Client identifier for per-client Qdrant collection isolation.
        file_name: Original file name for metadata storage.

    Returns:
        {"status": "complete", "chunks": int, "file_name": str} on success.
        {"status": "error", "detail": str} on failure.
    """
    logger.info(
        "Processing document: file_name=%s client=%s", file_name, client_id
    )

    # Step 1: Acquire GPU lock (covers the docproc call where OCR uses GPU)
    acquired = await acquire_gpu_lock(ctx["redis"])
    if not acquired:
        logger.warning(
            "GPU lock timeout for file_name=%s client=%s", file_name, client_id
        )
        return {"status": "error", "detail": "GPU lock timeout"}

    docproc_url = os.getenv("DOCPROC_URL", "http://docproc:8001")

    try:
        # Step 2: Call docproc HTTP API to extract text (OCR runs here if needed)
        response = await ctx["http_client"].post(
            f"{docproc_url}/process",
            json={"file_path": file_path, "ocr_enabled": True},
        )
        resp_data = response.json()
    except Exception as exc:
        logger.error(
            "Docproc HTTP call failed for file_name=%s: %s", file_name, exc
        )
        return {"status": "error", "detail": f"docproc request failed: {exc}"}
    finally:
        # Step 3: Always release GPU lock after docproc call completes
        await release_gpu_lock(ctx["redis"])

    # Step 4: Parse docproc response
    if resp_data.get("status") != "success":
        detail = resp_data.get("detail", "docproc failed")
        logger.error(
            "Docproc returned non-success for file_name=%s: %s", file_name, detail
        )
        return {"status": "error", "detail": detail}

    # Step 5: Index document — embedding calls Ollama (CPU-bound), no GPU lock needed
    chunk_count = index_document(
        client_id=client_id,
        pages=resp_data["pages"],
        file_name=file_name,
    )

    # Step 6: Return success result
    logger.info(
        "Document processed: file_name=%s chunks=%d client=%s",
        file_name,
        chunk_count,
        client_id,
    )
    return {"status": "complete", "chunks": chunk_count, "file_name": file_name}


class WorkerSettings:
    """ARQ WorkerSettings — configures the ingest worker process.

    max_jobs=1:      Documents processed one at a time for GPU sequencing (D-12).
    job_timeout=600: 10-minute limit per document (large scanned PDFs are slow).
    keep_result=3600: Retain job results 1 hour for status polling (D-03).
    """

    functions = [process_document]
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 1
    job_timeout = 600
    keep_result = 3600
