"""
NexusIQ — Async retry decorator.
Used by LLMRouter.invoke() to retry transient LLM failures.
"""
import asyncio
import functools
from loguru import logger


def with_retry(max_attempts: int = 5, base_delay: float = 1.0):
    """
    Decorator that retries an async function up to max_attempts times
    with exponential back-off (base_delay * 2^attempt).

    Re-raises the last exception if all attempts are exhausted.
    Does NOT retry on non-transient errors (but LLMRouter marks those
    as rate-limits and re-raises, so the distinction is handled there).
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"[retry] {fn.__name__} attempt {attempt + 1}/{max_attempts} "
                            f"failed: {exc}. Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"[retry] {fn.__name__} failed after {max_attempts} attempts: {exc}"
                        )
            raise last_exc
        return wrapper
    return decorator
