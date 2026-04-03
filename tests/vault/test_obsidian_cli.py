"""Tests for the Obsidian CLI wrapper."""

import json
import pytest
from unittest.mock import patch, MagicMock
from chronicler.vault.obsidian_cli import ObsidianCLI, ObsidianCLIError


@pytest.fixture
def cli():
    return ObsidianCLI(vault_name="Test Vault")


class TestObsidianCLI:
    def test_init(self, cli):
        assert cli.vault_name == "Test Vault"

    def test_create_note(self, cli):
        with patch.object(cli, "_get_vault_path", return_value="/tmp/test-vault"):
            with patch("chronicler.vault.obsidian_cli.Path") as MockPath:
                mock_path = MagicMock()
                MockPath.return_value.__truediv__ = MagicMock(return_value=mock_path)
                mock_path.parent.mkdir = MagicMock()
                mock_path.write_text = MagicMock()
                # Just verify no exception is raised
                cli.create("NPCs/Theron.md", "# Theron\n\nA ranger.")

    def test_read_note(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "# Theron\n\nA ranger."
            content = cli.read("NPCs/Theron.md")
            assert content == "# Theron\n\nA ranger."

    def test_search_returns_paths(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = '["NPCs/Theron.md", "Sessions/Session-001.md"]'
            results = cli.search("Theron")
            assert results == ["NPCs/Theron.md", "Sessions/Session-001.md"]

    def test_search_empty_results(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "[]"
            results = cli.search("nonexistent")
            assert results == []

    def test_set_property(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "Set type: npc"
            cli.set_property("NPCs/Theron.md", "type", "npc")
            args = mock_run.call_args[0][0]
            assert "property:set" in args

    def test_list_files(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = '["NPCs/Theron.md", "Sessions/Session-001.md"]'
            files = cli.list_files()
            assert len(files) == 2

    def test_delete_note(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "Moved to trash: NPCs/Theron.md"
            cli.delete("NPCs/Theron.md")
            args = mock_run.call_args[0][0]
            assert "delete" in args

    def test_note_exists_true(self, cli):
        with patch.object(cli, "read") as mock_read:
            mock_read.return_value = "# Theron"
            assert cli.note_exists("NPCs/Theron.md") is True

    def test_note_exists_false(self, cli):
        with patch.object(cli, "read", side_effect=ObsidianCLIError("Not found")):
            assert cli.note_exists("NPCs/Nonexistent.md") is False

    def test_find_notes_in_folder(self, cli):
        with patch.object(cli, "list_files") as mock_list:
            mock_list.return_value = ["NPCs/Theron.md", "NPCs/Sylvie.md", "Sessions/S01.md"]
            result = cli.find_notes_in_folder("NPCs/")
            assert result == ["NPCs/Theron.md", "NPCs/Sylvie.md"]

    def test_cli_error_on_failure(self, cli):
        with patch.object(cli, "_run", side_effect=ObsidianCLIError("CLI failed")):
            with pytest.raises(ObsidianCLIError):
                cli.read("bad/path.md")

    def test_health_check(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "1.12.7"
            assert cli.health_check() is True

    def test_health_check_failure(self, cli):
        with patch.object(cli, "_run", side_effect=ObsidianCLIError("not found")):
            assert cli.health_check() is False
