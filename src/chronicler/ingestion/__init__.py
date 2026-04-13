"""Public API for the ingestion module."""

from chronicler.ingestion.pdf_parser import (
    parse_plaud_pdf,
    ParsedPDF,
    PDFSection,
    PLAUDParseError,
)
from chronicler.ingestion.source_classifier import (
    classify_source_document,
    is_ambiguous,
)
from chronicler.ingestion.source_parser import (
    parse_source_document,
    UnsupportedSourceError,
)
from chronicler.ingestion.transcript_parser import parse_transcript, TimestampedSegment
from chronicler.ingestion.banter_filter import filter_banter
from chronicler.ingestion.normalizer import normalize_session

__all__ = [
    "parse_plaud_pdf",
    "ParsedPDF",
    "PDFSection",
    "PLAUDParseError",
    "classify_source_document",
    "is_ambiguous",
    "parse_source_document",
    "UnsupportedSourceError",
    "parse_transcript",
    "TimestampedSegment",
    "filter_banter",
    "normalize_session",
]
