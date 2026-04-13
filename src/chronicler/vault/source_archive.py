"""Archive imported source materials inside the vault."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from chronicler.models import SourceDocument


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def archive_source_document(vault_path: Path, document: SourceDocument) -> Path:
    """Copy an imported source and metadata into ``_Agent/Sources/``."""
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    archive_dir = (
        vault_path
        / "_Agent"
        / "Sources"
        / f"{timestamp}-{_slugify(document.original_filename)}"
    )
    archive_dir.mkdir(parents=True, exist_ok=True)

    original_target = archive_dir / document.original_filename
    original_target.write_bytes(document.source_path.read_bytes())

    if document.extracted_text:
        (archive_dir / "extracted.txt").write_text(
            document.extracted_text, encoding="utf-8"
        )

    classification_type = (
        document.classification.document_type.value
        if document.classification is not None
        else "unclassified"
    )
    confidence = (
        f"{document.classification.confidence:.2f}"
        if document.classification is not None
        else "n/a"
    )
    session_anchor = (
        str(document.classification.session_anchor)
        if document.classification
        and document.classification.session_anchor is not None
        else ""
    )
    source_attribution = document.source_attribution or ""
    metadata = "\n".join(
        [
            "---",
            "type: source-archive",
            f'original_filename: "{document.original_filename}"',
            f'media_type: "{document.media_type}"',
            f"classification: {classification_type}",
            f'confidence: "{confidence}"',
            f'session_anchor: "{session_anchor}"',
            f'source_attribution: "{source_attribution}"',
            "---",
            "",
            f"# {document.original_filename}",
            "",
            f"- Imported at: {timestamp}Z",
            f"- Classification: {classification_type}",
        ]
    )
    (archive_dir / "metadata.md").write_text(metadata, encoding="utf-8")
    return archive_dir
