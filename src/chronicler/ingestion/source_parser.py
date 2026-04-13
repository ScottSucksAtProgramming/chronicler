"""Parser registry for imported source documents."""

from pathlib import Path

from chronicler.ingestion.pdf_parser import PLAUDParseError, parse_plaud_pdf
from chronicler.models import SourceDocument


class UnsupportedSourceError(Exception):
    """Raised when a file type is not supported for source ingest."""


def _parse_text_source(path: Path, media_type: str) -> SourceDocument:
    return SourceDocument(
        source_path=path,
        original_filename=path.name,
        media_type=media_type,
        extracted_text=path.read_text(encoding="utf-8"),
    )


def _parse_pdf_source(path: Path) -> SourceDocument:
    try:
        parsed = parse_plaud_pdf(path)
        extracted_text = parsed.full_text
    except PLAUDParseError:
        extracted_text = _extract_generic_pdf_text(path)

    return SourceDocument(
        source_path=path,
        original_filename=path.name,
        media_type="application/pdf",
        extracted_text=extracted_text,
    )


def _extract_generic_pdf_text(path: Path) -> str:
    """Extract text from a non-PLAUD PDF conservatively."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise UnsupportedSourceError("pdfplumber is not installed") from exc

    try:
        with pdfplumber.open(path) as pdf:
            page_texts = [text for page in pdf.pages if (text := page.extract_text())]
    except Exception as exc:
        raise UnsupportedSourceError(f"Could not parse PDF source: {path}") from exc

    if not page_texts:
        raise UnsupportedSourceError(
            f"No text could be extracted from PDF source: {path}"
        )

    return "\n".join(page_texts)


def parse_source_document(path: Path) -> SourceDocument:
    """Parse a supported source file into a normalized document."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _parse_text_source(path, "text/plain")
    if suffix == ".md":
        return _parse_text_source(path, "text/markdown")
    if suffix == ".pdf":
        return _parse_pdf_source(path)
    raise UnsupportedSourceError(f"Unsupported source type: {path.suffix or '<none>'}")
