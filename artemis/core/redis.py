"""Centralized Redis connection pool — single pool reused everywhere."""

import asyncio
import os

import redis.asyncio as aioredis

from artemis.core.config import settings

# Map event loop → Redis pool. Each Celery task runs in a fresh event loop
# (asyncio.run() creates one per call), and aioredis connections are bound to
# the loop they were created on. Reusing a pool across loops causes
# "Event loop is closed" / "Future attached to a different loop" errors.
# Keying by id(loop) gives each loop its own pool while avoiding leaks
# (closed loops can be cleaned up if needed; the dict stays small in practice).
_pools: dict[int, aioredis.Redis] = {}

# Detect Celery context the same way core/database.py does
_in_celery = bool(os.environ.get("CELERY_WORKER")) or any("celery" in arg.lower() for arg in os.sys.argv)


async def get_redis() -> aioredis.Redis:
    """Get a Redis client bound to the current event loop."""
    if _in_celery:
        loop_id = id(asyncio.get_running_loop())
        pool = _pools.get(loop_id)
        if pool is None:
            pool = aioredis.from_url(settings.redis_url, decode_responses=True)
            _pools[loop_id] = pool
        return pool

    # Long-lived service (internal-api): single shared pool is fine.
    if 0 not in _pools:
        _pools[0] = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _pools[0]
