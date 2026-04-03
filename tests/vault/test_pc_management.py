"""Tests for player character note management."""

from unittest.mock import MagicMock

import pytest

from chronicler.models.context import PlayerCharacter
from chronicler.vault.note_renderer import render_pc_note
from chronicler.vault.vault_manager import VaultManager


class TestRenderPCNote:
    def test_render_pc_note_with_class(self) -> None:
        pc = PlayerCharacter(
            player_name="Scott",
            character_name="Seven",
            character_class="Wizard",
        )

        md = render_pc_note(pc)

        assert "# Seven" in md
        assert "Scott" in md
        assert "Wizard" in md
        assert "type: player-character" in md
        assert "## Overview" in md
        assert "## Timeline" in md
        assert "## Relationships" in md

    def test_render_pc_note_minimal(self) -> None:
        pc = PlayerCharacter(
            player_name="Unknown",
            character_name="Bastion",
        )

        md = render_pc_note(pc)

        assert "# Bastion" in md
        assert "Unknown" in md
        assert "character_class:" not in md
        assert "## Known Facts" in md
        assert "## Open Questions" in md


class TestVaultManagerPC:
    @pytest.fixture
    def mock_cli(self) -> MagicMock:
        cli = MagicMock()
        cli.vault_name = "Test Vault"
        cli.list_files.return_value = []
        cli.find_notes_in_folder.return_value = []
        cli.search.return_value = []
        cli.read.return_value = ""
        return cli

    @pytest.fixture
    def manager(self, mock_cli: MagicMock) -> VaultManager:
        return VaultManager(cli=mock_cli)

    def test_write_pc(self, manager: VaultManager, mock_cli: MagicMock) -> None:
        pc = PlayerCharacter(
            player_name="Scott",
            character_name="Seven",
            character_class="Wizard",
        )

        manager.write_pc(pc)

        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert path == "Party/Seven.md"

    def test_read_player_characters(self, manager: VaultManager, mock_cli: MagicMock) -> None:
        mock_cli.find_notes_in_folder.return_value = ["Party/Seven.md"]
        mock_cli.read.return_value = (
            "---\n"
            "type: player-character\n"
            "player_name: Scott\n"
            "character_name: Seven\n"
            "character_class: Wizard\n"
            "---\n"
            "# Seven\n"
        )

        pcs = manager.read_player_characters()

        assert len(pcs) == 1
        assert pcs[0].character_name == "Seven"
        assert pcs[0].player_name == "Scott"

    def test_player_characters_are_in_context_bundle(
        self,
        manager: VaultManager,
        mock_cli: MagicMock,
    ) -> None:
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": [],
            "Locations/": [],
            "Factions/": [],
            "Sessions/": [],
            "Party/": ["Party/Seven.md"],
        }.get(folder, [])
        mock_cli.read.side_effect = lambda path: {
            "Plot-Threads/_Open-Threads.md": "",
            "_Agent/Memory/entity-aliases.md": "",
            "Party/Seven.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Scott\n"
                "character_name: Seven\n"
                "character_class: Wizard\n"
                "---\n"
                "# Seven\n"
            ),
        }.get(path, "")

        bundle = manager.get_context_bundle(session_number=1)

        assert len(bundle.player_characters) == 1
        assert bundle.player_characters[0].character_name == "Seven"
