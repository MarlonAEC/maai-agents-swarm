"""
Stub tests for DOCP-06 (chat upload + ingest trigger).

These stubs will be filled in by Plan 03 (upload endpoint and ARQ job enqueue).
"""

import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 03 (upload endpoint)")
def test_ingest_endpoint_queues_job():
    """POST /ingest accepts a file upload and enqueues an ARQ process_document job."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 03 (upload endpoint)")
def test_ingest_skill_triggers_arq():
    """The ingest skill triggers an ARQ job and returns a job_id for status polling."""
    assert False
