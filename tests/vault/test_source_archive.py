"""Tests for archiving imported source materials."""

from pathlib import Path

from chronicler.models import DocumentType, SourceClassification, SourceDocument
from chronicler.vault.source_archive import archive_source_document


def test_archive_source_copies_original_and_metadata(tmp_path) -> None:
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    source_file = tmp_path / "legacy_note.md"
    source_file.write_text("# Old Notes\n\nTheron mapped the marsh chapel.", encoding="utf-8")
    document = SourceDocument(
        source_path=source_file,
        original_filename="legacy_note.md",
        media_type="text/markdown",
        extracted_text="Theron mapped the marsh chapel.",
        classification=SourceClassification(
            document_type=DocumentType.LEGACY_NOTE,
            confidence=0.8,
        ),
    )

    archived_dir = archive_source_document(vault_path, document)

    assert (archived_dir / "legacy_note.md").exists()
    metadata = (archived_dir / "metadata.md").read_text(encoding="utf-8")
    assert "legacy_note" in metadata


def test_archive_source_writes_normalized_text_when_available(tmp_path) -> None:
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    source_file = tmp_path / "background.txt"
    source_file.write_text("The shrine is beneath the marsh chapel.", encoding="utf-8")
    document = SourceDocument(
        source_path=source_file,
        original_filename="background.txt",
        media_type="text/plain",
        extracted_text="The shrine is beneath the marsh chapel.",
    )

    archived_dir = archive_source_document(vault_path, document)

    normalized = archived_dir / "extracted.txt"
    assert normalized.exists()
    assert "marsh chapel" in normalized.read_text(encoding="utf-8").lower()


def test_archive_source_records_source_attribution_when_available(tmp_path) -> None:
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    source_file = tmp_path / "background.txt"
    source_file.write_text("Notes from DM Jared about the marsh chapel.", encoding="utf-8")
    document = SourceDocument(
        source_path=source_file,
        original_filename="background.txt",
        media_type="text/plain",
        extracted_text="Notes from DM Jared about the marsh chapel.",
        source_attribution="DM Jared",
    )

    archived_dir = archive_source_document(vault_path, document)

    metadata = (archived_dir / "metadata.md").read_text(encoding="utf-8")
    assert 'source_attribution: "DM Jared"' in metadata
