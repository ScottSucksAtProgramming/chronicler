"""Tests for chat slash commands."""

from unittest.mock import MagicMock

from session_scribe.chat.app import ChatApp
from session_scribe.models.context import AgentMemory


class TestChatCommands:
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
