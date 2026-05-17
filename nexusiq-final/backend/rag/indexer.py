"""
NexusIQ — Qdrant indexer.
Embeds CodeChunk objects and upserts them into a per-session Qdrant collection.
"""
import hashlib
import uuid
from loguru import logger

from qdrant_client.http.models import Distance, VectorParams, PointStruct

from rag.parser import CodeChunk
from exceptions.base import AgentExecutionException

EMBEDDING_MODEL = "models/embedding-001"   # Must match RotatingEmbedder in llm_router
VECTOR_SIZE     = 768                       # embedding-001 output dimension
COLLECTION_NAME = "nexusiq_code"


class QdrantIndexer:
    """
    Embeds and upserts code chunks into Qdrant.
    Each chunk is stored with its session_id so retrievals are scoped per session.
    """

    def __init__(self, qdrant_client, embedder) -> None:
        self._qdrant   = qdrant_client
        self._embedder = embedder

    async def _ensure_collection(self) -> None:
        try:
            await self._qdrant.get_collection(COLLECTION_NAME)
        except Exception:
            await self._qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"[indexer] Created Qdrant collection: {COLLECTION_NAME}")

    async def index_chunks(self, chunks: list[CodeChunk], session_id: str) -> int:
        """
        Embed all chunks and upsert into Qdrant.
        Returns the number of chunks indexed.
        """
        if not chunks:
            return 0

        await self._ensure_collection()

        texts = [f"{c.name}\n{c.content}" for c in chunks]

        try:
            vectors = await self._embedder.aembed_documents(texts)
        except Exception as exc:
            raise AgentExecutionException(f"Embedding failed: {exc}") from exc

        points = []
        for chunk, vector in zip(chunks, vectors):
            chunk_id = hashlib.md5(
                f"{session_id}:{chunk.file_path}:{chunk.name}".encode()
            ).hexdigest()
            points.append(PointStruct(
                id=str(uuid.UUID(chunk_id)),
                vector=vector,
                payload={
                    "session_id": session_id,
                    "file_path":  chunk.file_path,
                    "chunk_type": chunk.chunk_type,
                    "name":       chunk.name,
                    "content":    chunk.content,
                    "language":   chunk.language,
                    "start_line": chunk.start_line,
                },
            ))

        await self._qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"[indexer] Upserted {len(points)} chunks for session={session_id}")
        return len(points)
