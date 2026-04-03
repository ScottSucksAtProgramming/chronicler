"""Tests for vault indexer."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from session_scribe.retrieval.indexer import VaultIndexer, NoteChunk


class TestNoteChunk:
    def test_chunk_creation(self):
        chunk = NoteChunk(
            path="NPCs/Theron.md",
            heading="Description",
            content="A ranger from the north.",
            note_type="npc",
        )
        assert chunk.path == "NPCs/Theron.md"
        assert chunk.note_type == "npc"


class TestChunkNote:
    def test_chunk_by_sections(self):
        content = (
            "---\ntype: npc\n---\n"
            "# Theron\n\n"
            "## Description\n\nA ranger from the north.\n\n"
            "## Key Interactions\n\n- Met the party in Session 1\n"
        )
        chunks = VaultIndexer.chunk_note("NPCs/Theron.md", content)
        assert len(chunks) >= 2
        assert any("ranger" in c.content for c in chunks)
        assert all(c.path == "NPCs/Theron.md" for c in chunks)
        assert all(c.note_type == "npc" for c in chunks)

    def test_short_note_single_chunk(self):
        content = "# Short Note\n\nJust a brief note."
        chunks = VaultIndexer.chunk_note("Notes/short.md", content)
        assert len(chunks) == 1

    def test_skips_empty_sections(self):
        content = "# Title\n\n## Empty\n\n## Has Content\n\nSome text here."
        chunks = VaultIndexer.chunk_note("test.md", content)
        contents = [c.content for c in chunks]
        assert not any(c.strip() == "" for c in contents)

    def test_extracts_type_from_frontmatter(self):
        content = "---\ntype: location\nname: Spire\n---\n# The Black Spire\n\nA cult site."
        chunks = VaultIndexer.chunk_note("Locations/Spire.md", content)
        assert all(c.note_type == "location" for c in chunks)

    def test_no_frontmatter(self):
        content = "# No Frontmatter\n\nJust content."
        chunks = VaultIndexer.chunk_note("test.md", content)
        assert chunks[0].note_type == ""


class TestIndexVault:
    @pytest.mark.asyncio
    async def test_index_vault_basic(self):
        mock_cli = MagicMock()
        mock_cli.read_all_notes.return_value = {
            "NPCs/Theron.md": "---\ntype: npc\n---\n# Theron\n\n## Description\n\nA ranger.",
            "Sessions/Session-001.md": "---\ntype: session\n---\n# Session 1\n\n## Summary\n\nThe party met.",
        }

        mock_embed_client = MagicMock()
        mock_embed_client.embed_batch = AsyncMock(return_value=[
            [0.1] * 768,
            [0.2] * 768,
        ])

        mock_collection = MagicMock()

        indexer = VaultIndexer(
            cli=mock_cli,
            embed_client=mock_embed_client,
            collection=mock_collection,
        )

        count = await indexer.index_vault()
        assert count >= 2
        mock_collection.upsert.assert_called()

    @pytest.mark.asyncio
    async def test_index_skips_agent_files(self):
        mock_cli = MagicMock()
        mock_cli.read_all_notes.return_value = {
            "_Agent/Memory/entity-aliases.md": "---\ntype: agent-memory\n---\n",
            "_Agent/Review-Log.md": "# Review Log\n",
            "NPCs/Theron.md": "# Theron\n\nA ranger.",
        }

        mock_embed_client = MagicMock()
        mock_embed_client.embed_batch = AsyncMock(return_value=[[0.1] * 768])

        mock_collection = MagicMock()

        indexer = VaultIndexer(
            cli=mock_cli,
            embed_client=mock_embed_client,
            collection=mock_collection,
        )

        count = await indexer.index_vault()
        assert count == 1  # Only the NPC, not agent files
