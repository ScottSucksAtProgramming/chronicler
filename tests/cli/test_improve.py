"""Tests for the improve CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chronicler.cli.main import app

runner = CliRunner()


class TestImproveCommand:
    def test_improve_help(self):
        result = runner.invoke(app, ["improve", "--help"])
        assert result.exit_code == 0

    def test_improve_runs_and_reports_summary(self):
        mock_report = MagicMock()
        mock_report.changed_count = 3
        mock_report.question_count = 2
        mock_report.changed_files = ["Sessions/Session-001.md"]
        mock_report.question_files = ["_Agent/Questions/question.md"]

        with patch("chronicler.cli.main.Settings") as MockSettings, \
             patch("chronicler.cli.main.ObsidianCLI"), \
             patch("chronicler.cli.main.improve_vault", return_value=mock_report):
            MockSettings.return_value = MagicMock(vault_name="Test")
            result = runner.invoke(app, ["improve"])

        assert result.exit_code == 0
        assert "3" in result.output
        assert "2" in result.output
        assert "improvement complete" in result.output.lower()
