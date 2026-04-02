"""Tests for the init CLI command."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestInitCommand:
    def test_init_help(self):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "vault" in result.output.lower() or "init" in result.output.lower()

    def test_init_command_exists(self):
        # Verify the command is registered
        result = runner.invoke(app, ["--help"])
        assert "init" in result.output

    def test_init_calls_vault_manager(self):
        """init command should create ObsidianCLI and VaultManager, then call init_vault."""
        mock_settings = MagicMock()
        mock_settings.vault_name = "TestVault"
        mock_settings.vault_path = MagicMock()
        mock_settings.vault_path.exists.return_value = True

        mock_vm = MagicMock()

        with (
            patch("session_scribe.cli.main.Settings", return_value=mock_settings),
            patch("session_scribe.cli.main.ObsidianCLI") as mock_cli_cls,
            patch("session_scribe.cli.main.VaultManager", return_value=mock_vm) as mock_vm_cls,
        ):
            result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        mock_cli_cls.assert_called_once_with("TestVault")
        mock_vm_cls.assert_called_once_with(mock_cli_cls.return_value)
        mock_vm.init_vault.assert_called_once()

    def test_init_errors_when_vault_name_empty(self):
        """init command should error when vault_name is empty."""
        mock_settings = MagicMock()
        mock_settings.vault_name = ""

        with patch("session_scribe.cli.main.Settings", return_value=mock_settings):
            result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "SCRIBE_VAULT_NAME" in result.output

    def test_init_handles_config_error(self):
        """init command should handle Settings load failure gracefully."""
        from pydantic import ValidationError

        with patch("session_scribe.cli.main.Settings", side_effect=Exception("bad config")):
            result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()
