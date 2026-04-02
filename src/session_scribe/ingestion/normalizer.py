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
    title = "Unknown Session"
    if parsed_pdf and parsed_pdf.title:
        title = parsed_pdf.title
    else:
        title = f"Session {session_number}"

    summary_text = parsed_pdf.full_text if parsed_pdf else None

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
        session_number, title, len(summary_text) if summary_text else 0, len(filtered_segments), in_game,
    )

    return result
