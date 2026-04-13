"""Conservative routing helpers for imported source documents."""

import re

from chronicler.models import DocumentType, SourceClassification, SourceDocument

_AMBIGUOUS_CONFIDENCE = 0.6
_TIMESTAMP_RE = re.compile(r"(?m)^\d{2}:\d{2}:\d{2}\s*$")


def classify_source_document(
    document: SourceDocument,
    session_override: int | None,
) -> SourceClassification:
    """Classify a parsed source document for ingest routing."""
    extracted = (document.extracted_text or "").strip().lower()
    filename = document.original_filename.lower()
    if document.media_type == "text/plain" and (
        "transcript" in filename or _TIMESTAMP_RE.search(document.extracted_text or "")
    ):
        return SourceClassification(
            document_type=DocumentType.SESSION_TRANSCRIPT,
            confidence=0.95,
            session_anchor=session_override,
        )

    if document.media_type == "application/pdf" and (
        "summary" in filename
        or ("session" in extracted and "summary" in extracted)
    ):
        return SourceClassification(
            document_type=DocumentType.SESSION_SUMMARY,
            confidence=0.85,
            session_anchor=session_override,
        )

    if not extracted or len(extracted) < 32:
        return SourceClassification(
            document_type=DocumentType.UNKNOWN,
            confidence=0.2,
            session_anchor=session_override,
        )

    return SourceClassification(
        document_type=DocumentType.LEGACY_NOTE,
        confidence=0.8,
        session_anchor=session_override,
    )


def is_ambiguous(classification: SourceClassification) -> bool:
    """Return True when ingest should stop and ask for user direction."""
    return (
        classification.document_type == DocumentType.UNKNOWN
        or classification.confidence < _AMBIGUOUS_CONFIDENCE
    )
