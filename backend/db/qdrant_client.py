"""
NexusIQ — Async Qdrant client singleton + FastAPI dependency.
"""
from typing import Optional

from loguru import logger
from qdrant_client import AsyncQdrantClient

from core.config import settings

_qdrant_client: Optional[AsyncQdrantClient] = None


async def get_qdrant_client() -> AsyncQdrantClient:
    """
    Returns the shared async Qdrant client.
    Creates it on first call (lazy init).
    """
    global _qdrant_client
    if _qdrant_client is None:
        kwargs = {"url": settings.QDRANT_URL}
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
        _qdrant_client = AsyncQdrantClient(**kwargs)
        logger.info(f"[qdrant] Connected to {settings.QDRANT_URL}")
    return _qdrant_client


async def close_qdrant() -> None:
    """Call on app shutdown."""
    global _qdrant_client
    if _qdrant_client:
        await _qdrant_client.close()
        _qdrant_client = None
        logger.info("[qdrant] Connection closed")
