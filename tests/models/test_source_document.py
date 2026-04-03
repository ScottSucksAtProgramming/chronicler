"""Tests for source-document data models."""

from pathlib import Path

import pytest

from chronicler.models import DocumentType, SourceClassification, SourceDocument


class TestSourceClassification:
    def test_create_classification(self) -> None:
        classification = SourceClassification(
            document_type=DocumentType.CAMPAIGN_BACKGROUND,
            confidence=0.92,
            session_anchor=22,
        )

        assert classification.document_type == DocumentType.CAMPAIGN_BACKGROUND
        assert classification.confidence == pytest.approx(0.92)
        assert classification.session_anchor == 22


class TestSourceDocument:
    def test_create_document_with_classification(self) -> None:
        document = SourceDocument(
            source_path=Path("Sources/notes/old-campaign-note.md"),
            original_filename="old-campaign-note.md",
            media_type="text/markdown",
            extracted_text="The note describes the hidden shrine.",
            classification=SourceClassification(
                document_type=DocumentType.LEGACY_NOTE,
                confidence=0.88,
            ),
        )

        assert document.source_path == Path("Sources/notes/old-campaign-note.md")
        assert document.original_filename == "old-campaign-note.md"
        assert document.media_type == "text/markdown"
        assert document.classification is not None
        assert document.classification.document_type == DocumentType.LEGACY_NOTE
        assert document.extracted_text == "The note describes the hidden shrine."

    def test_document_defaults_to_no_classification(self) -> None:
        document = SourceDocument(
            source_path=Path("Sources/maps/swamp-map.pdf"),
            original_filename="swamp-map.pdf",
            media_type="application/pdf",
            extracted_text=None,
        )

        assert document.classification is None
