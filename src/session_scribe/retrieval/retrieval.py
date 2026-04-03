# src/session_scribe/retrieval/retrieval.py
"""Semantic search retrieval layer over ChromaDB."""

import logging
from dataclasses import dataclass

from session_scribe.retrieval.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from the vault index."""

    path: str
    heading: str
    content: str
    score: float  # ChromaDB distance — lower = more relevant


class RetrievalLayer:
    """Semantic search interface over a ChromaDB collection."""

    def __init__(self, collection, embed_client: EmbeddingClient) -> None:
        self._collection = collection
        self._embed_client = embed_client

    async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search the vault index for chunks relevant to *query*.

        Returns an empty list for blank queries or when no results exist.
        """
        if not query.strip():
            return []

        embedding = await self._embed_client.embed(query)

        raw = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )

        ids: list[str] = raw.get("ids", [[]])[0]
        if not ids:
            return []

        documents: list[str] = raw.get("documents", [[]])[0]
        metadatas: list[dict] = raw.get("metadatas", [[]])[0]
        distances: list[float] = raw.get("distances", [[]])[0]

        results: list[SearchResult] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            results.append(
                SearchResult(
                    path=meta.get("path", ""),
                    heading=meta.get("heading", ""),
                    content=doc,
                    score=dist,
                )
            )

        logger.info("Search for %r returned %d results", query, len(results))
        return results

    def search_sync(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Synchronous version of search() for use in threaded contexts."""
        if not query.strip():
            return []

        embedding = self._embed_client.embed_sync(query)

        raw = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )

        ids: list[str] = raw.get("ids", [[]])[0]
        if not ids:
            return []

        documents: list[str] = raw.get("documents", [[]])[0]
        metadatas: list[dict] = raw.get("metadatas", [[]])[0]
        distances: list[float] = raw.get("distances", [[]])[0]

        results: list[SearchResult] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            results.append(
                SearchResult(
                    path=meta.get("path", ""),
                    heading=meta.get("heading", ""),
                    content=doc,
                    score=dist,
                )
            )

        logger.info("Search for %r returned %d results", query, len(results))
        return results
