"""
NexusIQ — Supabase Storage client (FREE, no credit card needed!)
Replaces MinIO completely. Sign up at https://supabase.com
"""
from supabase import create_client, Client
from core.config import settings
import asyncio
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def get_minio_client():
    """Named get_minio_client() to avoid changing imports elsewhere."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_supabase_client)
