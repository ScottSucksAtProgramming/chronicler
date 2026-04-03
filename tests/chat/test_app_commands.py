"""Tests for chat slash commands."""

from unittest.mock import MagicMock

from chronicler.chat.app import ChatApp
from chronicler.models.context import AgentMemory


class TestChatCommands:
    def test_format_sources_includes_core_and_supporting_notes(self) -> None:
        from chronicler.chat.context_loader import ChatContextBundle, DirectVaultNote
        from chronicler.retrieval.retrieval import SearchResult

        app = ChatApp(
            retrieval=MagicMock(),
            gateway=MagicMock(),
            model="test-model",
        )

        bundle = ChatContextBundle(
            core_notes=[DirectVaultNote(path="Party/Seven.md", content="Seven")],
            supporting_notes=[DirectVaultNote(path="Sessions/Session-002.md", content="Session 2")],
            retrieval_hits=[
                SearchResult(
                    path="Locations/Small Merchant Vessel.md",
                    heading="Description",
                    content="The Black Cherry.",
                    score=0.12,
                )
            ],
        )

        text = app._format_sources(bundle)

        assert "Party/Seven.md" in text
        assert "Sessions/Session-002.md" in text
        assert "Locations/Small Merchant Vessel.md > Description" in text

    def test_help_command_lists_available_commands(self) -> None:
        app = ChatApp(
            retrieval=MagicMock(),
            gateway=MagicMock(),
            model="test-model",
        )
        app._add_message = MagicMock()

        app._handle_command("/help")

        app._add_message.assert_called_once()
        message = app._add_message.call_args[0][0]
        assert "/help" in message
        assert "/alias" in message
        assert "/quit" in message

    def test_alias_command_updates_vault_manager(self) -> None:
        vault_manager = MagicMock()
        vault_manager.read_agent_memory.return_value = AgentMemory(
            entity_aliases={"The Black Spire": "the spire"}
        )
        app = ChatApp(
            retrieval=MagicMock(),
            gateway=MagicMock(),
            model="test-model",
            vault_manager=vault_manager,
        )
        app._add_message = MagicMock()

        app._handle_command('/alias "the tavern" "Smoked Eel Tavern"')

        vault_manager.update_entity_aliases.assert_called_once_with(
            {
                "The Black Spire": "the spire",
                "Smoked Eel Tavern": "the tavern",
            }
        )

    def test_unknown_command_shows_help_hint(self) -> None:
        app = ChatApp(
            retrieval=MagicMock(),
            gateway=MagicMock(),
            model="test-model",
        )
        app._add_message = MagicMock()

        app._handle_command("/bogus")

        app._add_message.assert_called_once()
        message = app._add_message.call_args[0][0]
        assert "unknown command" in message.lower()
