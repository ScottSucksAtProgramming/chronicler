"""Tests for PLAUD PDF summary parser."""

import pytest
from pathlib import Path
from session_scribe.ingestion.pdf_parser import parse_plaud_pdf, PLAUDParseError


class TestParsePLAUDPdf:
    def test_parses_session_022_pdf(self, session_022_dir):
        pdf_path = session_022_dir / "summary.pdf"
        result = parse_plaud_pdf(pdf_path)

        assert result.title is not None
        assert "No Loose Ends" in result.title
        assert len(result.sections) > 0
        assert result.full_text is not None
        assert len(result.full_text) > 100

    def test_extracts_sections(self, session_022_dir):
        pdf_path = session_022_dir / "summary.pdf"
        result = parse_plaud_pdf(pdf_path)

        section_titles = [s.title.lower() for s in result.sections]
        assert any("reconnaissance" in t for t in section_titles)
        assert any("interrogation" in t or "confrontation" in t for t in section_titles)

    def test_extracts_full_narrative_text(self, session_022_dir):
        pdf_path = session_022_dir / "summary.pdf"
        result = parse_plaud_pdf(pdf_path)

        assert "friendly face" in result.full_text.lower()
        assert "tunnel" in result.full_text.lower()

    def test_nonexistent_file_raises(self):
        with pytest.raises(PLAUDParseError, match="not found"):
            parse_plaud_pdf(Path("/nonexistent/file.pdf"))

    def test_non_pdf_file_raises(self, tmp_path):
        bad_file = tmp_path / "not_a_pdf.pdf"
        bad_file.write_text("this is not a PDF")
        with pytest.raises(PLAUDParseError):
            parse_plaud_pdf(bad_file)
