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
        sections=[PDFSection(title="Reconnaissance", content="The party scouted the area.")],
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
    async def test_normalize_with_pdf_and_transcript(self, sample_pdf, sample_segments):
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
    async def test_normalize_pdf_only(self, sample_pdf):
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
    async def test_normalize_transcript_only(self, sample_segments):
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
