# tests/retrieval/test_retrieval.py
"""Tests for the semantic search retrieval layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from chronicler.retrieval.retrieval import RetrievalLayer, SearchResult


@pytest.fixture
def mock_embed_client():
    client = MagicMock()
    client.embed = AsyncMock(return_value=[0.1, 0.2, 0.3] * 256)
    return client


@pytest.fixture
def mock_collection():
    collection = MagicMock()
    collection.query.return_value = {
        "ids": [["NPCs/Sylvie.md::Description", "Sessions/Session-001.md::Summary"]],
        "documents": [
            [
                "A mysterious elf from the forest.",
                "The party met Sylvie near the ruins.",
            ]
        ],
        "metadatas": [
            [
                {
                    "path": "NPCs/Sylvie.md",
                    "heading": "Description",
                    "note_type": "npc",
                },
                {
                    "path": "Sessions/Session-001.md",
                    "heading": "Summary",
                    "note_type": "session",
                },
            ]
        ],
        "distances": [[0.12, 0.35]],
    }
    return collection


class TestSearchResult:
    def test_search_result_fields(self):
        result = SearchResult(
            path="NPCs/Sylvie.md",
            heading="Description",
            content="A mysterious elf from the forest.",
            score=0.12,
        )
        assert result.path == "NPCs/Sylvie.md"
        assert result.heading == "Description"
        assert result.content == "A mysterious elf from the forest."
        assert result.score == 0.12


class TestRetrievalLayer:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_collection, mock_embed_client):
        layer = RetrievalLayer(
            collection=mock_collection, embed_client=mock_embed_client
        )
        results = await layer.search("Tell me about Sylvie", top_k=5)

        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        assert results[0].path == "NPCs/Sylvie.md"
        assert results[0].heading == "Description"
        assert results[0].content == "A mysterious elf from the forest."
        assert results[0].score == 0.12
        assert results[1].path == "Sessions/Session-001.md"
        assert results[1].score == 0.35

        mock_embed_client.embed.assert_awaited_once_with("Tell me about Sylvie")
        mock_collection.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(
        self, mock_collection, mock_embed_client
    ):
        layer = RetrievalLayer(
            collection=mock_collection, embed_client=mock_embed_client
        )
        results = await layer.search("", top_k=5)

        assert results == []
        mock_embed_client.embed.assert_not_awaited()
        mock_collection.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_no_results_returns_empty(
        self, mock_collection, mock_embed_client
    ):
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        layer = RetrievalLayer(
            collection=mock_collection, embed_client=mock_embed_client
        )
        results = await layer.search("Something obscure", top_k=5)

        assert results == []
