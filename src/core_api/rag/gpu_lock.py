"""
Redis-based GPU semaphore to prevent concurrent GPU workloads.

Per D-12: Only one GPU workload (LLM inference or OCR) runs at a time.
Per D-13: Chat (LLM inference) has priority — worker retries patiently.

The lock is implemented as a Redis SET NX PX key: atomic acquire with a
TTL so a crashed process never holds the lock indefinitely.
"""

import asyncio

import redis.asyncio as aioredis

from logging_config import get_logger

logger = get_logger(__name__)

GPU_LOCK_KEY = "maai:gpu_lock"
GPU_LOCK_TTL_MS = 120_000  # 2 minutes max hold time (large scanned PDFs are slow)


async def acquire_gpu_lock(
    redis_client: aioredis.Redis,
    ttl_ms: int = GPU_LOCK_TTL_MS,
    max_retries: int = 30,
    retry_delay: float = 1.0,
) -> bool:
    """Try to acquire the GPU lock with retries.

    Uses SET NX PX for atomic acquire-with-TTL so a crashed process
    never holds the lock indefinitely (D-12).

    Per D-13, the worker retries patiently (max_retries=30, 1s delay = 30s
    total wait) so that chat LLM inference (which also sets this lock) can
    complete without being starved.

    Args:
        redis_client: Async Redis client.
        ttl_ms: Lock TTL in milliseconds. Defaults to GPU_LOCK_TTL_MS (2 min).
        max_retries: Maximum acquire attempts before giving up.
        retry_delay: Seconds to wait between attempts.

    Returns:
        True if the lock was acquired, False if all retries were exhausted.
    """
    for attempt in range(max_retries):
        result = await redis_client.set(GPU_LOCK_KEY, "1", nx=True, px=ttl_ms)
        if result is True:
            logger.info("GPU lock acquired (attempt %d)", attempt + 1)
            return True
        await asyncio.sleep(retry_delay)
    logger.warning("GPU lock not acquired after %d retries", max_retries)
    return False


async def release_gpu_lock(redis_client: aioredis.Redis) -> None:
    """Release the GPU lock by deleting the Redis key."""
    await redis_client.delete(GPU_LOCK_KEY)
    logger.info("GPU lock released")
