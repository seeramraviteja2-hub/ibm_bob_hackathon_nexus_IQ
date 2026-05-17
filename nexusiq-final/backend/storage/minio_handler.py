"""
NexusIQ — Supabase Storage handler (replaces MinIO).
All method signatures identical so no other code changes needed.
"""
import asyncio
from loguru import logger
from exceptions.base import StorageException

class MinIOHandler:
    """Drop-in Supabase replacement for MinIO."""
    def __init__(self, client) -> None:
        self._client = client

    def _run(self, fn):
        """Run sync Supabase SDK call in thread pool."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, fn)

    async def upload_file(self, bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        try:
            await self._run(lambda: self._client.storage.from_(bucket).upload(
                path=object_name,
                file=data,
                file_options={"content-type": content_type, "upsert": "true"}
            ))
            logger.debug(f"[supabase] Uploaded {object_name} → {bucket}")
            return object_name
        except Exception as exc:
            raise StorageException(f"Upload failed for {object_name}: {exc}") from exc

    async def download_file(self, bucket: str, object_name: str) -> bytes:
        try:
            result = await self._run(lambda: self._client.storage.from_(bucket).download(object_name))
            return result
        except Exception as exc:
            raise StorageException(f"Download failed for {object_name}: {exc}") from exc

    async def delete_file(self, bucket: str, object_name: str) -> None:
        try:
            await self._run(lambda: self._client.storage.from_(bucket).remove([object_name]))
        except Exception as exc:
            raise StorageException(f"Delete failed for {object_name}: {exc}") from exc
