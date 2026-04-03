"""Tests for auto-reindex after ingest."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from session_scribe.cli.main import _auto_reindex_vault


class TestAutoReindex:
    def test_auto_reindex_runs_indexer_when_embeddings_are_available(self, tmp_path) -> None:
        settings = SimpleNamespace(
            lm_studio_base_url="http://localhost:1234/v1",
            embedding_model="text-embedding-test",
            vault_path=tmp_path,
        )
        cli = MagicMock()

        fake_embed_client = MagicMock()
        fake_embed_client.health_check.return_value = True

        fake_collection = MagicMock()
        fake_chroma_client = MagicMock()
        fake_chroma_client.get_or_create_collection.return_value = fake_collection

        fake_indexer = MagicMock()
        fake_indexer.index_vault = AsyncMock(return_value=42)

        with (
            patch("session_scribe.retrieval.embeddings.EmbeddingClient", return_value=fake_embed_client),
            patch("chromadb.PersistentClient", return_value=fake_chroma_client),
            patch("session_scribe.retrieval.indexer.VaultIndexer", return_value=fake_indexer),
        ):
            import asyncio

            chunk_count = asyncio.run(_auto_reindex_vault(settings, cli))

        assert chunk_count == 42
        fake_indexer.index_vault.assert_called_once()

    def test_auto_reindex_skips_when_embeddings_are_unavailable(self, tmp_path) -> None:
        settings = SimpleNamespace(
            lm_studio_base_url="http://localhost:1234/v1",
            embedding_model="text-embedding-test",
            vault_path=tmp_path,
        )
        cli = MagicMock()

        fake_embed_client = MagicMock()
        fake_embed_client.health_check.return_value = False

        with patch(
            "session_scribe.retrieval.embeddings.EmbeddingClient",
            return_value=fake_embed_client,
        ):
            import asyncio

            chunk_count = asyncio.run(_auto_reindex_vault(settings, cli))

        assert chunk_count is None
