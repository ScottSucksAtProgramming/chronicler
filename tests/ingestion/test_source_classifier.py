"""Tests for source-document classification."""

from pathlib import Path

from chronicler.ingestion.source_classifier import (
    classify_source_document,
    is_ambiguous,
)
from chronicler.models import DocumentType, SourceDocument


class TestClassifySourceDocument:
    def test_classifier_marks_timestamped_text_as_session_transcript(self) -> None:
        document = SourceDocument(
            source_path=Path("tests/fixtures/session_022/transcript.txt"),
            original_filename="transcript.txt",
            media_type="text/plain",
            extracted_text="00:00:00\nThe party enters the swamp.\n\n00:05:00\nTheron warns them away.",
        )

        classification = classify_source_document(document, session_override=None)

        assert classification.document_type == DocumentType.SESSION_TRANSCRIPT
        assert classification.confidence >= 0.9
        assert not is_ambiguous(classification)

    def test_classifier_marks_summary_pdf_as_session_summary(self) -> None:
        document = SourceDocument(
            source_path=Path("tests/fixtures/session_022/summary.pdf"),
            original_filename="session-summary.pdf",
            media_type="application/pdf",
            extracted_text="Session 22 summary. The party tracked down the Friendly Face.",
        )

        classification = classify_source_document(document, session_override=None)

        assert classification.document_type == DocumentType.SESSION_SUMMARY
        assert classification.confidence >= 0.7
        assert not is_ambiguous(classification)

    def test_classifier_marks_legacy_note_as_background(self) -> None:
        document = SourceDocument(
            source_path=Path("tests/fixtures/imports/legacy_note.md"),
            original_filename="legacy_note.md",
            media_type="text/markdown",
            extracted_text=(
                "The party learned that the hidden shrine sits beneath the marsh chapel.\n"
                "Theron warned them about the flooded tunnels."
            ),
        )

        classification = classify_source_document(document, session_override=None)

        assert classification.document_type == DocumentType.LEGACY_NOTE
        assert classification.confidence >= 0.7
        assert classification.session_anchor is None
        assert not is_ambiguous(classification)

    def test_classifier_returns_ambiguous_for_low_confidence_input(self) -> None:
        document = SourceDocument(
            source_path=Path("tests/fixtures/imports/ambiguous_note.md"),
            original_filename="ambiguous_note.md",
            media_type="text/markdown",
            extracted_text="Maybe this matters.",
        )

        classification = classify_source_document(document, session_override=None)

        assert classification.document_type == DocumentType.UNKNOWN
        assert classification.confidence < 0.6
        assert is_ambiguous(classification)

    def test_classifier_anchors_legacy_note_without_retyping_it_as_session_support(
        self,
    ) -> None:
        document = SourceDocument(
            source_path=Path("notes/background.md"),
            original_filename="background.md",
            media_type="text/markdown",
            extracted_text="General lore about the marsh cult.",
        )

        classification = classify_source_document(document, session_override=22)

        assert classification.document_type == DocumentType.LEGACY_NOTE
        assert classification.confidence >= 0.7
        assert classification.session_anchor == 22
