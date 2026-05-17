"""
NexusIQ — Async Redis client singleton + FastAPI dependency.
"""
from typing import Optional

import redis.asyncio as aioredis
from loguru import logger

from core.config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """
    Returns the shared async Redis client.
    Creates it on first call (lazy init).
    Safe to call from both FastAPI dependencies and agent code.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"[redis] Connected to {settings.REDIS_URL}")
    return _redis_client


async def close_redis() -> None:
    """Call on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("[redis] Connection closed")
