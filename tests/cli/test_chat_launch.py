"""Tests for chat and reindex CLI commands."""

from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from session_scribe.cli.main import app

runner = CliRunner()


class TestChatCommand:
    def test_chat_help(self):
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0


class TestReindexCommand:
    def test_reindex_help(self):
        result = runner.invoke(app, ["reindex", "--help"])
        assert result.exit_code == 0
