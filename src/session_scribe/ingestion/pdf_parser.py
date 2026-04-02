"""PLAUD PDF summary parser.

Extracts structured text from PLAUD-generated D&D session summary PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class PLAUDParseError(Exception):
    """Raised when a PLAUD PDF cannot be parsed."""


@dataclass
class PDFSection:
    """A named section extracted from a PLAUD PDF summary."""

    title: str
    content: str


@dataclass
class ParsedPDF:
    """Structured result of parsing a PLAUD PDF summary."""

    title: str | None
    sections: list[PDFSection] = field(default_factory=list)
    full_text: str = ""


def _is_section_header(line: str) -> bool:
    """Return True if a line looks like a PLAUD section header.

    PLAUD section headers are:
    - Reasonably short (under 80 characters)
    - Title-cased or ALL-CAPS
    - Do not end with punctuation like . , ; :
    - Are not blank
    - Are not action-item lines (start with [ ] or @)
    """
    line = line.strip()
    if not line:
        return False
    # Skip action-item lines
    if line.startswith("[ ]") or line.startswith("@"):
        return False
    # Must not end with sentence-ending punctuation
    if line[-1] in {".", ",", ";", ":", "?", "!"}:
        return False
    # Must be short enough to be a header
    if len(line) > 80:
        return False
    # Must have at least 2 words (to exclude stray single words)
    words = line.split()
    if len(words) < 2:
        return False
    # Must be title-cased: most words start with uppercase
    title_cased_words = sum(1 for w in words if w[0].isupper() or not w[0].isalpha())
    if title_cased_words / len(words) < 0.6:
        return False
    return True


def parse_plaud_pdf(pdf_path: Path) -> ParsedPDF:
    """Parse a PLAUD-generated PDF session summary.

    Args:
        pdf_path: Path to the PDF file to parse.

    Returns:
        A ParsedPDF with title, sections, and full_text.

    Raises:
        PLAUDParseError: If the file is not found or cannot be parsed.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise PLAUDParseError("pdfplumber is not installed") from exc

    if not pdf_path.exists():
        raise PLAUDParseError(f"PDF file not found: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise PLAUDParseError(f"PDF has no pages: {pdf_path}")

            # Collect per-page text
            page_texts: list[str] = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    page_texts.append(text)

    except PLAUDParseError:
        raise
    except Exception as exc:
        raise PLAUDParseError(f"Failed to open or read PDF: {pdf_path}: {exc}") from exc

    if not page_texts:
        raise PLAUDParseError(f"No text could be extracted from PDF: {pdf_path}")

    full_text = "\n".join(page_texts)

    # --- Extract title from the first page ---
    # PLAUD PDFs begin with the document title on page 1.
    # The first non-empty line(s) form the title.
    title: str | None = None
    first_page_lines = page_texts[0].splitlines()
    title_lines: list[str] = []
    for line in first_page_lines:
        stripped = line.strip()
        if not stripped:
            if title_lines:
                break
            continue
        title_lines.append(stripped)
        # The title ends when we see a line that looks like body text
        # (longer paragraph) or after collecting a reasonable title
        if len(stripped) > 80:
            break
        # Stop after two lines so we don't grab the whole summary
        if len(title_lines) >= 2:
            break

    if title_lines:
        title = " ".join(title_lines)

    # --- Extract sections ---
    # We scan all pages for section header lines followed by body content.
    # Section headers are identified by _is_section_header().
    sections: list[PDFSection] = []
    current_section_title: str | None = None
    current_section_lines: list[str] = []

    # We skip page 1 for section detection since it is the cover/summary page.
    all_lines: list[str] = []
    for page_text in page_texts[1:]:
        all_lines.extend(page_text.splitlines())
        all_lines.append("")  # blank line between pages

    for line in all_lines:
        stripped = line.strip()
        if _is_section_header(stripped):
            # Save the previous section if any
            if current_section_title is not None:
                sections.append(PDFSection(
                    title=current_section_title,
                    content="\n".join(current_section_lines).strip(),
                ))
            current_section_title = stripped
            current_section_lines = []
        else:
            if current_section_title is not None:
                current_section_lines.append(line)

    # Save the last open section
    if current_section_title is not None:
        sections.append(PDFSection(
            title=current_section_title,
            content="\n".join(current_section_lines).strip(),
        ))

    return ParsedPDF(title=title, sections=sections, full_text=full_text)
