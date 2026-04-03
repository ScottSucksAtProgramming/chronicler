"""Tests for the ask CLI command."""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestAskCommand:
    def test_ask_help(self):
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0

    def test_ask_no_questions(self):
        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI") as MockCLI:
            MockSettings.return_value = MagicMock(vault_name="Test")
            mock_cli = MockCLI.return_value
            mock_cli.find_notes_in_folder.return_value = []
            result = runner.invoke(app, ["ask"])
            assert result.exit_code == 0
            assert "no pending questions" in result.output.lower()

    def test_ask_shows_questions(self):
        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI") as MockCLI:
            MockSettings.return_value = MagicMock(vault_name="Test")
            mock_cli = MockCLI.return_value
            mock_cli.find_notes_in_folder.return_value = [
                "_Agent/Questions/q1.md",
            ]
            mock_cli.read.return_value = (
                "---\ntype: agent-question\npriority: medium\nsource_session: 22\n---\n"
                "# Is Santiago an NPC?\n\n## Context\nUnclear reference."
            )
            result = runner.invoke(app, ["ask"], input="\n")
            assert "Santiago" in result.output
