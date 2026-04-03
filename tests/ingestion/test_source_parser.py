"""Tests for source-document parsing."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from chronicler.ingestion.source_parser import (
    UnsupportedSourceError,
    parse_source_document,
)
from chronicler.ingestion.pdf_parser import PLAUDParseError


class TestParseSourceDocument:
    def test_parse_markdown_source_reads_utf8_text(self) -> None:
        note_path = Path("tests/fixtures/imports/legacy_note.md")

        document = parse_source_document(note_path)

        assert document.source_path == note_path
        assert document.original_filename == "legacy_note.md"
        assert document.media_type == "text/markdown"
        assert "hidden shrine" in (document.extracted_text or "").lower()

    def test_parse_pdf_source_uses_pdf_adapter(self, session_022_dir) -> None:
        pdf_path = session_022_dir / "summary.pdf"

        document = parse_source_document(pdf_path)

        assert document.source_path == pdf_path
        assert document.original_filename == "summary.pdf"
        assert document.media_type == "application/pdf"
        assert document.extracted_text is not None
        assert "friendly face" in document.extracted_text.lower()

    def test_parse_pdf_source_falls_back_to_generic_pdf_text(self, tmp_path, monkeypatch) -> None:
        pdf_path = tmp_path / "old-notes.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake content")

        def fake_parse_plaud_pdf(path: Path):
            raise PLAUDParseError("not a PLAUD summary")

        class FakePDF:
            pages = [
                SimpleNamespace(extract_text=lambda: "Old notes from DM Jared"),
                SimpleNamespace(extract_text=lambda: "The marsh chapel hides a shrine."),
            ]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_pdfplumber = SimpleNamespace(open=lambda path: FakePDF())

        monkeypatch.setattr("chronicler.ingestion.source_parser.parse_plaud_pdf", fake_parse_plaud_pdf)
        monkeypatch.setitem(__import__("sys").modules, "pdfplumber", fake_pdfplumber)

        document = parse_source_document(pdf_path)

        assert document.media_type == "application/pdf"
        assert "dm jared" in (document.extracted_text or "").lower()
        assert "marsh chapel" in (document.extracted_text or "").lower()

    def test_parse_source_rejects_unknown_extension(self, tmp_path) -> None:
        bad_file = tmp_path / "notes.rtf"
        bad_file.write_text("Old lore", encoding="utf-8")

        with pytest.raises(UnsupportedSourceError, match="Unsupported source type"):
            parse_source_document(bad_file)
