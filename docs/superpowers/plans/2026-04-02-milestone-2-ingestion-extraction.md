# Milestone 2: Ingestion + Extraction — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse PLAUD session files (PDF summaries + raw transcripts), filter out-of-game banter, extract structured D&D entities via LLM, and evaluate extraction quality against a golden fixture.

**Architecture:** Two new modules (`ingestion/` and `extraction/`) that consume PLAUD files and produce `ExtractionResult` Pydantic models. Ingestion parses and normalizes input. Extraction uses the LLM Gateway to pull structured entities. A golden fixture from Session 22 validates extraction quality. The CLI `ingest` command is wired to the pipeline.

**Tech Stack:** pdfplumber (PDF parsing), LLM Gateway (nano-gpt.com), existing Pydantic models, pytest with golden fixtures

**Spec:** `docs/superpowers/specs/2026-04-02-session-scribe-design.md` (Sections 3, 6, 7 — Milestone 2)

**Depends on:** Milestone 1 complete (models, gateway, config, CLI stubs)

---

## File Structure

```
src/session_scribe/
  ingestion/
    __init__.py          — exports: parse_pdf, parse_transcript, filter_banter, normalize_session
    pdf_parser.py        — Parse PLAUD PDF summaries into structured text
    transcript_parser.py — Parse raw transcripts into TimestampedSegment list
    banter_filter.py     — LLM-assisted classification of in-game vs out-of-game content
    normalizer.py        — Combine PDF summary + filtered transcript → NormalizedSession
  extraction/
    __init__.py          — exports: extract_session
    extractor.py         — Main extraction: NormalizedSession + ContextBundle → ExtractionResult
    prompts.py           — All prompt templates for extraction (entity, recap, quality judge)
    quality.py           — LLM-as-judge quality evaluation + structural validation

tests/
  ingestion/
    __init__.py
    test_pdf_parser.py
    test_transcript_parser.py
    test_banter_filter.py
    test_normalizer.py
  extraction/
    __init__.py
    test_extractor.py
    test_quality.py
  fixtures/
    session_022/
      summary.pdf        — Copy of PLAUD PDF for Session 22
      transcript.txt     — Copy of PLAUD transcript for Session 22
      golden.json        — Hand-labeled expected extraction output
```

---

## Chunk 1: Golden Fixture + Ingestion Parsers

### Task 1: Set Up Golden Fixture for Session 22

**Files:**
- Create: `tests/fixtures/session_022/golden.json`
- Copy: sample PDF and transcript into `tests/fixtures/session_022/`

This is the foundation of all extraction quality testing. We hand-label what Session 22 *should* produce.

- [ ] **Step 1: Copy sample files to fixtures directory**

```bash
mkdir -p tests/fixtures/session_022
cp "04-01 Summary of the D&D Session_ \"No Loose Ends\" Investigation-Summary.pdf" tests/fixtures/session_022/summary.pdf
cp "04-01 Summary of the D&D Session_ \"No Loose Ends\" Investigation-transcript.txt" tests/fixtures/session_022/transcript.txt
```

- [ ] **Step 2: Create the golden fixture JSON**

This is the hand-labeled expected output. Based on reading the actual Session 22 PDF and transcript:

```json
{
  "session_number": 22,
  "npcs": [
    {
      "name": "The Friendly Face",
      "first_appeared": "Session-022",
      "status": "dead",
      "description": "A cult-affiliated informant who had previously escaped the party. Operated from a booby-trapped safe house. Interrogated and then assassinated by his own clone.",
      "aliases": ["the friendly face", "the big guy"],
      "affiliations": ["Sylvie's Cult"],
      "tags": ["cult", "informant"]
    },
    {
      "name": "Sylvie",
      "first_appeared": "Session-022",
      "status": "unknown",
      "description": "Leader of the cult's smuggling operation. Controls approximately 20 townsfolk.",
      "aliases": [],
      "affiliations": ["Sylvie's Cult"],
      "tags": ["cult", "leader"]
    },
    {
      "name": "Bill Tidewater",
      "first_appeared": "Session-022",
      "status": "unknown",
      "description": "Lives at the farm that serves as a processing center for the cult.",
      "aliases": [],
      "affiliations": ["Sylvie's Cult"],
      "tags": ["cult"]
    },
    {
      "name": "Pavo",
      "first_appeared": "Session-022",
      "status": "alive",
      "description": "Cook on the party's ship. Had last watch with Yisela.",
      "aliases": ["Uncle Pavo"],
      "affiliations": [],
      "tags": ["crew"]
    },
    {
      "name": "Yisela Tideborn",
      "first_appeared": "Session-022",
      "status": "alive",
      "description": "Navigator/cartographer on the party's ship. Was on deck during last watch.",
      "aliases": [],
      "affiliations": [],
      "tags": ["crew"]
    },
    {
      "name": "Lyssa",
      "first_appeared": "Session-022",
      "status": "alive",
      "description": "Someone with authority at the docks who told watchers to leave the party's boat alone.",
      "aliases": ["Lisa"],
      "affiliations": [],
      "tags": ["docks"]
    },
    {
      "name": "Santiago",
      "first_appeared": "Session-022",
      "status": "alive",
      "description": "Crew member who was bad at keeping a stealthy watch. Very obvious when trying to be covert.",
      "aliases": [],
      "affiliations": [],
      "tags": ["crew"]
    },
    {
      "name": "Quattro",
      "first_appeared": "Session-022",
      "status": "alive",
      "description": "Crew member monitoring the Mayweather from across the street. Spotted two dock hand watchers.",
      "aliases": ["Quantrill"],
      "affiliations": [],
      "tags": ["crew"]
    }
  ],
  "locations": [
    {
      "name": "The Safe House",
      "first_appeared": "Session-022",
      "description": "Single-story booby-trapped house where the Friendly Face was hiding. Ransacked interior, powder traps on windows, poison dart on interior door, rotted floor with necrotic aura, hidden trapdoor to tunnel network.",
      "aliases": ["the house"],
      "connected_to": ["Underground Tunnel Network"],
      "tags": ["cult", "trapped"]
    },
    {
      "name": "Underground Tunnel Network",
      "first_appeared": "Session-022",
      "description": "Complex network of six earthen tunnels with cold saltwater. Serves as a smuggling grid connecting multiple locations across the area.",
      "aliases": ["the tunnels", "smuggling grid"],
      "connected_to": ["City Docks", "The Farm", "Noble District Wine Cellar", "Second Safe House", "The Safe House"],
      "tags": ["cult", "smuggling"]
    },
    {
      "name": "The Mayweather",
      "first_appeared": "Session-022",
      "description": "A suspicious ship at the docks carrying strange chemicals. Being watched by dock hands and monitored by Quattro.",
      "aliases": ["the boat"],
      "connected_to": ["City Docks"],
      "tags": ["cult", "ship"]
    },
    {
      "name": "The Black Spire",
      "first_appeared": "Session-022",
      "description": "A core cult site located in the swamp. Confirmed by the informant as a place where Sylvie has been seen.",
      "aliases": [],
      "connected_to": [],
      "tags": ["cult"]
    },
    {
      "name": "The Farm",
      "first_appeared": "Session-022",
      "description": "A remote farm with a still that serves as a processing center for the cult's smuggling operation. Run by Bill Tidewater.",
      "aliases": ["the nearby farm"],
      "connected_to": ["Underground Tunnel Network"],
      "tags": ["cult", "smuggling"]
    },
    {
      "name": "Smoked Eel Tavern",
      "first_appeared": "Session-022",
      "description": "A tavern that opens mid-morning. The party needs to visit for information gathering.",
      "aliases": ["the tavern"],
      "connected_to": [],
      "tags": []
    },
    {
      "name": "City Docks",
      "first_appeared": "Session-022",
      "description": "Where the party's ship and the Mayweather are docked. One tunnel exit emerges near here with a heavy scent of gillmen.",
      "aliases": ["the docks"],
      "connected_to": ["Underground Tunnel Network", "The Mayweather"],
      "tags": []
    },
    {
      "name": "Second Safe House",
      "first_appeared": "Session-022",
      "description": "Identical to the first safe house, accessed via the shortest tunnel through a trapped hatch. Where the informant was found sleeping.",
      "aliases": [],
      "connected_to": ["Underground Tunnel Network"],
      "tags": ["cult"]
    },
    {
      "name": "The Party's Ship",
      "first_appeared": "Session-022",
      "description": "The party's own vessel, docked near the Mayweather. Crew members Pavo and Yisela keep watch.",
      "aliases": ["our ship", "the ship"],
      "connected_to": ["City Docks"],
      "tags": []
    }
  ],
  "factions": [
    {
      "name": "Sylvie's Cult",
      "first_appeared": "Session-022",
      "description": "A smuggling operation controlled by Sylvie. Involves approximately 20 townsfolk. Smuggles chemicals, soil, and sometimes sick people. Uses clones and magical traps. Has operated for at least three months.",
      "known_members": ["Sylvie", "The Friendly Face", "Bill Tidewater"],
      "aliases": ["the cult"],
      "tags": ["antagonist", "smuggling"]
    }
  ],
  "loot": [
    {
      "name": "Hallucinogen-Laced Poison",
      "found_in": "Session-022",
      "description": "Poison found on dart traps in the safe house. The same type commonly used by the cult."
    }
  ],
  "plot_threads": [
    {
      "title": "The Black Spire",
      "status": "open",
      "introduced_in": "Session-022",
      "summary": "A core cult site in the swamp. Confirmed by the informant. Party has not yet visited."
    },
    {
      "title": "The Mayweather Investigation",
      "status": "open",
      "introduced_in": "Session-022",
      "summary": "Suspicious ship carrying cult-related chemicals. Being monitored by Quattro. Dock hands also watching it."
    },
    {
      "title": "Sylvie's Smuggling Operation",
      "status": "open",
      "introduced_in": "Session-022",
      "summary": "Cult smuggling chemicals, soil, and sick people through underground tunnels. ~20 townsfolk involved. Farm serves as processing center."
    },
    {
      "title": "Cult Cloning Activities",
      "status": "open",
      "introduced_in": "Session-022",
      "summary": "The cult uses clones. The informant was killed by his own clone. Attackers who ambushed the party were likely clones too."
    },
    {
      "title": "Unexplored Tunnels",
      "status": "open",
      "introduced_in": "Session-022",
      "summary": "Two of the six tunnels were not explored. Noble district tunnel leads through magical darkness. Full network not yet mapped."
    }
  ],
  "recap": {
    "session_number": 22,
    "title": "No Loose Ends Investigation",
    "summary": "The party pursued a loose end — the 'friendly face' informant with cult connections. After finding his safe house ransacked and booby-trapped, they discovered a hidden underground tunnel network used for smuggling. Following the tunnels to a second safe house, they found and interrogated the informant, extracting critical intelligence about Sylvie's cult operations: smuggling through the tunnels, a processing center at a nearby farm, the Black Spire in the swamp, and the use of clones. The interrogation was cut short when the informant was assassinated by his own clone.",
    "key_events": [
      {"description": "Party decided to track down the 'friendly face' informant at 3 AM", "timestamp": "00:17:15"},
      {"description": "Arcane eye scouting revealed the safe house was ransacked", "timestamp": "00:21:59"},
      {"description": "Party split into two teams to breach the booby-trapped house", "timestamp": "00:31:42"},
      {"description": "Magic Mouth triggered a 7th-level Glyph of Warding fireball ambush", "timestamp": null},
      {"description": "Hidden trapdoor discovered beneath a rug, leading to underground tunnels", "timestamp": null},
      {"description": "Party explored six earthen tunnels forming a smuggling grid", "timestamp": null},
      {"description": "Informant found asleep in second safe house and interrogated", "timestamp": null},
      {"description": "Informant revealed cult details: Sylvie, the farm, the Black Spire, ~20 townsfolk", "timestamp": null},
      {"description": "Informant assassinated by his own clone via crossbow bolt to the head", "timestamp": null}
    ]
  }
}
```

- [ ] **Step 3: Create a conftest fixture to load golden data**

```python
# tests/fixtures/__init__.py
# (empty)
```

Add to `tests/conftest.py`:

```python
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def session_022_dir():
    """Path to Session 022 fixture files."""
    return FIXTURES_DIR / "session_022"


@pytest.fixture
def session_022_golden(session_022_dir):
    """Load the golden fixture for Session 022."""
    golden_path = session_022_dir / "golden.json"
    return json.loads(golden_path.read_text())
```

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/ tests/conftest.py
git commit -m "test: add Session 22 golden fixture with hand-labeled expected extraction output"
```

---

### Task 2: PDF Parser

**Files:**
- Create: `src/session_scribe/ingestion/__init__.py`
- Create: `src/session_scribe/ingestion/pdf_parser.py`
- Create: `tests/ingestion/__init__.py`
- Create: `tests/ingestion/test_pdf_parser.py`

- [ ] **Step 1: Add pdfplumber dependency**

```bash
uv add pdfplumber
```

- [ ] **Step 2: Write failing tests**

```python
# tests/ingestion/test_pdf_parser.py
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

        # Should find the major narrative sections from the PDF
        section_titles = [s.title.lower() for s in result.sections]
        assert any("reconnaissance" in t for t in section_titles)
        assert any("interrogation" in t or "confrontation" in t for t in section_titles)

    def test_extracts_full_narrative_text(self, session_022_dir):
        pdf_path = session_022_dir / "summary.pdf"
        result = parse_plaud_pdf(pdf_path)

        # Should contain key narrative elements
        assert "friendly face" in result.full_text.lower()
        assert "tunnel" in result.full_text.lower()
        assert "smuggling" in result.full_text.lower() or "cult" in result.full_text.lower()

    def test_nonexistent_file_raises(self):
        with pytest.raises(PLAUDParseError, match="not found"):
            parse_plaud_pdf(Path("/nonexistent/file.pdf"))

    def test_non_pdf_file_raises(self, tmp_path):
        bad_file = tmp_path / "not_a_pdf.pdf"
        bad_file.write_text("this is not a PDF")
        with pytest.raises(PLAUDParseError):
            parse_plaud_pdf(bad_file)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/ingestion/test_pdf_parser.py -v
```

- [ ] **Step 4: Implement PDF parser**

```python
# src/session_scribe/ingestion/pdf_parser.py
"""Parse PLAUD PDF summaries into structured text."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


class PLAUDParseError(Exception):
    """Raised when a PLAUD PDF cannot be parsed."""


@dataclass
class PDFSection:
    """A section extracted from a PLAUD PDF summary."""

    title: str
    content: str


@dataclass
class ParsedPDF:
    """Result of parsing a PLAUD PDF summary."""

    title: str | None
    sections: list[PDFSection]
    full_text: str


def parse_plaud_pdf(pdf_path: Path) -> ParsedPDF:
    """Parse a PLAUD-generated PDF summary into structured text.

    Extracts the document title, narrative sections, and full text content.
    Validates that the file exists and is a readable PDF.

    Args:
        pdf_path: Path to the PLAUD PDF summary file.

    Returns:
        ParsedPDF with title, sections, and full_text.

    Raises:
        PLAUDParseError: If the file cannot be found or parsed.
    """
    if not pdf_path.exists():
        raise PLAUDParseError(f"PDF not found: {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise PLAUDParseError(f"PDF has no pages: {pdf_path}")

            all_text_parts: list[str] = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text_parts.append(text)

            full_text = "\n\n".join(all_text_parts)

    except Exception as e:
        if isinstance(e, PLAUDParseError):
            raise
        raise PLAUDParseError(f"Failed to parse PDF: {pdf_path}: {e}") from e

    if not full_text.strip():
        raise PLAUDParseError(f"PDF contains no extractable text: {pdf_path}")

    title = _extract_title(full_text)
    sections = _extract_sections(full_text)

    logger.info(
        "Parsed PDF: title=%r, sections=%d, chars=%d",
        title,
        len(sections),
        len(full_text),
    )

    return ParsedPDF(title=title, sections=sections, full_text=full_text)


def _extract_title(text: str) -> str | None:
    """Extract the document title from the first lines of text."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        # PLAUD titles are typically the first substantial line
        if len(line) > 10 and not line.startswith("SESSION"):
            # Clean up common PLAUD artifacts
            line = re.sub(r"^\d{2}-\d{2}\s*", "", line)  # Remove date prefix like "04-01 "
            return line.strip()
    return None


def _extract_sections(text: str) -> list[PDFSection]:
    """Extract narrative sections from the PDF text.

    Looks for lines that appear to be section headers:
    - Lines that are short, title-cased, and followed by paragraph text
    - Common PLAUD section patterns
    """
    lines = text.split("\n")
    sections: list[PDFSection] = []
    current_title: str | None = None
    current_content: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _is_section_header(stripped):
            # Save previous section
            if current_title and current_content:
                sections.append(PDFSection(
                    title=current_title,
                    content="\n".join(current_content).strip(),
                ))
            current_title = stripped
            current_content = []
        elif current_title is not None:
            current_content.append(stripped)

    # Don't forget the last section
    if current_title and current_content:
        sections.append(PDFSection(
            title=current_title,
            content="\n".join(current_content).strip(),
        ))

    return sections


def _is_section_header(line: str) -> bool:
    """Heuristic: is this line likely a section header?"""
    # Too long to be a header
    if len(line) > 80:
        return False
    # Too short to be meaningful
    if len(line) < 5:
        return False
    # Looks like a title (mostly capitalized words, no trailing period)
    if line.endswith(".") or line.endswith(","):
        return False
    # Check if it's title-cased or all-caps
    words = line.split()
    capitalized = sum(1 for w in words if w[0].isupper()) if words else 0
    return capitalized >= len(words) * 0.6 and len(words) <= 10
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/ingestion/test_pdf_parser.py -v
```

Note: The heuristic section detection may need tuning based on actual test results. If the section titles aren't being detected correctly from the PLAUD PDF format, adjust `_is_section_header` based on what pdfplumber actually extracts. The key is that `full_text` is always available as fallback — sections are a bonus.

- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/ingestion/ tests/ingestion/ pyproject.toml uv.lock
git commit -m "feat: add PLAUD PDF parser with section extraction and validation"
```

---

### Task 3: Transcript Parser

**Files:**
- Create: `src/session_scribe/ingestion/transcript_parser.py`
- Create: `tests/ingestion/test_transcript_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ingestion/test_transcript_parser.py
"""Tests for raw transcript parser."""

import pytest
from session_scribe.ingestion.transcript_parser import (
    parse_transcript,
    TimestampedSegment,
)


SAMPLE_TRANSCRIPT = """00:00:00
Captain, and then you haven't gone back to see her because it is yeah.
00:00:56
I'm missing. Are there any trulies left in there?
00:01:27
Does anybody want the beer? Trevor. No, I'll FedEx it to you overnight.
"""


class TestParseTranscript:
    def test_parses_timestamped_segments(self):
        segments = parse_transcript(SAMPLE_TRANSCRIPT)
        assert len(segments) == 3
        assert segments[0].timestamp == "00:00:00"
        assert "Captain" in segments[0].text
        assert segments[1].timestamp == "00:00:56"
        assert segments[2].timestamp == "00:01:27"

    def test_segments_have_text(self):
        segments = parse_transcript(SAMPLE_TRANSCRIPT)
        for seg in segments:
            assert len(seg.text) > 0
            assert seg.text.strip() == seg.text  # no leading/trailing whitespace

    def test_empty_input(self):
        segments = parse_transcript("")
        assert segments == []

    def test_no_timestamps(self):
        segments = parse_transcript("Just some text with no timestamps at all.")
        assert len(segments) == 1
        assert segments[0].timestamp == "00:00:00"  # default timestamp

    def test_parses_real_session_022(self, session_022_dir):
        transcript_path = session_022_dir / "transcript.txt"
        text = transcript_path.read_text()
        segments = parse_transcript(text)

        # Session 22 is 3-4 hours, should have many segments
        assert len(segments) > 50

        # First segment should start at 00:00:00
        assert segments[0].timestamp == "00:00:00"

        # Should contain game content somewhere
        all_text = " ".join(s.text for s in segments)
        assert "Mayweather" in all_text

    def test_segments_are_in_order(self):
        segments = parse_transcript(SAMPLE_TRANSCRIPT)
        for i in range(len(segments) - 1):
            assert segments[i].timestamp <= segments[i + 1].timestamp
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement transcript parser**

```python
# src/session_scribe/ingestion/transcript_parser.py
"""Parse raw PLAUD transcripts into timestamped segments."""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Matches timestamps like 00:00:00, 01:23:45
_TIMESTAMP_RE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)


@dataclass
class TimestampedSegment:
    """A chunk of transcript text with its timestamp."""

    timestamp: str
    text: str


def parse_transcript(raw_text: str) -> list[TimestampedSegment]:
    """Parse a PLAUD transcript into timestamped segments.

    PLAUD transcripts alternate between timestamp lines (HH:MM:SS)
    and text blocks. This parser splits on timestamps and pairs
    each timestamp with its following text.

    Args:
        raw_text: Raw transcript text from PLAUD export.

    Returns:
        List of TimestampedSegment in chronological order.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        return []

    # Find all timestamp positions
    matches = list(_TIMESTAMP_RE.finditer(raw_text))

    if not matches:
        # No timestamps found — return entire text as a single segment
        return [TimestampedSegment(timestamp="00:00:00", text=raw_text.strip())]

    segments: list[TimestampedSegment] = []

    for i, match in enumerate(matches):
        timestamp = match.group(1)

        # Text runs from end of this timestamp line to start of next timestamp (or end of file)
        text_start = match.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)

        text = raw_text[text_start:text_end].strip()

        if text:
            segments.append(TimestampedSegment(timestamp=timestamp, text=text))

    logger.info("Parsed transcript: %d segments", len(segments))
    return segments
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/ingestion/test_transcript_parser.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/ingestion/transcript_parser.py tests/ingestion/test_transcript_parser.py
git commit -m "feat: add transcript parser for PLAUD timestamped segments"
```

---

## Chunk 2: Banter Filter + Normalizer

### Task 4: Banter Filter (LLM-Assisted)

**Files:**
- Create: `src/session_scribe/ingestion/banter_filter.py`
- Create: `tests/ingestion/test_banter_filter.py`

The banter filter classifies transcript segments as in-game or out-of-game. This is the first LLM call in the pipeline. It processes segments in batches to balance context and cost.

- [ ] **Step 1: Write failing tests**

```python
# tests/ingestion/test_banter_filter.py
"""Tests for LLM-assisted banter filtering."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from session_scribe.ingestion.banter_filter import (
    filter_banter,
    BANTER_FILTER_PROMPT,
)
from session_scribe.ingestion.transcript_parser import TimestampedSegment
from session_scribe.models.session import TranscriptSegment


GAME_SEGMENT = TimestampedSegment(
    timestamp="00:17:15",
    text="There is one thing that has been irking me. We have a ship that says no loose ends, and there is that one chap, the friendly face.",
)

BANTER_SEGMENT = TimestampedSegment(
    timestamp="00:02:00",
    text="So they, God kills all the kids. Yeah, we got to paint the blood when we go home. April first? Oh, firstborn, firstborn. Passover.",
)

FOOD_SEGMENT = TimestampedSegment(
    timestamp="00:44:55",
    text="That's burrito. Thank you. Oh, BBR, who got the BBR? We have the eco-friendly stuff. Who got empanada? I got an empanada.",
)


class TestBanterFilter:
    def test_prompt_template_exists(self):
        assert len(BANTER_FILTER_PROMPT) > 100  # Not empty/trivial

    @pytest.mark.asyncio
    async def test_filter_classifies_segments(self):
        """Test that the filter calls the LLM and produces TranscriptSegments."""
        segments = [GAME_SEGMENT, BANTER_SEGMENT, FOOD_SEGMENT]

        # Mock the LLM to return classification results
        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(return_value=MagicMock(
            content=json.dumps({
                "classifications": [
                    {"index": 0, "is_in_game": True},
                    {"index": 1, "is_in_game": False},
                    {"index": 2, "is_in_game": False},
                ]
            }),
            usage=MagicMock(total_tokens=100),
        ))

        result = await filter_banter(segments, mock_gateway, model="test-model")

        assert len(result) == 3
        assert isinstance(result[0], TranscriptSegment)
        assert result[0].is_in_game is True
        assert result[1].is_in_game is False
        assert result[2].is_in_game is False

    @pytest.mark.asyncio
    async def test_filter_handles_empty_input(self):
        mock_gateway = MagicMock()
        result = await filter_banter([], mock_gateway, model="test-model")
        assert result == []
        mock_gateway.complete.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement banter filter**

```python
# src/session_scribe/ingestion/banter_filter.py
"""LLM-assisted filtering of out-of-game banter from D&D transcripts."""

import json
import logging
from typing import TYPE_CHECKING

from session_scribe.ingestion.transcript_parser import TimestampedSegment
from session_scribe.models.session import TranscriptSegment
from session_scribe.gateway.types import LLMRequest

if TYPE_CHECKING:
    from session_scribe.gateway.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

# v1 — 2026-04-02
BANTER_FILTER_PROMPT = """You are classifying segments of a D&D tabletop RPG session transcript.

Each segment is a chunk of conversation from the table. Your job is to classify each segment as either:
- **in_game**: Content related to the D&D game — character dialogue, DM narration, combat, exploration, planning, rules discussion, dice rolls, spell descriptions, NPC interactions, plot discussion.
- **out_of_game**: Real-life conversation unrelated to the game — food orders, personal stories, discussions about real-world events, holidays, delivery logistics, unrelated jokes, meta-discussion about the recording setup.

Some segments may mix both. If a segment is MOSTLY in-game content with minor real-life asides, classify it as in_game. Only classify as out_of_game if the segment is PRIMARILY real-life conversation.

Return a JSON object with a "classifications" array. Each item has "index" (0-based) and "is_in_game" (boolean).

Example response:
```json
{"classifications": [{"index": 0, "is_in_game": true}, {"index": 1, "is_in_game": false}]}
```

Here are the segments to classify:

{segments}
"""

_BATCH_SIZE = 20  # Process this many segments per LLM call


async def filter_banter(
    segments: list[TimestampedSegment],
    gateway: "LLMGateway",
    model: str,
) -> list[TranscriptSegment]:
    """Classify transcript segments as in-game or out-of-game using the LLM.

    Processes segments in batches to manage context window and cost.

    Args:
        segments: Raw timestamped segments from the transcript parser.
        gateway: LLM Gateway for making classification calls.
        model: Model name to use for classification.

    Returns:
        List of TranscriptSegment with is_in_game set based on LLM classification.
    """
    if not segments:
        return []

    all_results: list[TranscriptSegment] = []

    for batch_start in range(0, len(segments), _BATCH_SIZE):
        batch = segments[batch_start : batch_start + _BATCH_SIZE]
        classifications = await _classify_batch(batch, gateway, model)

        for seg, is_in_game in zip(batch, classifications):
            all_results.append(TranscriptSegment(
                timestamp=seg.timestamp,
                text=seg.text,
                is_in_game=is_in_game,
            ))

    in_game_count = sum(1 for r in all_results if r.is_in_game)
    logger.info(
        "Banter filter: %d/%d segments classified as in-game",
        in_game_count,
        len(all_results),
    )

    return all_results


async def _classify_batch(
    segments: list[TimestampedSegment],
    gateway: "LLMGateway",
    model: str,
) -> list[bool]:
    """Classify a batch of segments via the LLM."""
    # Format segments for the prompt
    formatted = "\n\n".join(
        f"[Segment {i}] ({seg.timestamp})\n{seg.text}"
        for i, seg in enumerate(segments)
    )

    prompt = BANTER_FILTER_PROMPT.format(segments=formatted)

    request = LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.0,
    )

    response = await gateway.complete(request)

    try:
        content = response.content.strip()
        # Handle markdown code fences
        if content.startswith("```"):
            first_nl = content.find("\n")
            if first_nl != -1:
                content = content[first_nl + 1:]
            if content.rstrip().endswith("```"):
                content = content.rstrip().rsplit("```", 1)[0].strip()

        data = json.loads(content)
        classifications = data.get("classifications", [])

        # Build result array, defaulting to True (in-game) for missing indices
        result = [True] * len(segments)
        for item in classifications:
            idx = item.get("index", -1)
            if 0 <= idx < len(segments):
                result[idx] = item.get("is_in_game", True)

        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Banter filter LLM response parsing failed: %s. Defaulting all to in-game.", e)
        return [True] * len(segments)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/ingestion/test_banter_filter.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/ingestion/banter_filter.py tests/ingestion/test_banter_filter.py
git commit -m "feat: add LLM-assisted banter filter for transcript classification"
```

---

### Task 5: Session Normalizer

**Files:**
- Create: `src/session_scribe/ingestion/normalizer.py`
- Create: `tests/ingestion/test_normalizer.py`
- Modify: `src/session_scribe/ingestion/__init__.py` — add exports

- [ ] **Step 1: Write failing tests**

```python
# tests/ingestion/test_normalizer.py
"""Tests for session normalizer that combines PDF + transcript."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from session_scribe.ingestion.normalizer import normalize_session
from session_scribe.ingestion.pdf_parser import ParsedPDF, PDFSection
from session_scribe.ingestion.transcript_parser import TimestampedSegment
from session_scribe.models.session import NormalizedSession


@pytest.fixture
def sample_pdf():
    return ParsedPDF(
        title="No Loose Ends Investigation",
        sections=[
            PDFSection(title="Reconnaissance", content="The party scouted the area."),
        ],
        full_text="Session summary text about the investigation.",
    )


@pytest.fixture
def sample_segments():
    return [
        TimestampedSegment(timestamp="00:00:00", text="Game starts here."),
        TimestampedSegment(timestamp="00:02:00", text="Food delivery discussion."),
        TimestampedSegment(timestamp="00:05:00", text="Back to the game."),
    ]


class TestNormalizeSession:
    @pytest.mark.asyncio
    async def test_normalize_with_pdf_and_transcript(self, sample_pdf, sample_segments, settings):
        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(return_value=MagicMock(
            content='{"classifications": [{"index": 0, "is_in_game": true}, {"index": 1, "is_in_game": false}, {"index": 2, "is_in_game": true}]}',
            usage=MagicMock(total_tokens=50),
        ))

        result = await normalize_session(
            session_number=22,
            parsed_pdf=sample_pdf,
            transcript_segments=sample_segments,
            gateway=mock_gateway,
            model="test-model",
        )

        assert isinstance(result, NormalizedSession)
        assert result.session_number == 22
        assert result.title == "No Loose Ends Investigation"
        assert result.summary_text == "Session summary text about the investigation."
        assert len(result.transcript_segments) == 3
        assert result.transcript_segments[0].is_in_game is True
        assert result.transcript_segments[1].is_in_game is False

    @pytest.mark.asyncio
    async def test_normalize_pdf_only(self, sample_pdf, settings):
        result = await normalize_session(
            session_number=22,
            parsed_pdf=sample_pdf,
            transcript_segments=None,
            gateway=MagicMock(),
            model="test-model",
        )

        assert result.summary_text is not None
        assert result.transcript_segments == []

    @pytest.mark.asyncio
    async def test_normalize_transcript_only(self, sample_segments, settings):
        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(return_value=MagicMock(
            content='{"classifications": [{"index": 0, "is_in_game": true}, {"index": 1, "is_in_game": true}, {"index": 2, "is_in_game": true}]}',
            usage=MagicMock(total_tokens=50),
        ))

        result = await normalize_session(
            session_number=22,
            parsed_pdf=None,
            transcript_segments=sample_segments,
            gateway=mock_gateway,
            model="test-model",
        )

        assert result.summary_text is None
        assert len(result.transcript_segments) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement normalizer**

```python
# src/session_scribe/ingestion/normalizer.py
"""Combine parsed PDF and filtered transcript into a NormalizedSession."""

import logging
from typing import TYPE_CHECKING

from session_scribe.ingestion.banter_filter import filter_banter
from session_scribe.ingestion.pdf_parser import ParsedPDF
from session_scribe.ingestion.transcript_parser import TimestampedSegment
from session_scribe.models.session import NormalizedSession

if TYPE_CHECKING:
    from session_scribe.gateway.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


async def normalize_session(
    session_number: int,
    parsed_pdf: ParsedPDF | None,
    transcript_segments: list[TimestampedSegment] | None,
    gateway: "LLMGateway",
    model: str,
) -> NormalizedSession:
    """Combine a parsed PDF summary and transcript into a NormalizedSession.

    Either parsed_pdf or transcript_segments (or both) must be provided.

    Args:
        session_number: The session number for this recording.
        parsed_pdf: Parsed PLAUD PDF summary, or None.
        transcript_segments: Raw timestamped segments, or None.
        gateway: LLM Gateway for banter filtering.
        model: Model name for banter filtering.

    Returns:
        NormalizedSession ready for extraction.
    """
    # Extract title from PDF, or generate a default
    title = "Unknown Session"
    if parsed_pdf and parsed_pdf.title:
        title = parsed_pdf.title
    else:
        title = f"Session {session_number}"

    # Use PDF full text as summary
    summary_text = parsed_pdf.full_text if parsed_pdf else None

    # Filter transcript banter if transcript is provided
    filtered_segments = []
    if transcript_segments:
        filtered_segments = await filter_banter(transcript_segments, gateway, model)

    result = NormalizedSession(
        session_number=session_number,
        title=title,
        summary_text=summary_text,
        transcript_segments=filtered_segments,
    )

    in_game = sum(1 for s in filtered_segments if s.is_in_game)
    logger.info(
        "Normalized session %d: title=%r, summary=%d chars, segments=%d (%d in-game)",
        session_number,
        title,
        len(summary_text) if summary_text else 0,
        len(filtered_segments),
        in_game,
    )

    return result
```

- [ ] **Step 4: Update ingestion package exports**

```python
# src/session_scribe/ingestion/__init__.py
"""Public API for the ingestion module."""

from session_scribe.ingestion.pdf_parser import parse_plaud_pdf, ParsedPDF, PDFSection, PLAUDParseError
from session_scribe.ingestion.transcript_parser import parse_transcript, TimestampedSegment
from session_scribe.ingestion.banter_filter import filter_banter
from session_scribe.ingestion.normalizer import normalize_session

__all__ = [
    "parse_plaud_pdf",
    "ParsedPDF",
    "PDFSection",
    "PLAUDParseError",
    "parse_transcript",
    "TimestampedSegment",
    "filter_banter",
    "normalize_session",
]
```

- [ ] **Step 5: Run ALL tests**

```bash
uv run pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/ingestion/ tests/ingestion/
git commit -m "feat: add session normalizer combining PDF + filtered transcript into NormalizedSession"
```

---

## Chunk 3: Extraction Module

### Task 6: Extraction Prompts

**Files:**
- Create: `src/session_scribe/extraction/__init__.py`
- Create: `src/session_scribe/extraction/prompts.py`
- Create: `tests/extraction/__init__.py`
- Create: `tests/extraction/test_prompts.py`

The prompts are the core of extraction quality. These are versioned and tested for structure.

- [ ] **Step 1: Write tests for prompt templates**

```python
# tests/extraction/test_prompts.py
"""Tests for extraction prompt templates."""

from session_scribe.extraction.prompts import (
    build_extraction_prompt,
    build_recap_prompt,
    build_quality_judge_prompt,
)
from session_scribe.models.context import ContextBundle


class TestPromptTemplates:
    def test_extraction_prompt_includes_session_content(self):
        prompt = build_extraction_prompt(
            summary_text="The party explored a dungeon.",
            transcript_text="We go into the cave.",
            context=ContextBundle(session_number=5),
        )
        assert "party explored a dungeon" in prompt
        assert "cave" in prompt

    def test_extraction_prompt_includes_context(self):
        context = ContextBundle(
            session_number=5,
            known_npcs=[],
            entity_aliases={"the tavern": "Smoked Eel Tavern"},
        )
        prompt = build_extraction_prompt(
            summary_text="Session content.",
            transcript_text=None,
            context=context,
        )
        assert "Smoked Eel Tavern" in prompt

    def test_extraction_prompt_handles_no_transcript(self):
        prompt = build_extraction_prompt(
            summary_text="Summary only.",
            transcript_text=None,
            context=ContextBundle(session_number=1),
        )
        assert "Summary only" in prompt

    def test_recap_prompt_includes_content(self):
        prompt = build_recap_prompt(
            summary_text="The party fought a dragon.",
            session_number=10,
        )
        assert "dragon" in prompt
        assert "10" in prompt

    def test_quality_judge_prompt_includes_extraction(self):
        prompt = build_quality_judge_prompt(
            source_text="Original session text.",
            extraction_json='{"npcs": []}',
        )
        assert "Original session text" in prompt
        assert '{"npcs": []}' in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement prompts**

```python
# src/session_scribe/extraction/prompts.py
"""Prompt templates for entity extraction, recap generation, and quality evaluation.

All prompts are versioned. Changes are tracked in git.
"""

from session_scribe.models.context import ContextBundle


def _format_context(context: ContextBundle) -> str:
    """Format a ContextBundle into a string for inclusion in prompts."""
    parts = []

    if context.known_npcs:
        npc_list = ", ".join(
            f"{n.name} ({'/'.join(n.aliases)})" if n.aliases else n.name
            for n in context.known_npcs
        )
        parts.append(f"Known NPCs: {npc_list}")

    if context.known_locations:
        loc_list = ", ".join(n.name for n in context.known_locations)
        parts.append(f"Known Locations: {loc_list}")

    if context.known_factions:
        fac_list = ", ".join(n.name for n in context.known_factions)
        parts.append(f"Known Factions: {fac_list}")

    if context.active_threads:
        thread_list = "\n".join(f"  - {t.title}: {t.summary}" for t in context.active_threads)
        parts.append(f"Active Plot Threads:\n{thread_list}")

    if context.entity_aliases:
        alias_list = "\n".join(f'  - "{k}" → {v}' for k, v in context.entity_aliases.items())
        parts.append(f"Entity Aliases (use these to resolve ambiguous references):\n{alias_list}")

    if context.player_characters:
        pc_list = ", ".join(
            f"{pc.character_name} (played by {pc.player_name})"
            for pc in context.player_characters
        )
        parts.append(f"Player Characters (do NOT extract these as NPCs): {pc_list}")

    if context.recent_events:
        events = "\n".join(f"  - {e}" for e in context.recent_events)
        parts.append(f"Recent Events (for continuity):\n{events}")

    return "\n\n".join(parts) if parts else "No prior campaign context available."


# v1 — 2026-04-02
def build_extraction_prompt(
    summary_text: str | None,
    transcript_text: str | None,
    context: ContextBundle,
) -> str:
    """Build the entity extraction prompt."""

    context_str = _format_context(context)

    source_parts = []
    if summary_text:
        source_parts.append(f"## PLAUD Session Summary (primary source — high signal)\n\n{summary_text}")
    if transcript_text:
        source_parts.append(f"## Raw Transcript (supplementary — use to fill gaps and verify details)\n\n{transcript_text}")

    source_text = "\n\n---\n\n".join(source_parts) if source_parts else "No source text provided."

    return f"""You are extracting structured D&D campaign data from a session recording.

## Campaign Context

{context_str}

## Source Material

{source_text}

## Instructions

Extract ALL of the following from the session material. Be thorough — missing an NPC or location is worse than including a minor one.

**IMPORTANT RULES:**
- Do NOT extract player characters as NPCs. Player characters are listed in the context above.
- Do NOT extract real-world people, places, or events. Only extract in-game D&D content.
- If a name appears in the context as an existing entity, use the EXACT name from context (not a variation).
- If you're uncertain whether something is an NPC or a player character, flag it as a question.
- For the `first_appeared` field, use "Session-{session_number:03d}" format.

Return a JSON object with this exact structure:
```json
{{
  "npcs": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN",
      "status": "alive|dead|unknown",
      "description": "string",
      "aliases": ["string"],
      "affiliations": ["string"],
      "tags": ["string"],
      "key_interactions": ["string — brief summary of what this NPC did this session"]
    }}
  ],
  "locations": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN",
      "description": "string",
      "aliases": ["string"],
      "connected_to": ["string"],
      "tags": ["string"]
    }}
  ],
  "factions": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN",
      "description": "string",
      "known_members": ["string"],
      "aliases": ["string"],
      "tags": ["string"]
    }}
  ],
  "loot": [
    {{
      "name": "string",
      "found_in": "Session-NNN",
      "description": "string",
      "held_by": "string or null — who currently has this item",
      "tags": ["string"]
    }}
  ],
  "plot_threads": [
    {{
      "title": "string",
      "status": "open|closed",
      "introduced_in": "Session-NNN",
      "summary": "string"
    }}
  ],
  "questions": [
    {{
      "question": "string",
      "context": "string",
      "priority": "low|medium|high"
    }}
  ]
}}
```

Return ONLY the JSON object. No markdown formatting, no explanation."""


# v1 — 2026-04-02
def build_recap_prompt(summary_text: str, session_number: int) -> str:
    """Build the session recap generation prompt."""
    return f"""You are writing a session recap for D&D Session {session_number}.

Based on the following session summary, write a concise but complete recap that captures:
1. The main narrative arc of the session
2. Key decisions the party made
3. Important revelations or discoveries
4. How the session ended

Also identify the key events with approximate timestamps if available.

## Source Material

{summary_text}

Return a JSON object:
```json
{{
  "title": "Short session title",
  "summary": "2-4 paragraph narrative recap",
  "key_events": [
    {{"description": "What happened", "timestamp": "HH:MM:SS or null"}}
  ]
}}
```

Return ONLY the JSON object."""


# v1 — 2026-04-02
def build_quality_judge_prompt(source_text: str, extraction_json: str) -> str:
    """Build the LLM-as-judge quality evaluation prompt."""
    return f"""You are evaluating the quality of a D&D session entity extraction.

## Original Source Material

{source_text}

## Extraction Result

{extraction_json}

## Evaluation Criteria

Score each dimension from 1 (poor) to 5 (excellent):

1. **Completeness**: Did the extraction capture all NPCs, locations, factions, plot threads, and loot mentioned in the source?
2. **Accuracy**: Are the extracted names, descriptions, and relationships correct? No hallucinated details?
3. **Coherence**: Does the session recap read as a clear narrative? Would someone who wasn't there understand what happened?
4. **Relevance**: Was real-life banter correctly excluded? Only in-game D&D content extracted?
5. **Linking Quality**: Are entity names consistent? Would aliases resolve correctly? Are affiliations and connections accurate?

Return a JSON object:
```json
{{
  "completeness": 1-5,
  "accuracy": 1-5,
  "coherence": 1-5,
  "relevance": 1-5,
  "linking_quality": 1-5,
  "notes": "Brief explanation of any low scores"
}}
```

Return ONLY the JSON object."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/extraction/test_prompts.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/extraction/ tests/extraction/
git commit -m "feat: add extraction prompt templates for entities, recap, and quality judge"
```

---

### Task 7: Entity Extractor

**Files:**
- Create: `src/session_scribe/extraction/extractor.py`
- Create: `tests/extraction/test_extractor.py`

This is the core orchestrator that calls the LLM to extract entities, generate a recap, and evaluate quality.

- [ ] **Step 1: Write failing tests**

```python
# tests/extraction/test_extractor.py
"""Tests for the entity extraction orchestrator."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from session_scribe.extraction.extractor import extract_session
from session_scribe.models.session import NormalizedSession, TranscriptSegment
from session_scribe.models.context import ContextBundle
from session_scribe.models.extraction import ExtractionResult


MOCK_EXTRACTION_RESPONSE = json.dumps({
    "npcs": [
        {
            "name": "Theron",
            "first_appeared": "Session-001",
            "status": "alive",
            "description": "A ranger from the north.",
            "aliases": [],
            "affiliations": [],
            "tags": ["ranger"],
        }
    ],
    "locations": [
        {
            "name": "The Dark Forest",
            "first_appeared": "Session-001",
            "description": "A dense forest.",
            "aliases": ["dark forest"],
            "connected_to": [],
            "tags": [],
        }
    ],
    "factions": [],
    "loot": [],
    "plot_threads": [
        {
            "title": "Missing Merchant",
            "status": "open",
            "introduced_in": "Session-001",
            "summary": "A merchant went missing in the forest.",
        }
    ],
    "questions": [],
})

MOCK_RECAP_RESPONSE = json.dumps({
    "title": "Into the Dark Forest",
    "summary": "The party ventured into the forest and met Theron.",
    "key_events": [
        {"description": "Met Theron the ranger", "timestamp": "00:15:00"},
    ],
})

MOCK_QUALITY_RESPONSE = json.dumps({
    "completeness": 4,
    "accuracy": 5,
    "coherence": 4,
    "relevance": 5,
    "linking_quality": 4,
    "notes": "Good extraction.",
})


@pytest.fixture
def sample_session():
    return NormalizedSession(
        session_number=1,
        title="Test Session",
        summary_text="The party went into the dark forest and met Theron the ranger.",
        transcript_segments=[
            TranscriptSegment(timestamp="00:15:00", text="You see a ranger ahead.", is_in_game=True),
        ],
    )


@pytest.fixture
def mock_gateway():
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        side_effect=[
            # First call: entity extraction
            MagicMock(content=MOCK_EXTRACTION_RESPONSE, usage=MagicMock(total_tokens=500)),
            # Second call: recap generation
            MagicMock(content=MOCK_RECAP_RESPONSE, usage=MagicMock(total_tokens=200)),
            # Third call: quality evaluation
            MagicMock(content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)),
        ]
    )
    return gateway


class TestExtractSession:
    @pytest.mark.asyncio
    async def test_extract_produces_result(self, sample_session, mock_gateway):
        context = ContextBundle(session_number=1)
        result = await extract_session(
            session=sample_session,
            context=context,
            gateway=mock_gateway,
            model="test-model",
        )

        assert isinstance(result, ExtractionResult)
        assert result.session_number == 1
        assert len(result.npcs) == 1
        assert result.npcs[0].name == "Theron"
        assert len(result.locations) == 1
        assert len(result.plot_threads) == 1
        assert result.recap is not None
        assert result.recap.title == "Into the Dark Forest"
        assert result.quality_score is not None
        assert result.quality_score.has_failures is False

    @pytest.mark.asyncio
    async def test_extract_makes_three_llm_calls(self, sample_session, mock_gateway):
        context = ContextBundle(session_number=1)
        await extract_session(
            session=sample_session,
            context=context,
            gateway=mock_gateway,
            model="test-model",
        )
        assert mock_gateway.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_passes_context_to_prompt(self, sample_session, mock_gateway):
        context = ContextBundle(
            session_number=1,
            entity_aliases={"the forest": "The Dark Forest"},
        )
        await extract_session(
            session=sample_session,
            context=context,
            gateway=mock_gateway,
            model="test-model",
        )

        # First call should be extraction — check that context was included
        first_call_messages = mock_gateway.complete.call_args_list[0][0][0].messages
        prompt_text = first_call_messages[0]["content"]
        assert "The Dark Forest" in prompt_text
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement extractor**

```python
# src/session_scribe/extraction/extractor.py
"""Main extraction orchestrator: NormalizedSession → ExtractionResult."""

import json
import logging
from typing import TYPE_CHECKING

from session_scribe.extraction.prompts import (
    build_extraction_prompt,
    build_recap_prompt,
    build_quality_judge_prompt,
)
from session_scribe.gateway.types import LLMRequest
from session_scribe.models.context import ContextBundle
from pydantic import BaseModel, Field
from session_scribe.models.entities import NPC, Location, Faction, LootItem, PlotThread
from session_scribe.models.extraction import (
    AgentQuestion,
    ExtractionResult,
    QualityScore,
)
from session_scribe.models.session import KeyEvent, NormalizedSession, SessionRecap

if TYPE_CHECKING:
    from session_scribe.gateway.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


async def extract_session(
    session: NormalizedSession,
    context: ContextBundle,
    gateway: "LLMGateway",
    model: str,
) -> ExtractionResult:
    """Extract structured entities from a normalized session.

    Makes three LLM calls:
    1. Entity extraction (NPCs, locations, factions, loot, plot threads)
    2. Session recap generation
    3. Quality evaluation (LLM-as-judge)

    Args:
        session: The normalized session document.
        context: Campaign context for deduplication and continuity.
        gateway: LLM Gateway for making calls.
        model: Model name to use.

    Returns:
        Complete ExtractionResult with entities, recap, and quality score.
    """
    # Build transcript text from in-game segments only
    transcript_text = _build_transcript_text(session)

    # Step 1: Extract entities
    entities = await _extract_entities(
        summary_text=session.summary_text,
        transcript_text=transcript_text,
        context=context,
        gateway=gateway,
        model=model,
    )

    # Step 2: Generate recap
    recap = await _generate_recap(
        summary_text=session.summary_text or transcript_text or "",
        session_number=session.session_number,
        gateway=gateway,
        model=model,
    )

    # Step 3: Quality evaluation
    source_text = session.summary_text or transcript_text or ""
    quality_score = await _evaluate_quality(
        source_text=source_text,
        entities=entities,
        recap=recap,
        gateway=gateway,
        model=model,
    )

    return ExtractionResult(
        session_number=session.session_number,
        npcs=entities.npcs,
        locations=entities.locations,
        factions=entities.factions,
        loot=entities.loot,
        plot_threads=entities.plot_threads,
        recap=recap,
        questions=entities.questions,
        quality_score=quality_score,
    )


def _build_transcript_text(session: NormalizedSession) -> str | None:
    """Build a single text string from in-game transcript segments."""
    in_game = [s for s in session.transcript_segments if s.is_in_game]
    if not in_game:
        return None
    return "\n\n".join(f"[{s.timestamp}] {s.text}" for s in in_game)


# IMPORTANT: Do NOT duplicate _strip_code_fences here.
# Import from the gateway: from session_scribe.gateway.llm_gateway import LLMGateway
# Use: LLMGateway._strip_code_fences(response.content)
# The banter_filter.py should also use this instead of its inline implementation.


class _RawEntities(BaseModel):
    """Intermediate typed container for extracted entities before building ExtractionResult."""

    npcs: list[NPC] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    factions: list[Faction] = Field(default_factory=list)
    loot: list[LootItem] = Field(default_factory=list)
    plot_threads: list[PlotThread] = Field(default_factory=list)
    questions: list[AgentQuestion] = Field(default_factory=list)


async def _extract_entities(
    summary_text: str | None,
    transcript_text: str | None,
    context: ContextBundle,
    gateway: "LLMGateway",
    model: str,
) -> _RawEntities:
    """Extract entities via LLM and parse into typed models."""
    prompt = build_extraction_prompt(summary_text, transcript_text, context)

    response = await gateway.complete(LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.0,
    ))

    raw = json.loads(_strip_code_fences(response.content))

    result = _RawEntities(
        npcs=[NPC.model_validate(n) for n in raw.get("npcs", [])],
        locations=[Location.model_validate(l) for l in raw.get("locations", [])],
        factions=[Faction.model_validate(f) for f in raw.get("factions", [])],
        loot=[LootItem.model_validate(i) for i in raw.get("loot", [])],
        plot_threads=[PlotThread.model_validate(t) for t in raw.get("plot_threads", [])],
        questions=[AgentQuestion.model_validate(q) for q in raw.get("questions", [])],
    )

    logger.info(
        "Extracted: %d NPCs, %d locations, %d factions, %d loot, %d threads, %d questions",
        len(result.npcs), len(result.locations), len(result.factions),
        len(result.loot), len(result.plot_threads), len(result.questions),
    )

    return result


async def _generate_recap(
    summary_text: str,
    session_number: int,
    gateway: "LLMGateway",
    model: str,
) -> SessionRecap:
    """Generate a session recap via LLM."""
    prompt = build_recap_prompt(summary_text, session_number)

    response = await gateway.complete(LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.0,
    ))

    raw = json.loads(_strip_code_fences(response.content))

    return SessionRecap(
        session_number=session_number,
        title=raw.get("title", f"Session {session_number}"),
        summary=raw.get("summary", ""),
        key_events=[
            KeyEvent(
                description=e.get("description", ""),
                timestamp=e.get("timestamp"),
            )
            for e in raw.get("key_events", [])
        ],
    )


async def _evaluate_quality(
    source_text: str,
    entities: _RawEntities,
    recap: SessionRecap,
    gateway: "LLMGateway",
    model: str,
) -> QualityScore | None:
    """Evaluate extraction quality using LLM-as-judge."""
    try:
        # Serialize the extraction for the judge
        extraction_json = json.dumps({
            "npcs": [n.model_dump() for n in entities.npcs],
            "locations": [l.model_dump() for l in entities.locations],
            "factions": [f.model_dump() for f in entities.factions],
            "plot_threads": [t.model_dump() for t in entities.plot_threads],
            "recap": recap.model_dump(),
        }, indent=2)

        prompt = build_quality_judge_prompt(source_text, extraction_json)

        response = await gateway.complete(LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.0,
        ))

        raw = json.loads(_strip_code_fences(response.content))

        return QualityScore(
            completeness=raw.get("completeness", 3),
            accuracy=raw.get("accuracy", 3),
            coherence=raw.get("coherence", 3),
            relevance=raw.get("relevance", 3),
            linking_quality=raw.get("linking_quality", 3),
        )

    except Exception as e:
        logger.warning("Quality evaluation failed: %s. Skipping.", e)
        return None
```

- [ ] **Step 4: Update extraction package exports**

```python
# src/session_scribe/extraction/__init__.py
"""Public API for the extraction module."""

from session_scribe.extraction.extractor import extract_session

__all__ = ["extract_session"]
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/extraction/ -v
```

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -v
```

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/extraction/ tests/extraction/
git commit -m "feat: add entity extraction orchestrator with LLM calls for entities, recap, and quality eval"
```

---

## Chunk 4: CLI Wiring + Eval Harness + User-Style Testing

### Task 8: Wire CLI Ingest Command

**Files:**
- Modify: `src/session_scribe/cli/main.py` — wire `ingest` command to the pipeline
- Create: `tests/cli/test_ingest.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/cli/test_ingest.py
"""Tests for the ingest CLI command (integration-level)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestIngestCommand:
    def test_ingest_with_nonexistent_file(self):
        result = runner.invoke(app, ["ingest", "nonexistent.pdf"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_ingest_shows_processing_message(self, session_022_dir):
        """Ingest should at least attempt to process real files."""
        pdf_path = str(session_022_dir / "summary.pdf")
        # This will fail at the LLM call stage since no real API,
        # but should get past file validation
        with patch("session_scribe.cli.main._run_ingest_pipeline") as mock_pipeline:
            mock_pipeline.return_value = None
            result = runner.invoke(app, ["ingest", pdf_path, "--session", "22"])
            assert result.exit_code == 0 or mock_pipeline.called
```

- [ ] **Step 2: Implement the wired ingest command**

Update `src/session_scribe/cli/main.py` — replace the `ingest` command stub with a real implementation that:
1. Validates files exist and are the right types (.pdf, .txt)
2. Parses PDF and transcript
3. Calls `normalize_session`
4. Calls `extract_session`
5. Prints a summary of what was extracted

The full pipeline call should be in a separate function `_run_ingest_pipeline` that can be mocked in tests. For now, wrap it in a `try/except` that catches errors gracefully and prints them.

The ingest command should work like:
```bash
scribe ingest summary.pdf transcript.txt --session 22
scribe ingest summary.pdf --session 22  # PDF only
scribe ingest transcript.txt --session 22  # transcript only
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/cli/ -v
```

- [ ] **Step 4: Commit**

```bash
git add src/session_scribe/cli/ tests/cli/
git commit -m "feat: wire ingest CLI command to ingestion + extraction pipeline"
```

---

### Task 9: Eval Harness

**Files:**
- Create: `tests/extraction/test_golden_eval.py`

This is the golden fixture evaluation — compare extraction output against hand-labeled expected results. These tests are marked as `integration` since they require an LLM API call.

- [ ] **Step 1: Write eval tests**

```python
# tests/extraction/test_golden_eval.py
"""Golden fixture evaluation tests for extraction quality.

These tests call the real LLM API and compare extraction results
against hand-labeled expected output. They are slow and costly,
so they're marked as integration tests.

Run with: pytest -m integration tests/extraction/test_golden_eval.py -v
"""

import json
import pytest

from session_scribe.ingestion import parse_plaud_pdf, parse_transcript
from session_scribe.ingestion.normalizer import normalize_session
from session_scribe.extraction import extract_session
from session_scribe.models.context import ContextBundle
from session_scribe.gateway.llm_gateway import LLMGateway
from session_scribe.config.settings import Settings


def _precision_recall(extracted_names: set[str], expected_names: set[str]) -> tuple[float, float]:
    """Compute precision and recall between extracted and expected name sets."""
    if not extracted_names:
        return 0.0, 0.0
    if not expected_names:
        return 0.0 if extracted_names else 1.0, 1.0

    # Fuzzy matching: lowercased containment
    extracted_lower = {n.lower() for n in extracted_names}
    expected_lower = {n.lower() for n in expected_names}

    true_positives = extracted_lower & expected_lower
    precision = len(true_positives) / len(extracted_lower) if extracted_lower else 0.0
    recall = len(true_positives) / len(expected_lower) if expected_lower else 0.0
    return precision, recall


@pytest.fixture(scope="module")
def _extraction_result_cache():
    """Module-scoped cache to avoid re-running the pipeline for each test."""
    return {"result": None}


@pytest.fixture
async def extraction_result(session_022_dir, _extraction_result_cache):
    """Run extraction once and cache the result across all tests in this class.

    This avoids making 12+ LLM API calls (4 tests x 3 calls each).
    """
    if _extraction_result_cache["result"] is None:
        settings = Settings()
        gateway = LLMGateway(settings)

        try:
            pdf = parse_plaud_pdf(session_022_dir / "summary.pdf")
            transcript_segs = parse_transcript(
                (session_022_dir / "transcript.txt").read_text()
            )

            normalized = await normalize_session(
                session_number=22,
                parsed_pdf=pdf,
                transcript_segments=transcript_segs,
                gateway=gateway,
                model=settings.nanogpt_model,
            )

            context = ContextBundle(session_number=22)
            _extraction_result_cache["result"] = await extract_session(
                session=normalized,
                context=context,
                gateway=gateway,
                model=settings.nanogpt_model,
            )
        finally:
            await gateway.close()

    return _extraction_result_cache["result"]


@pytest.mark.integration
class TestGoldenEval:
    """Evaluate extraction against the Session 22 golden fixture.

    These tests require:
    - A valid SCRIBE_NANOGPT_API_KEY in .env
    - Network access to nano-gpt.com

    The extraction pipeline runs ONCE and results are shared across all tests.
    """

    @pytest.mark.asyncio
    async def test_extraction_npc_recall(self, extraction_result, session_022_golden):
        """Are we finding all the NPCs we should?"""
        golden_npcs = {npc["name"].lower() for npc in session_022_golden["npcs"]}
        extracted_npcs = {npc.name.lower() for npc in extraction_result.npcs}

        _, recall = _precision_recall(extracted_npcs, golden_npcs)
        print(f"\nNPC Recall: {recall:.1%}")
        print(f"  Extracted: {sorted(extracted_npcs)}")
        print(f"  Expected:  {sorted(golden_npcs)}")
        print(f"  Missing:   {sorted(golden_npcs - extracted_npcs)}")
        print(f"  Extra:     {sorted(extracted_npcs - golden_npcs)}")

        assert recall >= 0.5, f"NPC recall too low: {recall:.1%}"

    @pytest.mark.asyncio
    async def test_extraction_location_recall(self, extraction_result, session_022_golden):
        """Are we finding all the locations we should?"""
        golden_locs = {loc["name"].lower() for loc in session_022_golden["locations"]}
        extracted_locs = {loc.name.lower() for loc in extraction_result.locations}

        _, recall = _precision_recall(extracted_locs, golden_locs)
        print(f"\nLocation Recall: {recall:.1%}")
        print(f"  Missing: {sorted(golden_locs - extracted_locs)}")

        assert recall >= 0.5, f"Location recall too low: {recall:.1%}"

    @pytest.mark.asyncio
    async def test_extraction_has_recap(self, extraction_result):
        """Does it produce a reasonable recap?"""
        assert extraction_result.recap is not None
        assert len(extraction_result.recap.summary) > 100
        assert len(extraction_result.recap.key_events) >= 3

    @pytest.mark.asyncio
    async def test_quality_score_above_threshold(self, extraction_result):
        """Does the LLM-as-judge rate it acceptably?"""
        if extraction_result.quality_score:
            print(f"\nQuality: {extraction_result.quality_score.model_dump()}")
            assert not extraction_result.quality_score.has_failures, (
                f"Quality failures: {extraction_result.quality_score.failed_dimensions}"
            )
```

- [ ] **Step 2: Verify non-integration tests still pass**

```bash
uv run pytest -v -m "not integration"
```

- [ ] **Step 3: Commit**

```bash
git add tests/extraction/test_golden_eval.py
git commit -m "test: add golden fixture eval harness for extraction quality measurement"
```

---

### Task 10: User-Style Testing

Execute manually after all code is complete. Not automated.

- [ ] **Story 1:** "I run `scribe ingest summary.pdf transcript.txt --session 22` — does it process without errors?"

- [ ] **Story 2:** "I give it just a PDF with no transcript — does it handle that gracefully?"

- [ ] **Story 3:** "I give it just a transcript with no PDF — does it handle that gracefully?"

- [ ] **Story 4:** "I give it a corrupted or non-PDF file — does it fail with a clear message?"

- [ ] **Story 5:** "I look at the extracted entities — are they accurate? Are the NPCs real NPCs and not players? Are the locations real locations and not real-world references? Did it filter out the food delivery conversation?"

- [ ] **Story 6:** "I look at the flagged questions — are they reasonable?"

- [ ] **Story 7:** "I look at the session recap — does it capture the key beats? Would I know what happened?"

- [ ] **Story 8:** "I run the golden eval tests — `uv run pytest -m integration tests/extraction/test_golden_eval.py -v -s` — do they pass?"

Document all issues, fix them, re-test.

---

## Summary

After completing all tasks, the project has:

- **Ingestion module:** PDF parser (pdfplumber), transcript parser, LLM banter filter, session normalizer
- **Extraction module:** Entity extractor with three LLM calls (entities, recap, quality judge), versioned prompts
- **Golden fixture:** Hand-labeled Session 22 expected output
- **Eval harness:** Precision/recall metrics against golden fixture
- **CLI wired:** `scribe ingest` processes real files end-to-end
- **User-style testing:** Manual QA on real session data
