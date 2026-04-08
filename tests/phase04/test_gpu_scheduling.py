"""
Tests for DOCP-07 (GPU lock sequencing).

Covers:
- acquire_gpu_lock returns True on successful Redis SET NX PX
- acquire_gpu_lock returns False after exhausting retries (Redis always returns None)
- release_gpu_lock deletes the correct Redis key
- Lock key and TTL are set correctly on acquire
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_gpu_lock_acquire_success():
    """acquire_gpu_lock returns True when Redis SET NX PX succeeds."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    from rag.gpu_lock import acquire_gpu_lock

    result = await acquire_gpu_lock(mock_redis, max_retries=3, retry_delay=0.0)

    assert result is True
    # SET must have been called at least once
    mock_redis.set.assert_called()
    # Verify NX and px (TTL) are set for atomic acquire-with-expiry
    call_kwargs = mock_redis.set.call_args.kwargs
    assert call_kwargs.get("nx") is True
    assert "px" in call_kwargs


@pytest.mark.asyncio
async def test_gpu_lock_acquire_timeout():
    """acquire_gpu_lock returns False when Redis SET NX always fails (lock held by another)."""
    mock_redis = AsyncMock()
    # Redis returns None when SET NX fails (key already exists)
    mock_redis.set = AsyncMock(return_value=None)

    with patch("rag.gpu_lock.asyncio.sleep", new_callable=AsyncMock):
        from rag.gpu_lock import acquire_gpu_lock

        result = await acquire_gpu_lock(mock_redis, max_retries=2, retry_delay=0.01)

    assert result is False
    # Must have tried exactly max_retries times
    assert mock_redis.set.call_count == 2


@pytest.mark.asyncio
async def test_gpu_lock_release():
    """release_gpu_lock calls redis.delete with the correct lock key."""
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)

    from rag.gpu_lock import GPU_LOCK_KEY, release_gpu_lock

    await release_gpu_lock(mock_redis)

    mock_redis.delete.assert_called_once_with(GPU_LOCK_KEY)
    assert GPU_LOCK_KEY == "maai:gpu_lock"


@pytest.mark.asyncio
async def test_gpu_lock_serializes_workloads():
    """GPU lock key is 'maai:gpu_lock' and TTL is explicitly set on acquire.

    This ensures that a crashed process cannot hold the lock indefinitely —
    the px (TTL in ms) parameter causes Redis to auto-expire the key.
    """
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    from rag.gpu_lock import GPU_LOCK_KEY, GPU_LOCK_TTL_MS, acquire_gpu_lock

    await acquire_gpu_lock(mock_redis, max_retries=1, retry_delay=0.0)

    call_kwargs = mock_redis.set.call_args.kwargs
    # Verify the key and TTL
    assert mock_redis.set.call_args.args[0] == GPU_LOCK_KEY
    assert call_kwargs.get("px") == GPU_LOCK_TTL_MS
    # TTL must be substantial (>= 60 seconds = 60000 ms) to cover slow OCR
    assert GPU_LOCK_TTL_MS >= 60_000
