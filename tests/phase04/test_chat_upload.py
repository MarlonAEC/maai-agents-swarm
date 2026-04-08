"""Stub tests for DOCP-06 — chat upload and ingest trigger.

Covers:
  - POST /ingest endpoint accepts a file upload and queues an ARQ background job
  - ingest_documents skill triggers the ARQ queue job via Core API

These stubs will be filled in by Plan 03 (RAG query skill + Core API integration).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 03")
def test_ingest_endpoint_queues_job():
    """POST /ingest queues an ARQ job and returns a job_id in the response."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 03")
def test_ingest_skill_triggers_arq():
    """ingest_documents skill calls the /ingest endpoint and reports queued job_id."""
    assert False
