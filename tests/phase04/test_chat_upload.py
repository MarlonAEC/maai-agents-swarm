"""
Tests for DOCP-06 (chat upload + ingest trigger) — Plan 03 implementation.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


def test_ingest_skill_uses_call_ingest_tool():
    """The document_ingest skill lists call_ingest in its tools configuration (per D-02)."""
    skill_path = (
        Path(__file__).resolve().parent.parent.parent
        / "clients"
        / "default"
        / "skills"
        / "document_ingest.yaml"
    )
    assert skill_path.exists(), f"document_ingest.yaml not found at {skill_path}"

    skill_def = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
    assert skill_def["name"] == "document_ingest"
    assert "call_ingest" in skill_def["tools"], (
        f"call_ingest not in tools: {skill_def['tools']}"
    )


def test_call_ingest_tool_name():
    """CallIngestTool has the correct tool name for registry discovery."""
    from tools.call_ingest_tool import CallIngestTool

    tool = CallIngestTool()
    assert tool.name == "call_ingest"


def test_job_status_tool_name():
    """JobStatusTool has the correct tool name for registry discovery."""
    from tools.job_status_tool import JobStatusTool

    tool = JobStatusTool()
    assert tool.name == "job_status"


def test_ingest_endpoint_queues_job():
    """POST /ingest accepts a file_name and enqueues an ARQ process_document job."""
    import sys

    # Ensure sys.path includes core_api for FastAPI app import
    core_api_dir = str(
        Path(__file__).resolve().parent.parent.parent / "src" / "core_api"
    )
    if core_api_dir not in sys.path:
        sys.path.insert(0, core_api_dir)

    from fastapi.testclient import TestClient

    # Mock arq create_pool, Path.exists, and the job object
    mock_job = MagicMock()
    mock_job.job_id = "test-job-id-12345"

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock(return_value=mock_job)
    mock_redis.close = AsyncMock()

    mock_create_pool = AsyncMock(return_value=mock_redis)

    with (
        patch("routers.ingest.create_pool", mock_create_pool),
        patch("routers.ingest.Path.exists", return_value=True),
    ):
        from routers.ingest import router
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)
        client = TestClient(test_app)

        response = client.post(
            "/ingest",
            json={"file_name": "report.pdf", "client_id": "test_client"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["job_id"] == "test-job-id-12345"
    assert data["status"] == "queued"


def test_ingest_skill_triggers_arq():
    """The document_ingest skill's call_ingest tool references the /ingest endpoint."""
    from tools.call_ingest_tool import CallIngestTool

    # Verify the tool POSTs to /ingest (inspect the source via string check)
    import inspect

    source = inspect.getsource(CallIngestTool._run)
    assert "/ingest" in source, "CallIngestTool._run must reference /ingest endpoint"
