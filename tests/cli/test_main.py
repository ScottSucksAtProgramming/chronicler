"""Tests for the CLI entry point."""

from typer.testing import CliRunner
from chronicler.cli.main import app

runner = CliRunner()


class TestCLI:
    def test_help_shows_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Chronicler" in result.output
        assert "ingest" in result.output
        assert "chat" in result.output
        assert "review" in result.output
        assert "improve" in result.output
        assert "ask" in result.output
        assert "stats" in result.output
        assert "config" in result.output
        assert "reindex" in result.output

    def test_help_describes_ingest_as_session_recordings_and_source_materials(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "session recordings" in result.output
        assert "source materials" in result.output
        assert "PLAUD" not in result.output

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "chronicler v0.1.0" in result.output

    def test_ingest_requires_files(self):
        result = runner.invoke(app, ["ingest"])
        assert result.exit_code != 0

    def test_stats_runs(self):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
