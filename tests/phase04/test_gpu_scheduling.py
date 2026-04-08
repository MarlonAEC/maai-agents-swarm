"""Stub tests for DOCP-07 — GPU lock sequencing for inference workloads.

Covers:
  - GPU lock can be acquired and released correctly via the locking mechanism
  - GPU lock serializes concurrent GPU workloads (only one job runs at a time)

These stubs will be filled in by Plan 04 (GPU scheduling + ARQ worker).
"""
import pytest


@pytest.mark.xfail(reason="stub — implementation in Plan 04")
def test_gpu_lock_acquire_release():
    """GPU lock is acquired before inference and released after completion."""
    assert False


@pytest.mark.xfail(reason="stub — implementation in Plan 04")
def test_gpu_lock_serializes_workloads():
    """A second GPU workload waits until the first releases the lock before starting."""
    assert False
