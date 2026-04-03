"""Tests for the review CLI command."""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestReviewCommand:
    def test_review_help(self):
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0

    def test_review_runs(self):
        mock_report = MagicMock()
        mock_report.findings = []
        mock_report.total_findings = 0
        mock_report.error_count = 0
        mock_report.warning_count = 0
        mock_report.info_count = 0

        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI"), \
             patch("session_scribe.cli.main.review_vault", return_value=mock_report):
            MockSettings.return_value = MagicMock(vault_name="Test")
            result = runner.invoke(app, ["review"])
            assert result.exit_code == 0
            assert "review complete" in result.output.lower() or "0" in result.output
