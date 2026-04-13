"""Parse raw PLAUD transcripts into timestamped segments."""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")


@dataclass
class TimestampedSegment:
    """A chunk of transcript text with its timestamp."""

    timestamp: str
    text: str


def _split_untimestamped_text(raw_text: str) -> list[TimestampedSegment]:
    """Split untimestamped transcripts conservatively on paragraph boundaries."""
    blocks = [
        block.strip() for block in _PARAGRAPH_SPLIT_RE.split(raw_text) if block.strip()
    ]
    if not blocks:
        return []
    return [TimestampedSegment(timestamp="00:00:00", text=block) for block in blocks]


def parse_transcript(raw_text: str) -> list[TimestampedSegment]:
    """Parse a PLAUD transcript into timestamped segments."""
    raw_text = raw_text.strip()
    if not raw_text:
        return []

    matches = list(_TIMESTAMP_RE.finditer(raw_text))

    if not matches:
        segments = _split_untimestamped_text(raw_text)
        logger.info("Parsed untimestamped transcript: %d segments", len(segments))
        return segments

    segments: list[TimestampedSegment] = []
    for i, match in enumerate(matches):
        timestamp = match.group(1)
        text_start = match.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        text = raw_text[text_start:text_end].strip()
        if text:
            segments.append(TimestampedSegment(timestamp=timestamp, text=text))

    logger.info("Parsed transcript: %d segments", len(segments))
    return segments
