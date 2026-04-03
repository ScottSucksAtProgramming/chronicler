"""Tests for the party CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chronicler.cli.main import app
from chronicler.models.context import PlayerCharacter

runner = CliRunner()


class TestPartyCommand:
    def test_party_help(self) -> None:
        result = runner.invoke(app, ["party", "--help"])
        assert result.exit_code == 0

    def test_party_list_empty(self) -> None:
        with (
            patch("chronicler.cli.main.Settings") as mock_settings_cls,
            patch("chronicler.cli.main.ObsidianCLI"),
            patch("chronicler.cli.main.VaultManager") as mock_vm_cls,
        ):
            mock_settings_cls.return_value = MagicMock(vault_name="Test")
            mock_vm_cls.return_value.read_player_characters.return_value = []

            result = runner.invoke(app, ["party", "list"])

        assert result.exit_code == 0
        assert "no player characters" in result.output.lower()

    def test_party_list_populated(self) -> None:
        with (
            patch("chronicler.cli.main.Settings") as mock_settings_cls,
            patch("chronicler.cli.main.ObsidianCLI"),
            patch("chronicler.cli.main.VaultManager") as mock_vm_cls,
        ):
            mock_settings_cls.return_value = MagicMock(vault_name="Test")
            mock_vm_cls.return_value.read_player_characters.return_value = [
                PlayerCharacter(
                    player_name="Scott",
                    character_name="Seven",
                    character_class="Wizard",
                )
            ]

            result = runner.invoke(app, ["party", "list"])

        assert result.exit_code == 0
        assert "Scott" in result.output
        assert "Seven" in result.output
        assert "Wizard" in result.output

    def test_party_add(self) -> None:
        with (
            patch("chronicler.cli.main.Settings") as mock_settings_cls,
            patch("chronicler.cli.main.ObsidianCLI"),
            patch("chronicler.cli.main.VaultManager") as mock_vm_cls,
        ):
            mock_settings_cls.return_value = MagicMock(vault_name="Test")
            mock_vm = mock_vm_cls.return_value

            result = runner.invoke(
                app,
                [
                    "party",
                    "add",
                    "--player",
                    "Scott",
                    "--character",
                    "Seven",
                    "--class",
                    "Wizard",
                ],
            )

        assert result.exit_code == 0
        mock_vm.write_pc.assert_called_once()

    def test_party_remove(self) -> None:
        with (
            patch("chronicler.cli.main.Settings") as mock_settings_cls,
            patch("chronicler.cli.main.ObsidianCLI"),
            patch("chronicler.cli.main.VaultManager") as mock_vm_cls,
        ):
            mock_settings_cls.return_value = MagicMock(vault_name="Test")
            mock_vm = mock_vm_cls.return_value

            result = runner.invoke(
                app,
                ["party", "remove", "--character", "Seven"],
            )

        assert result.exit_code == 0
        mock_vm.remove_pc.assert_called_once_with("Seven")
