"""Tests for the ingest CLI command."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from session_scribe.cli.main import app

runner = CliRunner()


class TestIngestCommand:
    def test_ingest_with_nonexistent_file(self):
        result = runner.invoke(app, ["ingest", "nonexistent.pdf"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_ingest_shows_help_for_file_types(self):
        result = runner.invoke(app, ["ingest", "--help"])
        assert "pdf" in result.output.lower() or "PLAUD" in result.output

    def test_ingest_rejects_unsupported_file_type(self, tmp_path):
        bad_file = tmp_path / "session.docx"
        bad_file.write_text("content")
        result = runner.invoke(app, ["ingest", str(bad_file)])
        assert result.exit_code == 1
        assert ".pdf" in result.output or ".txt" in result.output

    def test_ingest_requires_at_least_one_file(self):
        result = runner.invoke(app, ["ingest"])
        assert result.exit_code != 0

    def test_ingest_pipeline_called_with_pdf(self, tmp_path):
        """Verify the pipeline is invoked when a valid PDF is given."""
        pdf_file = tmp_path / "session.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_result = MagicMock()
        mock_result.npcs = [MagicMock(), MagicMock()]
        mock_result.locations = [MagicMock()]
        mock_result.factions = []
        mock_result.loot = [MagicMock(), MagicMock(), MagicMock()]
        mock_result.plot_threads = [MagicMock()]
        mock_result.questions = []
        mock_result.recap = MagicMock()
        mock_result.recap.title = "Test Session"
        mock_result.recap.summary = "The party fought a dragon."

        async def fake_pipeline(*args, **kwargs):
            return mock_result

        with patch("session_scribe.cli.main._run_ingest_pipeline", side_effect=fake_pipeline):
            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 0
        assert "2" in result.output  # 2 NPCs
        assert "The party fought a dragon." in result.output

    def test_ingest_pipeline_called_with_txt(self, tmp_path):
        """Verify the pipeline is invoked when a valid .txt transcript is given."""
        txt_file = tmp_path / "transcript.txt"
        txt_file.write_text("00:00:00\nHello world")

        mock_result = MagicMock()
        mock_result.npcs = []
        mock_result.locations = []
        mock_result.factions = []
        mock_result.loot = []
        mock_result.plot_threads = []
        mock_result.questions = []
        mock_result.recap = MagicMock()
        mock_result.recap.title = "Transcript Session"
        mock_result.recap.summary = "A quiet evening."

        async def fake_pipeline(*args, **kwargs):
            return mock_result

        with patch("session_scribe.cli.main._run_ingest_pipeline", side_effect=fake_pipeline):
            result = runner.invoke(app, ["ingest", str(txt_file)])

        assert result.exit_code == 0
        assert "A quiet evening." in result.output

    def test_ingest_shows_settings_error_hint(self, tmp_path):
        """When Settings fails, user sees a hint to run 'scribe config'."""
        pdf_file = tmp_path / "session.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        with patch("session_scribe.config.settings.Settings", side_effect=Exception("Missing API key")):
            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 1
        assert "config" in result.output.lower()

    def test_ingest_shows_pipeline_error_message(self, tmp_path):
        """When the pipeline raises, user sees a friendly error."""
        pdf_file = tmp_path / "session.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        async def failing_pipeline(*args, **kwargs):
            raise RuntimeError("LLM unreachable")

        with patch("session_scribe.cli.main._run_ingest_pipeline", side_effect=failing_pipeline):
            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 1
        assert "LLM unreachable" in result.output or "error" in result.output.lower()

    def test_ingest_session_number_option(self, tmp_path):
        """--session flag is accepted and forwarded."""
        pdf_file = tmp_path / "session.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        captured = {}

        async def capturing_pipeline(files, session_number, *args, **kwargs):
            captured["session_number"] = session_number
            mock_result = MagicMock()
            mock_result.npcs = []
            mock_result.locations = []
            mock_result.factions = []
            mock_result.loot = []
            mock_result.plot_threads = []
            mock_result.questions = []
            mock_result.recap = MagicMock()
            mock_result.recap.title = "S"
            mock_result.recap.summary = "Summary."
            return mock_result

        with patch("session_scribe.cli.main._run_ingest_pipeline", side_effect=capturing_pipeline):
            result = runner.invoke(app, ["ingest", str(pdf_file), "--session", "22"])

        assert result.exit_code == 0
        assert captured.get("session_number") == 22
