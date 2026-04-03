"""Tests for hybrid chat context loading."""

from unittest.mock import MagicMock

from chronicler.retrieval.retrieval import SearchResult


class TestChatContextLoader:
    def test_load_chat_context_falls_back_to_filename_matches_for_entity_queries(self) -> None:
        from chronicler.chat.context_loader import load_chat_context

        cli = MagicMock()
        cli.note_exists.return_value = False
        cli.find_notes_in_folder.side_effect = lambda folder: {
            "_Agent/Memory/": ["_Agent/Memory/entity-aliases.md"],
            "Party/": [],
        }.get(folder, [])
        cli.list_files.return_value = [
            "Locations/Small Merchant Vessel.md",
            "Sessions/Session-002.md",
            "_Agent/Memory/entity-aliases.md",
        ]
        cli.read.side_effect = lambda path: {
            "_Agent/Memory/entity-aliases.md": "---\ntype: agent-memory\n---\nSmall Merchant Vessel: Black Cherry\n",
            "Locations/Small Merchant Vessel.md": "# Small Merchant Vessel\n## Description\nThe Black Cherry is a merchant vessel.",
            "Sessions/Session-002.md": "# Session 2\n## Summary\nThe party swam for the Black Cherry.",
        }[path]

        bundle = load_chat_context(
            cli=cli,
            query="What is the Black Cherry?",
            retrieval_results=[],
        )

        paths = {note.path for note in bundle.supporting_notes}
        assert "Locations/Small Merchant Vessel.md" in paths
        assert "Sessions/Session-002.md" in paths

    def test_load_chat_context_falls_back_to_content_search_for_missing_entity_names(self) -> None:
        from chronicler.chat.context_loader import load_chat_context

        cli = MagicMock()
        cli.note_exists.return_value = False
        cli.find_notes_in_folder.side_effect = lambda folder: {
            "_Agent/Memory/": [],
            "Party/": [],
        }.get(folder, [])
        cli.list_files.return_value = [
            "Locations/Small Merchant Vessel.md",
            "Sessions/Session-002.md",
        ]
        cli.search.side_effect = lambda query: ["Sessions/Session-002.md"] if query == "Black Cherry" else []
        cli.read.side_effect = lambda path: {
            "Sessions/Session-002.md": "# Session 2\n## Summary\nThe party swam for the Black Cherry.",
        }[path]

        bundle = load_chat_context(
            cli=cli,
            query="What is the Black Cherry?",
            retrieval_results=[],
        )

        paths = {note.path for note in bundle.supporting_notes}
        assert "Sessions/Session-002.md" in paths

    def test_load_chat_context_detects_meta_questions_and_reads_session_notes(self) -> None:
        from chronicler.chat.context_loader import load_chat_context

        cli = MagicMock()
        cli.note_exists.side_effect = lambda path: path in {
            "_Dashboard.md",
            "Timeline.md",
            "Plot-Threads/_Open-Threads.md",
        }
        cli.find_notes_in_folder.side_effect = lambda folder: {
            "_Agent/Memory/": [],
            "Party/": [],
            "Sessions/": ["Sessions/Session-001.md", "Sessions/Session-002.md"],
        }.get(folder, [])
        cli.read.side_effect = lambda path: {
            "_Dashboard.md": "# Dashboard",
            "Timeline.md": "# Timeline",
            "Plot-Threads/_Open-Threads.md": "# Open Plot Threads",
            "Sessions/Session-001.md": "# Session 1",
            "Sessions/Session-002.md": "# Session 2",
        }[path]

        bundle = load_chat_context(
            cli=cli,
            query="What questions do you have?",
            retrieval_results=[],
        )

        paths = {note.path for note in bundle.supporting_notes}
        assert "Sessions/Session-001.md" in paths
        assert "Sessions/Session-002.md" in paths

    def test_load_chat_context_includes_core_vault_notes(self) -> None:
        from chronicler.chat.context_loader import load_chat_context

        cli = MagicMock()
        cli.note_exists.side_effect = lambda path: path in {
            "_Agent/Memory/vault-guide.md",
            "_Dashboard.md",
            "Timeline.md",
            "Plot-Threads/_Open-Threads.md",
        }
        cli.read.side_effect = lambda path: {
            "_Agent/Memory/vault-guide.md": "# Vault Guide\nUse Party/ for PCs.",
            "_Dashboard.md": "# Dashboard\nSession 22",
            "Timeline.md": "# Timeline\n- Session 22",
            "Plot-Threads/_Open-Threads.md": "# Open Plot Threads\n- Find the merchant",
            "Party/Seven.md": "---\ntype: player-character\nplayer_name: Scott\ncharacter_name: Seven\n---\n",
            "_Agent/Memory/entity-aliases.md": "---\ntype: agent-memory\n---\nBlack Cherry: merchant vessel\n",
        }[path]
        cli.find_notes_in_folder.side_effect = lambda folder: {
            "Party/": ["Party/Seven.md"],
            "_Agent/Memory/": [
                "_Agent/Memory/vault-guide.md",
                "_Agent/Memory/entity-aliases.md",
            ],
        }.get(folder, [])

        bundle = load_chat_context(cli=cli, query="Who are the player characters?", retrieval_results=[])

        paths = {note.path for note in bundle.core_notes}
        assert "_Agent/Memory/vault-guide.md" in paths
        assert "_Dashboard.md" in paths
        assert "Timeline.md" in paths
        assert "Plot-Threads/_Open-Threads.md" in paths
        assert "Party/Seven.md" in paths
        assert "_Agent/Memory/entity-aliases.md" in paths

    def test_load_chat_context_reads_retrieval_source_files_directly(self) -> None:
        from chronicler.chat.context_loader import load_chat_context

        cli = MagicMock()
        cli.note_exists.return_value = False
        cli.find_notes_in_folder.return_value = []
        cli.read.side_effect = lambda path: {
            "Sessions/Session-002.md": "# Session 2\n## Key Events\nThe party boarded the Black Cherry.",
            "Locations/Small Merchant Vessel.md": "# Vessel\nThe Black Cherry is a small merchant ship.",
        }[path]

        retrieval_results = [
            SearchResult(
                path="Sessions/Session-002.md",
                heading="Key Events",
                content="The party boarded a ship.",
                score=0.10,
            ),
            SearchResult(
                path="Locations/Small Merchant Vessel.md",
                heading="Description",
                content="A small merchant ship.",
                score=0.12,
            ),
        ]

        bundle = load_chat_context(cli=cli, query="What happened in session 2?", retrieval_results=retrieval_results)

        paths = {note.path for note in bundle.supporting_notes}
        assert "Sessions/Session-002.md" in paths
        assert "Locations/Small Merchant Vessel.md" in paths
        assert len(bundle.retrieval_hits) == 2
