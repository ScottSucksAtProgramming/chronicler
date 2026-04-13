"""Tests for the ingest CLI command."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from chronicler.cli import main as cli_main
from chronicler.cli.main import app

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
        assert "unsupported" in result.output.lower()

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

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_ingest_pipeline", side_effect=fake_pipeline),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_summary",
                confidence=0.95,
                session_anchor=None,
            )
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

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_ingest_pipeline", side_effect=fake_pipeline),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_transcript",
                confidence=0.95,
                session_anchor=None,
            )
            result = runner.invoke(app, ["ingest", str(txt_file)])

        assert result.exit_code == 0
        assert "A quiet evening." in result.output

    def test_ingest_shows_settings_error_hint(self, tmp_path):
        """When Settings fails, user sees a hint to run 'scribe config'."""
        pdf_file = tmp_path / "session.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main.Settings", side_effect=Exception("Missing API key")),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_summary",
                confidence=0.95,
                session_anchor=None,
            )
            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 1
        assert "config" in result.output.lower()

    def test_ingest_shows_pipeline_error_message(self, tmp_path):
        """When the pipeline raises, user sees a friendly error."""
        pdf_file = tmp_path / "session.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        async def failing_pipeline(*args, **kwargs):
            raise RuntimeError("LLM unreachable")

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_ingest_pipeline", side_effect=failing_pipeline),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_summary",
                confidence=0.95,
                session_anchor=None,
            )
            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 1
        assert "LLM unreachable" in result.output or "error" in result.output.lower()

    def test_ingest_shows_clear_message_for_content_filtered_transcript(self, tmp_path):
        pdf_file = tmp_path / "session.txt"
        pdf_file.write_text("00:00:00\nhello")

        async def failing_pipeline(*args, **kwargs):
            raise RuntimeError(
                "LLM provider rejected the transcript as high-risk content, likely due to explicit off-topic banter."
            )

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_ingest_pipeline", side_effect=failing_pipeline),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_transcript",
                confidence=0.95,
                session_anchor=None,
            )
            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 1
        assert "high-risk content" in result.output
        assert "explicit off-topic banter" in result.output

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

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_ingest_pipeline", side_effect=capturing_pipeline),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_support",
                confidence=1.0,
                session_anchor=22,
            )
            result = runner.invoke(app, ["ingest", str(pdf_file), "--session", "22"])

        assert result.exit_code == 0
        assert captured.get("session_number") == 22

    def test_ingest_stops_and_prompts_when_classification_is_ambiguous(self, tmp_path):
        note_file = tmp_path / "notes.md"
        note_file.write_text("Maybe this matters.", encoding="utf-8")

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main.typer.prompt", return_value="legacy_note") as mock_prompt,
            patch("chronicler.cli.main._run_source_ingest_pipeline", return_value=MagicMock(
                npcs=[],
                locations=[],
                factions=[],
                loot=[],
                plot_threads=[],
                questions=[],
                recap=None,
            )),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="unknown",
                confidence=0.3,
                session_anchor=None,
            )

            result = runner.invoke(app, ["ingest", str(note_file)])

        assert result.exit_code == 0
        assert mock_prompt.called
        assert "could not confidently classify" in result.output.lower()

    def test_ingest_passes_session_override_to_classifier(self, tmp_path):
        note_file = tmp_path / "notes.md"
        note_file.write_text("The marsh chapel is older than the village.", encoding="utf-8")

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_source_ingest_pipeline", return_value=MagicMock(
                npcs=[],
                locations=[],
                factions=[],
                loot=[],
                plot_threads=[],
                questions=[],
                recap=None,
            )),
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="legacy_note",
                confidence=0.75,
                session_anchor=22,
            )

            result = runner.invoke(app, ["ingest", str(note_file), "--session", "22"])

        assert result.exit_code == 0
        mock_classify.assert_called_once_with(mock_parse.return_value, 22)

    def test_ingest_routes_background_note_to_source_pipeline(self, tmp_path):
        note_file = tmp_path / "notes.md"
        note_file.write_text("The marsh chapel hides the shrine entrance.", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.npcs = [MagicMock()]
        mock_result.locations = [MagicMock()]
        mock_result.factions = []
        mock_result.loot = []
        mock_result.plot_threads = []
        mock_result.questions = []
        mock_result.recap = None

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_source_ingest_pipeline", return_value=mock_result) as mock_pipeline,
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="legacy_note",
                confidence=0.75,
                session_anchor=None,
            )

            result = runner.invoke(app, ["ingest", str(note_file)])

        assert result.exit_code == 0
        mock_pipeline.assert_called_once()
        assert "Knowledge ingest complete" in result.output

    def test_ingest_routes_anchored_markdown_note_to_source_pipeline(self, tmp_path):
        note_file = tmp_path / "session-notes.md"
        note_file.write_text("The marsh chapel hides the shrine entrance.", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.npcs = []
        mock_result.locations = [MagicMock()]
        mock_result.factions = []
        mock_result.loot = []
        mock_result.plot_threads = []
        mock_result.questions = []
        mock_result.recap = None

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_source_ingest_pipeline", return_value=mock_result) as mock_source,
            patch("chronicler.cli.main._run_ingest_pipeline") as mock_session,
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="legacy_note",
                confidence=0.9,
                session_anchor=6,
            )

            result = runner.invoke(app, ["ingest", str(note_file), "--session", "6"])

        assert result.exit_code == 0
        mock_source.assert_called_once()
        mock_session.assert_not_called()

    def test_ingest_routes_txt_legacy_note_to_source_pipeline(self, tmp_path):
        note_file = tmp_path / "notes.txt"
        note_file.write_text("Background lore from DM Jared about the marsh chapel.", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.npcs = []
        mock_result.locations = []
        mock_result.factions = []
        mock_result.loot = []
        mock_result.plot_threads = []
        mock_result.questions = []
        mock_result.recap = None

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_source_ingest_pipeline", return_value=mock_result) as mock_source,
            patch("chronicler.cli.main._run_ingest_pipeline") as mock_session,
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="legacy_note",
                confidence=0.85,
                session_anchor=None,
            )

            result = runner.invoke(app, ["ingest", str(note_file)])

        assert result.exit_code == 0
        mock_source.assert_called_once()
        mock_session.assert_not_called()

    def test_ingest_routes_pdf_summary_to_session_pipeline(self, tmp_path):
        pdf_file = tmp_path / "summary.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_result = MagicMock()
        mock_result.npcs = []
        mock_result.locations = []
        mock_result.factions = []
        mock_result.loot = []
        mock_result.plot_threads = []
        mock_result.questions = []
        mock_result.recap = MagicMock()
        mock_result.recap.title = "Session Summary"
        mock_result.recap.summary = "Summary text."

        with (
            patch("chronicler.cli.main.parse_source_document") as mock_parse,
            patch("chronicler.cli.main.classify_source_document") as mock_classify,
            patch("chronicler.cli.main._run_ingest_pipeline", return_value=mock_result) as mock_session,
            patch("chronicler.cli.main._run_source_ingest_pipeline") as mock_source,
        ):
            mock_parse.return_value = MagicMock()
            mock_classify.return_value = MagicMock(
                document_type="session_summary",
                confidence=0.92,
                session_anchor=None,
            )

            result = runner.invoke(app, ["ingest", str(pdf_file)])

        assert result.exit_code == 0
        mock_session.assert_called_once()
        mock_source.assert_not_called()

    def test_source_pipeline_archives_and_writes_to_vault(self, tmp_path):
        note_file = tmp_path / "notes.md"
        note_file.write_text("The marsh chapel hides the shrine entrance.", encoding="utf-8")

        settings = MagicMock()
        settings.vault_name = "Test Vault"
        settings.vault_path = tmp_path / "vault"
        settings.vault_path.mkdir()
        settings.llm_provider = "nanogpt"
        settings.nanogpt_model = "test-model"
        settings.kimi_model = None

        parsed_document = MagicMock()
        classified_document = MagicMock()
        classified_document.classification = MagicMock()

        extracted_result = MagicMock()

        with (
            patch("chronicler.cli.main.Settings", return_value=settings),
            patch("chronicler.cli.main.LLMGateway") as mock_gateway_cls,
            patch("chronicler.cli.main.parse_source_document", return_value=parsed_document),
            patch("chronicler.cli.main.classify_source_document", return_value=classified_document.classification),
            patch("chronicler.cli.main.extract_source_document", AsyncMock(return_value=extracted_result)),
            patch("chronicler.cli.main.archive_source_document") as mock_archive,
            patch("chronicler.cli.main.ObsidianCLI") as mock_obsidian_cls,
            patch("chronicler.cli.main.VaultManager") as mock_vm_cls,
        ):
            gateway = AsyncMock()
            gateway.close = AsyncMock()
            mock_gateway_cls.return_value = gateway
            mock_cli = MagicMock()
            mock_cli.get_vault_path.return_value = settings.vault_path
            mock_obsidian_cls.return_value = mock_cli
            mock_vm = MagicMock()
            mock_vm.get_context_bundle.return_value = MagicMock()
            mock_vm_cls.return_value = mock_vm

            result = asyncio.run(cli_main._run_source_ingest_pipeline([note_file], None))

        assert result is extracted_result
        mock_archive.assert_called_once_with(settings.vault_path, parsed_document)
        mock_vm.write_source_ingest_result.assert_called_once_with(extracted_result)
