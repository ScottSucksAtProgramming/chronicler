# src/chronicler/retrieval/embeddings.py
"""LM Studio embedding client using the OpenAI-compatible API."""

import logging
from typing import Sequence

import httpx

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


class EmbeddingClient:
    """Client for generating text embeddings via LM Studio."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30)

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        response = await self._client.post(
            "/embeddings",
            json={"input": list(texts), "model": self.model},
        )
        response.raise_for_status()
        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        logger.info("Generated %d embeddings (model=%s)", len(embeddings), self.model)
        return embeddings

    def embed_sync(self, text: str) -> list[float]:
        """Synchronous version of embed() for use in threaded contexts."""
        if not text.strip():
            raise ValueError("Cannot embed empty text")
        response = httpx.post(
            f"{self.base_url}/embeddings",
            json={"input": [text], "model": self.model},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    def health_check(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/models", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
