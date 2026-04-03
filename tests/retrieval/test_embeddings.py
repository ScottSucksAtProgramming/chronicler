# tests/retrieval/test_embeddings.py
"""Tests for the LM Studio embedding client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from chronicler.retrieval.embeddings import EmbeddingClient


@pytest.fixture
def client():
    return EmbeddingClient(
        base_url="http://localhost:1234/v1",
        model="text-embedding-nomic-embed-text-v1.5",
    )


class TestEmbeddingClient:
    @pytest.mark.asyncio
    async def test_embed_single_text(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3] * 256}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await client.embed("Test text")
            assert len(result) == 768

    @pytest.mark.asyncio
    async def test_embed_batch(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1] * 768},
                {"embedding": [0.2] * 768},
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            results = await client.embed_batch(["Text 1", "Text 2"])
            assert len(results) == 2
            assert len(results[0]) == 768

    @pytest.mark.asyncio
    async def test_embed_empty_raises(self, client):
        with pytest.raises(ValueError):
            await client.embed("")

    def test_health_check(self, client):
        with patch("httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert client.health_check() is True

    def test_health_check_failure(self, client):
        with patch("httpx.get", side_effect=Exception("connection refused")):
            assert client.health_check() is False
