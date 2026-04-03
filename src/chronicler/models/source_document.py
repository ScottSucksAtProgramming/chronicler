"""Data models for imported source documents."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """High-level intent detected for an imported document."""

    SESSION_TRANSCRIPT = "session_transcript"
    SESSION_SUMMARY = "session_summary"
    SESSION_SUPPORT = "session_support"
    CAMPAIGN_BACKGROUND = "campaign_background"
    LEGACY_NOTE = "legacy_note"
    MAP_IMAGE = "map_image"
    TABLE_REFERENCE = "table_reference"
    UNKNOWN = "unknown"


class SourceClassification(BaseModel):
    """Classification assigned to an imported source document."""

    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    session_anchor: int | None = None


class SourceDocument(BaseModel):
    """Normalized representation of an imported source."""

    source_path: Path
    original_filename: str
    media_type: str
    extracted_text: str | None = None
    source_attribution: str | None = None
    classification: SourceClassification | None = None
