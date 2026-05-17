"""
NexusIQ — Hybrid RAG retriever.
Uses dense (Qdrant vector) search with optional BM25 re-ranking.
Returns List[RetrievedChunk] — TypedDicts with a 'content' field.
"""
from typing import TypedDict

from loguru import logger
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from rag.indexer import COLLECTION_NAME
from exceptions.base import AgentExecutionException


class RetrievedChunk(TypedDict):
    content:    str
    file_path:  str
    name:       str
    score:      float
    session_id: str


class HybridRetriever:
    """
    Dense-only retriever (with BM25 extension point).
    Falls back gracefully if the Qdrant collection doesn't exist yet.
    """

    def __init__(self, qdrant_client, embedder, bm25_index=None, bm25_corpus=None) -> None:
        self._qdrant   = qdrant_client
        self._embedder = embedder
        # BM25 args accepted but unused — extension point for future hybrid ranking

    async def retrieve(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """
        Embed the query and retrieve top_k chunks scoped to session_id.
        Returns empty list if collection doesn't exist (safe for new sessions).
        """
        try:
            vector = await self._embedder.aembed_query(query)
        except Exception as exc:
            raise AgentExecutionException(f"Query embedding failed: {exc}") from exc

        try:
            results = await self._qdrant.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector,
                query_filter=Filter(
                    must=[FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )]
                ),
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:
            logger.warning(f"[retriever] Qdrant search failed (returning empty): {exc}")
            return []

        chunks: list[RetrievedChunk] = []
        for hit in results:
            payload = hit.payload or {}
            chunks.append(RetrievedChunk(
                content=payload.get("content", ""),
                file_path=payload.get("file_path", ""),
                name=payload.get("name", ""),
                score=hit.score,
                session_id=payload.get("session_id", session_id),
            ))

        logger.debug(f"[retriever] Retrieved {len(chunks)} chunks for query='{query[:40]}'")
        return chunks
