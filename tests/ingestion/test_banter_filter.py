"""Tests for LLM-assisted banter filtering."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from chronicler.ingestion.banter_filter import (
    filter_banter,
    BANTER_FILTER_PROMPT,
)
from chronicler.ingestion.transcript_parser import TimestampedSegment
from chronicler.models.session import TranscriptSegment

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
        assert len(BANTER_FILTER_PROMPT) > 100

    @pytest.mark.asyncio
    async def test_filter_classifies_segments(self):
        segments = [GAME_SEGMENT, BANTER_SEGMENT, FOOD_SEGMENT]

        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(
            return_value=MagicMock(
                content=json.dumps(
                    {
                        "classifications": [
                            {"index": 0, "is_in_game": True},
                            {"index": 1, "is_in_game": False},
                            {"index": 2, "is_in_game": False},
                        ]
                    }
                ),
                usage=MagicMock(total_tokens=100),
            )
        )

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
